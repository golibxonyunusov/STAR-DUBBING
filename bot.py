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

    # BIR MARTALIK TOZALASH: Render Environment bo'limida CLEAR_ASSET_CACHE=1
    # qo'shilgan bo'lsa, eski (endi yaroqsiz) keshlangan rasm file_id lari
    # bazadan o'chiriladi -- shunda bot ularni qaytadan lokal fayldan yuklab,
    # YANGI (joriy tokenga mos) file_id saqlaydi. Muammo hal bo'lgach, bu
    # o'zgaruvchini Render Environment'dan o'chirib qo'yish tavsiya etiladi
    # (majburiy emas -- qoldirilsa ham zarar keltirmaydi, faqat har safar
    # ishga tushganda keraksiz DELETE so'rovi bajariladi).
    if os.getenv("CLEAR_ASSET_CACHE") == "1":
        try:
            from database import get_client
            client = get_client()
            await client.execute("DELETE FROM bot_assets")
            logging.info("✅ [CLEAR_ASSET_CACHE] bot_assets jadvali tozalandi.")
        except Exception:
            logging.exception("❌ [CLEAR_ASSET_CACHE] bot_assets tozalanmadi:")

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