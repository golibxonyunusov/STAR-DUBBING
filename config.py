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

# /start buyrug'ida (asosiy xush kelibsiz xabarida) tepasida ko'rsatiladigan rasm.
# Fayl repoda "handlers/assets/welcome.jpg" da joylashgan.
WELCOME_IMAGE_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "handlers", "assets", "welcome.jpg"
)

PAGE_SIZE = 8  # bitta sahifada nechta anime/epizod ko'rsatish

# Botning @username'i (t.me/USERNAME). Sayt shu orqali Telegram'ga link beradi.
# .env faylida BOT_USERNAME=STAR_DUBBING_bot kabi (@ belgisisiz) kiritiladi.
# Agar @ bilan yozilgan bo'lsa ham, quyida avtomatik olib tashlanadi.
BOT_USERNAME = os.getenv("BOT_USERNAME", "").lstrip("@").strip()

# Saytning to'liq domeni (https:// bilan, oxirida "/" siz).
# Bot shu domen asosida "veb-profilga kirish" havolalarini tuzadi.
SITE_URL = os.getenv("SITE_URL", "https://star-dubbing.onrender.com").rstrip("/")

# ESKI USUL (endi ishlatilmaydi): avval sayt videolarni OCHIQ Telegram kanali
# postidan Telegram widget orqali ko'rsatar edi. Endi har bir epizod uchun
# saytga ALOHIDA to'g'ridan-to'g'ri video havolasi qo'shiladi (admin panel
# orqali, "episodes.web_video_url" ustunida saqlanadi) -- shuning uchun bu
# o'zgaruvchi endi kerak emas va olib tashlandi.

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