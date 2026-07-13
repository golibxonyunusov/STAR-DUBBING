"""Har oyning 1-sanasida o'tgan oy g'oliblarini (eng faol tomoshabin va eng
zo'r dublyajchi) avtomatik aniqlaydi, hammaga e'lon qiladi, g'oliblarga
shaxsiy tabrik yuboradi va adminlarga xabar beradi (Telegram Premium'ni
qo'lda sovg'a qilishlari uchun -- buni Bot API orqali avtomatik qilib
bo'lmaydi)."""

import asyncio
import logging
from datetime import datetime

from aiogram import Bot

import database as db
from config import ADMIN_IDS

CHECK_INTERVAL_SECONDS = 3600  # har soatda tekshiradi (kam resurs sarflaydi)


def _prev_month_range(today: datetime) -> tuple[str, str, str]:
    """Bugungi sanaga asosan O'TGAN OY chegaralarini (ISO satr) va oy
    nomini ("2026-06" kabi) qaytaradi."""
    first_of_this_month = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    end = first_of_this_month
    if first_of_this_month.month == 1:
        start = first_of_this_month.replace(year=first_of_this_month.year - 1, month=12)
    else:
        start = first_of_this_month.replace(month=first_of_this_month.month - 1)
    month_label = start.strftime("%Y-%m")
    return start.isoformat(), end.isoformat(), month_label


def _display_name(row: dict) -> str:
    if row.get("full_name"):
        return row["full_name"]
    if row.get("username"):
        return f"@{row['username']}"
    return f"ID{row['user_id']}"


async def _process_month_if_needed(bot: Bot):
    now = datetime.utcnow()
    if now.day != 1:
        return  # faqat oyning 1-kunida ishlaydi

    start_iso, end_iso, month_label = _prev_month_range(now)

    viewer_done = await db.has_monthly_winner_recorded(month_label, "viewer")
    dubber_done = await db.has_monthly_winner_recorded(month_label, "dubber")
    if viewer_done and dubber_done:
        return  # bu oy uchun allaqachon e'lon qilingan (server qayta ishga tushgan bo'lishi mumkin)

    viewer, viewer_count = await db.get_top_viewer_for_period(start_iso, end_iso)
    dubber, dubber_count = await db.get_top_dubber_for_period(start_iso, end_iso)

    lines = [f"🏆 <b>{month_label} oyining g'oliblari!</b>\n"]

    if viewer and viewer_count > 0:
        lines.append(f"👤 <b>Eng faol tomoshabin:</b> {_display_name(viewer)} — {viewer_count} ta epizod ko'rdi!")
        if not viewer_done:
            await db.record_monthly_winner(month_label, "viewer", viewer["user_id"], viewer_count)
    else:
        lines.append("👤 Eng faol tomoshabin: bu oy hech kim epizod ko'rmadi.")

    if dubber and dubber_count > 0:
        lines.append(f"🎙 <b>Eng zo'r dublyajchi:</b> {_display_name(dubber)} — {dubber_count} marta 5⭐ baho oldi!")
        if not dubber_done:
            await db.record_monthly_winner(month_label, "dubber", dubber["user_id"], dubber_count)
    else:
        lines.append("🎙 Eng zo'r dublyajchi: bu oy hech kim 5⭐ olmadi.")

    lines.append("\n🎁 G'oliblarga <b>Telegram Premium</b> sovg'a qilinadi!")
    lines.append("Keyingi oy SIZ ham g'olib bo'lishingiz mumkin — faolroq bo'ling! 🚀")
    announcement = "\n".join(lines)

    # 1) Barcha foydalanuvchilarga e'lon (bildirishnomani o'chirmaganlarga)
    user_ids = await db.get_notifiable_user_ids()
    for uid in user_ids:
        try:
            await bot.send_message(uid, announcement)
        except Exception:
            pass
        await asyncio.sleep(0.05)  # Telegram flood-limitiga tegmaslik uchun

    # 2) G'oliblarga shaxsiy tabrik
    for winner, count, label in (
        (viewer, viewer_count, "eng faol tomoshabin"),
        (dubber, dubber_count, "eng zo'r dublyajchi"),
    ):
        if winner and count > 0:
            try:
                await bot.send_message(
                    winner["user_id"],
                    f"🎉 Tabriklaymiz! Siz o'tgan oyning <b>{label}i</b> bo'ldingiz!\n"
                    f"🎁 Sizga <b>Telegram Premium</b> sovg'a qilinadi -- tez orada "
                    f"administrator siz bilan bog'lanadi.",
                )
            except Exception:
                pass

    # 3) Adminlarga xabar -- kimga qo'lda Premium sovg'a qilish kerakligini bilishlari uchun
    admin_lines = [f"📊 <b>{month_label}</b> oyi g'oliblari aniqlandi:\n"]
    if viewer and viewer_count > 0:
        uname = f"@{viewer['username']}" if viewer["username"] else "username yo'q"
        admin_lines.append(f"👤 Tomoshabin: {viewer['full_name']} ({uname}, ID: <code>{viewer['user_id']}</code>) — {viewer_count} epizod")
    if dubber and dubber_count > 0:
        uname = f"@{dubber['username']}" if dubber["username"] else "username yo'q"
        admin_lines.append(f"🎙 Dublyajchi: {dubber['full_name']} ({uname}, ID: <code>{dubber['user_id']}</code>) — {dubber_count} ta 5⭐")
    admin_lines.append("\n👉 Ularga qo'lda Telegram Premium sovg'a qiling (Telegram profilida \"Gift Premium\").")
    admin_text = "\n".join(admin_lines)
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(admin_id, admin_text)
        except Exception:
            pass

    logging.info(f"[OYLIK SOVRIN] {month_label} oyi g'oliblari e'lon qilindi.")


async def monthly_rewards_loop(bot: Bot):
    """Fon vazifasi -- botning butun umri davomida har soatda tekshiradi,
    oyning 1-kuni bo'lsa (va hali e'lon qilinmagan bo'lsa) g'oliblarni
    aniqlab e'lon qiladi."""
    while True:
        try:
            await _process_month_if_needed(bot)
        except Exception:
            logging.exception("[OYLIK SOVRIN] Xatolik yuz berdi:")
        await asyncio.sleep(CHECK_INTERVAL_SECONDS)
