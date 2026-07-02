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

DB_PATH = os.getenv("DB_PATH", "anisinus.db")

PAGE_SIZE = 8  # bitta sahifada nechta anime/epizod ko'rsatish

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
