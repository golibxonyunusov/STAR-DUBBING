import aiosqlite
from datetime import datetime
from config import DB_PATH

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
"""


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(CREATE_TABLES_SQL)
        await db.commit()


# ---------- USERS ----------

async def add_user(user_id: int, username: str, full_name: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO users (user_id, username, full_name, joined_at) VALUES (?, ?, ?, ?)",
            (user_id, username, full_name, datetime.utcnow().isoformat()),
        )
        await db.commit()


async def get_users_count() -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT COUNT(*) FROM users")
        row = await cur.fetchone()
        return row[0] if row else 0


async def get_all_user_ids() -> list[int]:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT user_id FROM users")
        rows = await cur.fetchall()
        return [r[0] for r in rows]


# ---------- ANIME ----------

async def add_anime(title, description, poster_file_id, genre, year) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "INSERT INTO anime (title, description, poster_file_id, genre, year, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (title, description, poster_file_id, genre, year, datetime.utcnow().isoformat()),
        )
        await db.commit()
        return cur.lastrowid


async def get_anime(anime_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM anime WHERE id = ?", (anime_id,))
        return await cur.fetchone()


async def delete_anime(anime_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM episodes WHERE anime_id = ?", (anime_id,))
        await db.execute("DELETE FROM anime WHERE id = ?", (anime_id,))
        await db.commit()


async def search_anime(query: str, limit: int = 20):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT * FROM anime WHERE title LIKE ? ORDER BY id DESC LIMIT ?",
            (f"%{query}%", limit),
        )
        return await cur.fetchall()


async def list_anime(offset: int = 0, limit: int = 8, genre: str | None = None):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        if genre:
            cur = await db.execute(
                "SELECT * FROM anime WHERE genre LIKE ? ORDER BY id DESC LIMIT ? OFFSET ?",
                (f"%{genre}%", limit, offset),
            )
        else:
            cur = await db.execute(
                "SELECT * FROM anime ORDER BY id DESC LIMIT ? OFFSET ?", (limit, offset)
            )
        return await cur.fetchall()


async def count_anime(genre: str | None = None) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        if genre:
            cur = await db.execute(
                "SELECT COUNT(*) FROM anime WHERE genre LIKE ?", (f"%{genre}%",)
            )
        else:
            cur = await db.execute("SELECT COUNT(*) FROM anime")
        row = await cur.fetchone()
        return row[0] if row else 0


async def get_all_genres() -> list[str]:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT DISTINCT genre FROM anime WHERE genre IS NOT NULL AND genre != ''")
        rows = await cur.fetchall()
        genres = set()
        for r in rows:
            for g in r[0].split(","):
                g = g.strip()
                if g:
                    genres.add(g)
        return sorted(genres)


# ---------- EPISODES ----------

async def add_episode(anime_id: int, episode_number: int, file_id: str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "INSERT INTO episodes (anime_id, episode_number, file_id, added_at) VALUES (?, ?, ?, ?)",
            (anime_id, episode_number, file_id, datetime.utcnow().isoformat()),
        )
        await db.commit()
        return cur.lastrowid


async def get_episodes(anime_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT * FROM episodes WHERE anime_id = ? ORDER BY episode_number ASC",
            (anime_id,),
        )
        return await cur.fetchall()


async def get_episode_by_number(anime_id: int, number: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT * FROM episodes WHERE anime_id = ? AND episode_number = ?",
            (anime_id, number),
        )
        return await cur.fetchone()


async def get_episodes_count(anime_id: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT COUNT(*) FROM episodes WHERE anime_id = ?", (anime_id,))
        row = await cur.fetchone()
        return row[0] if row else 0


async def delete_episode(episode_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM episodes WHERE id = ?", (episode_id,))
        await db.commit()


# ---------- REQUIRED CHANNELS (majburiy obuna) ----------

async def add_required_channel(chat_id: str, title: str, invite_link: str = ""):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO required_channels (chat_id, title, invite_link) VALUES (?, ?, ?)",
            (chat_id, title, invite_link),
        )
        await db.commit()


async def remove_required_channel(row_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM required_channels WHERE id = ?", (row_id,))
        await db.commit()


async def get_required_channels():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM required_channels")
        return await cur.fetchall()
