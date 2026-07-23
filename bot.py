import asyncio
import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiohttp import web

from config import BOT_TOKEN
from database import init_db
from handlers import admin, user
import web as website
import monthly_rewards
import safe_photo_patch


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

    # MUHIM: admin router birinchi ulanadi, aks holda foydalanuvchi
    # qidiruv handleri (har qanday matn) admin FSM xabarlarini "yeb qo'yadi".
    dp.include_router(admin.router)
    dp.include_router(user.router)

    await start_web_server(bot)

    asyncio.create_task(monthly_rewards.monthly_rewards_loop(bot))

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())