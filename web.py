"""
STAR DUBBING veb-sayti.

Bu -- botning o'zi bilan bir joyda (Render'da) ishlaydigan, o'sha SQLite
ma'lumotlar bazasidan foydalanadigan ochiq (public) katalog sayti.

MUHIM TEXNIK IZOH: epizod videolari Telegram serverida (file_id orqali)
saqlanadi, veb-brauzerda to'g'ridan-to'g'ri ijro etib bo'lmaydi (bot API
orqali katta fayllarni yuklab olish imkoni cheklangan). Shuning uchun sayt
videoni o'zida ko'rsatmaydi -- "Tomosha qilish" tugmasi Telegram botini
ochib, videoni o'sha yerda avtomatik yuboradi (deep-link orqali).

DIZAYN YO'NALISHI: "yulduzli osmon / kosmik anime" estetikasi -- bu
Telegram kanalidagi STAR DUBBING logotipiga (galaktika, yulduzlar, tungi
osmonga tikilgan qahramon) mos keladi. Signature elementlar: tirik
yulduzli fon (twinkle + otar yulduz animatsiyasi), "konstellyatsiya"
uslubidagi bo'lim ajratgichlari va gradientli STAR/DUBBING wordmark.
"""

import html
import json
import random
from urllib.parse import quote

import aiohttp
from aiohttp import web

import database as db
from config import GEMINI_API_KEY, ASSISTANT_MODEL, BOT_USERNAME, PAGE_SIZE

ACCENT = "#9b8cff"

# Google Gemini API (BEPUL tarif) -- model nomi URL ichiga qo'yiladi.
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
ASSISTANT_SYSTEM_PROMPT = (
    "Sen STAR DUBBING anime dublyaj saytining sayt-ichi AI yordamchisisan. "
    "Foydalanuvchilarga sayt bo'yicha (animelarni topish, janrlar, TOP reyting, "
    "VIP, Telegram bot orqali tomosha qilish) yordam berasan, shuningdek umumiy "
    "savollarga ham javob berasan. Foydalanuvchi qanday tilda yozsa (o'zbek, rus, "
    "ingliz va h.k.), o'sha tilda javob ber -- aks holda o'zbek tilida javob ber. "
    "Javoblaring qisqa, aniq va do'stona bo'lsin. Foydalanuvchi rasm yoki hujjat "
    "(PDF/matn) biriktirsa, uni ko'rib tahlil qila olasan. Video yoki audio fayl "
    "biriktirilsa, uni bevosita ko'ra/eshita olmasligingni ochiq ayt, lekin fayl "
    "nomi/tavsifi asosida yordam berishga harakat qil."
)

SESSION_COOKIE = "sid"
THEME_COOKIE = "theme"


# ---------- SESSIYA / PROFIL YORDAMCHILARI ----------

async def get_current_user(request):
    """Cookie'dagi sessiya ID'si orqali joriy foydalanuvchini topadi.
    Topilmasa None qaytaradi (mehmon holati)."""
    session_id = request.cookies.get(SESSION_COOKIE)
    if not session_id:
        return None
    user_id = await db.get_session_user_id(session_id)
    if not user_id:
        return None
    user = await db.get_user(user_id)
    if not user:
        return None
    settings = await db.get_user_settings(user_id)
    vip = await db.get_vip(user_id)
    return {"user_id": user_id, "user": user, "settings": settings, "vip": vip}


def get_theme(request, current_user) -> str:
    if current_user and current_user["settings"]["theme"]:
        return current_user["settings"]["theme"]
    theme = request.cookies.get(THEME_COOKIE)
    return theme if theme in ("dark", "light") else "dark"


# ---------- STIL (CSS) ----------
# Alohida string sifatida saqlanadi -- shunda base_page() f-string ichida
# jingalak qavslarni ikkilantirish shart bo'lmaydi.

STYLES = """
  :root {
    --bg: #06060c;
    --bg-a: #0b0a1a;
    --bg-b: #120c22;
    --panel: #12111f;
    --panel-hi: #191830;
    --line: #262244;
    --line-soft: #1d1a30;
    --ink: #f3f1fb;
    --muted: #8d8aa8;
    --violet: #9b8cff;
    --violet-deep: #6c5ce7;
    --blue: #5aa7ff;
    --pink: #d6a6ff;
    --horizon: #ffb37a;
    --vip: #ff5d7a;
    --ok: #5aa7ff;
  }
  /* ---- kunduzgi (light) mavzu -- deyarli barcha ranglar CSS
     o'zgaruvchilariga bog'langani uchun shu joyda qayta belgilash kifoya ---- */
  html[data-theme="light"] {
    --bg: #f3f2fb;
    --bg-a: #ffffff;
    --bg-b: #ece8fb;
    --panel: #ffffff;
    --panel-hi: #f1eefc;
    --line: #e1ddf3;
    --line-soft: #ebe8f8;
    --ink: #191530;
    --muted: #6b6785;
    --violet: #6c5ce7;
    --violet-deep: #5b48d0;
    --blue: #2f7fe0;
    --pink: #b25fe0;
    --horizon: #e0812f;
    --vip: #e0355a;
    --ok: #2f7fe0;
  }
  html[data-theme="light"] body { background-attachment: fixed; }
  html[data-theme="light"] .star-dot { background: #6c5ce7; }
  html[data-theme="light"] .card .sub-strip {
    background: linear-gradient(180deg, transparent, #ffffffea 45%);
  }
  html[data-theme="light"] .badge-vip { background: #ffffffd0; }
  html[data-theme="light"] .live-results { background: #ffffff; }
  /* Oq matnga tayangan gradient yozuvlar kunduzgi fonda deyarli
     ko'rinmay qolgani uchun -- shu yerda alohida qayta belgilanadi. */
  html[data-theme="light"] header {
    background: rgba(255,255,255,0.82);
  }
  html[data-theme="light"] .wordmark,
  html[data-theme="light"] .detail .meta h1 {
    background: linear-gradient(160deg, var(--violet-deep) 0%, var(--violet) 55%, var(--blue) 100%);
    -webkit-background-clip: text; background-clip: text; color: transparent;
    filter: drop-shadow(0 4px 26px #6c5ce733);
  }
  html[data-theme="light"] .logo .grad-txt {
    background: linear-gradient(135deg, var(--violet-deep) 10%, var(--violet) 55%, var(--blue) 90%);
    -webkit-background-clip: text; background-clip: text; color: transparent;
  }
  html[data-theme="light"] .logo .star-ic {
    background: linear-gradient(135deg, var(--violet-deep), var(--blue) 70%);
    -webkit-background-clip: text; background-clip: text; color: transparent;
    filter: drop-shadow(0 0 6px #6c5ce740);
  }
  html[data-theme="light"] .shooting-star { background: linear-gradient(90deg, var(--violet), transparent); }
  html[data-theme="light"] .shooting-star,
  html[data-theme="light"] .star-dot { filter: none; }
  html[data-theme="light"] .card .poster-wrap,
  html[data-theme="light"] .detail .poster-big-wrap { background: var(--panel-hi); }
  html[data-theme="light"] ::-webkit-scrollbar-thumb { background: #d3cdef; }
  html[data-theme="light"] .cta-primary .play { background: #ffffff40; }
  html[data-theme="light"] .lock-notice {
    background: repeating-linear-gradient(135deg, #fdeef2 0 10px, #fbe4ea 10px 20px);
    border-color: #ff5d7a66; color: #b23a55;
  }
  * { box-sizing: border-box; }
  html { scroll-behavior: smooth; }
  @media (prefers-reduced-motion: reduce) {
    *:not(.marquee-track) { animation: none !important; }
    *, *::before, *::after { transition: none !important; }
    /* Animatsiya o'chirilganda ham kontent ko'rinishi shart -- .card va
       shu kabi elementlar boshlang'ich holati opacity:0 bo'lgani uchun,
       animatsiyasiz ular abadiy ko'rinmas bo'lib qolardi. */
    .card { opacity: 1 !important; transform: none !important; }
    .star-dot { opacity: var(--max-op, .6) !important; }
    /* .marquee-track animatsiyasi ataylab qoldirilgan -- u sof bezak emas,
       balki yuqoridagi yugurib turuvchi matn orqali ma'lumot uzatadi. */
    .marquee-track { animation: marquee 20s linear infinite !important; }
  }
  body {
    margin: 0;
    background:
      radial-gradient(1000px 600px at 15% -10%, #6c5ce733, transparent 60%),
      radial-gradient(900px 560px at 90% 0%, #5aa7ff22, transparent 60%),
      radial-gradient(1200px 700px at 50% 110%, #ffb37a14, transparent 60%),
      linear-gradient(180deg, var(--bg-a), var(--bg) 40%, var(--bg-b));
    background-attachment: fixed;
    color: var(--ink);
    font-family: 'Inter', 'Segoe UI', sans-serif;
    line-height: 1.6;
    min-height: 100vh;
    position: relative;
  }
  ::selection { background: var(--violet); color: #0b0a17; }
  ::-webkit-scrollbar { width: 10px; }
  ::-webkit-scrollbar-track { background: var(--bg); }
  ::-webkit-scrollbar-thumb { background: #2a2750; border-radius: 10px; }
  a { color: inherit; text-decoration: none; }
  .mono { font-family: 'IBM Plex Mono', monospace; }

  /* ---- starfield (fixed, decorative, behind everything) ---- */
  #starfield {
    position: fixed; inset: 0; z-index: 0; overflow: hidden; pointer-events: none;
  }
  .star-dot {
    position: absolute; border-radius: 50%; background: #fff;
    animation: twinkle linear infinite;
  }
  @keyframes twinkle {
    0%, 100% { opacity: var(--min-op, .15); }
    50% { opacity: var(--max-op, .9); }
  }
  .shooting-star {
    position: absolute; width: 140px; height: 2px; border-radius: 2px;
    background: linear-gradient(90deg, #fff, transparent);
    filter: drop-shadow(0 0 6px #ffffffaa);
    animation: shoot 1.6s linear forwards;
    opacity: 0;
  }
  @keyframes shoot {
    0% { opacity: 0; transform: translate(0,0) rotate(-18deg); }
    8% { opacity: 1; }
    85% { opacity: .7; }
    100% { opacity: 0; transform: translate(-620px, 220px) rotate(-18deg); }
  }
  header, main, footer { position: relative; z-index: 1; }

  /* ---- header ---- */
  header {
    position: sticky; top: 0; z-index: 20;
    background: rgba(8,7,17,0.78);
    backdrop-filter: blur(16px) saturate(150%);
    border-bottom: 1px solid var(--line);
  }
  .rail {
    display: flex; align-items: center; justify-content: space-between;
    gap: 16px; padding: 6px 32px;
    font-family: 'IBM Plex Mono', monospace; font-size: 11px;
    color: var(--muted); border-bottom: 1px dashed var(--line-soft);
    letter-spacing: 0.4px; overflow: hidden;
  }
  .marquee { flex: 1; overflow: hidden; mask-image: linear-gradient(90deg, transparent, #000 6%, #000 94%, transparent); }
  .marquee-track {
    display: inline-flex; white-space: nowrap; gap: 28px;
    animation: marquee 20s linear infinite;
    padding-right: 28px;
  }
  @keyframes marquee { from { transform: translateX(0); } to { transform: translateX(-50%); } }
  .rail .on-air { display: flex; align-items: center; gap: 7px; color: var(--ok); flex-shrink: 0; }
  .rec-dot {
    width: 7px; height: 7px; border-radius: 50%; background: var(--vip);
    box-shadow: 0 0 0 0 #ff5d7a70;
    animation: pulse 1.6s infinite;
  }
  .dot-blue { background: var(--blue); box-shadow: 0 0 0 0 #5aa7ff70; }
  @keyframes pulse {
    0% { box-shadow: 0 0 0 0 currentColor; opacity: 1; }
    70% { box-shadow: 0 0 0 6px transparent; opacity: .6; }
    100% { box-shadow: 0 0 0 0 transparent; opacity: 1; }
  }
  header .bar {
    padding: 14px 32px;
    display: flex; align-items: center; justify-content: space-between;
    gap: 20px; flex-wrap: wrap;
  }
  .logo {
    font-family: 'Oswald', sans-serif; font-weight: 700; font-size: 21px;
    letter-spacing: 0.5px; text-transform: uppercase;
    display: flex; align-items: center; gap: 8px; color: var(--ink);
  }
  .logo .star-ic {
    display: inline-flex; font-size: 18px;
    background: linear-gradient(135deg, #fff, var(--violet) 60%, var(--blue));
    -webkit-background-clip: text; background-clip: text; color: transparent;
    filter: drop-shadow(0 0 8px #9b8cff70);
  }
  .logo .grad-txt {
    background: linear-gradient(135deg, #fff 10%, #d9d0ff 45%, var(--violet) 80%);
    -webkit-background-clip: text; background-clip: text; color: transparent;
  }
  nav { display: flex; gap: 4px; font-size: 13px; font-weight: 600; }
  nav a {
    color: var(--muted); padding: 8px 15px; border-radius: 3px;
    text-transform: uppercase; letter-spacing: 0.6px; font-size: 12px;
    border-bottom: 2px solid transparent;
    transition: all .2s;
  }
  nav a.active, nav a:hover { color: var(--ink); border-bottom-color: var(--violet); }
  .search-wrap { position: relative; min-width: 240px; }
  .search-box {
    display: flex; align-items: center; gap: 9px;
    background: var(--panel); border: 1px solid var(--line); border-radius: 5px;
    padding: 10px 16px; width: 100%;
    transition: border-color .2s, box-shadow .2s;
  }
  .search-box:focus-within { border-color: var(--violet); box-shadow: 0 0 0 3px #9b8cff1f; }
  .search-box span { color: var(--muted); font-size: 13px; }
  .search-box input {
    background: transparent; border: none; outline: none; color: var(--ink);
    font-size: 13.5px; width: 100%; font-family: 'IBM Plex Mono', monospace;
  }
  .search-box input::placeholder { color: var(--muted); }
  .live-results {
    position: absolute; top: calc(100% + 8px); left: 0; right: 0; z-index: 30;
    background: #100f1d; border: 1px solid var(--line); border-radius: 8px;
    overflow: hidden; box-shadow: 0 24px 50px -18px #000000c0;
    display: none; max-height: 420px; overflow-y: auto;
  }
  .live-results.show { display: block; }
  .live-item {
    display: flex; align-items: center; gap: 12px; padding: 9px 13px;
    border-bottom: 1px solid var(--line-soft); transition: background .15s;
  }
  .live-item:last-child { border-bottom: none; }
  .live-item:hover, .live-item.sel { background: var(--panel-hi); }
  .live-item .thumb {
    width: 34px; height: 46px; border-radius: 3px; object-fit: cover;
    background: var(--panel-hi); flex-shrink: 0;
  }
  .live-item .info { min-width: 0; flex: 1; }
  .live-item .t {
    font-size: 13px; font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  }
  .live-item .m { font-size: 11px; color: var(--muted); font-family: 'IBM Plex Mono', monospace; }
  .live-empty { padding: 16px; text-align: center; color: var(--muted); font-size: 12.5px; }
  .live-more {
    display: block; text-align: center; padding: 10px; font-size: 12px;
    color: var(--violet); font-weight: 700; background: var(--panel);
    letter-spacing: 0.4px; text-transform: uppercase;
  }
  .live-more:hover { background: var(--panel-hi); }

  main { max-width: 1180px; margin: 0 auto; padding: 0 28px 70px; }

  /* ---- hero ---- */
  .hero { text-align: center; padding: 72px 16px 30px; position: relative; }
  .hero .eyebrow {
    display: inline-flex; align-items: center; gap: 8px;
    font-family: 'IBM Plex Mono', monospace; font-size: 11.5px; font-weight: 500;
    color: var(--pink); letter-spacing: 1px; margin-bottom: 26px;
    padding: 6px 14px; border: 1px solid #d6a6ff40; border-radius: 30px;
    background: #d6a6ff0d;
  }
  .wordmark {
    font-family: 'Oswald', sans-serif; font-weight: 700;
    font-size: clamp(46px, 11vw, 92px); line-height: 0.92; margin: 0 0 22px;
    text-transform: uppercase; letter-spacing: 1px;
    background: linear-gradient(160deg, #ffffff 5%, #d9d0ff 35%, var(--violet) 65%, var(--blue) 100%);
    -webkit-background-clip: text; background-clip: text; color: transparent;
    filter: drop-shadow(0 4px 40px #6c5ce755);
  }
  .wordmark span { display: block; }
  .tagline {
    max-width: 560px; margin: 0 auto; color: var(--muted); font-size: 15.5px;
  }
  .hero-ctas {
    display: flex; gap: 14px; justify-content: center; flex-wrap: wrap;
    margin-top: 30px;
  }
  .cta-primary {
    display: inline-flex; align-items: center; gap: 10px;
    padding: 15px 30px;
    background: linear-gradient(135deg, var(--violet-deep), var(--blue));
    color: #fff; border-radius: 40px;
    font-weight: 700; font-size: 14px; text-transform: uppercase; letter-spacing: 0.5px;
    box-shadow: 0 10px 30px -8px #6c5ce780;
    transition: transform .2s, box-shadow .2s;
  }
  .cta-primary:hover { transform: translateY(-2px); box-shadow: 0 16px 36px -6px #6c5ce7a0; }
  .cta-primary .play {
    width: 20px; height: 20px; border-radius: 50%; background: #ffffff30;
    display: inline-flex; align-items: center; justify-content: center; font-size: 10px;
  }
  .cta-secondary {
    display: inline-flex; align-items: center; gap: 9px;
    padding: 14px 26px; border: 1px solid var(--line); border-radius: 40px;
    color: var(--ink); font-weight: 700; font-size: 13.5px; text-transform: uppercase;
    letter-spacing: 0.5px; background: var(--panel);
    transition: all .2s;
  }
  .cta-secondary:hover { border-color: var(--violet); color: var(--violet); transform: translateY(-2px); }

  .stats-row { display: flex; justify-content: center; gap: 42px; margin-top: 46px; flex-wrap: wrap; }
  .stat { text-align: center; }
  .stat .num {
    display: block; font-family: 'Oswald', sans-serif; font-weight: 700;
    font-size: 30px; color: var(--ink);
  }
  .stat .label {
    font-size: 11px; color: var(--muted); text-transform: uppercase;
    letter-spacing: 1px; font-family: 'IBM Plex Mono', monospace;
  }

  /* ---- section divider (constellation line) ---- */
  h2.section {
    font-family: 'Oswald', sans-serif; text-transform: uppercase;
    font-size: 16px; color: var(--ink); font-weight: 600;
    margin: 56px 0 20px; letter-spacing: 0.6px;
    display: flex; align-items: center; gap: 12px;
  }
  h2.section .ic { color: var(--violet); font-size: 14px; }
  h2.section .count {
    font-family: 'IBM Plex Mono', monospace; font-size: 11px; color: var(--muted);
    font-weight: 500; background: var(--panel); border: 1px solid var(--line);
    padding: 3px 9px; border-radius: 20px;
  }
  h2.section::after {
    content: ""; flex: 1; height: 1px;
    background: linear-gradient(90deg, var(--line) 0%, transparent 100%);
  }

  /* ---- featured strip (horizontal scroll) ---- */
  .strip { display: flex; gap: 16px; overflow-x: auto; padding: 4px 4px 14px; scrollbar-width: thin; }
  .strip .card { min-width: 158px; max-width: 158px; }
  .strip::-webkit-scrollbar { height: 8px; }

  .grid {
    display: grid; grid-template-columns: repeat(auto-fill, minmax(168px, 1fr));
    gap: 20px;
  }
  .card {
    background: var(--panel); border-radius: 8px; overflow: hidden;
    border: 1px solid var(--line);
    transition: transform .22s cubic-bezier(.2,.8,.2,1), box-shadow .22s, border-color .22s;
    position: relative; display: block;
    opacity: 0; transform: translateY(16px);
    animation: rise .5s ease forwards;
  }
  @keyframes rise { to { opacity: 1; transform: translateY(0); } }
  .card:hover {
    transform: translateY(-6px);
    border-color: #4a3f8c;
    box-shadow: 0 22px 46px -18px #6c5ce770;
  }
  .card .poster-wrap {
    position: relative; overflow: hidden; aspect-ratio: 2/3; background: #150f28;
  }
  .card .poster-wrap::before, .card .poster-wrap::after {
    content: ""; position: absolute; width: 14px; height: 14px; z-index: 3;
    border-color: var(--violet); opacity: 0; transition: opacity .2s;
  }
  .card .poster-wrap::before { top: 8px; left: 8px; border-top: 2px solid; border-left: 2px solid; }
  .card .poster-wrap::after { top: 8px; right: 8px; border-top: 2px solid; border-right: 2px solid; }
  .card:hover .poster-wrap::before, .card:hover .poster-wrap::after { opacity: 1; }
  .card .poster {
    width: 100%; height: 100%; object-fit: cover; display: block;
    transition: transform .4s;
  }
  .card:hover .poster { transform: scale(1.06); }
  .card .poster-wrap.empty::before {
    content: "\\2727"; position: absolute; inset: 0; display: flex; border: none;
    align-items: center; justify-content: center; font-size: 30px; opacity: .25; color: var(--violet);
  }
  .card .scanline {
    position: absolute; left: 0; right: 0; height: 45%; z-index: 2;
    background: linear-gradient(180deg, transparent, #9b8cff22, transparent);
    top: -60%; transition: top .5s ease;
  }
  .card:hover .scanline { top: 110%; }
  .card .sub-strip {
    position: absolute; left: 0; right: 0; bottom: 0; z-index: 2;
    background: linear-gradient(180deg, transparent, #050410ea 45%);
    padding: 24px 12px 10px;
  }
  .card .sub-strip .t {
    font-size: 13.5px; font-weight: 600; margin: 0 0 3px; color: var(--ink);
    overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
  }
  .card .sub-strip .m {
    font-size: 11px; color: var(--pink); font-family: 'IBM Plex Mono', monospace;
  }
  .badge-vip {
    position: absolute; top: 9px; left: 9px; z-index: 3;
    background: #100c1eb0; border: 1px solid var(--vip); color: var(--vip);
    font-family: 'IBM Plex Mono', monospace;
    font-size: 10px; font-weight: 600; padding: 4px 9px 4px 7px; border-radius: 20px;
    display: flex; align-items: center; gap: 5px; letter-spacing: 0.5px;
  }
  .badge-vip .rec-dot { width: 6px; height: 6px; }
  .badge-new {
    position: absolute; top: 9px; right: 9px; z-index: 3;
    background: linear-gradient(135deg, var(--violet-deep), var(--blue));
    color: #fff; font-size: 9.5px; font-weight: 700; letter-spacing: 0.5px;
    padding: 4px 9px; border-radius: 20px; text-transform: uppercase;
  }
  .empty { color: var(--muted); text-align: center; padding: 70px 0; font-size: 14px; }
  .pager { display: flex; justify-content: center; gap: 12px; margin-top: 38px; }
  .pager a {
    background: var(--panel); border: 1px solid var(--line); padding: 10px 20px;
    border-radius: 30px; font-size: 13px; font-weight: 600;
    font-family: 'IBM Plex Mono', monospace;
    transition: all .2s;
  }
  .pager a:hover { border-color: var(--violet); background: var(--panel-hi); color: var(--violet); }
  .genres { display: flex; flex-wrap: wrap; gap: 9px; margin: 20px 0 0; justify-content: center; }
  .genres a {
    background: var(--panel); border: 1px solid var(--line); padding: 8px 17px;
    border-radius: 30px; font-size: 12.5px; color: var(--muted); font-weight: 600;
    transition: all .2s;
  }
  .genres a:hover { color: var(--violet); border-color: var(--violet); background: var(--panel-hi); }

  /* ---- Anime detail page ---- */
  .detail { display: flex; gap: 38px; flex-wrap: wrap; padding-top: 22px; }
  .detail .poster-big-wrap {
    width: 260px; flex-shrink: 0; border-radius: 10px; overflow: hidden;
    aspect-ratio: 2/3; background: #150f28;
    box-shadow: 0 30px 70px -24px #000000c0, 0 0 0 1px var(--line);
    position: relative;
  }
  .detail .poster-big-wrap::before, .detail .poster-big-wrap::after {
    content: ""; position: absolute; width: 20px; height: 20px; z-index: 2;
    border-color: var(--violet); opacity: .9;
  }
  .detail .poster-big-wrap::before { top: 10px; left: 10px; border-top: 2px solid; border-left: 2px solid; }
  .detail .poster-big-wrap::after { bottom: 10px; right: 10px; border-bottom: 2px solid; border-right: 2px solid; }
  .detail .poster-big { width: 100%; height: 100%; object-fit: cover; display: block; }
  .detail .meta { flex: 1; min-width: 260px; }
  .detail .meta .eyebrow-tc {
    font-family: 'IBM Plex Mono', monospace; font-size: 11.5px; color: var(--violet);
    letter-spacing: 1px; margin-bottom: 10px; display: block;
  }
  .detail .meta h1 {
    font-family: 'Oswald', sans-serif;
    margin: 0 0 16px; font-size: 34px; font-weight: 700; letter-spacing: 0.3px;
    text-transform: uppercase; line-height: 1.15;
    background: linear-gradient(135deg, #fff, #d9d0ff 60%, var(--violet));
    -webkit-background-clip: text; background-clip: text; color: transparent;
  }
  .detail .meta .tags { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 20px; }
  .tag {
    background: var(--panel); border: 1px solid var(--line); padding: 5px 13px;
    border-radius: 20px; font-size: 12px; color: var(--muted); font-weight: 500;
    font-family: 'IBM Plex Mono', monospace;
  }
  .detail .meta p.desc {
    color: var(--muted); max-width: 640px; font-size: 15px;
    border-left: 2px solid var(--violet); padding-left: 16px;
  }
  .episodes {
    display: grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
    gap: 10px; margin-top: 24px; max-width: 620px;
  }
  .ep-btn {
    background: var(--panel); border: 1px solid var(--line); padding: 13px 16px;
    border-radius: 8px; font-size: 13.5px; font-weight: 600;
    display: flex; align-items: center; gap: 10px;
    transition: all .18s;
  }
  .ep-btn .num {
    font-family: 'IBM Plex Mono', monospace; color: var(--muted); font-size: 12.5px;
    min-width: 22px;
  }
  .ep-btn .play-ic {
    width: 24px; height: 24px; border-radius: 50%; background: var(--line);
    display: flex; align-items: center; justify-content: center; font-size: 9px;
    flex-shrink: 0; transition: background .18s, color .18s; color: var(--muted);
  }
  .ep-btn:hover { border-color: var(--violet); background: var(--panel-hi); transform: translateY(-2px); }
  .ep-btn:hover .play-ic { background: linear-gradient(135deg, var(--violet-deep), var(--blue)); color: #fff; }
  .lock-notice {
    background: repeating-linear-gradient(135deg, #1a0d18 0 10px, #1c0f1c 10px 20px);
    border: 1px solid #ff5d7a4d; color: #ffc4d1;
    padding: 20px 22px; border-radius: 10px; margin-top: 22px; font-size: 13.5px;
    font-family: 'IBM Plex Mono', monospace;
  }
  .lock-notice a { color: var(--violet); font-weight: 700; text-decoration: underline; }

  /* ---- theme toggle ---- */
  .theme-toggle {
    width: 38px; height: 38px; border-radius: 50%; flex-shrink: 0;
    display: flex; align-items: center; justify-content: center;
    background: var(--panel); border: 1px solid var(--line); cursor: pointer;
    font-size: 15px; transition: all .2s;
  }
  .theme-toggle:hover { border-color: var(--violet); background: var(--panel-hi); }

  /* ---- video embed ---- */
  .watch-wrap {
    max-width: 720px; margin: 22px 0; border-radius: 12px; overflow: hidden;
    border: 1px solid var(--line); background: #000;
  }
  .watch-embed { display: block; width: 100%; min-height: 360px; max-height: 70vh; background: #000; }
  .watch-nav { display: flex; justify-content: space-between; gap: 10px; margin-top: 16px; max-width: 720px; }
  .watch-title { font-size: 15px; font-weight: 700; margin: 18px 0 4px; }

  /* ---- profil sahifasi ---- */
  .profile-card {
    max-width: 560px; background: var(--panel); border: 1px solid var(--line);
    border-radius: 14px; padding: 30px; margin-top: 10px;
  }
  .profile-row {
    display: flex; justify-content: space-between; align-items: center;
    padding: 13px 0; border-bottom: 1px solid var(--line-soft); gap: 12px;
  }
  .profile-row:last-child { border-bottom: none; }
  .profile-row .lbl { color: var(--muted); font-size: 13px; }
  .profile-row .val { font-weight: 600; font-size: 14px; text-align: right; }
  .profile-row .val.vip-yes { color: var(--vip); }
  .switch {
    position: relative; width: 46px; height: 26px; flex-shrink: 0;
  }
  .switch input { opacity: 0; width: 0; height: 0; }
  .switch .slider {
    position: absolute; inset: 0; background: var(--line); border-radius: 30px;
    cursor: pointer; transition: background .2s;
  }
  .switch .slider::before {
    content: ""; position: absolute; width: 20px; height: 20px; left: 3px; top: 3px;
    background: #fff; border-radius: 50%; transition: transform .2s;
  }
  .switch input:checked + .slider { background: var(--violet); }
  .switch input:checked + .slider::before { transform: translateX(20px); }
  .profile-name-form { display: flex; gap: 10px; margin-top: 8px; }
  .profile-name-form input {
    flex: 1; background: var(--bg); border: 1px solid var(--line); border-radius: 6px;
    padding: 10px 13px; color: var(--ink); font-size: 13.5px;
  }
  .profile-name-form button, .btn-save {
    background: linear-gradient(135deg, var(--violet-deep), var(--blue)); color: #fff;
    border: none; border-radius: 6px; padding: 10px 18px; font-weight: 700;
    font-size: 13px; cursor: pointer;
  }
  .profile-toast {
    font-size: 12.5px; color: var(--ok); margin-top: 10px; height: 16px;
  }
  .login-prompt {
    max-width: 480px; text-align: center; padding: 60px 20px;
  }
  .login-prompt .cta-primary { margin-top: 22px; }

  /* ---- statik sahifalar (Biz haqimizda va h.k.) ---- */
  .static-page { max-width: 720px; margin: 10px auto 0; }
  .static-page p { color: var(--muted); font-size: 14.5px; margin: 0 0 16px; }
  .static-page p.lead { font-size: 16px; color: var(--ink); }
  .feature-list {
    display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 16px; margin: 26px 0;
  }
  .feature-item {
    background: var(--panel); border: 1px solid var(--line); border-radius: 10px;
    padding: 18px; transition: border-color .2s, transform .2s;
  }
  .feature-item:hover { border-color: var(--violet); transform: translateY(-3px); }
  .feature-item .f-ic { font-size: 22px; margin-bottom: 8px; display: block; }
  .feature-item .f-t { font-weight: 700; font-size: 13.5px; margin-bottom: 4px; }
  .feature-item .f-d { color: var(--muted); font-size: 12.5px; }

  /* ---- FAQ (savol-javob) ---- */
  .faq-list { max-width: 720px; margin: 10px auto 0; display: flex; flex-direction: column; gap: 10px; }
  .faq-item {
    background: var(--panel); border: 1px solid var(--line); border-radius: 10px; overflow: hidden;
  }
  .faq-item summary {
    padding: 16px 20px; cursor: pointer; font-weight: 600; font-size: 14px;
    list-style: none; display: flex; justify-content: space-between; align-items: center;
  }
  .faq-item summary::-webkit-details-marker { display: none; }
  .faq-item summary::after { content: "+"; color: var(--violet); font-size: 18px; transition: transform .2s; }
  .faq-item[open] summary::after { transform: rotate(45deg); }
  .faq-item .faq-a { padding: 0 20px 18px; color: var(--muted); font-size: 13.5px; }

  /* ---- VIP / narxlar rejalari ---- */
  .plans {
    display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
    gap: 20px; max-width: 760px; margin: 30px auto 0;
  }
  .plan-card {
    background: var(--panel); border: 1px solid var(--line); border-radius: 14px;
    padding: 28px; text-align: center;
  }
  .plan-card.vip { border-color: var(--vip); box-shadow: 0 20px 40px -20px #ff5d7a55; }
  .plan-card .p-name {
    font-family: 'Oswald', sans-serif; text-transform: uppercase; font-weight: 700;
    font-size: 15px; letter-spacing: 0.5px;
  }
  .plan-card .p-perks {
    list-style: none; padding: 0; margin: 20px 0; text-align: left;
    display: flex; flex-direction: column; gap: 11px; font-size: 13px; color: var(--muted);
  }
  .plan-card .p-perks li::before { content: "✦ "; color: var(--violet); }
  .plan-card.vip .p-perks li::before { color: var(--vip); }

  /* ---- aloqa (kontakt) ---- */
  .contact-grid {
    display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 16px; max-width: 720px; margin: 26px auto 0;
  }
  .contact-card {
    background: var(--panel); border: 1px solid var(--line); border-radius: 12px;
    padding: 24px; text-align: center; transition: all .2s; display: block;
  }
  .contact-card:hover { border-color: var(--violet); transform: translateY(-3px); }
  .contact-card .c-ic { font-size: 26px; display: block; margin-bottom: 10px; }
  .contact-card .c-t { font-weight: 700; font-size: 13.5px; margin-bottom: 4px; }
  .contact-card .c-d { color: var(--muted); font-size: 12px; }

  footer {
    text-align: center; color: var(--muted); font-size: 12.5px;
    padding: 44px 16px 32px; margin-top: 58px;
    font-family: 'IBM Plex Mono', monospace;
    border-top: 1px solid var(--line-soft);
  }
  footer .f-logo { color: var(--ink); font-weight: 700; letter-spacing: 0.5px; }
  footer a { color: var(--violet); font-weight: 600; }

  @media (max-width: 560px) {
    .rail { padding: 5px 16px; }
    header .bar { padding: 12px 16px; }
    main { padding: 0 16px 50px; }
    .search-wrap { min-width: 0; width: 100%; order: 3; }
    .detail { gap: 22px; }
    .detail .poster-big-wrap { width: 170px; }
    .stats-row { gap: 26px; }
    .ai-panel { width: calc(100vw - 24px); height: min(70vh, 560px); right: 12px; bottom: 82px; }
    .ai-launcher { right: 16px; bottom: 16px; }
  }

  /* ---- AI yordamchi (pastki burchakdagi doimiy chat oynasi) ---- */
  .ai-launcher {
    position: fixed; right: 26px; bottom: 26px; z-index: 100;
    width: 58px; height: 58px; border-radius: 50%; border: none; cursor: pointer;
    background: linear-gradient(135deg, var(--violet-deep), var(--blue));
    box-shadow: 0 12px 30px -8px #6c5ce780, 0 0 0 1px #ffffff22 inset;
    display: flex; align-items: center; justify-content: center;
    font-size: 24px; color: #fff; transition: transform .2s, box-shadow .2s;
  }
  .ai-launcher:hover { transform: translateY(-2px) scale(1.04); box-shadow: 0 16px 36px -6px #6c5ce7a0; }
  .ai-launcher .ping {
    position: absolute; top: -3px; right: -3px; width: 14px; height: 14px; border-radius: 50%;
    background: var(--ok); border: 2px solid var(--bg-a); display: none;
  }
  .ai-launcher.has-unread .ping { display: block; }
  body.ai-open .ai-launcher .ic-open { display: none; }
  .ai-launcher .ic-close { display: none; }
  body.ai-open .ai-launcher .ic-close { display: block; }

  .ai-panel {
    position: fixed; right: 26px; bottom: 98px; z-index: 100;
    width: 380px; height: min(74vh, 620px);
    background: var(--panel); border: 1px solid var(--line); border-radius: 16px;
    box-shadow: 0 30px 70px -20px #000000a0, 0 0 0 1px var(--line-soft);
    display: none; flex-direction: column; overflow: hidden;
  }
  body.ai-open .ai-panel { display: flex; }
  .ai-head {
    display: flex; align-items: center; justify-content: space-between;
    padding: 14px 16px; border-bottom: 1px solid var(--line);
    background: linear-gradient(135deg, #6c5ce71a, #5aa7ff14);
    flex-shrink: 0;
  }
  .ai-head .ai-title { display: flex; align-items: center; gap: 10px; }
  .ai-head .ai-avatar {
    width: 32px; height: 32px; border-radius: 50%; flex-shrink: 0;
    background: linear-gradient(135deg, var(--violet-deep), var(--blue));
    display: flex; align-items: center; justify-content: center; font-size: 15px; color: #fff;
  }
  .ai-head .ai-name { font-weight: 700; font-size: 13.5px; color: var(--ink); }
  .ai-head .ai-sub { font-size: 11px; color: var(--muted); font-family: 'IBM Plex Mono', monospace; }
  .ai-head .ai-sub .dot { display: inline-block; width: 6px; height: 6px; border-radius: 50%; background: var(--ok); margin-right: 5px; }
  .ai-close-btn {
    width: 28px; height: 28px; border-radius: 50%; border: 1px solid var(--line);
    background: var(--panel-hi); color: var(--muted); cursor: pointer; font-size: 13px;
    display: flex; align-items: center; justify-content: center; flex-shrink: 0;
    transition: all .15s;
  }
  .ai-close-btn:hover { color: var(--ink); border-color: var(--violet); }

  .ai-body {
    flex: 1; overflow-y: auto; padding: 16px; display: flex; flex-direction: column; gap: 12px;
    position: relative;
  }
  .ai-msg { max-width: 88%; font-size: 13.3px; line-height: 1.5; white-space: pre-wrap; word-break: break-word; }
  .ai-msg.user { align-self: flex-end; background: linear-gradient(135deg, var(--violet-deep), var(--blue)); color: #fff; padding: 10px 13px; border-radius: 12px 12px 3px 12px; }
  .ai-msg.bot { align-self: flex-start; background: var(--panel-hi); color: var(--ink); padding: 10px 13px; border-radius: 12px 12px 12px 3px; border: 1px solid var(--line-soft); }
  .ai-msg.bot.typing { display: flex; gap: 4px; align-items: center; padding: 13px; }
  .ai-msg .dot-anim { width: 6px; height: 6px; border-radius: 50%; background: var(--muted); animation: aiDot 1.1s infinite ease-in-out; }
  .ai-msg .dot-anim:nth-child(2) { animation-delay: .15s; }
  .ai-msg .dot-anim:nth-child(3) { animation-delay: .3s; }
  @keyframes aiDot { 0%, 60%, 100% { opacity: .3; transform: translateY(0); } 30% { opacity: 1; transform: translateY(-3px); } }
  .ai-msg-file {
    display: flex; align-items: center; gap: 7px; font-size: 11.5px;
    background: #ffffff20; border-radius: 8px; padding: 5px 9px; margin-top: 6px;
  }
  .ai-msg.bot .ai-msg-file { background: var(--panel); border: 1px solid var(--line-soft); }
  .ai-empty-hint { text-align: center; color: var(--muted); font-size: 12.5px; margin: auto; padding: 20px; }
  .ai-empty-hint .ai-avatar { margin: 0 auto 12px; width: 44px; height: 44px; font-size: 20px; }

  .ai-drop-overlay {
    position: absolute; inset: 0; z-index: 5; display: none;
    align-items: center; justify-content: center; text-align: center;
    background: #6c5ce71a; backdrop-filter: blur(2px);
    border: 2px dashed var(--violet); border-radius: 10px; margin: 8px;
    font-size: 12.5px; color: var(--violet); font-weight: 700;
  }
  .ai-body.drag-over .ai-drop-overlay { display: flex; }

  .ai-files-preview { display: flex; gap: 6px; flex-wrap: wrap; padding: 0 12px; }
  .ai-file-chip {
    display: flex; align-items: center; gap: 6px; font-size: 11px;
    background: var(--panel-hi); border: 1px solid var(--line); border-radius: 20px;
    padding: 4px 6px 4px 10px; color: var(--ink);
  }
  .ai-file-chip button {
    border: none; background: var(--line); color: var(--ink); border-radius: 50%;
    width: 16px; height: 16px; font-size: 10px; cursor: pointer; line-height: 1;
  }

  .ai-foot { padding: 10px 12px 12px; border-top: 1px solid var(--line); flex-shrink: 0; }
  .ai-input-row { display: flex; align-items: flex-end; gap: 8px; }
  .ai-attach-btn {
    width: 36px; height: 36px; border-radius: 50%; border: 1px solid var(--line);
    background: var(--panel-hi); color: var(--muted); cursor: pointer; font-size: 15px;
    display: flex; align-items: center; justify-content: center; flex-shrink: 0; transition: all .15s;
  }
  .ai-attach-btn:hover { color: var(--violet); border-color: var(--violet); }
  .ai-input-row textarea {
    flex: 1; resize: none; max-height: 100px; min-height: 36px;
    background: var(--bg); border: 1px solid var(--line); border-radius: 12px;
    padding: 9px 12px; color: var(--ink); font-size: 13px; font-family: inherit;
    outline: none; transition: border-color .15s;
  }
  .ai-input-row textarea:focus { border-color: var(--violet); }
  .ai-send-btn {
    width: 36px; height: 36px; border-radius: 50%; border: none; cursor: pointer;
    background: linear-gradient(135deg, var(--violet-deep), var(--blue)); color: #fff;
    display: flex; align-items: center; justify-content: center; font-size: 14px; flex-shrink: 0;
    transition: opacity .15s; flex-shrink: 0;
  }
  .ai-send-btn:disabled { opacity: .4; cursor: default; }
  .ai-hint { font-size: 10px; color: var(--muted); margin-top: 6px; text-align: center; }
"""


SCRIPTS = """
  (function () {
    // ---- starfield: twinkling stars + occasional shooting stars ----
    var field = document.getElementById('starfield');
    if (field) {
      var n = window.innerWidth < 640 ? 60 : 130;
      for (var i = 0; i < n; i++) {
        var s = document.createElement('div');
        s.className = 'star-dot';
        var size = (Math.random() * 2 + 0.6).toFixed(2);
        s.style.width = size + 'px';
        s.style.height = size + 'px';
        s.style.left = (Math.random() * 100) + '%';
        s.style.top = (Math.random() * 100) + '%';
        s.style.setProperty('--min-op', (Math.random() * 0.25 + 0.05).toFixed(2));
        s.style.setProperty('--max-op', (Math.random() * 0.5 + 0.5).toFixed(2));
        s.style.animationDuration = (Math.random() * 4 + 2.5) + 's';
        s.style.animationDelay = (Math.random() * 5) + 's';
        field.appendChild(s);
      }
      function spawnShootingStar() {
        var st = document.createElement('div');
        st.className = 'shooting-star';
        st.style.top = (Math.random() * 45) + '%';
        st.style.left = (55 + Math.random() * 40) + '%';
        field.appendChild(st);
        setTimeout(function () { st.remove(); }, 1700);
      }
      setInterval(spawnShootingStar, 4200);
      setTimeout(spawnShootingStar, 900);
    }

    // ---- scroll reveal for cards / sections ----
    if ('IntersectionObserver' in window) {
      var obs = new IntersectionObserver(function (entries) {
        entries.forEach(function (e) {
          if (e.isIntersecting) {
            e.target.style.animationPlayState = 'running';
            obs.unobserve(e.target);
          }
        });
      }, { threshold: 0.08 });
      document.querySelectorAll('.card').forEach(function (c) { obs.observe(c); });
    }

    // ---- live search ----
    var input = document.getElementById('live-search-input');
    var box = document.getElementById('live-results');
    if (input && box) {
      var timer = null;
      var lastQ = '';
      function render(items, q) {
        if (!items || items.length === 0) {
          box.innerHTML = '<div class="live-empty">"' + q + '" bo\\'yicha hech narsa topilmadi</div>';
          box.classList.add('show');
          return;
        }
        var html = items.map(function (it) {
          var thumb = it.poster ? '<img class="thumb" src="' + it.poster + '" loading="lazy">' : '<div class="thumb"></div>';
          var meta = [it.genre, it.year].filter(Boolean).join(' \\u00b7 ');
          return '<a class="live-item" href="/anime/' + it.id + '">' + thumb +
            '<div class="info"><div class="t">' + it.title + '</div><div class="m">' + meta + '</div></div></a>';
        }).join('');
        html += '<a class="live-more" href="/qidiruv?q=' + encodeURIComponent(q) + '">Barcha natijalarni ko\\'rish \\u2192</a>';
        box.innerHTML = html;
        box.classList.add('show');
      }
      input.addEventListener('input', function () {
        var q = input.value.trim();
        lastQ = q;
        clearTimeout(timer);
        if (q.length < 2) { box.classList.remove('show'); box.innerHTML = ''; return; }
        timer = setTimeout(function () {
          fetch('/api/search?q=' + encodeURIComponent(q))
            .then(function (r) { return r.json(); })
            .then(function (data) { if (q === lastQ) render(data, q); })
            .catch(function () {});
        }, 220);
      });
      document.addEventListener('click', function (e) {
        if (!box.contains(e.target) && e.target !== input) box.classList.remove('show');
      });
      input.addEventListener('focus', function () {
        if (input.value.trim().length >= 2 && box.innerHTML) box.classList.add('show');
      });
    }

    // ---- theme toggle ----
    var toggle = document.getElementById('theme-toggle');
    if (toggle) {
      toggle.addEventListener('click', function () {
        var html = document.documentElement;
        var next = html.getAttribute('data-theme') === 'light' ? 'dark' : 'light';
        html.setAttribute('data-theme', next);
        toggle.textContent = next === 'light' ? '\\u2600\\ufe0f' : '\\ud83c\\udf19';
        document.cookie = 'theme=' + next + ';path=/;max-age=31536000';
        if (document.body.getAttribute('data-logged-in') === '1') {
          fetch('/api/profile', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ theme: next })
          }).catch(function () {});
        }
      });
    }

    // ---- AI yordamchi widget (barcha sahifalarda saqlanib qoladi) ----
    var aiLauncher = document.getElementById('ai-launcher');
    var aiPanel = document.getElementById('ai-panel');
    var aiBody = document.getElementById('ai-body');
    var aiForm = document.getElementById('ai-form');
    var aiInput = document.getElementById('ai-textarea');
    var aiSend = document.getElementById('ai-send');
    var aiClose = document.getElementById('ai-close');
    var aiAttachBtn = document.getElementById('ai-attach-btn');
    var aiFileInput = document.getElementById('ai-file-input');
    var aiFilesPreview = document.getElementById('ai-files-preview');

    if (aiLauncher && aiPanel) {
      var LS_OPEN = 'aiWidgetOpen';
      var LS_HISTORY = 'aiWidgetHistory';
      var MAX_FILE_BYTES = 12 * 1024 * 1024; // 12MB
      var pendingFiles = []; // { name, media_type, size, kind, data(base64|null) }
      var history = [];
      try { history = JSON.parse(localStorage.getItem(LS_HISTORY) || '[]'); } catch (e) { history = []; }

      function setOpen(open) {
        document.body.classList.toggle('ai-open', open);
        localStorage.setItem(LS_OPEN, open ? '1' : '0');
        if (open) { aiLauncher.classList.remove('has-unread'); setTimeout(function () { aiInput.focus(); }, 150); }
      }
      aiLauncher.addEventListener('click', function () {
        setOpen(!document.body.classList.contains('ai-open'));
      });
      aiClose.addEventListener('click', function () { setOpen(false); });
      if (localStorage.getItem(LS_OPEN) === '1') setOpen(true);

      function fileIcon(kind) {
        if (kind === 'image') return '\\ud83d\\uddbc\\ufe0f';
        if (kind === 'pdf') return '\\ud83d\\udcc4';
        if (kind === 'text') return '\\ud83d\\udcc3';
        if (kind === 'audio') return '\\ud83c\\udfb5';
        if (kind === 'video') return '\\ud83c\\udfac';
        return '\\ud83d\\udcce';
      }

      function renderMsg(role, text, files) {
        var wrap = document.createElement('div');
        wrap.className = 'ai-msg ' + (role === 'user' ? 'user' : 'bot');
        var t = document.createElement('div');
        t.textContent = text || '';
        wrap.appendChild(t);
        (files || []).forEach(function (f) {
          var chip = document.createElement('div');
          chip.className = 'ai-msg-file';
          chip.textContent = fileIcon(f.kind) + ' ' + f.name;
          wrap.appendChild(chip);
        });
        var hint = aiBody.querySelector('.ai-empty-hint');
        if (hint) hint.remove();
        aiBody.appendChild(wrap);
        aiBody.scrollTop = aiBody.scrollHeight;
        return wrap;
      }

      function persist() {
        try { localStorage.setItem(LS_HISTORY, JSON.stringify(history.slice(-30))); } catch (e) {}
      }

      // sahifa ochilganda avvalgi suhbatni tiklash
      history.forEach(function (m) { renderMsg(m.role, m.text, m.files); });

      function addFileChip(f, idx) {
        var chip = document.createElement('div');
        chip.className = 'ai-file-chip';
        chip.innerHTML = '<span>' + fileIcon(f.kind) + ' ' + f.name.slice(0, 22) + '</span>';
        var rm = document.createElement('button');
        rm.type = 'button'; rm.textContent = '\\u2715';
        rm.addEventListener('click', function () {
          pendingFiles.splice(idx, 1);
          renderFilesPreview();
        });
        chip.appendChild(rm);
        aiFilesPreview.appendChild(chip);
      }
      function renderFilesPreview() {
        aiFilesPreview.innerHTML = '';
        pendingFiles.forEach(function (f, i) { addFileChip(f, i); });
      }

      function classifyFile(file) {
        var type = file.type || '';
        if (type.indexOf('image/') === 0) return 'image';
        if (type === 'application/pdf') return 'pdf';
        if (type.indexOf('audio/') === 0) return 'audio';
        if (type.indexOf('video/') === 0) return 'video';
        if (type.indexOf('text/') === 0 || /\\.(txt|md|csv|json|py|js|html|css|log)$/i.test(file.name)) return 'text';
        return 'other';
      }

      function readAsBase64(file) {
        return new Promise(function (resolve, reject) {
          var r = new FileReader();
          r.onload = function () { resolve(r.result.split(',')[1] || ''); };
          r.onerror = reject;
          r.readAsDataURL(file);
        });
      }
      function readAsText(file) {
        return new Promise(function (resolve, reject) {
          var r = new FileReader();
          r.onload = function () { resolve(r.result); };
          r.onerror = reject;
          r.readAsText(file);
        });
      }

      function handleFiles(fileList) {
        Array.prototype.slice.call(fileList).forEach(function (file) {
          if (file.size > MAX_FILE_BYTES) {
            renderMsg('bot', '\\u26a0\\ufe0f "' + file.name + '" juda katta (12MB dan kichik fayl yuboring).');
            return;
          }
          var kind = classifyFile(file);
          var entry = { name: file.name, media_type: file.type || 'application/octet-stream', size: file.size, kind: kind, data: null, text: null };
          pendingFiles.push(entry);
          var idx = pendingFiles.length - 1;
          renderFilesPreview();
          if (kind === 'image' || kind === 'pdf') {
            readAsBase64(file).then(function (b64) { pendingFiles[idx].data = b64; });
          } else if (kind === 'text') {
            readAsText(file).then(function (txt) { pendingFiles[idx].text = txt.slice(0, 20000); });
          }
          // audio/video/other -- faqat metama'lumot yuboriladi (kontent emas)
        });
      }

      if (aiAttachBtn && aiFileInput) {
        aiAttachBtn.addEventListener('click', function () { aiFileInput.click(); });
        aiFileInput.addEventListener('change', function () {
          handleFiles(aiFileInput.files);
          aiFileInput.value = '';
        });
      }
      ['dragover', 'dragenter'].forEach(function (ev) {
        aiBody.addEventListener(ev, function (e) { e.preventDefault(); aiBody.classList.add('drag-over'); });
      });
      ['dragleave', 'drop'].forEach(function (ev) {
        aiBody.addEventListener(ev, function (e) {
          if (ev === 'drop') { e.preventDefault(); handleFiles(e.dataTransfer.files); }
          aiBody.classList.remove('drag-over');
        });
      });

      function autoGrow() {
        aiInput.style.height = 'auto';
        aiInput.style.height = Math.min(aiInput.scrollHeight, 100) + 'px';
      }
      aiInput.addEventListener('input', autoGrow);
      aiInput.addEventListener('keydown', function (e) {
        if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); aiForm.requestSubmit(); }
      });

      aiForm.addEventListener('submit', function (e) {
        e.preventDefault();
        var text = aiInput.value.trim();
        if (!text && pendingFiles.length === 0) return;

        var filesForDisplay = pendingFiles.map(function (f) { return { name: f.name, kind: f.kind }; });
        renderMsg('user', text, filesForDisplay);
        var outgoingFiles = pendingFiles.slice();
        history.push({ role: 'user', text: text, files: filesForDisplay });
        persist();

        aiInput.value = ''; autoGrow();
        pendingFiles = []; renderFilesPreview();
        aiSend.disabled = true;

        var typing = document.createElement('div');
        typing.className = 'ai-msg bot typing';
        typing.innerHTML = '<span class="dot-anim"></span><span class="dot-anim"></span><span class="dot-anim"></span>';
        aiBody.appendChild(typing);
        aiBody.scrollTop = aiBody.scrollHeight;

        fetch('/api/assistant', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            message: text,
            history: history.slice(0, -1).slice(-12),
            files: outgoingFiles.map(function (f) {
              return { name: f.name, media_type: f.media_type, size: f.size, kind: f.kind, data: f.data, text: f.text };
            })
          })
        }).then(function (r) { return r.json(); }).then(function (data) {
          typing.remove();
          var reply = data.reply || '\\u26a0\\ufe0f Xatolik yuz berdi, birozdan so\\'ng qayta urinib ko\\'ring.';
          renderMsg('bot', reply, []);
          history.push({ role: 'assistant', text: reply, files: [] });
          persist();
          if (!document.body.classList.contains('ai-open')) aiLauncher.classList.add('has-unread');
        }).catch(function () {
          typing.remove();
          renderMsg('bot', '\\u26a0\\ufe0f Ulanishda xatolik. Internetni tekshirib qayta urinib ko\\'ring.', []);
        }).finally(function () { aiSend.disabled = false; });
      });
    }
  })();
"""


def base_page(title: str, body: str, active: str = "", marquee_items=None,
               current_user=None, theme: str = "dark") -> str:
    if not marquee_items:
        marquee_items = [
            "YANGI QISMLAR MUNTAZAM YUKLANADI",
            "O'ZBEK TILIDA SIFATLI DUBLYAJ",
            "TELEGRAM BOT ORQALI ISTALGAN JOYDA TOMOSHA QILING",
        ]
    marquee_items = pad_marquee_items(marquee_items)
    track = " &nbsp;&#10022;&nbsp; ".join(html.escape(m) for m in marquee_items)
    marquee_html = f'<span>{track}</span> &nbsp;&#10022;&nbsp; <span>{track}</span>'
    theme_icon = "☀️" if theme == "light" else "🌙"
    logged_in = "1" if current_user else "0"

    if current_user:
        name = html.escape(current_user["settings"]["display_name"] or current_user["user"]["full_name"] or "Profil")
        profile_link = f'<a href="/profil" class="{"active" if active == "profil" else ""}">👤 {name}</a>'
    else:
        profile_link = f'<a href="/profil" class="{"active" if active == "profil" else ""}">👤 Profil</a>'

    return f"""<!DOCTYPE html>
<html lang="uz" data-theme="{theme}">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{html.escape(title)} — STAR DUBBING</title>
<link rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>⭐</text></svg>">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Oswald:wght@500;600;700&family=Inter:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<style>{STYLES}</style>
</head>
<body data-logged-in="{logged_in}">
<div id="starfield"></div>
<header>
  <div class="rail">
    <div class="marquee"><div class="marquee-track">{marquee_html}</div></div>
    <span class="on-air"><span class="rec-dot dot-blue"></span> JONLI</span>
  </div>
  <div class="bar">
    <a class="logo" href="/"><span class="star-ic">✦</span> <span class="grad-txt">STAR DUBBING</span></a>
    <nav>
      <a href="/" class="{'active' if active == 'home' else ''}">Bosh sahifa</a>
      <a href="/janrlar" class="{'active' if active == 'janrlar' else ''}">Janrlar</a>
      <a href="/top" class="{'active' if active == 'top' else ''}">TOP</a>
      <a href="/tasodifiy" class="{'active' if active == 'tasodifiy' else ''}">Tasodifiy</a>
      {profile_link}
      <a href="https://t.me/{BOT_USERNAME}" class="{'active' if active == 'bot' else ''}">Telegram bot</a>
    </nav>
    <div class="search-wrap">
      <form class="search-box" action="/qidiruv" method="get" autocomplete="off">
        <span>&#10022;</span>
        <input id="live-search-input" type="text" name="q" placeholder="anime nomini yozing (masalan: naruto)..." />
      </form>
      <div id="live-results" class="live-results"></div>
    </div>
    <button id="theme-toggle" class="theme-toggle" type="button" title="Mavzuni almashtirish">{theme_icon}</button>
  </div>
</header>
<main>
{body}
</main>
<footer>
  <div class="f-logo">✦ STAR DUBBING</div>
  <div style="margin-top:6px">o'zbek tilidagi anime dublyaj jamoasi. Barcha epizodlarni
  <a href="https://t.me/{BOT_USERNAME}">Telegram botimiz</a> orqali tomosha qiling.</div>
  <div style="margin-top:16px; display:flex; gap:18px; justify-content:center; flex-wrap:wrap;">
    <a href="/haqida">Biz haqimizda</a>
    <a href="/vip">VIP</a>
    <a href="/savollar">Savol-javob</a>
    <a href="/aloqa">Aloqa</a>
  </div>
</footer>
<button id="ai-launcher" class="ai-launcher" type="button" title="AI yordamchi">
  <span class="ping"></span>
  <span class="ic-open">✦</span>
  <span class="ic-close">✕</span>
</button>
<div id="ai-panel" class="ai-panel">
  <div class="ai-head">
    <div class="ai-title">
      <div class="ai-avatar">✦</div>
      <div>
        <div class="ai-name">STAR AI yordamchi</div>
        <div class="ai-sub"><span class="dot"></span>onlayn</div>
      </div>
    </div>
    <button id="ai-close" class="ai-close-btn" type="button" title="Yopish">✕</button>
  </div>
  <div id="ai-body" class="ai-body">
    <div class="ai-drop-overlay">📎 Faylni shu yerga tashlang</div>
    <div class="ai-empty-hint">
      <div class="ai-avatar">✦</div>
      Salom! Men STAR AI yordamchiman.<br>Savol bering yoki rasm/hujjat/video/audio biriktiring.
    </div>
  </div>
  <div id="ai-files-preview" class="ai-files-preview"></div>
  <form id="ai-form" class="ai-foot">
    <div class="ai-input-row">
      <button id="ai-attach-btn" class="ai-attach-btn" type="button" title="Fayl biriktirish">📎</button>
      <textarea id="ai-textarea" rows="1" placeholder="Xabar yozing..."></textarea>
      <button id="ai-send" class="ai-send-btn" type="submit" title="Yuborish">➤</button>
    </div>
    <input id="ai-file-input" type="file" multiple hidden accept="image/*,application/pdf,audio/*,video/*,text/*,.txt,.md,.csv,.json">
    <div class="ai-hint">Rasm, PDF va matnli fayllarni to'liq o'qiy oladi · video/audio faqat nom bo'yicha</div>
  </form>
</div>
<script>{SCRIPTS}</script>
</body>
</html>"""


def anime_card_html(a, is_new: bool = False) -> str:
    poster = f"/poster/{a['id']}" if a["poster_file_id"] else ""
    poster_tag = (
        f'<div class="poster-wrap"><img class="poster" src="{poster}" alt="{html.escape(a["title"])}" loading="lazy"><div class="scanline"></div></div>'
        if poster else '<div class="poster-wrap empty"><div class="scanline"></div></div>'
    )
    vip_badge = '<span class="badge-vip"><span class="rec-dot"></span>VIP</span>' if a["vip_only"] else ""
    new_badge = '<span class="badge-new">Yangi</span>' if (is_new and not a["vip_only"]) else ""
    meta = html.escape(a['genre'] or '')
    if a["year"]:
        meta += f' · {html.escape(a["year"])}'
    return f"""<a class="card" href="/anime/{a['id']}">
  {vip_badge}{new_badge}
  {poster_tag}
  <div class="sub-strip">
    <p class="t">{html.escape(a['title'])}</p>
    <p class="m">{meta}</p>
  </div>
</a>"""


def pad_marquee_items(items: list[str], min_chars: int = 260) -> list[str]:
    """Marquee tasmasi juda qisqa bo'lsa (masalan bitta-ikkita anime bo'lganda),
    matn deyarli ko'rinmay, uzilib-uzilib "ishlamayotgandek" tuyuladi -- shu
    sababli umumiy uzunlik yetarli bo'lguncha ro'yxatni takrorlaymiz, shunda
    tasma har doim to'liq va tekis yuguradi."""
    items = [i for i in items if i]
    if not items:
        return items
    result = list(items)
    guard = 0
    while sum(len(i) for i in result) < min_chars and guard < 8:
        result += items
        guard += 1
    return result


def pager_html(base_url: str, offset: int, total: int) -> str:
    parts = []
    if offset > 0:
        prev_offset = max(offset - PAGE_SIZE, 0)
        sep = "&" if "?" in base_url else "?"
        parts.append(f'<a href="{base_url}{sep}offset={prev_offset}">⏮ OLDINGI</a>')
    if offset + PAGE_SIZE < total:
        next_offset = offset + PAGE_SIZE
        sep = "&" if "?" in base_url else "?"
        parts.append(f'<a href="{base_url}{sep}offset={next_offset}">KEYINGI ⏭</a>')
    if not parts:
        return ""
    return f'<div class="pager">{"".join(parts)}</div>'


# ---------- ROUTE HANDLERLARI ----------

async def home(request):
    current_user = await get_current_user(request)
    theme = get_theme(request, current_user)
    offset = int(request.query.get("offset", 0))
    total = await db.count_anime()
    rows = await db.list_anime(offset=offset, limit=PAGE_SIZE * 3)
    genres = await db.get_all_genres()

    featured = rows[:10]
    strip_html = ""
    if offset == 0 and featured:
        cards = "".join(anime_card_html(a, is_new=True) for a in featured)
        strip_html = f"""
<h2 class="section"><span class="ic">&#10022;</span> Yangi qo'shilganlar <span class="count">{len(featured)}</span></h2>
<div class="strip">{cards}</div>
"""

    if rows:
        grid = f'<div class="grid">{"".join(anime_card_html(a) for a in rows)}</div>'
        grid += pager_html("/", offset, total)
    else:
        grid = '<p class="empty">Hozircha animelar qo\'shilmagan.</p>'

    genre_links = "".join(f'<a href="/janr/{quote(g)}">{html.escape(g)}</a>' for g in genres[:12])
    info_lines = [
        "YANGI QISMLAR MUNTAZAM YUKLANADI",
        "O'ZBEK TILIDA SIFATLI DUBLYAJ",
        "TELEGRAM BOT ORQALI ISTALGAN JOYDA TOMOSHA QILING",
    ]
    anime_titles = [a["title"] for a in featured]
    marquee_items = pad_marquee_items(info_lines + anime_titles)

    body = f"""
<section class="hero">
  <span class="eyebrow">&#10022; O'ZBEK TILIDA SIFATLI DUBLYAJ</span>
  <h1 class="wordmark"><span>STAR</span><span>DUBBING</span></h1>
  <p class="tagline">Sevimli animelaringizni sifatli dublyaj bilan tomosha qiling — yangi qismlar muntazam qo'shib boriladi.</p>
  <div class="hero-ctas">
    <a class="cta-primary" href="https://t.me/{BOT_USERNAME}"><span class="play">▶</span> Telegram botni ochish</a>
    <a class="cta-secondary" href="/tasodifiy">🎲 Tasodifiy anime</a>
  </div>
  <div class="stats-row">
    <div class="stat"><span class="num">{total}</span><span class="label">anime</span></div>
    <div class="stat"><span class="num">{len(genres)}</span><span class="label">janr</span></div>
    <div class="stat"><span class="num">24/7</span><span class="label">bot orqali</span></div>
  </div>
  <div class="genres">{genre_links}</div>
</section>
{strip_html}
<h2 class="section"><span class="ic">&#9642;</span> Barcha animelar <span class="count">{total}</span></h2>
{grid}
"""
    return web.Response(
        text=base_page("Bosh sahifa", body, active="home", marquee_items=marquee_items,
                        current_user=current_user, theme=theme),
        content_type="text/html",
    )


async def genres_page(request):
    current_user = await get_current_user(request)
    theme = get_theme(request, current_user)
    genres = await db.get_all_genres()
    links = "".join(f'<a href="/janr/{quote(g)}">{html.escape(g)}</a>' for g in genres)
    body = f"""
<h2 class="section"><span class="ic">&#10022;</span> Janrlar <span class="count">{len(genres)}</span></h2>
<div class="genres">{links or "<p class='empty'>Janrlar topilmadi.</p>"}</div>
"""
    return web.Response(
        text=base_page("Janrlar", body, active="janrlar", current_user=current_user, theme=theme),
        content_type="text/html",
    )


async def genre_detail(request):
    current_user = await get_current_user(request)
    theme = get_theme(request, current_user)
    genre = request.match_info["name"]
    offset = int(request.query.get("offset", 0))
    total = await db.count_anime(genre=genre)
    rows = await db.list_anime(offset=offset, limit=PAGE_SIZE * 3, genre=genre)

    if rows:
        grid = f'<div class="grid">{"".join(anime_card_html(a) for a in rows)}</div>'
        grid += pager_html(f"/janr/{quote(genre)}", offset, total)
    else:
        grid = '<p class="empty">Bu janrda animelar topilmadi.</p>'

    body = f'<h2 class="section"><span class="ic">&#10022;</span> {html.escape(genre)} <span class="count">{total}</span></h2>{grid}'
    return web.Response(
        text=base_page(genre, body, current_user=current_user, theme=theme), content_type="text/html"
    )


async def search_page(request):
    current_user = await get_current_user(request)
    theme = get_theme(request, current_user)
    q = request.query.get("q", "").strip()
    if not q:
        return web.HTTPFound("/")

    if q.isdigit():
        anime = await db.get_anime(int(q))
        rows = [anime] if anime else []
        if not rows:
            # Raqam anime ID'siga to'g'ri kelmasa ham, nom ichida shu raqam
            # uchrasa (masalan "86" anomeси kabi) qidiruvni davom ettiramiz.
            rows = await db.search_anime(q, limit=60)
    else:
        rows = await db.search_anime(q, limit=60)

    if rows:
        grid = f'<div class="grid">{"".join(anime_card_html(a) for a in rows)}</div>'
    else:
        grid = '<p class="empty">Hech narsa topilmadi. Nomning bir qismini yozib ko\'ring.</p>'

    body = f'<h2 class="section"><span class="ic">&gt;_</span> "{html.escape(q)}" bo\'yicha natijalar <span class="count">{len(rows)}</span></h2>{grid}'
    return web.Response(
        text=base_page(f"Qidiruv: {q}", body, current_user=current_user, theme=theme),
        content_type="text/html",
    )


async def api_search(request):
    """Live-qidiruv uchun JSON API — foydalanuvchi yozayotganda ishlaydi."""
    q = request.query.get("q", "").strip()
    if len(q) < 2:
        return web.json_response([])

    if q.isdigit():
        anime = await db.get_anime(int(q))
        rows = [anime] if anime else []
        if not rows:
            rows = await db.search_anime(q, limit=8)
    else:
        rows = await db.search_anime(q, limit=8)

    results = [
        {
            "id": a["id"],
            "title": a["title"],
            "genre": a["genre"] or "",
            "year": a["year"] or "",
            "poster": f"/poster/{a['id']}" if a["poster_file_id"] else None,
            "vip": bool(a["vip_only"]),
        }
        for a in rows
    ]
    return web.json_response(results)


async def random_anime(request):
    """'Tasodifiy anime' tugmasi — tasodifiy bitta animega yo'naltiradi."""
    total = await db.count_anime()
    if total == 0:
        return web.HTTPFound("/")
    offset = random.randint(0, total - 1)
    rows = await db.list_anime(offset=offset, limit=1)
    if not rows:
        return web.HTTPFound("/")
    return web.HTTPFound(f"/anime/{rows[0]['id']}")


async def anime_detail(request):
    current_user = await get_current_user(request)
    theme = get_theme(request, current_user)
    try:
        anime_id = int(request.match_info["id"])
    except ValueError:
        raise web.HTTPNotFound()

    anime = await db.get_anime(anime_id)
    if not anime:
        raise web.HTTPNotFound()

    await db.increment_anime_views(anime_id)

    is_vip_visitor = bool(current_user and current_user["vip"])
    episodes = await db.get_episodes(anime_id)
    poster = f"/poster/{anime['id']}" if anime["poster_file_id"] else ""
    poster_tag = (
        f'<div class="poster-big-wrap"><img class="poster-big" src="{poster}" alt=""></div>'
        if poster else '<div class="poster-big-wrap"></div>'
    )

    tags = "".join(
        f'<span class="tag">{html.escape(g.strip())}</span>'
        for g in (anime["genre"] or "").split(",") if g.strip()
    )
    if anime["year"]:
        tags += f'<span class="tag">📅 {html.escape(anime["year"])}</span>'
    if anime["vip_only"]:
        tags += '<span class="tag" style="border-color:#ff5d7a;color:#ff5d7a">🔒 VIP-only</span>'

    if anime["vip_only"] and not is_vip_visitor:
        login_hint = (
            '' if current_user else
            '<br>Agar VIP bo\'lsangiz, <a href="/profil">saytga kiring</a> avval.'
        )
        body_episodes = (
            '<div class="lock-notice">🔒 Bu anime faqat <b>VIP</b> foydalanuvchilar uchun. '
            f'VIP status olish uchun <a href="https://t.me/{BOT_USERNAME}">botga</a> yozing.'
            f'{login_hint}</div>'
        )
    elif episodes:
        buttons = []
        for ep in episodes:
            if ep["web_video_url"]:
                href = f'/anime/{anime_id}/qism/{ep["episode_number"]}'
            else:
                href = f'https://t.me/{BOT_USERNAME}?start=ep_{anime_id}_{ep["episode_number"]}'
            buttons.append(
                f'<a class="ep-btn" href="{href}">'
                f'<span class="play-ic">▶</span><span class="num">{ep["episode_number"]:02d}</span> {ep["episode_number"]}-qism</a>'
            )
        body_episodes = f'<div class="episodes">{"".join(buttons)}</div>'
    else:
        body_episodes = '<p class="empty" style="text-align:left">Hali epizod qo\'shilmagan.</p>'

    body = f"""
<div class="detail">
  {poster_tag}
  <div class="meta">
    <span class="eyebrow-tc mono">&#10022; NOW SCREENING</span>
    <h1>{html.escape(anime['title'])}</h1>
    <div class="tags">{tags}</div>
    <p class="desc">{html.escape(anime['description'] or '')}</p>
    {body_episodes}
  </div>
</div>
"""
    return web.Response(
        text=base_page(anime["title"], body, current_user=current_user, theme=theme),
        content_type="text/html",
    )


async def episode_watch(request):
    """Epizodni saytning o'zida ko'rsatadi -- Telegram bilan hech qanday
    aloqasi bo'lmagan, alohida saqlangan to'g'ridan-to'g'ri video havolasi
    orqali (<video> tegi bilan). Shu sababli sayt orqali Telegram kanali
    hech qachon ko'rinmaydi."""
    current_user = await get_current_user(request)
    theme = get_theme(request, current_user)
    try:
        anime_id = int(request.match_info["id"])
        ep_num = int(request.match_info["num"])
    except ValueError:
        raise web.HTTPNotFound()

    anime = await db.get_anime(anime_id)
    if not anime:
        raise web.HTTPNotFound()

    is_vip_visitor = bool(current_user and current_user["vip"])
    if anime["vip_only"] and not is_vip_visitor:
        body = (
            '<div class="lock-notice" style="max-width:560px">🔒 Bu anime faqat <b>VIP</b> '
            f'foydalanuvchilar uchun. VIP olish uchun <a href="https://t.me/{BOT_USERNAME}">botga</a> yozing, '
            'so\'ng <a href="/profil">saytga qayta kiring</a>.</div>'
        )
        return web.Response(
            text=base_page(anime["title"], body, current_user=current_user, theme=theme),
            content_type="text/html",
        )

    episode = await db.get_episode_by_number(anime_id, ep_num)
    if not episode:
        raise web.HTTPNotFound()

    if not episode["web_video_url"]:
        body = (
            '<div class="lock-notice" style="max-width:560px">ℹ️ Bu qism hali saytga bog\'lanmagan. '
            f'Hozircha <a href="https://t.me/{BOT_USERNAME}?start=ep_{anime_id}_{ep_num}">Telegram bot orqali</a> '
            'tomosha qiling.</div>'
        )
        return web.Response(
            text=base_page(anime["title"], body, current_user=current_user, theme=theme),
            content_type="text/html",
        )

    has_prev = await db.get_episode_by_number(anime_id, ep_num - 1) is not None
    has_next = await db.get_episode_by_number(anime_id, ep_num + 1) is not None
    nav = []
    if has_prev:
        nav.append(f'<a class="cta-secondary" href="/anime/{anime_id}/qism/{ep_num - 1}">⬅️ Oldingi</a>')
    else:
        nav.append("<span></span>")
    nav.append(f'<a class="cta-secondary" href="/anime/{anime_id}">📋 Epizodlar</a>')
    if has_next:
        nav.append(f'<a class="cta-secondary" href="/anime/{anime_id}/qism/{ep_num + 1}">Keyingi ➡️</a>')
    else:
        nav.append("<span></span>")

    video_url = html.escape(episode["web_video_url"], quote=True)
    body = f"""
<h1 class="watch-title">{html.escape(anime['title'])} — {ep_num}-qism</h1>
<div class="watch-wrap">
  <video class="watch-embed" controls preload="metadata" playsinline src="{video_url}"></video>
</div>
<div class="watch-nav">{''.join(nav)}</div>
"""
    return web.Response(
        text=base_page(f"{anime['title']} — {ep_num}-qism", body, current_user=current_user, theme=theme),
        content_type="text/html",
    )


async def poster_proxy(request):
    """Telegram'dagi poster rasmini saytda ko'rsatish uchun oraliq (proxy)."""
    try:
        anime_id = int(request.match_info["id"])
    except ValueError:
        raise web.HTTPNotFound()

    anime = await db.get_anime(anime_id)
    if not anime or not anime["poster_file_id"]:
        raise web.HTTPNotFound()

    bot = request.app["bot"]
    try:
        file = await bot.get_file(anime["poster_file_id"])
        file_bytes = await bot.download_file(file.file_path)
        return web.Response(body=file_bytes.read(), content_type="image/jpeg")
    except Exception:
        raise web.HTTPNotFound()


async def login_via_token(request):
    """Bot yuborgan bir martalik havola orqali kirish -- tokenni tekshirib,
    sessiya cookie'sini o'rnatadi va profilga yo'naltiradi."""
    token = request.query.get("token", "")
    user_id = await db.consume_login_token(token) if token else None
    if not user_id:
        body = (
            '<div class="login-prompt"><h2 class="section" style="justify-content:center">'
            '&#9888; Havola yaroqsiz</h2>'
            '<p class="empty" style="padding:10px 0 0">Havola muddati o\'tgan yoki allaqachon ishlatilgan. '
            'Botdan qaytadan yangi havola oling.</p>'
            f'<a class="cta-primary" href="https://t.me/{BOT_USERNAME}?start=veblogin">'
            '<span class="play">▶</span> Botni ochish</a></div>'
        )
        return web.Response(text=base_page("Kirish", body), content_type="text/html")

    session_id = await db.create_session(user_id)
    resp = web.HTTPFound("/profil")
    resp.set_cookie(SESSION_COOKIE, session_id, max_age=60 * 60 * 24 * 30, httponly=True, samesite="Lax")
    return resp


async def logout(request):
    session_id = request.cookies.get(SESSION_COOKIE)
    if session_id:
        await db.delete_session(session_id)
    resp = web.HTTPFound("/profil")
    resp.del_cookie(SESSION_COOKIE)
    return resp


async def profile_page(request):
    current_user = await get_current_user(request)
    theme = get_theme(request, current_user)

    if not current_user:
        body = f"""
<div class="login-prompt">
  <h2 class="section" style="justify-content:center">&#10022; Profilga kirish</h2>
  <p class="empty" style="padding:10px 0 0">Profilingizni ko'rish uchun avval Telegram botimizni oching va
  "🧑‍🚀 Profil" tugmasidan "🌐 Saytda profilni ochish" ni bosing -- sizga bir martalik kirish havolasi yuboriladi.</p>
  <a class="cta-primary" href="https://t.me/{BOT_USERNAME}?start=veblogin">
    <span class="play">▶</span> Botni ochib kirish havolasini olish</a>
</div>
"""
        return web.Response(
            text=base_page("Profil", body, active="profil", current_user=None, theme=theme),
            content_type="text/html",
        )

    user = current_user["user"]
    settings = current_user["settings"]
    vip = current_user["vip"]
    display_name = html.escape(settings["display_name"] or user["full_name"] or "")
    vip_html = '<span class="val vip-yes">❌ Yo\'q</span>'
    if vip:
        muddat = "♾ Umrbod" if not vip["expires_at"] else f"✅ {vip['expires_at'][:10]} gacha"
        vip_html = f'<span class="val vip-yes">{muddat}</span>'

    body = f"""
<h2 class="section"><span class="ic">&#10022;</span> Profil</h2>
<div class="profile-card">
  <div class="profile-row">
    <span class="lbl">Telegram ID</span>
    <span class="val mono">{user['user_id']}</span>
  </div>
  <div class="profile-row">
    <span class="lbl">Username</span>
    <span class="val">@{html.escape(user['username'] or '—')}</span>
  </div>
  <div class="profile-row">
    <span class="lbl">👑 VIP holati</span>
    {vip_html}
  </div>
  <div class="profile-row">
    <span class="lbl">A'zo bo'lgan sana</span>
    <span class="val">{(user['joined_at'] or '')[:10]}</span>
  </div>
</div>

<h2 class="section"><span class="ic">&#9881;</span> Sozlamalar</h2>
<div class="profile-card">
  <div class="profile-row">
    <span class="lbl">🌙 Tungi rejim</span>
    <label class="switch">
      <input type="checkbox" id="theme-switch" {"checked" if settings["theme"] == "dark" else ""}>
      <span class="slider"></span>
    </label>
  </div>
  <div class="profile-row">
    <span class="lbl">🔔 Bildirishnomalar</span>
    <label class="switch">
      <input type="checkbox" id="notif-switch" {"checked" if settings["notifications_enabled"] else ""}>
      <span class="slider"></span>
    </label>
  </div>
  <div class="profile-row" style="flex-direction:column;align-items:stretch">
    <span class="lbl">✏️ Ko'rsatiladigan ism</span>
    <div class="profile-name-form">
      <input type="text" id="display-name-input" value="{display_name}" maxlength="64" placeholder="Ismingiz">
      <button id="save-name-btn" class="btn-save" type="button">Saqlash</button>
    </div>
    <div class="profile-toast" id="profile-toast"></div>
  </div>
</div>

<p style="margin-top:26px"><a href="/chiqish" class="cta-secondary">🚪 Chiqish</a></p>

<script>
(function () {{
  function toast(msg) {{
    var t = document.getElementById('profile-toast');
    if (t) {{ t.textContent = msg; setTimeout(function () {{ t.textContent = ''; }}, 2200); }}
  }}
  function save(payload) {{
    fetch('/api/profile', {{
      method: 'POST', headers: {{ 'Content-Type': 'application/json' }},
      body: JSON.stringify(payload)
    }}).then(function (r) {{ if (r.ok) toast('✅ Saqlandi'); else toast('❌ Xatolik'); }})
      .catch(function () {{ toast('❌ Xatolik'); }});
  }}
  var themeSwitch = document.getElementById('theme-switch');
  if (themeSwitch) {{
    themeSwitch.addEventListener('change', function () {{
      var next = themeSwitch.checked ? 'dark' : 'light';
      document.documentElement.setAttribute('data-theme', next);
      document.cookie = 'theme=' + next + ';path=/;max-age=31536000';
      save({{ theme: next }});
    }});
  }}
  var notifSwitch = document.getElementById('notif-switch');
  if (notifSwitch) {{
    notifSwitch.addEventListener('change', function () {{
      save({{ notifications_enabled: notifSwitch.checked }});
    }});
  }}
  var saveBtn = document.getElementById('save-name-btn');
  if (saveBtn) {{
    saveBtn.addEventListener('click', function () {{
      var val = document.getElementById('display-name-input').value.trim();
      save({{ display_name: val }});
    }});
  }}
}})();
</script>
"""
    return web.Response(
        text=base_page("Profil", body, active="profil", current_user=current_user, theme=theme),
        content_type="text/html",
    )


async def api_profile_update(request):
    current_user = await get_current_user(request)
    if not current_user:
        return web.json_response({"error": "kirish talab qilinadi"}, status=401)
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "noto'g'ri so'rov"}, status=400)

    theme = data.get("theme")
    if theme not in (None, "dark", "light"):
        return web.json_response({"error": "noto'g'ri mavzu"}, status=400)
    notifications_enabled = data.get("notifications_enabled")
    display_name = data.get("display_name")
    if isinstance(display_name, str):
        display_name = display_name.strip()[:64] or None

    await db.update_user_settings(
        current_user["user_id"],
        display_name=display_name if "display_name" in data else None,
        theme=theme,
        notifications_enabled=notifications_enabled if isinstance(notifications_enabled, bool) else None,
    )
    return web.json_response({"ok": True})


def _build_assistant_content(message: str, files: list) -> list:
    """Foydalanuvchi xabari va biriktirilgan fayllardan Gemini API uchun
    "parts" ro'yxatini yasaydi (rasm/PDF -- inline_data, matn -- text)."""
    parts = []
    if message:
        parts.append({"text": message})
    for f in files or []:
        if not isinstance(f, dict):
            continue
        name = str(f.get("name", "fayl"))[:200]
        kind = f.get("kind")
        media_type = f.get("media_type") or "application/octet-stream"
        if kind == "image" and f.get("data"):
            parts.append({"inline_data": {"mime_type": media_type, "data": f["data"]}})
        elif kind == "pdf" and f.get("data"):
            parts.append({"inline_data": {"mime_type": "application/pdf", "data": f["data"]}})
        elif kind == "text" and f.get("text"):
            parts.append({"text": f"[Biriktirilgan fayl: {name}]\n{f['text']}"})
        else:
            size_kb = round((f.get("size") or 0) / 1024)
            parts.append({
                "text": f"[Foydalanuvchi fayl biriktirdi: {name} ({media_type}, ~{size_kb}KB) -- "
                        f"bu turdagi faylning ichini ko'ra/eshita olmaysan, faqat nomi va "
                        f"kontekstga qarab javob ber.]",
            })
    if not parts:
        parts.append({"text": "(bo'sh xabar)"})
    return parts


async def api_assistant(request):
    if not GEMINI_API_KEY:
        return web.json_response(
            {"reply": "AI yordamchi hali sozlanmagan (server tomonida GEMINI_API_KEY yo'q). "
                      "Bepul kalitni https://aistudio.google.com/apikey saytidan olsa bo'ladi."},
            status=200,
        )
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"reply": "Noto'g'ri so'rov."}, status=400)

    message = str(data.get("message", ""))[:8000]
    files = data.get("files") or []
    if not isinstance(files, list):
        files = []
    files = files[:5]
    raw_history = data.get("history") or []
    if not isinstance(raw_history, list):
        raw_history = []

    # Gemini'da rollar "user" va "model" bo'ladi (Anthropic'dagi "assistant" emas).
    contents = []
    for item in raw_history[-12:]:
        if not isinstance(item, dict):
            continue
        role = "user" if item.get("role") == "user" else "model"
        text = str(item.get("text", ""))[:4000]
        if text:
            contents.append({"role": role, "parts": [{"text": text}]})
    contents.append({"role": "user", "parts": _build_assistant_content(message, files)})

    payload = {
        "system_instruction": {"parts": [{"text": ASSISTANT_SYSTEM_PROMPT}]},
        "contents": contents,
        "generationConfig": {"maxOutputTokens": 1024},
    }
    headers = {
        "x-goog-api-key": GEMINI_API_KEY,
        "content-type": "application/json",
    }
    url = GEMINI_API_URL.format(model=ASSISTANT_MODEL)
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers,
                                     timeout=aiohttp.ClientTimeout(total=45)) as resp:
                result = await resp.json()
                if resp.status != 200:
                    err_msg = (result.get("error") or {}).get("message", "Noma'lum xatolik")
                    return web.json_response({"reply": f"⚠️ AI xatosi: {err_msg}"}, status=200)
    except Exception:
        return web.json_response(
            {"reply": "⚠️ AI yordamchiga ulanib bo'lmadi, birozdan so'ng qayta urinib ko'ring."},
            status=200,
        )

    candidates = result.get("candidates") or []
    reply = "..."
    if candidates:
        finish_reason = candidates[0].get("finishReason")
        cand_parts = (candidates[0].get("content") or {}).get("parts") or []
        reply_parts = [p.get("text", "") for p in cand_parts if isinstance(p, dict) and p.get("text")]
        reply = "\n".join(p for p in reply_parts if p).strip() or "..."
        if finish_reason == "SAFETY":
            reply = "⚠️ Bu so'rovga javob berib bo'lmadi (xavfsizlik cheklovi)."
    else:
        blocked = (result.get("promptFeedback") or {}).get("blockReason")
        if blocked:
            reply = "⚠️ Bu so'rovga javob berib bo'lmadi (xavfsizlik cheklovi)."
    return web.json_response({"reply": reply})


async def top_page(request):
    """TOP reyting -- eng ko'p ko'rilgan (anime_detail sahifasi ochilgan
    sonlari bo'yicha) animelar ro'yxati."""
    current_user = await get_current_user(request)
    theme = get_theme(request, current_user)
    rows = await db.get_top_anime(limit=30)

    if rows:
        cards = "".join(anime_card_html(a) for a in rows)
        grid = f'<div class="grid">{cards}</div>'
    else:
        grid = '<p class="empty">Hozircha reyting uchun yetarli ma\'lumot yo\'q -- animelar tomosha ' \
               'qilingan sayin bu yerda ko\'rinadi.</p>'

    body = f"""
<h2 class="section"><span class="ic">&#128293;</span> TOP reyting <span class="count">{len(rows)}</span></h2>
{grid}
"""
    return web.Response(
        text=base_page("TOP reyting", body, active="top", current_user=current_user, theme=theme),
        content_type="text/html",
    )


async def about_page(request):
    """'Biz haqimizda' -- oddiy statik ma'lumot sahifasi."""
    current_user = await get_current_user(request)
    theme = get_theme(request, current_user)
    total = await db.count_anime()
    genres = await db.get_all_genres()

    body = f"""
<h2 class="section"><span class="ic">&#10022;</span> Biz haqimizda</h2>
<div class="static-page">
  <p class="lead">STAR DUBBING — o'zbek tilida sifatli anime dublyaji bilan shug'ullanuvchi jamoa.</p>
  <p>Maqsadimiz — sevimli animelaringizni ona tilingizda, sifatli va qulay tarzda tomosha qilish
  imkonini berish. Barcha epizodlar avvalo Telegram botimiz orqali chiqadi, so'ng ularning bir qismi
  saytda ham mavjud bo'ladi.</p>
  <p>Jamoamiz tarjima, dublyaj va montaj ustida doimiy ishlaydi — shu sababli yangi qismlar
  muntazam qo'shilib boriladi.</p>
  <div class="feature-list">
    <div class="feature-item"><span class="f-ic">🎙️</span>
      <div class="f-t">Sifatli dublyaj</div><div class="f-d">Professional ovoz va tahrir bilan tayyorlangan qismlar.</div></div>
    <div class="feature-item"><span class="f-ic">⚡</span>
      <div class="f-t">Tezkor yangilanish</div><div class="f-d">Yangi qismlar chiqishi bilan darhol yuklanadi.</div></div>
    <div class="feature-item"><span class="f-ic">🤖</span>
      <div class="f-t">Bot + sayt</div><div class="f-d">Istalgan joyda — Telegram botda yoki saytda tomosha qiling.</div></div>
    <div class="feature-item"><span class="f-ic">👑</span>
      <div class="f-t">VIP imkoniyatlar</div><div class="f-d">Ba'zi anime va qismlar VIP a'zolar uchun maxsus ochiladi.</div></div>
  </div>
  <div class="stats-row" style="margin-top:6px">
    <div class="stat"><span class="num">{total}</span><span class="label">anime</span></div>
    <div class="stat"><span class="num">{len(genres)}</span><span class="label">janr</span></div>
    <div class="stat"><span class="num">24/7</span><span class="label">faol bot</span></div>
  </div>
  <p style="text-align:center;margin-top:34px">
    <a class="cta-primary" href="https://t.me/{BOT_USERNAME}"><span class="play">▶</span> Telegram botni ochish</a>
  </p>
</div>
"""
    return web.Response(
        text=base_page("Biz haqimizda", body, active="haqida", current_user=current_user, theme=theme),
        content_type="text/html",
    )


async def vip_page(request):
    """VIP/Premium haqida ma'lumot -- VIP tugmasi botga olib boradi
    (VIP berish/sotib olish mantiqi bot tarafida ishlaydi)."""
    current_user = await get_current_user(request)
    theme = get_theme(request, current_user)

    body = f"""
<h2 class="section"><span class="ic">&#128081;</span> VIP / Premium</h2>
<p class="empty" style="text-align:center;max-width:620px;margin:0 auto;padding:0">
  VIP status ba'zi maxsus anime va qismlarga to'liq kirish imkonini beradi hamda jamoamizni
  qo'llab-quvvatlaydi.
</p>
<div class="plans">
  <div class="plan-card">
    <div class="p-name">Oddiy</div>
    <ul class="p-perks">
      <li>Barcha ochiq anime va qismlar</li>
      <li>Janr va qidiruv orqali qidirish</li>
      <li>Telegram bot orqali tomosha qilish</li>
    </ul>
    <span class="cta-secondary" style="pointer-events:none;opacity:.65">Joriy holat</span>
  </div>
  <div class="plan-card vip">
    <div class="p-name" style="color:var(--vip)">👑 VIP</div>
    <ul class="p-perks">
      <li>VIP-only animelarga to'liq kirish</li>
      <li>Yangi qismlarga birinchilardan bo'lib kirish</li>
      <li>Jamoani qo'llab-quvvatlash</li>
    </ul>
    <a class="cta-primary" href="https://t.me/{BOT_USERNAME}"><span class="play">▶</span> VIP olish</a>
  </div>
</div>
"""
    return web.Response(
        text=base_page("VIP", body, active="vip", current_user=current_user, theme=theme),
        content_type="text/html",
    )


async def faq_page(request):
    """Savol-javob (FAQ) -- native <details>/<summary> orqali, JS shart emas."""
    current_user = await get_current_user(request)
    theme = get_theme(request, current_user)

    faqs = [
        ("Sayt va bot bepulmi?",
         "Ha, kontentning katta qismi butunlay bepul. Ba'zi anime yoki qismlar VIP status uchun "
         "maxsus ochilgan."),
        ("VIP statusni qanday olsam bo'ladi?",
         "Telegram botimizga yozing — u yerda VIP olish bo'yicha yo'riqnoma beriladi."),
        ("Nega ba'zi qismlar saytda ishlamayapti?",
         "Ba'zi qismlar hali saytga bog'lanmagan bo'lishi mumkin — bunday holda "
         "\"Telegram bot orqali tomosha qilish\" havolasi ko'rsatiladi."),
        ("Yangi qismlar qachon chiqadi?",
         "Jamoamiz muntazam ishlaydi, biroq aniq jadval yo'q — yangiliklardan xabardor bo'lish "
         "uchun profilingizda bildirishnomalarni yoqib qo'ying."),
        ("Anime so'rovi qoldirsam bo'ladimi?",
         "Albatta! Qaysi animeni dublyaj qilishimizni xohlasangiz, Telegram bot orqali murojaat qiling."),
    ]
    items = "".join(
        f'<details class="faq-item"><summary>{html.escape(q)}</summary>'
        f'<div class="faq-a">{html.escape(a)}</div></details>'
        for q, a in faqs
    )
    body = f"""
<h2 class="section"><span class="ic">&#10022;</span> Savol-javob</h2>
<div class="faq-list">{items}</div>
"""
    return web.Response(
        text=base_page("Savol-javob", body, active="savollar", current_user=current_user, theme=theme),
        content_type="text/html",
    )


async def contact_page(request):
    """Aloqa -- saytda backend/email yo'qligi sababli, barcha murojaatlar
    Telegram bot orqali yo'naltiriladi."""
    current_user = await get_current_user(request)
    theme = get_theme(request, current_user)

    body = f"""
<h2 class="section"><span class="ic">&#10022;</span> Aloqa</h2>
<div class="contact-grid">
  <a class="contact-card" href="https://t.me/{BOT_USERNAME}">
    <span class="c-ic">🤖</span><div class="c-t">Telegram bot</div>
    <div class="c-d">Savol, taklif yoki anime so'rovi uchun</div>
  </a>
  <a class="contact-card" href="/savollar">
    <span class="c-ic">❓</span><div class="c-t">Savol-javob</div>
    <div class="c-d">Tez-tez beriladigan savollarga javoblar</div>
  </a>
  <a class="contact-card" href="/vip">
    <span class="c-ic">👑</span><div class="c-t">VIP olish</div>
    <div class="c-d">VIP status va imkoniyatlar haqida</div>
  </a>
</div>
"""
    return web.Response(
        text=base_page("Aloqa", body, active="aloqa", current_user=current_user, theme=theme),
        content_type="text/html",
    )


async def ping(request):
    return web.Response(text="STAR DUBBING bot va sayt ishlayapti ✅")


def create_app(bot) -> web.Application:
    app = web.Application(client_max_size=20 * 1024 * 1024)  # AI widget fayl yuklashlari uchun
    app["bot"] = bot
    app.router.add_get("/", home)
    app.router.add_get("/ping", ping)
    app.router.add_get("/janrlar", genres_page)
    app.router.add_get("/janr/{name}", genre_detail)
    app.router.add_get("/top", top_page)
    app.router.add_get("/haqida", about_page)
    app.router.add_get("/vip", vip_page)
    app.router.add_get("/savollar", faq_page)
    app.router.add_get("/aloqa", contact_page)
    app.router.add_get("/qidiruv", search_page)
    app.router.add_get("/api/search", api_search)
    app.router.add_get("/tasodifiy", random_anime)
    app.router.add_get("/anime/{id}", anime_detail)
    app.router.add_get("/anime/{id}/qism/{num}", episode_watch)
    app.router.add_get("/poster/{id}", poster_proxy)
    app.router.add_get("/kirish", login_via_token)
    app.router.add_get("/chiqish", logout)
    app.router.add_get("/profil", profile_page)
    app.router.add_post("/api/profile", api_profile_update)
    app.router.add_post("/api/assistant", api_assistant)
    return app