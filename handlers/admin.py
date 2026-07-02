from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

import database as db
from config import ADMIN_IDS
from states import AddAnime, AddEpisode, DeleteAnime, Broadcast, AddChannel
from keyboards import admin_menu_kb, main_menu_kb, choose_anime_kb, confirm_kb

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
    await message.answer("📝 Anime nomini kiriting:")


@router.message(AddAnime.title)
async def add_anime_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text)
    await state.set_state(AddAnime.description)
    await message.answer("📝 Anime haqida qisqacha ma'lumot (tavsif) kiriting:")


@router.message(AddAnime.description)
async def add_anime_description(message: Message, state: FSMContext):
    await state.update_data(description=message.text)
    await state.set_state(AddAnime.genre)
    await message.answer("🎭 Janr(lar)ni kiriting (vergul bilan, masalan: Action, Fantastika):")


@router.message(AddAnime.genre)
async def add_anime_genre(message: Message, state: FSMContext):
    await state.update_data(genre=message.text)
    await state.set_state(AddAnime.year)
    await message.answer("📅 Chiqarilgan yilini kiriting:")


@router.message(AddAnime.year)
async def add_anime_year(message: Message, state: FSMContext):
    await state.update_data(year=message.text)
    await state.set_state(AddAnime.poster)
    await message.answer("🖼 Anime posterini (rasm) yuboring:")


@router.message(AddAnime.poster, F.photo)
async def add_anime_poster(message: Message, state: FSMContext):
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

    await db.add_episode(data["anime_id"], data["episode_number"], file_id)
    anime = await db.get_anime(data["anime_id"])
    await state.clear()
    await message.answer(
        f"✅ \"{anime['title']}\" — {data['episode_number']}-qism qo'shildi!",
        reply_markup=admin_menu_kb(),
    )


@router.message(AddEpisode.video)
async def add_episode_video_invalid(message: Message):
    await message.answer("Iltimos, video fayl yuboring.")


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
async def delete_anime_do(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await db.delete_anime(data["anime_id"])
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
    user_ids = await db.get_all_user_ids()
    await state.clear()
    await call.message.answer(f"⏳ {len(user_ids)} ta foydalanuvchiga yuborilmoqda...")

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
