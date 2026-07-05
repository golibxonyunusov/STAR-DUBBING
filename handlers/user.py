from aiogram import Router, F, Bot
from aiogram.filters import CommandStart, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.exceptions import TelegramBadRequest

import database as db
from config import (
    PAGE_SIZE,
    REQUIRED_CHANNELS,
    SITE_URL,
    WELCOME_IMAGE_PATH,
    SEARCH_IMAGE_PATH,
    CATALOG_IMAGE_PATH,
    GENRES_IMAGE_PATH,
    PROFIL_IMAGE_PATH,
    VIP_IMAGE_PATH,
)
from states import EditProfile
from keyboards import (
    main_menu_kb,
    subscribe_kb,
    anime_list_kb,
    genres_kb,
    anime_card_kb,
    episodes_list_kb,
    episode_nav_kb,
    profile_kb,
    web_login_kb,
)

router = Router()

# Xush kelibsiz rasmining file_id keshi -- birinchi yuborilgandan keyin
# Telegram file_id orqali qayta yuboriladi (qayta yuklash shart emas).
_welcome_photo_file_id: str | None = None

# Qidirish/Barcha animelar/Janrlar bo'limlarining rasm file_id keshi.
_section_photo_ids: dict[str, str] = {}


async def send_section_photo(message: Message, key: str, path: str, caption: str, reply_markup=None):
    """Berilgan bo'lim uchun rasm + matnni birga yuboradi, file_id'ni keshlaydi."""
    photo = _section_photo_ids.get(key) or FSInputFile(path)
    sent = await message.answer_photo(photo=photo, caption=caption, reply_markup=reply_markup)
    if key not in _section_photo_ids and sent.photo:
        _section_photo_ids[key] = sent.photo[-1].file_id


async def send_welcome_message(message: Message):
    global _welcome_photo_file_id
    caption = (
        "<b>STAR DUBBING</b> ga xush kelibsiz!\n\n"
        "Bu yerda sevimli anime va animelaringizning o'zbek tilidagi dublyaj qilingan "
        "epizodlarini topishingiz mumkin.\n\n"
        "🔭 Qidirish orqali anime nomini yozing\n"
        "🌌 Barcha animelar bo'limidan ro'yxatni ko'ring\n"
        "🪐 Janrlar bo'yicha tanlang"
    )
    photo = _welcome_photo_file_id or FSInputFile(WELCOME_IMAGE_PATH)
    sent = await message.answer_photo(photo=photo, caption=caption, reply_markup=main_menu_kb())
    if not _welcome_photo_file_id and sent.photo:
        _welcome_photo_file_id = sent.photo[-1].file_id


# ---------- MAJBURIY OBUNA ----------

async def get_required_channels():
    # config.py da hardcode qilingan kanallar + admin panel orqali qo'shilgan kanallar
    db_channels = await db.get_required_channels()
    db_list = [dict(ch) for ch in db_channels]
    return REQUIRED_CHANNELS + db_list


async def check_subscription(bot: Bot, user_id: int) -> bool:
    # VIP foydalanuvchilar majburiy obunadan ozod
    if await db.is_vip(user_id):
        return True

    channels = await get_required_channels()
    if not channels:
        return True
    for ch in channels:
        try:
            member = await bot.get_chat_member(chat_id=ch["chat_id"], user_id=user_id)
            if member.status in ("left", "kicked"):
                return False
        except TelegramBadRequest:
            # bot kanalga admin qilib qo'yilmagan yoki chat topilmadi -- bloklamaymiz
            continue
    return True


async def send_subscribe_prompt(message: Message):
    channels = await get_required_channels()
    await message.answer(
        "Botdan foydalanish uchun quyidagi kanal(lar)ga obuna bo'ling, so'ng "
        "\"✅ Tekshirish\" tugmasini bosing:",
        reply_markup=subscribe_kb(channels),
    )


# ---------- VEB-PROFILGA KIRISH (magic-link) ----------

async def send_web_login_link(message: Message, user_id: int):
    token = await db.create_login_token(user_id)
    url = f"{SITE_URL}/kirish?token={token}"
    await message.answer(
        "🌐 Saytdagi profilingizga kirish uchun quyidagi tugmani bosing.\n"
        "⏳ Havola 10 daqiqa amal qiladi va faqat bir marta ishlatiladi.",
        reply_markup=web_login_kb(url),
    )


# ---------- START ----------

@router.message(CommandStart())
async def cmd_start(message: Message, bot: Bot, command: CommandObject):
    await db.add_user(message.from_user.id, message.from_user.username or "", message.from_user.full_name)

    if not await check_subscription(bot, message.from_user.id):
        await send_subscribe_prompt(message)
        return

    payload = command.args  # sayt orqali kelgan bo'lsa: "ep_3_1", "anime_3" yoki "veblogin"

    if payload:
        if payload == "veblogin":
            # Sayt "Kirish" tugmasi orqali bot ochilgan -- darhol veb-profilga
            # kirish havolasini yuboramiz.
            await send_web_login_link(message, message.from_user.id)
            await message.answer("Asosiy menyu:", reply_markup=main_menu_kb())
            return
        if payload.startswith("ep_"):
            try:
                _, anime_id_str, ep_num_str = payload.split("_")
                await deliver_episode(message, int(anime_id_str), int(ep_num_str), message.from_user.id)
                return
            except (ValueError, IndexError):
                pass
        elif payload.startswith("anime_"):
            try:
                anime_id = int(payload.split("_")[1])
                await render_anime_card(message, anime_id, message.from_user.id)
                await message.answer("Asosiy menyu:", reply_markup=main_menu_kb())
                return
            except (ValueError, IndexError):
                pass

    await send_welcome_message(message)


@router.callback_query(F.data == "check_sub")
async def cb_check_sub(call: CallbackQuery, bot: Bot):
    if await check_subscription(bot, call.from_user.id):
        await call.message.delete()
        await call.message.answer(
            "✅ Obuna tasdiqlandi! Botdan foydalanishingiz mumkin.",
            reply_markup=main_menu_kb(),
        )
    else:
        await call.answer("❌ Siz hali barcha kanallarga obuna bo'lmadingiz.", show_alert=True)


# ---------- QIDIRISH ----------

@router.message(F.text == "🔭 Qidirish")
async def ask_search(message: Message, bot: Bot):
    if not await check_subscription(bot, message.from_user.id):
        await send_subscribe_prompt(message)
        return
    await send_section_photo(
        message,
        "search",
        SEARCH_IMAGE_PATH,
        "🔭 <b>Anime qidirish</b>\n\n"
        "Sizga kerakli olam minglab yulduzlar orasida yashiringan bo'lishi mumkin — "
        "lekin tashvishlanmang, biz uni birga topamiz! ✨\n\n"
        "Animening nomini (yoki nomining bir qismini) yozib yuboring.\n\n"
        "💡 Agar animening kodini bilsangiz (masalan <code>5</code>), "
        "to'g'ridan-to'g'ri shu raqamni yuborsangiz ham bo'ladi — bot uni darhol topib beradi.",
    )


@router.message(F.text == "🌌 Barcha animelar")
async def show_all_anime(message: Message, bot: Bot):
    if not await check_subscription(bot, message.from_user.id):
        await send_subscribe_prompt(message)
        return
    total = await db.count_anime()
    if total == 0:
        await message.answer("Hozircha animelar qo'shilmagan.")
        return
    rows = await db.list_anime(offset=0, limit=PAGE_SIZE)
    await send_section_photo(
        message,
        "catalog",
        CATALOG_IMAGE_PATH,
        "🌌 <b>Barcha animelar katalogi</b>\n\n"
        "Minglab olam, yuzlab qahramon — hammasi shu yerda, bir necha bosishda "
        "tomoshangizni kutmoqda.\n\n"
        f"📦 Jami: <b>{total} ta</b> anime\n\n"
        "Quyidagi ro'yxatdan o'zingizga yoqqan animeni tanlang 👇",
        reply_markup=anime_list_kb(rows, 0, total),
    )


@router.callback_query(F.data.startswith("list_"))
async def paginate_anime(call: CallbackQuery):
    offset = int(call.data.split("_")[1])
    total = await db.count_anime()
    rows = await db.list_anime(offset=offset, limit=PAGE_SIZE)
    try:
        await call.message.edit_caption(
            caption=(
                "🌌 <b>Barcha animelar katalogi</b>\n\n"
                "Minglab olam, yuzlab qahramon — hammasi shu yerda, bir necha bosishda "
                "tomoshangizni kutmoqda.\n\n"
                f"📦 Jami: <b>{total} ta</b> anime\n\n"
                "Quyidagi ro'yxatdan o'zingizga yoqqan animeni tanlang 👇"
            ),
            reply_markup=anime_list_kb(rows, offset, total),
        )
    except TelegramBadRequest:
        pass
    await call.answer()


@router.message(F.text == "🪐 Janrlar")
async def show_genres(message: Message, bot: Bot):
    if not await check_subscription(bot, message.from_user.id):
        await send_subscribe_prompt(message)
        return
    genres = await db.get_all_genres()
    if not genres:
        await message.answer("Hozircha janrlar mavjud emas.")
        return
    await send_section_photo(
        message,
        "genres",
        GENRES_IMAGE_PATH,
        "🪐 <b>Janrlar galaktikasi</b>\n\n"
        "Har bir janr — o'z sayyorasi: ishq-muhabbatdan tortib sirli va "
        "qo'rqinchli dunyolargacha.\n\n"
        "O'zingizga yoqqan janrni tanlang va o'sha olamga sayohatni boshlang 👇",
        reply_markup=genres_kb(genres),
    )


@router.callback_query(F.data.startswith("genre_"))
async def show_genre_list(call: CallbackQuery):
    genre = call.data.split("_", 1)[1]
    total = await db.count_anime(genre=genre)
    rows = await db.list_anime(offset=0, limit=PAGE_SIZE, genre=genre)
    if not rows:
        await call.answer("Bu janrda animelar topilmadi.", show_alert=True)
        return
    await call.message.answer(
        f"🎭 <b>{genre}</b> ({total} ta):",
        reply_markup=anime_list_kb(rows, 0, total, genre=genre),
    )
    await call.answer()


@router.callback_query(F.data.startswith("listg_"))
async def paginate_genre_list(call: CallbackQuery):
    _, genre, offset_str = call.data.split("_", 2)
    offset = int(offset_str)
    total = await db.count_anime(genre=genre)
    rows = await db.list_anime(offset=offset, limit=PAGE_SIZE, genre=genre)
    try:
        await call.message.edit_text(
            f"🎭 <b>{genre}</b> ({total} ta):",
            reply_markup=anime_list_kb(rows, offset, total, genre=genre),
        )
    except TelegramBadRequest:
        pass
    await call.answer()


@router.message(F.text == "✨ Bot haqida")
async def about_bot(message: Message):
    await message.answer(
        "✦ <b>STAR DUBBING</b>\n\n"
        "Ushbu bot orqali anime va animelarning o'zbek tilidagi dublyajini "
        "bepul tomosha qilishingiz mumkin.\n\n"
        "📖 <b>Botdan foydalanish tartibi:</b>\n\n"
        "1️⃣ 🔭 <b>Qidirish</b> — tugmani bosing, so'ng anime nomini yoki "
        "uning kodini (masalan: <code>3</code>) yozing.\n\n"
        "2️⃣ 🌌 <b>Barcha animelar</b> — mavjud barcha animelar ro'yxatini "
        "ko'rasiz, har birining oldida <code>#kod</code> ko'rsatilgan.\n\n"
        "3️⃣ 🪐 <b>Janrlar</b> — o'zingizga yoqqan janrni tanlab, shu janrdagi "
        "animelarni ko'rasiz.\n\n"
        "4️⃣ Anime ustiga bosgach, uning haqida ma'lumot (tavsif, janr, yil) "
        "va \"🎬 Epizodlar\" tugmasi chiqadi.\n\n"
        "5️⃣ Epizodlar tugmasini bosib, kerakli qism raqamini tanlang — "
        "video darhol yuboriladi. Video ostidagi \"⬅️ Oldingi\" / \"➡️ Keyingi\" "
        "tugmalari orqali qismlar orasida qulay o'tishingiz mumkin.\n\n"
        "💡 <b>Maslahat:</b> agar animening kodini bilsangiz "
        "(masalan <code>5</code>), uni to'g'ridan-to'g'ri qidiruv maydoniga "
        "yozib yuboring — bot darhol o'sha animeni ochib beradi.\n\n"
        "❓ Savol va takliflar uchun @xumoyun_best1 bilan bog'laning."
    )


@router.message(F.text == "👑 VIP")
async def vip_status(message: Message):
    vip = await db.get_vip(message.from_user.id)
    if vip:
        if vip["expires_at"]:
            muddat = f"tugash sanasi: {vip['expires_at'][:10]}"
        else:
            muddat = "umrbod ♾"
        caption = (
            f"👑 Siz <b>VIP</b> foydalanuvchisiz!\n"
            f"📅 {muddat}\n\n"
            f"✅ Majburiy obunasiz botdan foydalanasiz\n"
            f"✅ Barcha VIP-only animelarni ko'ra olasiz"
        )
    else:
        caption = (
            "👑 <b>VIP maqomi</b>\n\n"
            "Yulduzlar orasidagi eng maxsus joy — sizni kutmoqda! ✨\n\n"
            "VIP status orqali:\n"
            "✅ Majburiy obunasiz botdan foydalanish\n"
            "✅ Yopiq (VIP-only) animelarni ko'rish imkoniga ega bo'lasiz\n\n"
            "VIP olish uchun @rudeus1111 bilan bog'laning."
        )
    await send_section_photo(message, "vip", VIP_IMAGE_PATH, caption)


# ---------- PROFIL ----------

@router.message(F.text == "🧑‍🚀 Profil")
async def show_profile(message: Message):
    user = await db.get_user(message.from_user.id)
    settings = await db.get_user_settings(message.from_user.id)
    vip = await db.get_vip(message.from_user.id)

    display_name = settings["display_name"] or (user["full_name"] if user else message.from_user.full_name)
    vip_line = "❌ Yo'q"
    if vip:
        vip_line = "♾ Umrbod" if not vip["expires_at"] else f"✅ {vip['expires_at'][:10]} gacha"

    caption = (
        f"🧑\u200d🚀 <b>Profil</b>\n\n"
        f"📛 Ism: <b>{display_name}</b>\n"
        f"🆔 Telegram ID: <code>{message.from_user.id}</code>\n"
        f"👤 Username: @{message.from_user.username or '—'}\n"
        f"👑 VIP: {vip_line}\n\n"
        f"🌐 Profilingizni saytda ham ochib, mavzu va bildirishnoma "
        f"sozlamalarini boshqarishingiz mumkin."
    )
    await send_section_photo(message, "profil", PROFIL_IMAGE_PATH, caption, reply_markup=profile_kb())


@router.callback_query(F.data == "profile_edit_name")
async def profile_edit_name_start(call: CallbackQuery, state: FSMContext):
    await state.set_state(EditProfile.display_name)
    await call.message.answer("✏️ Yangi ismingizni (saytda va botda ko'rinadigan) kiriting:")
    await call.answer()


@router.message(EditProfile.display_name)
async def profile_edit_name_save(message: Message, state: FSMContext):
    name = message.text.strip()[:64]
    await db.update_user_settings(message.from_user.id, display_name=name)
    await state.clear()
    await message.answer(f"✅ Ismingiz \"{name}\" qilib saqlandi.", reply_markup=main_menu_kb())


@router.callback_query(F.data == "profile_web_login")
async def profile_web_login(call: CallbackQuery):
    await send_web_login_link(call.message, call.from_user.id)
    await call.answer()


# ---------- ANIME KARTASI ----------

async def render_anime_card(message: Message, anime_id: int, user_id: int) -> bool:
    """Anime kartasini (poster + ma'lumot + kod) yuboradi. Topilmasa False qaytaradi."""
    anime = await db.get_anime(anime_id)
    if not anime:
        return False

    if anime["vip_only"] and not await db.is_vip(user_id):
        await message.answer(
            f"🔒 <b>{anime['title']}</b>\n\n"
            "Bu anime faqat 👑 <b>VIP</b> foydalanuvchilar uchun ochiq.\n"
            "VIP status olish uchun @rudeus1111 bilan bog'laning."
        )
        return True

    episodes_count = await db.get_episodes_count(anime_id)

    caption = (
        f"{'🔒 ' if anime['vip_only'] else ''}🎬 <b>{anime['title']}</b>\n"
        f"🆔 Kod: <code>{anime['id']}</code>\n\n"
        f"{anime['description'] or ''}\n\n"
        f"🎭 Janr: {anime['genre'] or '-'}\n"
        f"📅 Yil: {anime['year'] or '-'}\n"
        f"📌 Holat: {anime['status'] or '-'}\n"
        f"🎞 Epizodlar soni: {episodes_count}"
    )

    kb = anime_card_kb(anime_id, episodes_count)

    if anime["poster_file_id"]:
        await message.answer_photo(anime["poster_file_id"], caption=caption, reply_markup=kb)
    else:
        await message.answer(caption, reply_markup=kb)
    return True


@router.callback_query(F.data.startswith("anime_"))
async def show_anime_card(call: CallbackQuery):
    anime_id = int(call.data.split("_")[1])
    found = await render_anime_card(call.message, anime_id, call.from_user.id)
    if not found:
        await call.answer("Anime topilmadi.", show_alert=True)
        return
    await call.answer()


@router.callback_query(F.data == "back_to_list")
async def back_to_list(call: CallbackQuery):
    total = await db.count_anime()
    rows = await db.list_anime(offset=0, limit=PAGE_SIZE)
    await call.message.answer(
        f"🌌 Barcha animelar ({total} ta):",
        reply_markup=anime_list_kb(rows, 0, total),
    )
    await call.answer()


# ---------- EPIZODLAR RO'YXATI ----------

@router.callback_query(F.data.startswith("episodes_"))
async def show_episodes(call: CallbackQuery):
    _, anime_id_str, offset_str = call.data.split("_")
    anime_id, offset = int(anime_id_str), int(offset_str)

    all_episodes = await db.get_episodes(anime_id)
    total = len(all_episodes)
    if total == 0:
        await call.answer("Bu anime uchun hali epizod qo'shilmagan.", show_alert=True)
        return

    page_episodes = all_episodes[offset: offset + PAGE_SIZE]
    anime = await db.get_anime(anime_id)

    text = f"🎬 <b>{anime['title']}</b>\nEpizodni tanlang:"
    try:
        await call.message.edit_caption(caption=text, reply_markup=episodes_list_kb(anime_id, page_episodes, offset, total))
    except TelegramBadRequest:
        try:
            await call.message.edit_text(text, reply_markup=episodes_list_kb(anime_id, page_episodes, offset, total))
        except TelegramBadRequest:
            await call.message.answer(text, reply_markup=episodes_list_kb(anime_id, page_episodes, offset, total))
    await call.answer()


async def deliver_episode(message: Message, anime_id: int, ep_num: int, user_id: int) -> bool:
    """Epizodni yuboradi (Message yoki CallbackQuery.message bo'lishi mumkin)."""
    anime = await db.get_anime(anime_id)
    if not anime:
        await message.answer("Anime topilmadi.")
        return False

    if anime["vip_only"] and not await db.is_vip(user_id):
        await message.answer("🔒 Bu anime faqat VIP foydalanuvchilar uchun.")
        return False

    episode = await db.get_episode_by_number(anime_id, ep_num)
    if not episode:
        await message.answer("Bu epizod topilmadi.")
        return False

    total_eps = await db.get_episodes_count(anime_id)
    has_prev = await db.get_episode_by_number(anime_id, ep_num - 1) is not None
    has_next = await db.get_episode_by_number(anime_id, ep_num + 1) is not None

    await message.answer_video(
        episode["file_id"],
        caption=f"🎬 <b>{anime['title']}</b>\n{ep_num}-qism / {total_eps}",
        reply_markup=episode_nav_kb(anime_id, ep_num, has_prev, has_next),
    )
    return True


@router.callback_query(F.data.startswith("ep_"))
async def send_episode(call: CallbackQuery, bot: Bot):
    if not await check_subscription(bot, call.from_user.id):
        await call.answer()
        await send_subscribe_prompt(call.message)
        return

    _, anime_id_str, ep_num_str = call.data.split("_")
    await deliver_episode(call.message, int(anime_id_str), int(ep_num_str), call.from_user.id)
    await call.answer()


# ---------- MATNLI QIDIRUV (oxirida, boshqa handlerlarga tegmasin) ----------

@router.message(F.text)
async def text_search(message: Message, bot: Bot):
    if not await check_subscription(bot, message.from_user.id):
        await send_subscribe_prompt(message)
        return

    query = message.text.strip()

    # Agar foydalanuvchi faqat raqam yozsa -- bu anime KODI (ID) deb qaraymiz
    if query.isdigit():
        found = await render_anime_card(message, int(query), message.from_user.id)
        if not found:
            await message.answer(
                f"😔 <code>{query}</code> kodli anime topilmadi. Kodni tekshirib qayta urinib ko'ring."
            )
        return

    if len(query) < 2:
        await message.answer("Kamida 2 ta harf kiriting yoki anime kodini (raqamini) yuboring.")
        return

    results = await db.search_anime(query)
    if not results:
        await message.answer("😔 Hech narsa topilmadi. Boshqa nom yoki anime kodi bilan urinib ko'ring.")
        return

    total = len(results)
    await message.answer(
        f"🔭 \"{query}\" bo'yicha natijalar ({total} ta):",
        reply_markup=anime_list_kb(results[:PAGE_SIZE], 0, total),
    )