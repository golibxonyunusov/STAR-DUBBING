# STAR DUBBING Bot

O'zbek tilida dublyaj qilingan anime/animelarni foydalanuvchilarga yetkazib beruvchi Telegram bot:
qidirish, katalog, janrlar, epizodlarni ko'rish, majburiy obuna,
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
Shu sababli serverda joy tejaladi va video yuborish tezkor bo'ladi — bu shunga o'xshash
botlarda keng ishlatiladigan usul.

## 6.1. Videoni saytda (Telegramga chiqmasdan) tomosha qilish

Bot va sayt uchun video **ikki mustaqil manbadan** ko'rsatiladi — biri
ikkinchisiga bog'liq emas:

- **Telegram bot** — video `file_id` orqali (Telegramning o'zida saqlanadi).
- **Sayt** — har bir epizod uchun ADMIN tomonidan alohida kiritiladigan
  **to'g'ridan-to'g'ri video havolasi** (`episodes.web_video_url` ustunida
  saqlanadi) orqali. Bu havola istalgan hostingdan bo'lishi mumkin (masalan,
  to'g'ridan-to'g'ri `.mp4` linki beruvchi xizmat). Muhimi — havola
  `http://` yoki `https://` bilan boshlanishi va brauzerda to'g'ridan-to'g'ri
  video sifatida ochilishi kerak.

Shu sababli saytda **Telegram kanali umuman ko'rinmaydi** — na kanal nomi,
na havolasi, chunki sayt Telegram widget/iframe emas, oddiy HTML5
`<video>` tegi orqali ko'rsatadi.

**Qo'shish tartibi:**

1. `🎬 Epizod qo'shish` orqali video Telegramga (bot uchun) yuboriladi.
2. Bot darhol sayt uchun alohida video havolasini so'raydi.
   - Havolangiz bo'lsa — yuboring, epizod darhol saytga bog'lanadi.
   - Hozircha yo'q bo'lsa — `/skip` yozing, epizod Telegram uchun
     baribir qo'shiladi, saytga esa keyinroq `🔗 Epizodni saytga bog'lash`
     orqali qaytib kiritish mumkin.
3. VIP-only animelar uchun saytda tomosha qilish faqat **saytga kirgan va VIP
   statusi bor** foydalanuvchilarga ochiq (pastdagi "Veb-profil" bo'limiga
   qarang). Ochiq (VIP bo'lmagan) animelarni istalgan mehmon ko'ra oladi.

## 6.2. Veb-profil (saytga "kirish")

To'liq login/parol tizimi emas, balki bot orqali beriladigan **bir martalik
havola** (magic link) ishlatiladi:

1. Foydalanuvchi botda "👤 Profil" → "🌐 Saytda profilni ochish" ni bosadi
   (yoki saytdagi "👤 Profil" bo'limidan botni ochadi).
2. Bot 10 daqiqa amal qiladigan, bir marta ishlatiladigan havola yuboradi
   (`SITE_URL/kirish?token=...`).
3. Havolani bosgach, brauzerda 30 kunlik sessiya cookie o'rnatiladi va
   foydalanuvchi `/profil` sahifasida quyidagilarni ko'radi/boshqaradi:
   - Telegram ID, username, qo'shilgan sana
   - VIP holati (muddati)
   - 🌙 Tungi/☀️ kunduzgi rejim (butun saytda, header'dagi tugma orqali ham)
   - 🔔 Bildirishnomalar yoqish/o'chirish (o'chirilsa, admin "📢 Xabar
     yuborish" broadcast'ida bu foydalanuvchiga xabar bormaydi)
   - ✏️ Ko'rsatiladigan ismni o'zgartirish (botda ham, saytda ham bir xil
     ko'rinadi)

## 6.3. Qidiruv

Qidiruv endi anime nomining **istalgan qismi** bo'yicha ishlaydi (boshida,
o'rtasida yoki oxirida joylashgan bo'lsa ham), katta/kichik harf va apostrof
turi (`'`/`’`/`‘`) farq qilmaydi. Agar faqat raqam kiritilsa, avval anime
kodi (ID) sifatida qaraladi; topilmasa, xuddi shu raqam nomlar ichida ham
qidiriladi.

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
- Inline mode (`@BotUsername nomi` deb yozib istalgan chatda qidirish)

git add .
git commit -m "top bo'limi"
git push