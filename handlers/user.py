from aiogram import Router, F, Bot
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.exceptions import TelegramBadRequest

import database as db
from config import PAGE_SIZE, REQUIRED_CHANNELS
from keyboards import (
    main_menu_kb,
    subscribe_kb,
    anime_list_kb,
    genres_kb,
    anime_card_kb,
    episodes_list_kb,
    episode_nav_kb,
)

router = Router()


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


# ---------- START ----------

@router.message(CommandStart())
async def cmd_start(message: Message, bot: Bot):
    await db.add_user(message.from_user.id, message.from_user.username or "", message.from_user.full_name)

    if not await check_subscription(bot, message.from_user.id):
        await send_subscribe_prompt(message)
        return

    await message.answer(
        "🎌 <b>AniSinus</b> ga xush kelibsiz!\n\n"
        "Bu yerda sevimli anime va animelaringizning o'zbek tilidagi dublyaj qilingan "
        "epizodlarini topishingiz mumkin.\n\n"
        "🔍 Qidirish orqali anime nomini yozing\n"
        "📚 Barcha animelar bo'limidan ro'yxatni ko'ring\n"
        "🎭 Janrlar bo'yicha tanlang",
        reply_markup=main_menu_kb(),
    )


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

@router.message(F.text == "🔍 Qidirish")
async def ask_search(message: Message, bot: Bot):
    if not await check_subscription(bot, message.from_user.id):
        await send_subscribe_prompt(message)
        return
    await message.answer("Anime nomini kiriting:")


@router.message(F.text == "📚 Barcha animelar")
async def show_all_anime(message: Message, bot: Bot):
    if not await check_subscription(bot, message.from_user.id):
        await send_subscribe_prompt(message)
        return
    total = await db.count_anime()
    if total == 0:
        await message.answer("Hozircha animelar qo'shilmagan.")
        return
    rows = await db.list_anime(offset=0, limit=PAGE_SIZE)
    await message.answer(
        f"📚 Barcha animelar ({total} ta):",
        reply_markup=anime_list_kb(rows, 0, total),
    )


@router.callback_query(F.data.startswith("list_"))
async def paginate_anime(call: CallbackQuery):
    offset = int(call.data.split("_")[1])
    total = await db.count_anime()
    rows = await db.list_anime(offset=offset, limit=PAGE_SIZE)
    try:
        await call.message.edit_text(
            f"📚 Barcha animelar ({total} ta):",
            reply_markup=anime_list_kb(rows, offset, total),
        )
    except TelegramBadRequest:
        pass
    await call.answer()


@router.message(F.text == "🎭 Janrlar")
async def show_genres(message: Message, bot: Bot):
    if not await check_subscription(bot, message.from_user.id):
        await send_subscribe_prompt(message)
        return
    genres = await db.get_all_genres()
    if not genres:
        await message.answer("Hozircha janrlar mavjud emas.")
        return
    await message.answer("🎭 Janrni tanlang:", reply_markup=genres_kb(genres))


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


@router.message(F.text == "ℹ️ Bot haqida")
async def about_bot(message: Message):
    await message.answer(
        "🎌 <b>AniSinus</b>\n\n"
        "Ushbu bot orqali anime va animelarning o'zbek tilidagi dublyajini "
        "bepul tomosha qilishingiz mumkin.\n\n"
        "Savol va takliflar uchun admin bilan bog'laning."
    )


@router.message(F.text == "👑 VIP")
async def vip_status(message: Message):
    vip = await db.get_vip(message.from_user.id)
    if vip:
        if vip["expires_at"]:
            muddat = f"tugash sanasi: {vip['expires_at'][:10]}"
        else:
            muddat = "umrbod ♾"
        await message.answer(
            f"👑 Siz <b>VIP</b> foydalanuvchisiz!\n"
            f"📅 {muddat}\n\n"
            f"✅ Majburiy obunasiz botdan foydalanasiz\n"
            f"✅ Barcha VIP-only animelarni ko'ra olasiz"
        )
    else:
        await message.answer(
            "👑 Siz hozircha VIP emassiz.\n\n"
            "VIP status orqali:\n"
            "✅ Majburiy obunasiz botdan foydalanish\n"
            "✅ Yopiq (VIP-only) animelarni ko'rish imkoniga ega bo'lasiz\n\n"
            "VIP olish uchun admin bilan bog'laning."
        )


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
            "VIP status olish uchun admin bilan bog'laning."
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
        f"📚 Barcha animelar ({total} ta):",
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


@router.callback_query(F.data.startswith("ep_"))
async def send_episode(call: CallbackQuery, bot: Bot):
    if not await check_subscription(bot, call.from_user.id):
        await call.answer()
        await send_subscribe_prompt(call.message)
        return

    _, anime_id_str, ep_num_str = call.data.split("_")
    anime_id, ep_num = int(anime_id_str), int(ep_num_str)

    anime = await db.get_anime(anime_id)
    if not anime:
        await call.answer("Anime topilmadi.", show_alert=True)
        return

    if anime["vip_only"] and not await db.is_vip(call.from_user.id):
        await call.answer("🔒 Bu anime faqat VIP foydalanuvchilar uchun.", show_alert=True)
        return

    episode = await db.get_episode_by_number(anime_id, ep_num)
    if not episode:
        await call.answer("Bu epizod topilmadi.", show_alert=True)
        return

    total_eps = await db.get_episodes_count(anime_id)
    has_prev = await db.get_episode_by_number(anime_id, ep_num - 1) is not None
    has_next = await db.get_episode_by_number(anime_id, ep_num + 1) is not None

    await call.message.answer_video(
        episode["file_id"],
        caption=f"🎬 <b>{anime['title']}</b>\n{ep_num}-qism / {total_eps}",
        reply_markup=episode_nav_kb(anime_id, ep_num, has_prev, has_next),
    )
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
        f"🔍 \"{query}\" bo'yicha natijalar ({total} ta):",
        reply_markup=anime_list_kb(results[:PAGE_SIZE], 0, total),
    )
