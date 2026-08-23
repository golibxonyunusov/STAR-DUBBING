import logging

from aiogram import Router, F, Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    InlineQuery,
    InlineQueryResultArticle,
    InputTextMessageContent,
)

import database as db
from config import ADMIN_IDS, ANNOUNCE_CHANNEL_ID, BOT_USERNAME, PAGE_SIZE
from states import (
    AddAnime,
    AddEpisode,
    DeleteAnime,
    Broadcast,
    AddChannel,
    GrantVip,
    RemoveVip,
    LinkEpisode,
    WriteToUser,
    SearchUser,
)
from keyboards import (
    admin_menu_kb,
    main_menu_kb,
    choose_anime_kb,
    confirm_kb,
    cancel_kb,
    vip_admin_menu_kb,
    vip_duration_kb,
    anime_vip_toggle_kb,
    users_list_kb,
    user_actions_kb,
    exit_only_kb,
    users_search_results_kb,
)

router = Router()


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


@router.message(Command("admin"))
async def cmd_admin(message: Message):
    if not is_admin(message.from_user.id):
        return
    await message.answer("🔧 Admin panelga xush kelibsiz.", reply_markup=admin_menu_kb())


@router.message(F.text == "⬅️ Foydalanuvchi menyusi")
async def back_to_user_menu(message: Message):
    if not is_admin(message.from_user.id):
        return
    await message.answer("Asosiy menyu:", reply_markup=main_menu_kb())


# ==================== ANIME QO'SHISH ====================

@router.message(F.text == "➕ Anime qo'shish")
async def add_anime_start(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.set_state(AddAnime.title)
    await message.answer("📝 Anime nomini kiriting:", reply_markup=cancel_kb())


@router.message(StateFilter(AddAnime), F.text == "❌ Bekor qilish")
async def add_anime_cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Bekor qilindi.", reply_markup=admin_menu_kb())


@router.message(AddAnime.title)
async def add_anime_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text)
    await state.set_state(AddAnime.description)
    await message.answer("📝 Anime haqida qisqacha ma'lumot (tavsif) kiriting:", reply_markup=cancel_kb())


@router.message(AddAnime.description)
async def add_anime_description(message: Message, state: FSMContext):
    await state.update_data(description=message.text)
    await state.set_state(AddAnime.genre)
    await message.answer(
        "🎭 Janr(lar)ni kiriting (vergul bilan, masalan: Action, Fantastika):",
        reply_markup=cancel_kb(),
    )


@router.message(AddAnime.genre)
async def add_anime_genre(message: Message, state: FSMContext):
    await state.update_data(genre=message.text)
    await state.set_state(AddAnime.year)
    await message.answer("📅 Chiqarilgan yilini kiriting:", reply_markup=cancel_kb())


@router.message(AddAnime.year)
async def add_anime_year(message: Message, state: FSMContext):
    await state.update_data(year=message.text)
    await state.set_state(AddAnime.poster)
    await message.answer("🖼 Anime posterini (rasm) yuboring:", reply_markup=cancel_kb())


async def _announce_new_anime(bot: Bot, anime_id: int, data: dict, poster_file_id: str):
    """Yangi qo'shilgan animeni (poster + ma'lumotlar bilan) e'lon kanaliga
    yuboradi. Xatolik bo'lsa (masalan bot kanalda admin emas), faqat logga
    yoziladi -- admin panel ishlashida xalaqit bermaydi."""
    if not ANNOUNCE_CHANNEL_ID:
        return
    caption = (
        f"🆕 <b>Yangi anime qo'shildi!</b>\n\n"
        f"🎬 <b>{data['title']}</b>\n"
        f"📅 Yil: {data['year']}\n"
        f"🎭 Janr: {data['genre']}\n\n"
        f"{data['description']}\n\n"
        f"🆔 Kod: <code>{anime_id}</code>\n"
        f"📥 Botda tomosha qilish uchun botga o'ting va shu kodni yuboring."
    )
    kb = None
    if BOT_USERNAME:
        deep_link = f"https://t.me/{BOT_USERNAME}?start=anime_{anime_id}"
        kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="✨ Tomosha qilish ✨", url=deep_link)
        ]])

    try:
        sent = await bot.send_photo(
            chat_id=ANNOUNCE_CHANNEL_ID, photo=poster_file_id, caption=caption, reply_markup=kb
        )
        await db.set_announce_message(anime_id, sent.chat.id, sent.message_id)
    except TelegramBadRequest as e:
        logging.warning(f"[ANIME E'LONI] Kanalga yuborib bo'lmadi ({ANNOUNCE_CHANNEL_ID}): {e}")


@router.message(AddAnime.poster, F.photo)
async def add_anime_poster(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    poster_file_id = message.photo[-1].file_id

    anime_id = await db.add_anime(
        title=data["title"],
        description=data["description"],
        poster_file_id=poster_file_id,
        genre=data["genre"],
        year=data["year"],
    )
    await state.clear()
    await message.answer(
        f"✅ Anime muvaffaqiyatli qo'shildi!\nID: <code>{anime_id}</code>\n"
        f"Endi \"🎬 Epizod qo'shish\" orqali epizodlar qo'shishingiz mumkin.",
        reply_markup=admin_menu_kb(),
    )

    await _announce_new_anime(bot, anime_id, data, poster_file_id)


@router.message(AddAnime.poster)
async def add_anime_poster_invalid(message: Message):
    await message.answer("Iltimos, rasm (poster) yuboring.")


# ==================== EPIZOD QO'SHISH ====================

@router.message(F.text == "🎬 Epizod qo'shish")
async def add_episode_start(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    rows = await db.list_anime(offset=0, limit=50)
    if not rows:
        await message.answer("Avval anime qo'shing.")
        return
    await state.set_state(AddEpisode.choose_anime)
    await message.answer("Qaysi animega epizod qo'shmoqchisiz?", reply_markup=choose_anime_kb(rows, action="epanime"))


@router.callback_query(AddEpisode.choose_anime, F.data.startswith("epanime_"))
async def add_episode_choose_anime(call: CallbackQuery, state: FSMContext):
    anime_id = int(call.data.split("_")[1])
    await state.update_data(anime_id=anime_id)
    await state.set_state(AddEpisode.episode_number)
    await call.message.answer("🔢 Epizod raqamini kiriting (masalan: 1):")
    await call.answer()


@router.message(AddEpisode.episode_number)
async def add_episode_number(message: Message, state: FSMContext):
    if not message.text.strip().isdigit():
        await message.answer("Iltimos, faqat raqam kiriting.")
        return
    await state.update_data(episode_number=int(message.text.strip()))
    await state.set_state(AddEpisode.video)
    await message.answer("🎥 Endi shu epizod videosini yuboring (yoki kanaldan forward qiling):")


@router.message(AddEpisode.video, F.video)
async def add_episode_video(message: Message, state: FSMContext):
    data = await state.get_data()
    file_id = message.video.file_id

    existing = await db.get_episode_by_number(data["anime_id"], data["episode_number"])
    if existing:
        await message.answer(
            f"⚠️ {data['episode_number']}-qism allaqachon mavjud edi, yangisi bilan almashtirilmadi. "
            f"Avval eskisini o'chiring."
        )
        await state.clear()
        return

    episode_id = await db.add_episode(data["anime_id"], data["episode_number"], file_id)
    await state.update_data(episode_id=episode_id)
    await state.set_state(AddEpisode.web_video)
    await message.answer(
        f"✅ Video saqlandi (bu — Telegram bot uchun, file_id orqali).\n\n"
        f"🌐 Endi SAYT uchun ALOHIDA video havolasini yuboring -- bu Telegramdagi videodan "
        f"mustaqil, boshqa hostingga (masalan YouTube, Google Drive, yoki to'g'ridan-to'g'ri "
        f".mp4 link beruvchi xizmat) joylangan bo'lishi kerak. Faqat to'g'ridan-to'g'ri "
        f"havolani yuboring (http:// yoki https:// bilan boshlanishi kerak).\n\n"
        f"Agar hozircha bu qadamni o'tkazib yubormoqchi bo'lsangiz, /skip yozing "
        f"(keyinroq \"🔗 Epizodni saytga bog'lash\" orqali qo'shib qo'yish mumkin)."
    )


@router.message(AddEpisode.video)
async def add_episode_video_invalid(message: Message):
    await message.answer("Iltimos, video fayl yuboring.")


@router.message(AddEpisode.web_video, Command("skip"))
async def add_episode_web_video_skip(message: Message, state: FSMContext):
    data = await state.get_data()
    anime = await db.get_anime(data["anime_id"])
    await state.clear()
    await message.answer(
        f"✅ \"{anime['title']}\" — {data['episode_number']}-qism qo'shildi!\n"
        f"ℹ️ Sayt uchun video havolasi hali qo'shilmadi -- bu epizod saytda faqat "
        f"Telegram orqali (bot deep-link) ko'rinadi.",
        reply_markup=admin_menu_kb(),
    )


@router.message(AddEpisode.web_video)
async def add_episode_web_video(message: Message, state: FSMContext):
    data = await state.get_data()
    url = (message.text or "").strip()
    if not url.lower().startswith(("http://", "https://")):
        await message.answer(
            "⚠️ Havola noto'g'ri. To'g'ridan-to'g'ri video havolasini yuboring "
            "(http:// yoki https:// bilan boshlanishi kerak) yoki /skip yozing."
        )
        return

    await db.set_episode_web_video(data["episode_id"], url)
    anime = await db.get_anime(data["anime_id"])
    await state.clear()
    await message.answer(
        f"✅ \"{anime['title']}\" — {data['episode_number']}-qism qo'shildi va saytga bog'landi!\n"
        f"🌐 Endi bu epizod saytda to'g'ridan-to'g'ri (Telegram kanalisiz) tomosha qilinadi.",
        reply_markup=admin_menu_kb(),
    )


# ==================== MAVJUD EPIZODNI SAYTGA (RETROAKTIV) BOG'LASH ====================
# Bu bo'lim "🎬 Epizod qo'shish" dan farqli o'laroq, ALLAQACHON qo'shilgan
# epizodni (masalan, funksiya qo'shilishidan oldin yuklangan yoki /skip
# bosilgan epizodni) ochiq kanaldagi postga keyinroq bog'lash uchun.

@router.message(F.text == "🔗 Epizodni saytga bog'lash")
async def link_episode_start(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    rows = await db.list_anime(offset=0, limit=50)
    if not rows:
        await message.answer("Avval anime qo'shing.")
        return
    await state.set_state(LinkEpisode.choose_anime)
    await message.answer(
        "Qaysi animening epizodini saytga bog'lamoqchisiz?",
        reply_markup=choose_anime_kb(rows, action="linkanime"),
    )


@router.callback_query(LinkEpisode.choose_anime, F.data.startswith("linkanime_"))
async def link_episode_choose_anime(call: CallbackQuery, state: FSMContext):
    anime_id = int(call.data.split("_")[1])
    await state.update_data(anime_id=anime_id)
    await state.set_state(LinkEpisode.episode_number)
    await call.message.answer("🔢 Qaysi epizod raqamini bog'lamoqchisiz? (masalan: 1):")
    await call.answer()


@router.message(LinkEpisode.episode_number)
async def link_episode_number(message: Message, state: FSMContext):
    data = await state.get_data()
    if not message.text.strip().isdigit():
        await message.answer("Iltimos, faqat raqam kiriting.")
        return
    ep_num = int(message.text.strip())
    episode = await db.get_episode_by_number(data["anime_id"], ep_num)
    if not episode:
        await message.answer(f"⚠️ {ep_num}-qism topilmadi. Boshqa raqam kiriting yoki /cancel yozing.")
        return
    await state.update_data(episode_id=episode["id"], episode_number=ep_num)
    await state.set_state(LinkEpisode.web_video_link)
    await message.answer(
        "🌐 Endi shu epizod uchun SAYTGA mo'ljallangan to'g'ridan-to'g'ri video havolasini yuboring "
        "(http:// yoki https:// bilan boshlanishi kerak)."
    )


@router.message(LinkEpisode.web_video_link)
async def link_episode_web_video(message: Message, state: FSMContext):
    data = await state.get_data()
    url = (message.text or "").strip()
    if not url.lower().startswith(("http://", "https://")):
        await message.answer(
            "⚠️ Havola noto'g'ri. To'g'ridan-to'g'ri video havolasini qayta yuboring "
            "(http:// yoki https:// bilan boshlanishi kerak)."
        )
        return

    await db.set_episode_web_video(data["episode_id"], url)
    anime = await db.get_anime(data["anime_id"])
    await state.clear()
    await message.answer(
        f"✅ \"{anime['title']}\" — {data['episode_number']}-qism saytga bog'landi!\n"
        f"🌐 Endi u saytda to'g'ridan-to'g'ri (Telegram kanalisiz) tomosha qilinadi.",
        reply_markup=admin_menu_kb(),
    )


# ==================== ANIME O'CHIRISH ====================

@router.message(F.text == "🗑 Anime o'chirish")
async def delete_anime_start(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    rows = await db.list_anime(offset=0, limit=50)
    if not rows:
        await message.answer("O'chirish uchun animelar yo'q.")
        return
    await state.set_state(DeleteAnime.choose_anime)
    await message.answer("Qaysi animeni o'chirmoqchisiz?", reply_markup=choose_anime_kb(rows, action="delanime"))


@router.callback_query(DeleteAnime.choose_anime, F.data.startswith("delanime_"))
async def delete_anime_confirm(call: CallbackQuery, state: FSMContext):
    anime_id = int(call.data.split("_")[1])
    anime = await db.get_anime(anime_id)
    await state.update_data(anime_id=anime_id)
    await call.message.answer(
        f"⚠️ \"{anime['title']}\" va uning barcha epizodlarini o'chirishni tasdiqlaysizmi?",
        reply_markup=confirm_kb(yes_cb="confirm_delanime", no_cb="cancel_delanime"),
    )
    await call.answer()


@router.callback_query(F.data == "confirm_delanime")
async def delete_anime_do(call: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    anime_id = data["anime_id"]

    anime = await db.get_anime(anime_id)
    if anime and anime["announce_chat_id"] and anime["announce_msg_id"]:
        try:
            await bot.delete_message(chat_id=anime["announce_chat_id"], message_id=anime["announce_msg_id"])
        except TelegramBadRequest as e:
            logging.warning(f"[ANIME O'CHIRISH] Kanaldagi xabarni o'chirib bo'lmadi: {e}")

    await db.delete_anime(anime_id)
    await state.clear()
    await call.message.answer("🗑 Anime o'chirildi.", reply_markup=admin_menu_kb())
    await call.answer()


@router.callback_query(F.data == "cancel_delanime")
async def delete_anime_cancel(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.answer("Bekor qilindi.", reply_markup=admin_menu_kb())
    await call.answer()


# ==================== STATISTIKA ====================

@router.message(F.text == "📊 Statistika")
async def show_stats(message: Message):
    if not is_admin(message.from_user.id):
        return
    users_count = await db.get_users_count()
    anime_count = await db.count_anime()
    await message.answer(
        f"📊 <b>Statistika</b>\n\n👤 Foydalanuvchilar: {users_count}\n🎬 Animelar: {anime_count}"
    )


# ==================== XABAR YUBORISH (BROADCAST) ====================

@router.message(F.text == "📢 Xabar yuborish")
async def broadcast_start(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.set_state(Broadcast.content)
    await message.answer("📢 Yuboriladigan xabarni kiriting (matn, rasm, video bo'lishi mumkin):")


@router.message(Broadcast.content)
async def broadcast_preview(message: Message, state: FSMContext):
    await state.update_data(chat_id=message.chat.id, message_id=message.message_id)
    await state.set_state(Broadcast.confirm)
    await message.answer(
        "Yuqoridagi xabar barcha foydalanuvchilarga yuborilsinmi?",
        reply_markup=confirm_kb(yes_cb="confirm_broadcast", no_cb="cancel_broadcast"),
    )


@router.callback_query(F.data == "confirm_broadcast")
async def broadcast_send(call: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    user_ids = await db.get_notifiable_user_ids()
    await state.clear()
    await call.message.answer(f"⏳ {len(user_ids)} ta foydalanuvchiga yuborilmoqda (bildirishnomani o'chirganlar hisobga kirmaydi)...")

    sent, failed = 0, 0
    for uid in user_ids:
        try:
            await bot.copy_message(chat_id=uid, from_chat_id=data["chat_id"], message_id=data["message_id"])
            sent += 1
        except Exception:
            failed += 1

    await call.message.answer(f"✅ Yuborildi: {sent}\n❌ Yuborilmadi: {failed}", reply_markup=admin_menu_kb())
    await call.answer()


@router.callback_query(F.data == "cancel_broadcast")
async def broadcast_cancel(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.answer("Bekor qilindi.", reply_markup=admin_menu_kb())
    await call.answer()


# ==================== FOYDALANUVCHILAR (ro'yxat / yozish / bloklash) ====================
# "👥 Foydalanuvchilar" -- barcha foydalanuvchilar username bilan ro'yxatda
# chiqadi, birinchi qatorda "🌐 HAMMAGA (ALL)" tugmasi bor (bosilsa --
# barchaga bir vaqtda e'lon yuboriladi, xuddi "📢 Xabar yuborish" kabi).
# Har bir foydalanuvchini bosganda uning profili (VIP, ko'rgan epizodlar,
# yuklagan dublyajlar) va 2 ta tugma chiqadi: 🚫 Bloklash / ✍️ Yozish.

@router.message(F.text == "👥 Foydalanuvchilar")
async def users_list_start(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.clear()
    total = await db.get_users_count()
    users = await db.get_users_page(offset=0, limit=PAGE_SIZE)
    await message.answer(
        f"👥 Jami foydalanuvchilar: <b>{total}</b>\n"
        f"💬 belgisi bilan -- adminga murojaat yozgan foydalanuvchilar "
        f"(ular ro'yxat boshida, xabarlar soni bilan) ko'rsatilgan.\n\n"
        f"Hammaga birdek e'lon qilish uchun \"🌐 HAMMAGA (ALL)\" ni bosing, "
        f"yoki ro'yxatdan kerakli foydalanuvchini tanlang:",
        reply_markup=users_list_kb(users, 0, total),
    )


@router.callback_query(F.data.startswith("userspage_"))
async def users_list_page(call: CallbackQuery):
    offset = int(call.data.split("_")[1])
    total = await db.get_users_count()
    users = await db.get_users_page(offset=offset, limit=PAGE_SIZE)
    await call.message.edit_text(
        f"👥 Jami foydalanuvchilar: <b>{total}</b>\n\nKerakli foydalanuvchini tanlang:",
        reply_markup=users_list_kb(users, offset, total),
    )
    await call.answer()


@router.callback_query(F.data == "users_all")
async def users_all_broadcast(call: CallbackQuery, state: FSMContext):
    """"HAMMAGA (ALL)" tugmasi -- xuddi "📢 Xabar yuborish" kabi, admin bitta
    xabar yozadi va u bazadagi barcha foydalanuvchilarga bir vaqtda yuboriladi."""
    await state.set_state(Broadcast.content)
    await call.message.answer(
        "📢 Barchaga bir vaqtda yuboriladigan xabarni kiriting (matn, rasm, video bo'lishi mumkin):"
    )
    await call.answer()


@router.callback_query(F.data == "users_search")
async def users_search_start(call: CallbackQuery, state: FSMContext):
    await state.set_state(SearchUser.query)
    await call.message.answer(
        "🔍 Foydalanuvchining ismi, username'i yoki ID raqamining bir qismini yozing:"
    )
    await call.answer()


@router.message(SearchUser.query)
async def users_search_results(message: Message, state: FSMContext):
    await state.clear()
    query = message.text.strip()
    results = await db.search_users(query, limit=20)
    if not results:
        await message.answer(
            f"❌ \"{query}\" bo'yicha hech kim topilmadi.",
            reply_markup=users_search_results_kb([]),
        )
        return
    await message.answer(
        f"🔍 \"{query}\" bo'yicha topildi: {len(results)} ta\n\nKerakli foydalanuvchini tanlang:",
        reply_markup=users_search_results_kb(results),
    )


async def _send_user_info_card(send, user_id: int):
    """Foydalanuvchi profil kartasini chiqaradi -- ro'yxatdagi tugma orqali
    ham, inline qidiruv orqali kelgan /showuser_ buyrug'i orqali ham
    ishlatiladi. `send` -- message.answer yoki call.message.answer."""
    info = await db.get_user_full_info(user_id)
    if not info:
        await send("Foydalanuvchi topilmadi.")
        return

    username = f"@{info['username']}" if info["username"] else "—"
    if info["vip"]:
        vip_status = "♾ Umrbod" if not info["vip_expires_at"] else f"{info['vip_expires_at'][:10]} gacha"
    else:
        vip_status = "Yo'q"
    blocked_status = "🚫 Bloklangan" if info["blocked"] else "✅ Faol"
    joined = info["joined_at"][:10] if info["joined_at"] else "—"

    text = (
        f"👤 <b>Foydalanuvchi profili</b>\n\n"
        f"🆔 ID: <code>{info['user_id']}</code>\n"
        f"Username: {username}\n"
        f"Ism: {info['full_name'] or '—'}\n"
        f"📅 Qo'shilgan: {joined}\n"
        f"Holati: {blocked_status}\n"
        f"👑 VIP: {vip_status}\n"
        f"🎬 Ko'rgan epizodlar: {info['watched_count']}\n"
        f"🎙 Yuklagan dublyajlar: {info['dubs_count']}\n"
        f"📨 Adminga yozgan murojaatlar: {info['msg_count']}\n\n"
        f"Botdan qanday foydalangani shu yerda -- kerakli amalni tanlang:"
    )
    await send(text, reply_markup=user_actions_kb(user_id, bool(info["blocked"])))


@router.callback_query(F.data.startswith("userinfo_"))
async def user_info_show(call: CallbackQuery):
    user_id = int(call.data.split("_")[1])
    await _send_user_info_card(call.message.answer, user_id)
    await call.answer()


# ---------- INLINE QIDIRUV: yozayotganda, yubormasdan turib natija chiqishi ----------
# Bu ishlashi uchun @BotFather'da botga bir marta /setinline orqali inline
# rejim yoqilgan bo'lishi kerak. Admin botning O'ZINING chatida
# "@BotUsername qidiruv_so'zi" deb yozishni boshlaydi -- Telegram hali
# yubormasdan turib mos foydalanuvchilarni ro'yxat qilib ko'rsatadi.
# Birini tanlasa, u "/showuser_<id>" degan xabar sifatida shu chatga
# yuboriladi va bot uni ushlab profilni ochadi.

@router.inline_query()
async def users_inline_search(inline_query: InlineQuery):
    if not is_admin(inline_query.from_user.id):
        await inline_query.answer([], cache_time=1, is_personal=True)
        return

    query = inline_query.query.strip()
    if not query:
        await inline_query.answer([], cache_time=1, is_personal=True)
        return

    found = await db.search_users(query, limit=20)
    articles = []
    for u in found:
        username = f"@{u['username']}" if u["username"] else "username yo'q"
        name = u["full_name"] or "Ism yo'q"
        blocked_mark = "🚫 " if u["blocked"] else ""
        articles.append(
            InlineQueryResultArticle(
                id=str(u["user_id"]),
                title=f"{blocked_mark}{username}",
                description=f"{name} • ID: {u['user_id']}",
                input_message_content=InputTextMessageContent(
                    message_text=f"/showuser_{u['user_id']}"
                ),
            )
        )

    await inline_query.answer(articles, cache_time=1, is_personal=True)


@router.message(F.text.regexp(r"^/showuser_(\d+)$"))
async def show_user_via_inline(message: Message):
    if not is_admin(message.from_user.id):
        return
    user_id = int(message.text.split("_")[1])
    await _send_user_info_card(message.answer, user_id)


@router.callback_query(F.data.startswith("blockuser_"))
async def user_block(call: CallbackQuery):
    user_id = int(call.data.split("_")[1])
    await db.block_user(user_id)
    await call.message.edit_reply_markup(reply_markup=user_actions_kb(user_id, True))
    await call.answer("🚫 Foydalanuvchi bloklandi.")


@router.callback_query(F.data.startswith("unblockuser_"))
async def user_unblock(call: CallbackQuery):
    user_id = int(call.data.split("_")[1])
    await db.unblock_user(user_id)
    await call.message.edit_reply_markup(reply_markup=user_actions_kb(user_id, False))
    await call.answer("✅ Blokdan chiqarildi.")


@router.callback_query(F.data.startswith("writeuser_"))
async def user_write_start(call: CallbackQuery, state: FSMContext):
    user_id = int(call.data.split("_")[1])
    await state.update_data(target_user_id=user_id)
    await state.set_state(WriteToUser.message)
    await call.message.answer(
        f"✍️ <code>{user_id}</code> ga shaxsan yuboriladigan xabarni kiriting "
        f"(matn, rasm yoki video bo'lishi mumkin):"
    )
    await call.answer()


@router.message(WriteToUser.message)
async def user_write_send(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    target_user_id = data["target_user_id"]
    await state.clear()
    try:
        await bot.copy_message(chat_id=target_user_id, from_chat_id=message.chat.id, message_id=message.message_id)
        content = message.text or message.caption or "· media xabar"
        await db.log_message(target_user_id, "out", content)
        await message.answer("✅ Xabar foydalanuvchiga yuborildi.", reply_markup=exit_only_kb())
    except Exception as e:
        await message.answer(f"❌ Yuborib bo'lmadi: {e}", reply_markup=exit_only_kb())


@router.callback_query(F.data == "users_exit")
async def users_exit(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.answer("🔧 Admin panel:", reply_markup=admin_menu_kb())
    await call.answer()


# ==================== KANAL SOZLASH (majburiy obuna) ====================

@router.message(F.text == "📡 Kanal sozlash")
async def channel_settings(message: Message):
    if not is_admin(message.from_user.id):
        return
    channels = await db.get_required_channels()
    text = "📡 <b>Majburiy obuna kanallari</b>\n\n"
    if not channels:
        text += "Hozircha kanal qo'shilmagan.\n\n"
    else:
        for ch in channels:
            text += f"• {ch['title']} (<code>{ch['chat_id']}</code>) — /delch_{ch['id']}\n"
    text += "\nYangi kanal qo'shish uchun /addch buyrug'ini yuboring."
    await message.answer(text)


@router.message(Command("addch"))
async def add_channel_start(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.set_state(AddChannel.chat_id)
    await message.answer(
        "Kanal chat_id yoki username kiriting (masalan: @kanal_username yoki -1001234567890).\n"
        "⚠️ Bot shu kanalda ADMIN bo'lishi shart!"
    )


@router.message(AddChannel.chat_id)
async def add_channel_chatid(message: Message, state: FSMContext):
    await state.update_data(chat_id=message.text.strip())
    await state.set_state(AddChannel.title)
    await message.answer("Kanal nomini kiriting (foydalanuvchiga ko'rinadigan nom):")


@router.message(AddChannel.title)
async def add_channel_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text.strip())
    await state.set_state(AddChannel.link)
    await message.answer("Kanalga qo'shilish havolasini kiriting (https://t.me/...):")


@router.message(AddChannel.link)
async def add_channel_link(message: Message, state: FSMContext):
    data = await state.get_data()
    await db.add_required_channel(data["chat_id"], data["title"], message.text.strip())
    await state.clear()
    await message.answer("✅ Kanal qo'shildi.", reply_markup=admin_menu_kb())


@router.message(F.text.regexp(r"^/delch_(\d+)$"))
async def delete_channel(message: Message):
    if not is_admin(message.from_user.id):
        return
    row_id = int(message.text.split("_")[1])
    await db.remove_required_channel(row_id)
    await message.answer("🗑 Kanal o'chirildi.")


# ==================== VIP BOSHQARISH ====================

@router.message(F.text == "👑 VIP boshqarish")
async def vip_menu(message: Message):
    if not is_admin(message.from_user.id):
        return
    await message.answer("👑 VIP foydalanuvchilarni boshqarish:", reply_markup=vip_admin_menu_kb())


@router.callback_query(F.data == "vip_grant")
async def vip_grant_start(call: CallbackQuery, state: FSMContext):
    await state.set_state(GrantVip.user_id)
    await call.message.answer("Foydalanuvchining Telegram ID raqamini kiriting:")
    await call.answer()


@router.message(GrantVip.user_id)
async def vip_grant_userid(message: Message, state: FSMContext):
    if not message.text.strip().isdigit():
        await message.answer("Iltimos, faqat raqam (ID) kiriting.")
        return
    await state.update_data(user_id=int(message.text.strip()))
    await state.set_state(GrantVip.days)
    await message.answer("Muddatni tanlang:", reply_markup=vip_duration_kb())


@router.callback_query(GrantVip.days, F.data.startswith("vipdays_"))
async def vip_grant_finish(call: CallbackQuery, state: FSMContext, bot: Bot):
    days = int(call.data.split("_")[1])
    data = await state.get_data()
    user_id = data["user_id"]
    await db.grant_vip(user_id, days=None if days == 0 else days)
    await state.clear()

    muddat = "umrbod" if days == 0 else f"{days} kunga"
    await call.message.answer(f"✅ <code>{user_id}</code> foydalanuvchiga {muddat} VIP status berildi.", reply_markup=admin_menu_kb())

    try:
        await bot.send_message(
            user_id,
            f"🎉 Tabriklaymiz! Sizga {muddat} VIP status berildi.\n"
            f"Endi barcha VIP animelarga va majburiy obunasiz botdan foydalanishingiz mumkin!"
        )
    except Exception:
        pass
    await call.answer()


@router.callback_query(F.data == "vip_remove")
async def vip_remove_start(call: CallbackQuery, state: FSMContext):
    await state.set_state(RemoveVip.user_id)
    await call.message.answer("VIP olib tashlanadigan foydalanuvchi ID raqamini kiriting:")
    await call.answer()


@router.message(RemoveVip.user_id)
async def vip_remove_finish(message: Message, state: FSMContext):
    if not message.text.strip().isdigit():
        await message.answer("Iltimos, faqat raqam (ID) kiriting.")
        return
    user_id = int(message.text.strip())
    await db.remove_vip(user_id)
    await state.clear()
    await message.answer(f"🗑 <code>{user_id}</code> foydalanuvchidan VIP status olib tashlandi.", reply_markup=admin_menu_kb())


@router.callback_query(F.data == "vip_list")
async def vip_list(call: CallbackQuery):
    rows = await db.list_vip_users()
    if not rows:
        await call.message.answer("Hozircha VIP foydalanuvchilar yo'q.")
        await call.answer()
        return

    text = "👑 <b>VIP foydalanuvchilar</b>\n\n"
    for r in rows:
        muddat = "umrbod" if not r["expires_at"] else r["expires_at"][:10]
        text += f"• <code>{r['user_id']}</code> — {muddat}\n"
    await call.message.answer(text)
    await call.answer()


# ==================== ANIMENI VIP QILISH ====================

@router.message(F.text == "🔒 Anime VIP qilish")
async def anime_vip_start(message: Message):
    if not is_admin(message.from_user.id):
        return
    rows = await db.list_anime(offset=0, limit=50)
    if not rows:
        await message.answer("Hozircha animelar yo'q.")
        return
    await message.answer("Qaysi animeni sozlamoqchisiz?", reply_markup=choose_anime_kb(rows, action="vipanimepick"))


@router.callback_query(F.data.startswith("vipanimepick_"))
async def anime_vip_toggle_menu(call: CallbackQuery):
    anime_id = int(call.data.split("_")[1])
    anime = await db.get_anime(anime_id)
    status = "🔒 VIP-only" if anime["vip_only"] else "🔓 Hammaga ochiq"
    await call.message.answer(
        f"\"{anime['title']}\" hozirgi holati: {status}",
        reply_markup=anime_vip_toggle_kb(anime_id, anime["vip_only"]),
    )
    await call.answer()


@router.callback_query(F.data.startswith("vipanime_on_"))
async def anime_vip_on(call: CallbackQuery):
    anime_id = int(call.data.split("_")[2])
    await db.set_anime_vip(anime_id, True)
    await call.message.edit_text("🔒 Bu anime endi faqat VIP foydalanuvchilar uchun.")
    await call.answer()


@router.callback_query(F.data.startswith("vipanime_off_"))
async def anime_vip_off(call: CallbackQuery):
    anime_id = int(call.data.split("_")[2])
    await db.set_anime_vip(anime_id, False)
    await call.message.edit_text("🔓 Bu anime endi hammaga ochiq.")
    await call.answer()