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

## 6.1. Videoni saytda (Telegramga chiqmasdan) tomosha qilish

Sayt videoni to'g'ridan-to'g'ri Telegram serveridan ola olmaydi (bot API katta
fayllarni yuklab olishga imkon bermaydi), shu sababli quyidagi usul qo'llanildi:

1. `.env` faylida `PUBLIC_CHANNEL_USERNAME` — videolar joylanadigan **ochiq**
   (public, @username bor) Telegram kanal nomi ko'rsatiladi.
2. Epizod qo'shishda (`🎬 Epizod qo'shish`) video yuborilgach, bot sizdan shu
   videoning ochiq kanaldagi post havolasini so'raydi
   (masalan: `https://t.me/PUBLIC_CHANNEL_USERNAME/123`).
   - Avval videoni ochiq kanalga joylang, keyin uning havolasini botga yuboring.
   - Agar hozircha ochiq kanalga joylay olmasangiz, `/skip` yozing — epizod
     baribir qo'shiladi, lekin saytda faqat "Telegram bot orqali tomosha
     qilish" tugmasi ko'rinadi (eski usul bo'yicha).
3. Havola to'g'ri bo'lsa, sayt shu postni Telegramning rasmiy
   `telegram-widget.js` orqali sahifaning o'ziga o'rnatadi — foydalanuvchi
   hech qayerga chiqmasdan videoni ko'radi.
4. VIP-only animelar uchun saytda tomosha qilish faqat **saytga kirgan va VIP
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
- Inline mode (`@AniSinusBot nomi` deb yozib istalgan chatda qidirish)

git add .
git commit -m "yangilanish"
git push