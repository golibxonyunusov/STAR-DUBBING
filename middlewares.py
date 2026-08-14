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


class ChatLogMiddleware(BaseMiddleware):
    """Har bir oddiy foydalanuvchi (admin emas) botga yozgan xabarni
    message_log jadvaliga saqlaydi -- bot ichidagi admin panelda ham,
    veb-saytdagi /panel bo'limida ham "yozishganlar tarixi" shu orqali
    ko'rsatiladi. Rasm/video/ovoz kabi matnsiz xabarlar uchun turini
    ko'rsatuvchi qisqa yorliq saqlanadi (masalan "📷 Rasm")."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        if isinstance(event, Message):
            user = data.get("event_from_user")
            if user and user.id not in ADMIN_IDS:
                content = event.text or event.caption
                if not content:
                    if event.photo:
                        content = "📷 Rasm"
                    elif event.video:
                        content = "🎬 Video"
                    elif event.voice:
                        content = "🎙 Ovozli xabar"
                    elif event.video_note:
                        content = "⭕ Video xabar"
                    elif event.document:
                        content = "📎 Fayl"
                    elif event.sticker:
                        content = "🩷 Stiker"
                    else:
                        content = "· xabar"
                try:
                    await db.log_message(user.id, "in", content)
                except Exception:
                    pass  # loglash xatosi asosiy funksiyani to'xtatmasligi kerak

        return await handler(event, data)