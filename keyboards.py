from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
from config import PAGE_SIZE

# ---------- REPLY (asosiy menyu) ----------

def main_menu_kb() -> ReplyKeyboardMarkup:
    kb = [
        [KeyboardButton(text="🔍 Qidirish"), KeyboardButton(text="📚 Barcha animelar")],
        [KeyboardButton(text="🎭 Janrlar"), KeyboardButton(text="ℹ️ Bot haqida")],
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)


def admin_menu_kb() -> ReplyKeyboardMarkup:
    kb = [
        [KeyboardButton(text="➕ Anime qo'shish"), KeyboardButton(text="🎬 Epizod qo'shish")],
        [KeyboardButton(text="🗑 Anime o'chirish"), KeyboardButton(text="📊 Statistika")],
        [KeyboardButton(text="📢 Xabar yuborish"), KeyboardButton(text="📡 Kanal sozlash")],
        [KeyboardButton(text="⬅️ Foydalanuvchi menyusi")],
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)


# ---------- SUBSCRIBE CHECK ----------

def subscribe_kb(channels) -> InlineKeyboardMarkup:
    rows = []
    for ch in channels:
        link = ch["invite_link"] or f"https://t.me/{str(ch['chat_id']).lstrip('@')}"
        rows.append([InlineKeyboardButton(text=f"➕ {ch['title']}", url=link)])
    rows.append([InlineKeyboardButton(text="✅ Tekshirish", callback_data="check_sub")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


# ---------- ANIME LIST ----------

def anime_list_kb(anime_rows, offset, total, genre=None):
    rows = []
    for a in anime_rows:
        rows.append([InlineKeyboardButton(text=f"#{a['id']} {a['title']}", callback_data=f"anime_{a['id']}")])

    nav = []
    prefix = f"listg_{genre}" if genre else "list"
    if offset > 0:
        nav.append(InlineKeyboardButton(text="⬅️", callback_data=f"{prefix}_{max(offset - PAGE_SIZE, 0)}"))
    if offset + PAGE_SIZE < total:
        nav.append(InlineKeyboardButton(text="➡️", callback_data=f"{prefix}_{offset + PAGE_SIZE}"))
    if nav:
        rows.append(nav)

    return InlineKeyboardMarkup(inline_keyboard=rows)


def genres_kb(genres):
    rows = []
    row = []
    for i, g in enumerate(genres, 1):
        row.append(InlineKeyboardButton(text=g, callback_data=f"genre_{g}"))
        if i % 2 == 0:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    return InlineKeyboardMarkup(inline_keyboard=rows)


# ---------- ANIME CARD ----------

def anime_card_kb(anime_id, episodes_count):
    rows = [[InlineKeyboardButton(text=f"🎬 Epizodlar ({episodes_count})", callback_data=f"episodes_{anime_id}_0")]]
    rows.append([InlineKeyboardButton(text="⬅️ Ortga", callback_data="back_to_list")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def episodes_list_kb(anime_id, episodes, offset, total):
    rows = []
    row = []
    for i, ep in enumerate(episodes, 1):
        row.append(InlineKeyboardButton(text=str(ep["episode_number"]), callback_data=f"ep_{anime_id}_{ep['episode_number']}"))
        if i % 5 == 0:
            rows.append(row)
            row = []
    if row:
        rows.append(row)

    nav = []
    if offset > 0:
        nav.append(InlineKeyboardButton(text="⬅️", callback_data=f"episodes_{anime_id}_{max(offset - PAGE_SIZE, 0)}"))
    if offset + PAGE_SIZE < total:
        nav.append(InlineKeyboardButton(text="➡️", callback_data=f"episodes_{anime_id}_{offset + PAGE_SIZE}"))
    if nav:
        rows.append(nav)

    rows.append([InlineKeyboardButton(text="⬅️ Anime sahifasiga", callback_data=f"anime_{anime_id}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def episode_nav_kb(anime_id, episode_number, has_prev, has_next):
    row = []
    if has_prev:
        row.append(InlineKeyboardButton(text="⬅️ Oldingi", callback_data=f"ep_{anime_id}_{episode_number - 1}"))
    if has_next:
        row.append(InlineKeyboardButton(text="Keyingi ➡️", callback_data=f"ep_{anime_id}_{episode_number + 1}"))
    rows = [row] if row else []
    rows.append([InlineKeyboardButton(text="📋 Epizodlar ro'yxati", callback_data=f"episodes_{anime_id}_0")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


# ---------- ADMIN: anime tanlash (epizod qo'shish uchun) ----------

def choose_anime_kb(anime_rows, action="pickanime"):
    rows = [[InlineKeyboardButton(text=a["title"], callback_data=f"{action}_{a['id']}")] for a in anime_rows]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def confirm_kb(yes_cb, no_cb):
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Ha", callback_data=yes_cb),
        InlineKeyboardButton(text="❌ Yo'q", callback_data=no_cb),
    ]])
