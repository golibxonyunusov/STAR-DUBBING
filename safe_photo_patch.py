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

    # MUHIM: handlers/user.py da "send_section_photo = send_cached_photo" kabi
    # bitta ORIGINAL funksiyaga bir nechta nom (alias) berilgan bo'lishi mumkin.
    # Bunday aliaslar modul yuklanganda funksiya OBYEKTINING o'ziga bog'lanadi,
    # shuning uchun keyinroq faqat "send_cached_photo" nomini almashtirish
    # boshqa aliaslarni (masalan send_section_photo) tuzatmaydi -- ular hamon
    # eski, patchlanmagan funksiyaga ishora qilib qolaveradi. Shu sabab BARCHA
    # nomlarni topib, bir xil xavfsiz versiya bilan almashtiramiz.
    original_func = user_module.send_cached_photo
    alias_names = [
        name for name, value in vars(user_module).items()
        if callable(value) and value is original_func
    ]
    if "send_cached_photo" not in alias_names:
        alias_names.append("send_cached_photo")

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

    for name in alias_names:
        setattr(user_module, name, safe_send_cached_photo)
    logging.info(
        f"[safe_photo_patch] Xavfsiz versiya bilan almashtirildi: {', '.join(alias_names)}"
    )


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

    for fn_name in ("set_asset_file_id", "set_asset", "set_bot_asset", "save_asset", "update_asset", "cache_asset"):
        fn = getattr(db, fn_name, None)
        if callable(fn):
            try:
                await fn(key, new_file_id)
                logging.info(f"[safe_photo_patch] Yangi file_id '{key}' uchun saqlandi ({fn_name}).")
            except Exception as e:
                logging.warning(f"[safe_photo_patch] {fn_name} orqali saqlash muvaffaqiyatsiz: {e}")
            return