import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import BOT_TOKEN
from database import init_db
from handlers import admin, user


async def main():
    logging.basicConfig(level=logging.INFO)

    if not BOT_TOKEN or BOT_TOKEN == "PUT_YOUR_BOT_TOKEN_HERE":
        raise RuntimeError(
            "BOT_TOKEN sozlanmagan! .env faylida BOT_TOKEN=... qiymatini kiriting."
        )

    await init_db()

    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()

    # MUHIM: admin router birinchi ulanadi, aks holda foydalanuvchi
    # qidiruv handleri (har qanday matn) admin FSM xabarlarini "yeb qo'yadi".
    dp.include_router(admin.router)
    dp.include_router(user.router)

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
