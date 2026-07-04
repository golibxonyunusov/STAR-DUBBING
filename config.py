import os
from dotenv import load_dotenv

load_dotenv()

# .env faylidan o'qiladi (pastda misol bor)
BOT_TOKEN = os.getenv("BOT_TOKEN", "PUT_YOUR_BOT_TOKEN_HERE")

# Bot adminlari (Telegram user_id lar), vergul bilan ajratilgan .env da:
# ADMIN_IDS=123456789,987654321
ADMIN_IDS = [
    int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip().isdigit()
]

# Epizod videolari saqlanadigan yopiq kanal (bot shu kanalda admin bo'lishi kerak).
# Masalan: -1001234567890 yoki @kanal_username
STORAGE_CHANNEL_ID = os.getenv("STORAGE_CHANNEL_ID", "")

# Videoni SAYTDA (Telegram'ga chiqmasdan) ko'rsatish uchun kerak bo'ladigan
# OCHIQ (public, @username bor) kanal nomi, @ belgisisiz.
# Bu kanal orqali "iframe" embed qilinadi -- shu sababli kanal ochiq bo'lishi shart.
STORAGE_CHANNEL_USERNAME = os.getenv("STORAGE_CHANNEL_USERNAME", "").lstrip("@").strip()

DB_PATH = os.getenv("DB_PATH", "anisinus.db")

PAGE_SIZE = 8  # bitta sahifada nechta anime/epizod ko'rsatish

# Botning @username'i (t.me/USERNAME). Sayt shu orqali Telegram'ga link beradi.
# .env faylida BOT_USERNAME=STAR_DUBBING_bot kabi (@ belgisisiz) kiritiladi.
# Agar @ bilan yozilgan bo'lsa ham, quyida avtomatik olib tashlanadi.
BOT_USERNAME = os.getenv("BOT_USERNAME", "").lstrip("@").strip()

# Majburiy obuna kanallari — to'g'ridan-to'g'ri shu yerda (kodda) belgilanadi.
# chat_id: kanal username (@ bilan) yoki -100... ko'rinishidagi ID.
# Bot bu kanallarda ADMIN bo'lishi shart, aks holda obunani tekshira olmaydi.
REQUIRED_CHANNELS = [
    {
        "chat_id": "@stardub_best",
        "title": "Stardub",
        "invite_link": "https://t.me/stardub_best",
    },
    {
        "chat_id": "@xumoyun_best",
        "title": "Xumoyun",
        "invite_link": "https://t.me/xumoyun_best",
    },
]