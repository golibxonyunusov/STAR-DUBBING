# AniSinus Bot

O'zbek tilida dublyaj qilingan anime/animelarni foydalanuvchilarga yetkazib beruvchi Telegram bot.
`@AniSinusBot` ga o'xshash: qidirish, katalog, janrlar, epizodlarni ko'rish, majburiy obuna,
admin panel (anime/epizod qo'shish, statistika, xabar yuborish).

## 1. O'rnatish

```bash
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## 2. Sozlash

1. `.env.example` faylini `.env` deb nusxalang:
   ```bash
   cp .env.example .env
   ```
2. [@BotFather](https://t.me/BotFather) dan token oling va `.env` ichidagi `BOT_TOKEN` ga qo'ying.
3. O'z Telegram `user_id` ingizni bilish uchun [@userinfobot](https://t.me/userinfobot) ga yozing,
   raqamni `.env` dagi `ADMIN_IDS` ga qo'ying (bir nechta admin — vergul bilan: `111,222`).

## 3. Ishga tushirish

```bash
python bot.py
```

Bot ishga tushgach, Telegram'da botingizga `/start` yozing.

## 4. Admin panel

Admin sifatida botga `/admin` buyrug'ini yuboring. Quyidagilar mavjud:

- **➕ Anime qo'shish** — nom, tavsif, janr, yil, poster (rasm) ketma-ket so'raladi.
- **🎬 Epizod qo'shish** — animeni tanlaysiz, epizod raqamini kiritasiz, video yuborasiz
  (kanaldan forward qilsangiz ham bo'ladi — video file_id saqlanadi, fayl qayta yuklanmaydi).
- **🗑 Anime o'chirish** — animeni va uning barcha epizodlarini o'chiradi.
- **📊 Statistika** — foydalanuvchilar va animelar soni.
- **📢 Xabar yuborish** — barcha foydalanuvchilarga matn/rasm/video yuborish (broadcast).
- **📡 Kanal sozlash** — majburiy obuna kanallarini boshqarish (`/addch` orqali qo'shish,
  ro'yxatdagi `/delch_<id>` orqali o'chirish). **Bot shu kanal(lar)da ADMIN bo'lishi shart**,
  aks holda obunani tekshira olmaydi.

## 5. Loyihaning tuzilishi

```
anisinus_bot/
├── bot.py              # ishga tushirish nuqtasi
├── config.py           # token, admin ID lar, sozlamalar
├── database.py         # SQLite bilan ishlash (aiosqlite)
├── keyboards.py        # inline/reply klaviaturalar
├── states.py           # admin FSM holatlari
├── handlers/
│   ├── user.py         # foydalanuvchi: qidirish, katalog, epizod ko'rish, majburiy obuna
│   └── admin.py        # admin: anime/epizod qo'shish-o'chirish, broadcast, kanal sozlash
├── requirements.txt
└── .env.example
```

## 6. Nima uchun video fayllar to'g'ridan-to'g'ri Telegram orqali saqlanadi?

Har bir video Telegram serverida saqlanadi, biz faqat uning `file_id` sini bazaga yozamiz.
Shu sababli serverda joy tejaladi va video yuborish tezkor bo'ladi — bu aynan AniSinusBot
kabi botlarda ishlatiladigan usul.

## 7. Serverga qo'yish (production)

- Oddiy VPS (Ubuntu) da `systemd` service yoki `tmux`/`screen` orqali `python bot.py` ni doim
  ishlab turishini ta'minlang.
- Yoki `pm2`, `supervisor` kabi process-manager ishlatishingiz mumkin.
- Katta yuk kutilsa (minglab foydalanuvchi), SQLite o'rniga PostgreSQL ga o'tish tavsiya etiladi —
  `database.py` shu maqsadda alohida modul qilib ajratilgan, kerak bo'lsa almashtirish oson.

## 8. Kengaytirish g'oyalari

- Anime uchun reyting/izoh qo'shish
- "Sevimlilar" ro'yxati (foydalanuvchi anime saqlab qo'yishi)
- Yangi epizod chiqqanda avtomatik xabarnoma yuborish
- Inline mode (`@AniSinusBot nomi` deb yozib istalgan chatda qidirish)

git add .
git commit -m "yangilanish"
git push