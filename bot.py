import asyncio
import logging
import os

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ChatType, ParseMode
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.types import Message
from aiohttp import web

from config import BOT_TOKEN, ADMIN_IDS
from database import init_db
from handlers import admin, user
import database as db
import web as website
import monthly_rewards
import safe_photo_patch


async def _log_incoming_message(message: Message):
    """Foydalanuvchining botga yozgan xabarini chat_messages jadvaliga
    saqlaydi (admin panel suhbat tarixi uchun)."""
    try:
        if message.chat.type != ChatType.PRIVATE:
            return
        user_id = message.from_user.id if message.from_user else None
        if not user_id or user_id in ADMIN_IDS:
            return
        text = (message.text or message.caption or "").strip()
        if text:
            await db.save_chat_message(user_id, "user", text)
    except Exception:
        logging.exception("Chat xabarini DB ga yozishda xato")


async def chat_log_middleware(handler, event, data):
    """Har bir kiruvchi foydalanuvchi xabaridan keyin uni DB ga yozadi."""
    await _log_incoming_message(event)
    return await handler(event, data)


def _patch_bot_send_logging(bot: Bot):
    """Bot orqali yuborilgan javoblarni chat_messages jadvaliga saqlaydi
    (faqat shaxsiy chatlar, ya'ni chat_id > 0 bo'lsa).

    Admin panelidan yuborilgan xabarlar web.py da '_skip_chat_log=True'
    bilan chaqiriladi -- ular bu yerda saqlanmaydi, chunki web.py ularni
    'admin' sifatida alohida saqlaydi (aks holda ikki marta yozilib
    qolardi)."""

    def make_wrapper(original):
        async def wrapper(*args, **kwargs):
            skip = kwargs.pop("_skip_chat_log", False)
            result = await original(*args, **kwargs)
            try:
                if skip:
                    return result
                chat_id = args[0] if args else kwargs.get("chat_id")
                if not isinstance(chat_id, int) or chat_id <= 0:
                    return result  # kanal / guruh / noma'lum chat
                text = ""
                if isinstance(result, list):  # send_media_group kabi
                    for m in result:
                        if m and (m.text or m.caption):
                            text = text or (m.text or m.caption)
                elif result and (result.text or result.caption):
                    text = result.text or result.caption
                text = (text or "").strip()
                if text:
                    await db.save_chat_message(chat_id, "bot", text)
            except Exception:
                logging.exception("Bot javobini DB ga yozishda xato")
            return result
        return wrapper

    for method_name in (
        "send_message", "send_photo", "send_video", "send_animation",
        "send_audio", "send_document", "send_voice", "send_media_group",
    ):
        original = getattr(bot, method_name)
        setattr(bot, method_name, make_wrapper(original))


async def start_web_server(bot: Bot):
    # Render.com PORT o'zgaruvchisini avtomatik beradi. Agar mavjud bo'lmasa
    # (masalan lokal kompyuterda ishga tushirilsa), sayt/keep-alive server
    # ishga tushmaydi -- botga hech qanday ta'sir qilmaydi.
    port = os.getenv("PORT")
    logging.info(f"PORT muhit o'zgaruvchisi: {port!r}")

    if not port:
        logging.warning("PORT topilmadi -- veb-sayt ishga tushmaydi.")
        return

    try:
        app = website.create_app(bot)
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, host="0.0.0.0", port=int(port))
        await site.start()
        logging.info(f"✅ Veb-sayt 0.0.0.0:{port} portida ishga tushdi")
    except Exception:
        logging.exception("❌ Veb-sayt ishga tushmadi:")


def register_maintenance_commands(dp: Dispatcher):
    """Render Shell'ga kirmasdan, botning o'zi orqali (faqat adminlar uchun)
    texnik xizmat buyruqlarini bajarish imkonini beradi."""

    @dp.message(Command("clearcache"), F.from_user.id.in_(ADMIN_IDS))
    async def clear_asset_cache(message: Message):
        try:
            client = db.get_client()
            await client.execute("DELETE FROM bot_assets")
            await message.answer(
                "✅ bot_assets jadvali tozalandi. Endi rasmlar qaytadan "
                "lokal fayldan yuklanib, yangi file_id saqlanadi."
            )
            logging.info("[clearcache] bot_assets admin buyrug'i orqali tozalandi.")
        except Exception as e:
            await message.answer(f"⚠️ Xatolik: {e}")
            logging.exception("[clearcache] Xatolik:")

    @dp.message(Command("checkfiles"), F.from_user.id.in_(ADMIN_IDS))
    async def check_broken_files(message: Message, bot: Bot):
        """Barcha anime posterlari va epizod videolarini tekshiradi (bot.get_file
        orqali) va qaysi file_id lar yaroqsiz (masalan eski bot tokeniga tegishli)
        ekanini ro'yxat qilib beradi -- shunda birma-bir bosib tekshirish shart emas."""
        await message.answer("🔎 Tekshirilmoqda, biroz kuting...")

        broken = []
        total_checked = 0

        try:
            total = await db.count_anime()
            anime_rows = await db.list_anime(offset=0, limit=max(total, 1))
        except Exception as e:
            await message.answer(f"⚠️ Animelar ro'yxatini olishda xatolik: {e}")
            return

        for anime in anime_rows:
            anime_id = anime["id"]
            title = anime["title"]

            poster_id = anime["poster_file_id"]
            if poster_id:
                total_checked += 1
                try:
                    await bot.get_file(poster_id)
                except TelegramBadRequest:
                    broken.append(f"🖼 #{anime_id} \"{title}\" -- POSTER buzilgan")
                await asyncio.sleep(0.05)

            try:
                episodes = await db.get_episodes(anime_id)
            except Exception:
                episodes = []

            for ep in episodes:
                total_checked += 1
                try:
                    await bot.get_file(ep["file_id"])
                except TelegramBadRequest:
                    broken.append(
                        f"🎬 #{anime_id} \"{title}\" -- {ep['episode_number']}-qism VIDEO buzilgan"
                    )
                await asyncio.sleep(0.05)

        if not broken:
            await message.answer(
                f"✅ Tekshiruv tugadi ({total_checked} ta fayl). Buzilgan fayl topilmadi!"
            )
            return

        header = f"⚠️ Tekshiruv tugadi ({total_checked} ta fayldan {len(broken)} tasi buzilgan):\n\n"
        body = "\n".join(broken)
        full_text = header + body

        # Telegram xabar uzunligi cheklangan (4096 belgi) -- kerak bo'lsa bo'lib yuboramiz.
        for i in range(0, len(full_text), 3500):
            await message.answer(full_text[i:i + 3500])

        logging.info(f"[checkfiles] {len(broken)} ta buzilgan fayl topildi.")


async def main():
    logging.basicConfig(level=logging.INFO)

    if not BOT_TOKEN or BOT_TOKEN == "PUT_YOUR_BOT_TOKEN_HERE":
        raise RuntimeError(
            "BOT_TOKEN sozlanmagan! .env faylida BOT_TOKEN=... qiymatini kiriting."
        )

    await init_db()

    # Eski bot tokeniga tegishli file_id lar yaroqsiz bo'lib qolgan bo'lsa,
    # avtomatik ravishda lokal fayldan qayta yuklaydi (bot yiqilib qolmasin
    # uchun). Bu router'lar ulanishidan OLDIN chaqirilishi kerak.
    safe_photo_patch.apply()

    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()

    # ---- Chat tarixini saqlash ----
    # Foydalanuvchining yozgan xabarlari va botning javoblari chat_messages
    # jadvaliga yoziladi -- admin panelda har bir foydalanuvchi yonida shu
    # suhbat ko'rinishida ko'rsatiladi.
    dp.message.outer_middleware(chat_log_middleware)
    _patch_bot_send_logging(bot)

    # Texnik xizmat buyruqlari (masalan /clearcache) -- eng birinchi ulanadi.
    register_maintenance_commands(dp)

    # MUHIM: admin router birinchi ulanadi, aks holda foydalanuvchi
    # qidiruv handleri (har qanday matn) admin FSM xabarlarini "yeb qo'yadi".
    dp.include_router(admin.router)
    dp.include_router(user.router)

    await start_web_server(bot)

    asyncio.create_task(monthly_rewards.monthly_rewards_loop(bot))

    # MUHIM: drop_pending_updates=False -- aks holda, bot Render'da "uxlab
    # qolgan" (spin-down) paytda kelgan xabarlar (masalan /start) bot
    # uyg'ongach BUTUNLAY o'chirilib, hech qanday javob berilmay qoladi.
    await bot.delete_webhook(drop_pending_updates=False)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())