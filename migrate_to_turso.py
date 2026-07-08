import asyncio
import sqlite3

import database as db
from config import DB_PATH, TURSO_DATABASE_URL

TABLES = [
    "users", "anime", "episodes", "required_channels", "vip_users",
    "user_settings", "login_tokens", "sessions", "bot_assets",
]


async def main():
    if not TURSO_DATABASE_URL:
        print("XATO: avval .env faylida TURSO_DATABASE_URL va TURSO_AUTH_TOKEN ni to'ldiring!")
        return

    print(f"Manba (mahalliy) baza: {DB_PATH}")
    print(f"Maqsad (Turso) baza:   {TURSO_DATABASE_URL}\n")

    # 1) Turso'da bo'sh jadvallarni yaratish
    await db.init_db()

    # 2) Mahalliy faylni ochish
    local = sqlite3.connect(DB_PATH)
    local.row_factory = sqlite3.Row

    client = db.get_client()

    total = 0
    for table in TABLES:
        try:
            cur = local.execute(f"SELECT * FROM {table}")
        except sqlite3.OperationalError:
            print(f"  {table}: mahalliy bazada topilmadi, o'tkazib yuborildi")
            continue
        rows = cur.fetchall()
        if not rows:
            print(f"  {table}: bo'sh, o'tkazib yuborildi")
            continue
        columns = rows[0].keys()
        placeholders = ", ".join(["?"] * len(columns))
        col_list = ", ".join(columns)
        sql = f"INSERT OR IGNORE INTO {table} ({col_list}) VALUES ({placeholders})"
        for row in rows:
            await client.execute(sql, tuple(row))
        print(f"  {table}: {len(rows)} qator ko'chirildi")
        total += len(rows)

    local.close()
    await db.close_db()
    print(f"\n✅ Tayyor! Jami {total} qator Turso'ga muvaffaqiyatli ko'chirildi.")


if __name__ == "__main__":
    asyncio.run(main())
