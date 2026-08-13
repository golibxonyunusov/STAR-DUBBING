from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

import database as db
from config import ADMIN_IDS


class BlockCheckMiddleware(BaseMiddleware):
    """Admin panelidan bloklangan foydalanuvchilarning xabarlari va tugma
    bosishlari botga umuman yetib bormasligini ta'minlaydi.
    Adminlar (ADMIN_IDS) hech qachon bloklanmaydi -- ular har doim o'tadi."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        user = data.get("event_from_user")

        if user and user.id not in ADMIN_IDS:
            if await db.is_user_blocked(user.id):
                if isinstance(event, CallbackQuery):
                    await event.answer("🚫 Siz botdan foydalanishdan bloklangansiz.", show_alert=True)
                # Oddiy xabarlarga (Message) jim javob bermaymiz -- bloklangan
                # foydalanuvchi buni sezmasligi kerak.
                return None

        return await handler(event, data)