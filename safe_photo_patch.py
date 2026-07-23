"""Bot tokeni almashtirilganda eski Telegram file_id lar yaroqsiz bo'lib
qoladi (file_id har doim ma'lum bir botga bog'liq). Bu modul ORIGINAL
handlers/user.py faylga tegmasdan, uning `send_cached_photo` funksiyasini
ishga tushish vaqtida "o'raydi" (monkeypatch): agar keshlangan file_id
Telegram tomonidan rad etilsa (TelegramBadRequest), avtomatik ravishda
LOKAL fayldan (masalan WELCOME_IMAGE_PATH) qayta yuklaydi -- shunda bot
hech qachon shu xato tufayli "yiqilib" qolmaydi.

ISHLATISH:
1) Bu faylni asosiy loyihaga qo'shing (masalan `safe_photo_patch.py` nomi
   bilan, `bot.py` bilan bir papkaga).
2) `bot.py` faylining eng yuqorisiga, boshqa importlardan keyin, quyidagi
   ikki qatorni qo'shing:

       import safe_photo_patch
       safe_photo_patch.apply()

   Buni dispatcher/routerlar ishga tushishidan OLDIN chaqiring (masalan
   `async def main():` ichida `await init_db()` dan keyin, `dp.include_router`
   dan oldin -- yoki oddiygina faylning eng boshida, import qatorlari orasida).
"""

import logging

from aiogram.exceptions import TelegramBadRequest
from aiogram.types import FSInputFile


def apply():
    """handlers.user modulidagi send_cached_photo funksiyasini xavfsiz
    versiyasi bilan almashtiradi."""
    try:
        import handlers.user as user_module
    except Exception as e:
        logging.error(f"[safe_photo_patch] handlers.user import qilinmadi: {e}")
        return

    if not hasattr(user_module, "send_cached_photo"):
        logging.error(
            "[safe_photo_patch] handlers.user ichida send_cached_photo topilmadi -- "
            "patch qo'llanmadi (funksiya nomi boshqacha bo'lishi mumkin)."
        )
        return

    original_func = user_module.send_cached_photo

    async def safe_send_cached_photo(message, key, path, caption, reply_markup=None):
        try:
            return await original_func(message, key, path, caption, reply_markup=reply_markup)
        except TelegramBadRequest as e:
            logging.warning(
                f"[safe_photo_patch] Keshlangan rasm ('{key}') yaroqsiz "
                f"({e}) -- lokal fayldan qayta yuklanmoqda: {path}"
            )
            try:
                sent = await message.answer_photo(
                    photo=FSInputFile(path),
                    caption=caption,
                    reply_markup=reply_markup,
                )
                # Yangi (to'g'ri) file_id ni bazaga qayta yozishga urinib ko'ramiz,
                # agar mos funksiya mavjud bo'lsa (nomi loyihada har xil bo'lishi mumkin).
                await _try_update_cached_asset(key, sent)
                return sent
            except Exception as inner_e:
                logging.exception(
                    f"[safe_photo_patch] Zaxira yuklash ham muvaffaqiyatsiz "
                    f"tugadi ({path}): {inner_e}"
                )
                # Rasmsiz bo'lsa ham, foydalanuvchi kamida matnli javob olsin.
                return await message.answer(caption, reply_markup=reply_markup)

    user_module.send_cached_photo = safe_send_cached_photo
    logging.info("[safe_photo_patch] send_cached_photo xavfsiz versiya bilan almashtirildi.")


async def _try_update_cached_asset(key: str, sent_message):
    """Yangi file_id ni bazaga yozishga harakat qiladi (funksiya nomi
    loyihada boshqacha bo'lsa, jim tarzda o'tkazib yuboradi -- bu ixtiyoriy
    optimallashtirish, asosiy muammoni hal qilish uchun shart emas)."""
    try:
        import database as db
    except Exception:
        return

    new_file_id = None
    if getattr(sent_message, "photo", None):
        new_file_id = sent_message.photo[-1].file_id
    if not new_file_id:
        return

    for fn_name in ("set_asset", "set_bot_asset", "save_asset", "update_asset", "cache_asset"):
        fn = getattr(db, fn_name, None)
        if callable(fn):
            try:
                await fn(key, new_file_id)
                logging.info(f"[safe_photo_patch] Yangi file_id '{key}' uchun saqlandi ({fn_name}).")
            except Exception as e:
                logging.warning(f"[safe_photo_patch] {fn_name} orqali saqlash muvaffaqiyatsiz: {e}")
            return
