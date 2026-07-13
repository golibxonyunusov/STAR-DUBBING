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
        [KeyboardButton(text="🔭 Qidirish"), KeyboardButton(text="🌌 Barcha animelar")],
        [KeyboardButton(text="🪐 Janrlar"), KeyboardButton(text="👑 VIP")],
        [KeyboardButton(text="🏆 TOP"), KeyboardButton(text="🧑\u200d🚀 Profil")],
        [KeyboardButton(text="✨ Bot haqida")],
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)


def admin_menu_kb() -> ReplyKeyboardMarkup:
    kb = [
        [KeyboardButton(text="➕ Anime qo'shish"), KeyboardButton(text="🎬 Epizod qo'shish")],
        [KeyboardButton(text="🔗 Epizodni saytga bog'lash"), KeyboardButton(text="🗑 Anime o'chirish")],
        [KeyboardButton(text="📊 Statistika"), KeyboardButton(text="📢 Xabar yuborish")],
        [KeyboardButton(text="📡 Kanal sozlash"), KeyboardButton(text="👑 VIP boshqarish")],
        [KeyboardButton(text="🔒 Anime VIP qilish")],
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
        lock = "🔒 " if a["vip_only"] else ""
        rows.append([InlineKeyboardButton(text=f"{lock}#{a['id']} {a['title']}", callback_data=f"anime_{a['id']}")])

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

def anime_card_kb(anime_id, episodes_count, avg_rating=0.0, votes=0):
    rows = [[InlineKeyboardButton(text=f"🎬 Epizodlar ({episodes_count})", callback_data=f"episodes_{anime_id}_0")]]
    rating_label = f"⭐ Baholash ({avg_rating}/5, {votes} ovoz)" if votes else "⭐ Baho berish"
    rows.append([InlineKeyboardButton(text=rating_label, callback_data=f"ratemenu_{anime_id}")])
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


# ---------- PROFIL ----------

def profile_kb() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text="✏️ Ismni o'zgartirish", callback_data="profile_edit_name")],
        [InlineKeyboardButton(text="🌐 Saytda profilni ochish", callback_data="profile_web_login")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def web_login_kb(url: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🌐 Profilga kirish", url=url)]])


# ---------- ADMIN: anime tanlash (epizod qo'shish uchun) ----------

def choose_anime_kb(anime_rows, action="pickanime"):
    rows = [[InlineKeyboardButton(text=a["title"], callback_data=f"{action}_{a['id']}")] for a in anime_rows]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def confirm_kb(yes_cb, no_cb):
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Ha", callback_data=yes_cb),
        InlineKeyboardButton(text="❌ Yo'q", callback_data=no_cb),
    ]])


# ---------- VIP ----------

def vip_admin_menu_kb():
    rows = [
        [InlineKeyboardButton(text="➕ VIP berish", callback_data="vip_grant")],
        [InlineKeyboardButton(text="➖ VIP olib tashlash", callback_data="vip_remove")],
        [InlineKeyboardButton(text="📋 VIP foydalanuvchilar", callback_data="vip_list")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def vip_duration_kb():
    rows = [
        [
            InlineKeyboardButton(text="7 kun", callback_data="vipdays_7"),
            InlineKeyboardButton(text="30 kun", callback_data="vipdays_30"),
        ],
        [
            InlineKeyboardButton(text="90 kun", callback_data="vipdays_90"),
            InlineKeyboardButton(text="♾ Umrbod", callback_data="vipdays_0"),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def anime_vip_toggle_kb(anime_id, is_vip_only):
    if is_vip_only:
        btn = InlineKeyboardButton(text="🔓 VIP belgisini olib tashlash", callback_data=f"vipanime_off_{anime_id}")
    else:
        btn = InlineKeyboardButton(text="🔒 VIP-only qilish", callback_data=f"vipanime_on_{anime_id}")
    return InlineKeyboardMarkup(inline_keyboard=[[btn]])


# ---------- TOP / REYTING / DUBLYAJLAR ----------

def top_menu_kb() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text="🎁 Oylik g'oliblar", callback_data="monthlywinners")],
        [InlineKeyboardButton(text="👤 Top foydalanuvchilar", callback_data="topusers")],
        [InlineKeyboardButton(text="🌟 Top animelar", callback_data="topanime")],
        [InlineKeyboardButton(text="🎙 Top dublyajlar", callback_data="topdubs_0")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def rating_stars_kb(prefix: str, target_id: int) -> InlineKeyboardMarkup:
    """1 dan 5 gacha yulduz tanlash tugmalari. callback_data: '{prefix}_{target_id}_{n}'."""
    buttons = [
        InlineKeyboardButton(text="⭐" * n, callback_data=f"{prefix}_{target_id}_{n}")
        for n in range(1, 6)
    ]
    return InlineKeyboardMarkup(inline_keyboard=[buttons[:3], buttons[3:]])


def top_anime_kb(rows) -> InlineKeyboardMarkup:
    kb_rows = []
    for a in rows:
        avg = round(a["avg_rating"], 1) if a["avg_rating"] else 0.0
        kb_rows.append([InlineKeyboardButton(
            text=f"⭐{avg} ({a['votes']}) — {a['title']}",
            callback_data=f"anime_{a['id']}",
        )])
    return InlineKeyboardMarkup(inline_keyboard=kb_rows)


def top_dubs_kb(rows, offset, total) -> InlineKeyboardMarkup:
    kb_rows = [[InlineKeyboardButton(text="🎙 Dublyaj yuklash", callback_data="dubsubmit_start")]]
    for d in rows:
        avg = round(d["avg_rating"], 1) if d["avg_rating"] else 0.0
        title = d["anime_title"] or "Noma'lum"
        kb_rows.append([InlineKeyboardButton(
            text=f"⭐{avg} ({d['votes']}) — {title}",
            callback_data=f"dubview_{d['id']}",
        )])
    nav = []
    if offset > 0:
        nav.append(InlineKeyboardButton(text="⬅️", callback_data=f"topdubs_{max(offset - PAGE_SIZE, 0)}"))
    if offset + PAGE_SIZE < total:
        nav.append(InlineKeyboardButton(text="➡️", callback_data=f"topdubs_{offset + PAGE_SIZE}"))
    if nav:
        kb_rows.append(nav)
    return InlineKeyboardMarkup(inline_keyboard=kb_rows)


def dub_view_kb(dub_id) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text=f"{'⭐' * n} baho berish", callback_data=f"ratedub_{dub_id}_{n}")] for n in range(1, 6)]
    rows.append([InlineKeyboardButton(text="⬅️ Ro'yxatga qaytish", callback_data="topdubs_0")])
    return InlineKeyboardMarkup(inline_keyboard=rows)