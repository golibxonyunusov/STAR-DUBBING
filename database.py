import secrets
from datetime import datetime, timedelta

import libsql_client

from config import DB_PATH, TURSO_DATABASE_URL, TURSO_AUTH_TOKEN

CREATE_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    full_name TEXT,
    joined_at TEXT
);

CREATE TABLE IF NOT EXISTS anime (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT,
    poster_file_id TEXT,
    genre TEXT,
    year TEXT,
    status TEXT DEFAULT 'davom etmoqda',
    created_at TEXT
);

CREATE TABLE IF NOT EXISTS episodes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    anime_id INTEGER NOT NULL,
    episode_number INTEGER NOT NULL,
    file_id TEXT NOT NULL,
    added_at TEXT,
    FOREIGN KEY (anime_id) REFERENCES anime (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS required_channels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id TEXT NOT NULL,
    title TEXT,
    invite_link TEXT
);

CREATE TABLE IF NOT EXISTS vip_users (
    user_id INTEGER PRIMARY KEY,
    granted_at TEXT,
    expires_at TEXT
);

CREATE TABLE IF NOT EXISTS user_settings (
    user_id INTEGER PRIMARY KEY,
    display_name TEXT,
    theme TEXT DEFAULT 'dark',
    notifications_enabled INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS login_tokens (
    token TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL,
    created_at TEXT,
    expires_at TEXT,
    used INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS sessions (
    session_id TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL,
    created_at TEXT,
    expires_at TEXT
);

CREATE TABLE IF NOT EXISTS bot_assets (
    key TEXT PRIMARY KEY,
    file_id TEXT NOT NULL
);
"""


# ---------- ULANISH (Turso / libSQL) ----------
# TURSO_DATABASE_URL va TURSO_AUTH_TOKEN .env faylida berilgan bo'lsa,
# bulutdagi Turso bazasiga ulanamiz -- Render qayta ishga tushsa ham
# ma'lumotlar YO'QOLMAYDI, chunki baza endi Render'ning vaqtinchalik
# diskida emas, Turso'ning doimiy serverida saqlanadi.
#
# Agar ular berilmagan bo'lsa (masalan lokal kompyuteringizda sinov uchun),
# oddiy mahalliy faylga (DB_PATH) yozamiz -- xuddi avvalgidek ishlaydi,
# internetga ulanish shart emas.
_client: libsql_client.Client | None = None


def _resolve_url() -> str:
    if TURSO_DATABASE_URL:
        return TURSO_DATABASE_URL
    return f"file:{DB_PATH}"


def get_client() -> libsql_client.Client:
    global _client
    if _client is None:
        _client = libsql_client.create_client(
            url=_resolve_url(),
            auth_token=TURSO_AUTH_TOKEN or None,
        )
    return _client


async def close_db():
    """Ixtiyoriy: bot to'xtaganda ulanishni toza yopish uchun (bot.py da chaqirish mumkin)."""
    global _client
    if _client is not None:
        await _client.close()
        _client = None


async def init_db():
    client = get_client()
    statements = [s.strip() for s in CREATE_TABLES_SQL.split(";") if s.strip()]
    await client.batch(statements)

    # Eski bazalarda "anime" jadvalida vip_only ustuni bo'lmasligi mumkin --
    # xavfsiz migratsiya (xato chiqsa e'tibor bermaymiz, demak ustun allaqachon bor).
    try:
        await client.execute("ALTER TABLE anime ADD COLUMN vip_only INTEGER DEFAULT 0")
    except Exception:
        pass
    # Eski bazalarda "episodes" jadvalida public_msg_id ustuni bo'lmasligi mumkin --
    # bu ustun videoni OCHIQ kanaldagi mos postining xabar ID'sini saqlaydi
    # (eski usul -- Telegram widget orqali ko'rsatish uchun ishlatilgan edi,
    # endi ishlatilmaydi, lekin eski bazalar bilan moslik uchun qoldirilgan).
    try:
        await client.execute("ALTER TABLE episodes ADD COLUMN public_msg_id INTEGER")
    except Exception:
        pass
    # web_video_url -- saytda to'g'ridan-to'g'ri ko'rsatiladigan video havolasi
    # (masalan, .mp4 to'g'ridan-to'g'ri havolasi yoki boshqa hostingdagi link).
    # Bu Telegram file_id'dan MUSTAQIL: botda video file_id orqali, saytda esa
    # shu alohida havola orqali ko'rsatiladi -- shu sababli saytda Telegram
    # kanali hech qanday ko'rinishda ko'rinmaydi.
    try:
        await client.execute("ALTER TABLE episodes ADD COLUMN web_video_url TEXT")
    except Exception:
        pass


# ---------- USERS ----------

async def add_user(user_id: int, username: str, full_name: str):
    client = get_client()
    await client.execute(
        "INSERT OR IGNORE INTO users (user_id, username, full_name, joined_at) VALUES (?, ?, ?, ?)",
        (user_id, username, full_name, datetime.utcnow().isoformat()),
    )


async def get_users_count() -> int:
    client = get_client()
    rs = await client.execute("SELECT COUNT(*) FROM users")
    return rs.rows[0][0] if rs.rows else 0


async def get_all_user_ids() -> list[int]:
    client = get_client()
    rs = await client.execute("SELECT user_id FROM users")
    return [r[0] for r in rs.rows]


async def get_notifiable_user_ids() -> list[int]:
    """Bildirishnomani o'chirmagan foydalanuvchilar ro'yxati (broadcast uchun).
    user_settings jadvalida yozuvi bo'lmagan foydalanuvchilar ham kiradi --
    ular hali sozlamani o'zgartirmagan, demak standart holat: yoqilgan."""
    client = get_client()
    rs = await client.execute(
        """
        SELECT u.user_id FROM users u
        LEFT JOIN user_settings s ON u.user_id = s.user_id
        WHERE s.notifications_enabled IS NULL OR s.notifications_enabled = 1
        """
    )
    return [r[0] for r in rs.rows]


async def get_user(user_id: int):
    client = get_client()
    rs = await client.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    return rs.rows[0] if rs.rows else None


# ---------- ANIME ----------

async def add_anime(title, description, poster_file_id, genre, year, vip_only: bool = False) -> int:
    client = get_client()
    rs = await client.execute(
        "INSERT INTO anime (title, description, poster_file_id, genre, year, created_at, vip_only) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (title, description, poster_file_id, genre, year, datetime.utcnow().isoformat(), int(vip_only)),
    )
    return rs.last_insert_rowid


async def get_anime(anime_id: int):
    client = get_client()
    rs = await client.execute("SELECT * FROM anime WHERE id = ?", (anime_id,))
    return rs.rows[0] if rs.rows else None


async def delete_anime(anime_id: int):
    client = get_client()
    await client.execute("DELETE FROM episodes WHERE anime_id = ?", (anime_id,))
    await client.execute("DELETE FROM anime WHERE id = ?", (anime_id,))


def _normalize_search_text(text: str) -> str:
    """Qidiruvni ishonchli qilish uchun: kichik harfga o'tkazish, turli xil
    apostrof belgilarini ("'" ’ ‘ `) bittasiga tenglashtirish va LIKE'ning
    maxsus belgilarini (% _) ekranlash, aks holda foydalanuvchi ularni
    yozsa qidiruv kutilmagan natija berishi mumkin."""
    text = text.strip().lower()
    for ch in ("’", "‘", "`", "´"):
        text = text.replace(ch, "'")
    # LIKE uchun maxsus belgilarni ekranlaymiz (escape belgisi: \)
    text = text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return text


async def search_anime(query: str, limit: int = 20):
    """Anime nomi bo'yicha qidiradi -- nomning istalgan qismi (boshida,
    o'rtasida yoki oxirida) mos kelsa ham anime topiladi. Katta/kichik harf
    va apostrof turi (' ’ ‘) farq qilmaydi."""
    normalized = _normalize_search_text(query)
    client = get_client()
    rs = await client.execute(
        """
        SELECT * FROM (
            SELECT *,
                REPLACE(REPLACE(REPLACE(LOWER(title), '’', ''''), '‘', ''''), '`', '''')
                    AS _norm_title
            FROM anime
        )
        WHERE _norm_title LIKE ? ESCAPE '\\'
        ORDER BY
            CASE WHEN _norm_title LIKE ? ESCAPE '\\' THEN 0 ELSE 1 END,
            id DESC
        LIMIT ?
        """,
        (f"%{normalized}%", f"{normalized}%", limit),
    )
    return rs.rows


async def list_anime(offset: int = 0, limit: int = 8, genre: str | None = None):
    client = get_client()
    if genre:
        rs = await client.execute(
            "SELECT * FROM anime WHERE genre LIKE ? ORDER BY id DESC LIMIT ? OFFSET ?",
            (f"%{genre}%", limit, offset),
        )
    else:
        rs = await client.execute(
            "SELECT * FROM anime ORDER BY id DESC LIMIT ? OFFSET ?", (limit, offset)
        )
    return rs.rows


async def count_anime(genre: str | None = None) -> int:
    client = get_client()
    if genre:
        rs = await client.execute("SELECT COUNT(*) FROM anime WHERE genre LIKE ?", (f"%{genre}%",))
    else:
        rs = await client.execute("SELECT COUNT(*) FROM anime")
    return rs.rows[0][0] if rs.rows else 0


async def get_all_genres() -> list[str]:
    client = get_client()
    rs = await client.execute("SELECT DISTINCT genre FROM anime WHERE genre IS NOT NULL AND genre != ''")
    genres = set()
    for r in rs.rows:
        for g in r[0].split(","):
            g = g.strip()
            if g:
                genres.add(g)
    return sorted(genres)


# ---------- EPISODES ----------

async def add_episode(anime_id: int, episode_number: int, file_id: str) -> int:
    client = get_client()
    rs = await client.execute(
        "INSERT INTO episodes (anime_id, episode_number, file_id, added_at) VALUES (?, ?, ?, ?)",
        (anime_id, episode_number, file_id, datetime.utcnow().isoformat()),
    )
    return rs.last_insert_rowid


async def get_episodes(anime_id: int):
    client = get_client()
    rs = await client.execute(
        "SELECT * FROM episodes WHERE anime_id = ? ORDER BY episode_number ASC",
        (anime_id,),
    )
    return rs.rows


async def get_episode_by_number(anime_id: int, number: int):
    client = get_client()
    rs = await client.execute(
        "SELECT * FROM episodes WHERE anime_id = ? AND episode_number = ?",
        (anime_id, number),
    )
    return rs.rows[0] if rs.rows else None


async def get_episodes_count(anime_id: int) -> int:
    client = get_client()
    rs = await client.execute("SELECT COUNT(*) FROM episodes WHERE anime_id = ?", (anime_id,))
    return rs.rows[0][0] if rs.rows else 0


async def delete_episode(episode_id: int):
    client = get_client()
    await client.execute("DELETE FROM episodes WHERE id = ?", (episode_id,))


async def set_episode_public_msg(episode_id: int, public_msg_id: int | None):
    """Eski usul (endi ishlatilmaydi) -- moslik uchun qoldirilgan."""
    client = get_client()
    await client.execute(
        "UPDATE episodes SET public_msg_id = ? WHERE id = ?", (public_msg_id, episode_id)
    )


async def set_episode_web_video(episode_id: int, web_video_url: str | None):
    """Epizodning sayt uchun to'g'ridan-to'g'ri video havolasini saqlaydi.
    Bu Telegram file_id'dan mustaqil -- sayt shu havoladan foydalanadi,
    bot esa file_id orqali (Telegram ichida) videoni yuboradi."""
    client = get_client()
    await client.execute(
        "UPDATE episodes SET web_video_url = ? WHERE id = ?", (web_video_url, episode_id)
    )


# ---------- REQUIRED CHANNELS (majburiy obuna) ----------

async def add_required_channel(chat_id: str, title: str, invite_link: str = ""):
    client = get_client()
    await client.execute(
        "INSERT INTO required_channels (chat_id, title, invite_link) VALUES (?, ?, ?)",
        (chat_id, title, invite_link),
    )


async def remove_required_channel(row_id: int):
    client = get_client()
    await client.execute("DELETE FROM required_channels WHERE id = ?", (row_id,))


async def get_required_channels():
    client = get_client()
    rs = await client.execute("SELECT * FROM required_channels")
    return rs.rows


# ---------- VIP FOYDALANUVCHILAR ----------

async def grant_vip(user_id: int, days: int | None):
    """days=None -> umrbod VIP. days=30 -> 30 kunlik VIP (mavjud VIP bo'lsa yangilanadi)."""
    expires_at = None
    if days is not None:
        expires_at = (datetime.utcnow() + timedelta(days=days)).isoformat()

    client = get_client()
    await client.execute(
        "INSERT INTO vip_users (user_id, granted_at, expires_at) VALUES (?, ?, ?) "
        "ON CONFLICT(user_id) DO UPDATE SET granted_at=excluded.granted_at, expires_at=excluded.expires_at",
        (user_id, datetime.utcnow().isoformat(), expires_at),
    )


async def remove_vip(user_id: int):
    client = get_client()
    await client.execute("DELETE FROM vip_users WHERE user_id = ?", (user_id,))


async def get_vip(user_id: int):
    """VIP ma'lumotini qaytaradi. Muddati o'tgan bo'lsa avtomatik o'chirib, None qaytaradi."""
    client = get_client()
    rs = await client.execute("SELECT * FROM vip_users WHERE user_id = ?", (user_id,))
    if not rs.rows:
        return None
    row = rs.rows[0]
    if row["expires_at"]:
        if datetime.fromisoformat(row["expires_at"]) < datetime.utcnow():
            await client.execute("DELETE FROM vip_users WHERE user_id = ?", (user_id,))
            return None
    return row


async def is_vip(user_id: int) -> bool:
    return await get_vip(user_id) is not None


async def list_vip_users():
    client = get_client()
    rs = await client.execute("SELECT * FROM vip_users ORDER BY granted_at DESC")
    return rs.rows


async def set_anime_vip(anime_id: int, vip_only: bool):
    client = get_client()
    await client.execute(
        "UPDATE anime SET vip_only = ? WHERE id = ?", (int(vip_only), anime_id)
    )


# ---------- FOYDALANUVCHI SOZLAMALARI / PROFIL ----------

async def get_user_settings(user_id: int):
    """Foydalanuvchi sozlamalarini qaytaradi, agar hali mavjud bo'lmasa
    standart qiymatlar bilan yaratadi (theme=dark, notifications=yoqilgan)."""
    client = get_client()
    rs = await client.execute("SELECT * FROM user_settings WHERE user_id = ?", (user_id,))
    if rs.rows:
        return rs.rows[0]
    await client.execute(
        "INSERT INTO user_settings (user_id, theme, notifications_enabled) VALUES (?, 'dark', 1)",
        (user_id,),
    )
    rs = await client.execute("SELECT * FROM user_settings WHERE user_id = ?", (user_id,))
    return rs.rows[0] if rs.rows else None


async def update_user_settings(user_id: int, display_name: str = None, theme: str = None,
                                notifications_enabled: bool = None):
    """Faqat berilgan (None bo'lmagan) maydonlarni yangilaydi."""
    await get_user_settings(user_id)  # qatorni mavjud qilib qo'yish uchun
    fields, values = [], []
    if display_name is not None:
        fields.append("display_name = ?")
        values.append(display_name)
    if theme is not None:
        fields.append("theme = ?")
        values.append(theme)
    if notifications_enabled is not None:
        fields.append("notifications_enabled = ?")
        values.append(int(notifications_enabled))
    if not fields:
        return
    values.append(user_id)
    client = get_client()
    await client.execute(f"UPDATE user_settings SET {', '.join(fields)} WHERE user_id = ?", values)


# ---------- VEB-PROFILGA KIRISH (magic-link login) ----------

async def create_login_token(user_id: int, ttl_minutes: int = 10) -> str:
    """Bot orqali yuboriladigan bir martalik kirish tokenini yaratadi."""
    token = secrets.token_urlsafe(24)
    now = datetime.utcnow()
    expires_at = (now + timedelta(minutes=ttl_minutes)).isoformat()
    client = get_client()
    await client.execute(
        "INSERT INTO login_tokens (token, user_id, created_at, expires_at, used) VALUES (?, ?, ?, ?, 0)",
        (token, user_id, now.isoformat(), expires_at),
    )
    return token


async def consume_login_token(token: str) -> int | None:
    """Tokenni bir marta ishlatib, foydalanuvchi ID'sini qaytaradi.
    Muddati o'tgan yoki avval ishlatilgan bo'lsa None qaytaradi."""
    client = get_client()
    rs = await client.execute("SELECT * FROM login_tokens WHERE token = ?", (token,))
    if not rs.rows:
        return None
    row = rs.rows[0]
    if row["used"]:
        return None
    if datetime.fromisoformat(row["expires_at"]) < datetime.utcnow():
        return None
    await client.execute("UPDATE login_tokens SET used = 1 WHERE token = ?", (token,))
    return row["user_id"]


async def create_session(user_id: int, ttl_days: int = 30) -> str:
    session_id = secrets.token_urlsafe(32)
    now = datetime.utcnow()
    expires_at = (now + timedelta(days=ttl_days)).isoformat()
    client = get_client()
    await client.execute(
        "INSERT INTO sessions (session_id, user_id, created_at, expires_at) VALUES (?, ?, ?, ?)",
        (session_id, user_id, now.isoformat(), expires_at),
    )
    return session_id


async def get_session_user_id(session_id: str) -> int | None:
    if not session_id:
        return None
    client = get_client()
    rs = await client.execute("SELECT * FROM sessions WHERE session_id = ?", (session_id,))
    if not rs.rows:
        return None
    row = rs.rows[0]
    if datetime.fromisoformat(row["expires_at"]) < datetime.utcnow():
        await client.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
        return None
    return row["user_id"]


async def delete_session(session_id: str):
    client = get_client()
    await client.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))


# ---------- BOT ASSETS (rasm file_id keshi) ----------
# Xush kelibsiz/Qidirish/Barcha animelar/Janrlar/Profil/VIP rasmlarining
# Telegram file_id'lari shu yerda saqlanadi -- shunda bot qayta ishga
# tushganda ham rasm qayta yuklanmaydi, faqat file_id orqali darhol
# yuboriladi (tez).

async def get_asset_file_id(key: str) -> str | None:
    client = get_client()
    rs = await client.execute("SELECT file_id FROM bot_assets WHERE key = ?", (key,))
    return rs.rows[0][0] if rs.rows else None


async def set_asset_file_id(key: str, file_id: str):
    client = get_client()
    await client.execute(
        "INSERT INTO bot_assets (key, file_id) VALUES (?, ?) "
        "ON CONFLICT(key) DO UPDATE SET file_id = excluded.file_id",
        (key, file_id),
    )