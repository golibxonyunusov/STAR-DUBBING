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

# --- SAYTDAGI AI YORDAMCHI (pastki burchakdagi chat oynasi) ---
# https://console.anthropic.com dan API kalit oling va Render'da
# "Environment" bo'limiga ANTHROPIC_API_KEY nomi bilan qo'shing.
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
# Tezroq/arzonroq javoblar uchun "claude-haiku-4-5-20251001" ga
# almashtirish mumkin.
ASSISTANT_MODEL = os.getenv("ASSISTANT_MODEL", "claude-sonnet-5")

# --- TURSO (bulutdagi doimiy baza) ---
# Bot Render'da qayta ishga tushganda (uxlab qolish, qayta deploy, crash)
# ma'lumotlar YO'QOLMASLIGI uchun baza endi Turso'da (bulutda) saqlanadi.
# Ikkalasi ham bo'sh bo'lsa, dastur avtomatik ravishda yuqoridagi DB_PATH
# bo'yicha oddiy mahalliy faylga yozadi (faqat lokal sinov uchun -- Render'da
# bu holatda ma'lumotlar hamon yo'qolib turadi!).
# https://turso.tech dan bepul ro'yxatdan o'tib oling:
#   1) turso auth signup / turso auth login
#   2) turso db create anisinus
#   3) turso db show anisinus --url          -> TURSO_DATABASE_URL
#   4) turso db tokens create anisinus       -> TURSO_AUTH_TOKEN
TURSO_DATABASE_URL = os.getenv("TURSO_DATABASE_URL", "")
TURSO_AUTH_TOKEN = os.getenv("TURSO_AUTH_TOKEN", "")

# /start buyrug'ida (asosiy xush kelibsiz xabarida) tepasida ko'rsatiladigan rasm.
# Fayl repoda "handlers/assets/welcome.jpg" da joylashgan.
WELCOME_IMAGE_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "handlers", "assets", "welcome.jpg"
)

# Qidirish / Barcha animelar / Janrlar tugmalari bosilganda tepasida
# ko'rsatiladigan rasmlar (barchasi "handlers/assets/" papkasida).
_ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "handlers", "assets")
SEARCH_IMAGE_PATH = os.path.join(_ASSETS_DIR, "search.jpg")
CATALOG_IMAGE_PATH = os.path.join(_ASSETS_DIR, "catalog.jpg")
GENRES_IMAGE_PATH = os.path.join(_ASSETS_DIR, "genres.jpg")
PROFIL_IMAGE_PATH = os.path.join(_ASSETS_DIR, "profil.jpg")
VIP_IMAGE_PATH = os.path.join(_ASSETS_DIR, "vip.jpg")

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
# chat_id: kanal username (@ bilan) yoki -100... ko'rinishidagi ID -- foydalanuvchiga
#          "obuna bo'ling" tugmasida ko'rsatiladigan/link qilinadigan kanal.
# check_chat_id: obunani TEKSHIRISH uchun ishlatiladigan chat -- ba'zi kanallarda
#          Telegram getChatMember so'rovini "member list is inaccessible" deb
#          rad etadi, shuning uchun kanalga bog'langan MUHOKAMA GURUHI orqali
#          tekshiramiz (foydalanuvchi kanalga obuna bo'lsa, avtomatik shu
#          guruhga ham "a'zo" hisoblanadi). Agar berilmasa, chat_id ishlatiladi.
# Bot HAR IKKALASIDA (kanal va guruhda) ADMIN bo'lishi shart.
REQUIRED_CHANNELS = [
    {
        "chat_id": "@stardub_best",
        "title": "Stardub",
        "invite_link": "https://t.me/stardub_best",
        "check_chat_id": "@animechat_123",
    },
    {
        "chat_id": "@xumoyun_best",
        "title": "Xumoyun",
        "invite_link": "https://t.me/xumoyun_best",
        "check_chat_id": "@Worldchat_best",
    },
]