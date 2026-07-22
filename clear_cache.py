"""Eski bot tokeniga tegishli bo'lgan keshlangan Telegram file_id larni
(bot_assets jadvalidan) tozalaydi. Bot keyingi safar rasmlarni qaytadan
LOKAL FAYLDAN yuklaydi va YANGI (joriy tokenga mos) file_id saqlaydi.

Ishlatish:
    python clear_cache.py

Eslatma: bu skript sizning mavjud database.py modulingizdagi ulanishni
ishlatadi -- shuning uchun Turso'da bo'lsa ham, lokal SQLite'da bo'lsa ham
to'g'ri ishlaydi (qo'shimcha sozlash shart emas)."""

import asyncio

import database as db


async def main():
    await db.init_db()
    client = db.get_client()

    try:
        result = await client.execute("SELECT COUNT(*) as c FROM bot_assets")
        try:
            count_before = result.rows[0]["c"] if hasattr(result, "rows") else result[0][0]
        except Exception:
            count_before = "?"
        print(f"bot_assets jadvalida hozircha {count_before} ta yozuv bor.")
    except Exception as e:
        print(f"bot_assets jadvalini o'qib bo'lmadi (ehtimol hali yaratilmagan): {e}")
        await db.close_db()
        return

    await client.execute("DELETE FROM bot_assets")
    print("✅ bot_assets jadvali tozalandi. Bot keyingi safar rasmlarni "
          "qaytadan lokal fayldan yuklab, yangi file_id saqlaydi.")

    await db.close_db()


if __name__ == "__main__":
    asyncio.run(main())
