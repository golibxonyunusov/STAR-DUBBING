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

import base64
import hashlib
import hmac
import html
import json
import random
import time
from urllib.parse import quote

from aiohttp import web

import database as db
from config import BOT_TOKEN, BOT_USERNAME, PAGE_SIZE, STORAGE_CHANNEL_USERNAME

ACCENT = "#9b8cff"

SESSION_MAX_AGE = 60 * 60 * 24 * 30  # 30 kun


# ---------- TELEGRAM LOGIN WIDGET: HASH TEKSHIRISH VA SESSIYA ----------

def _telegram_check_hash(data: dict) -> bool:
    """Telegram Login Widget yuborgan ma'lumotning haqiqiyligini tekshiradi.
    https://core.telegram.org/widgets/login#checking-authorization
    """
    received_hash = data.get("hash", "")
    check_data = {k: v for k, v in data.items() if k != "hash"}
    data_check_string = "\n".join(f"{k}={check_data[k]}" for k in sorted(check_data))
    secret_key = hashlib.sha256(BOT_TOKEN.encode()).digest()
    computed_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(computed_hash, received_hash)


def _sign(payload_b64: str) -> str:
    secret = hashlib.sha256(BOT_TOKEN.encode()).digest()
    return hmac.new(secret, payload_b64.encode(), hashlib.sha256).hexdigest()[:32]


def make_session_cookie(user_data: dict) -> str:
    payload = {
        "id": user_data["id"],
        "first_name": user_data.get("first_name", ""),
        "username": user_data.get("username", ""),
        "photo_url": user_data.get("photo_url", ""),
        "ts": int(time.time()),
    }
    payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()
    return f"{payload_b64}.{_sign(payload_b64)}"


def read_session_cookie(cookie_value: str | None) -> dict | None:
    if not cookie_value or "." not in cookie_value:
        return None
    payload_b64, sig = cookie_value.rsplit(".", 1)
    if not hmac.compare_digest(_sign(payload_b64), sig):
        return None
    try:
        payload = json.loads(base64.urlsafe_b64decode(payload_b64.encode()))
    except Exception:
        return None
    if time.time() - payload.get("ts", 0) > SESSION_MAX_AGE:
        return None
    return payload


def get_session(request) -> dict | None:
    return read_session_cookie(request.cookies.get("session"))


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
  * { box-sizing: border-box; }
  html { scroll-behavior: smooth; }

  /* ---- yorug' (light) mavzu -- toggle tugmasi orqali almashtiriladi ---- */
  html[data-theme="light"] {
    --bg: #f4f3fb;
    --bg-a: #ffffff;
    --bg-b: #ecebf9;
    --panel: #ffffff;
    --panel-hi: #f1effb;
    --line: #e1dff2;
    --line-soft: #ebe9f7;
    --ink: #1c1a2e;
    --muted: #6d6a88;
  }
  html[data-theme="light"] #starfield { opacity: 0.12; }
  html[data-theme="light"] .wordmark { filter: drop-shadow(0 4px 30px #6c5ce730); }
  html[data-theme="light"] .card:hover { box-shadow: 0 22px 46px -18px #6c5ce730; }
  html[data-theme="light"] ::-webkit-scrollbar-thumb { background: #d8d5ec; }
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
    max-width: 560px; margin: 0 auto; color: #c9c6dc; font-size: 15.5px;
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
    color: #c9c6dc; max-width: 640px; font-size: 15px;
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
  button.ep-btn { font-family: inherit; cursor: pointer; text-align: left; width: 100%; }
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
  }

  /* ---- theme toggle & profil (header) ---- */
  .icon-btn {
    display: inline-flex; align-items: center; justify-content: center;
    width: 38px; height: 38px; border-radius: 50%;
    background: var(--panel); border: 1px solid var(--line);
    font-size: 15px; cursor: pointer; transition: all .2s; flex-shrink: 0;
  }
  .icon-btn:hover { border-color: var(--violet); background: var(--panel-hi); }
  .profile-chip {
    display: flex; align-items: center; gap: 8px;
    background: var(--panel); border: 1px solid var(--line); border-radius: 30px;
    padding: 5px 14px 5px 5px; font-size: 13px; font-weight: 600; transition: all .2s;
  }
  .profile-chip:hover { border-color: var(--violet); }
  .profile-chip img {
    width: 26px; height: 26px; border-radius: 50%; object-fit: cover;
    background: var(--panel-hi);
  }
  .header-actions { display: flex; align-items: center; gap: 10px; }

  /* ---- profil sahifasi ---- */
  .profile-card {
    max-width: 460px; margin: 40px auto; background: var(--panel);
    border: 1px solid var(--line); border-radius: 16px; padding: 36px 30px;
    text-align: center;
  }
  .profile-card img.avatar {
    width: 92px; height: 92px; border-radius: 50%; object-fit: cover;
    margin-bottom: 18px; border: 3px solid var(--violet); background: var(--panel-hi);
  }
  .profile-card h1 {
    font-family: 'Oswald', sans-serif; font-size: 22px; margin: 0 0 4px;
    text-transform: uppercase;
  }
  .profile-card .uname {
    color: var(--muted); font-family: 'IBM Plex Mono', monospace; font-size: 13px;
    margin-bottom: 22px;
  }
  .vip-pill {
    display: inline-flex; align-items: center; gap: 8px; padding: 10px 22px;
    border-radius: 30px; font-weight: 700; font-size: 13px; margin-bottom: 22px;
  }
  .vip-pill.active {
    background: linear-gradient(135deg, #ffb42e30, #ff5d7a30); border: 1px solid #ffb42e60;
    color: #ffcf7d;
  }
  .vip-pill.inactive {
    background: var(--panel-hi); border: 1px solid var(--line); color: var(--muted);
  }
  .profile-actions { display: flex; flex-direction: column; gap: 10px; }
  .login-widget-wrap { display: flex; justify-content: center; margin-top: 10px; }

  /* ---- video modal (saytda, Telegram'ga chiqmasdan tomosha) ---- */
  .video-modal {
    position: fixed; inset: 0; z-index: 100; background: #06060cd8;
    backdrop-filter: blur(6px);
    display: none; align-items: center; justify-content: center; padding: 20px;
  }
  .video-modal.open { display: flex; }
  .video-modal .box {
    width: 100%; max-width: 520px; background: #0b0a17; border: 1px solid var(--line);
    border-radius: 14px; overflow: hidden; box-shadow: 0 40px 90px -20px #000000e0;
  }
  .video-modal .box-head {
    display: flex; justify-content: space-between; align-items: center;
    padding: 12px 16px; border-bottom: 1px solid var(--line-soft);
    font-family: 'IBM Plex Mono', monospace; font-size: 12.5px; color: var(--muted);
  }
  .video-modal .box-head button {
    background: none; border: none; color: var(--muted); font-size: 20px;
    cursor: pointer; line-height: 1; padding: 0 4px;
  }
  .video-modal .box-head button:hover { color: var(--ink); }
  .video-modal iframe { width: 100%; aspect-ratio: 9/16; max-height: 75vh; border: none; display: block; }
"""


SCRIPTS = """
  (function () {
    // ---- theme toggle (dark/light) ----
    function applyThemeIcon() {
      var btn = document.getElementById('theme-toggle');
      if (!btn) return;
      var t = document.documentElement.getAttribute('data-theme') || 'dark';
      btn.textContent = t === 'dark' ? '\\u{1F319}' : '\\u2600\\uFE0F';
    }
    window.toggleTheme = function () {
      var html = document.documentElement;
      var cur = html.getAttribute('data-theme') || 'dark';
      var next = cur === 'dark' ? 'light' : 'dark';
      html.setAttribute('data-theme', next);
      try { localStorage.setItem('theme', next); } catch (e) {}
      applyThemeIcon();
    };
    applyThemeIcon();

    // ---- video modal (saytda tomosha qilish, Telegram'ga chiqmasdan) ----
    window.openPlayer = function (url) {
      var modal = document.getElementById('video-modal');
      var frame = document.getElementById('video-modal-frame');
      if (!modal || !frame) return;
      frame.src = url;
      modal.classList.add('open');
      document.body.style.overflow = 'hidden';
    };
    window.closePlayer = function () {
      var modal = document.getElementById('video-modal');
      var frame = document.getElementById('video-modal-frame');
      if (!modal || !frame) return;
      modal.classList.remove('open');
      frame.src = '';
      document.body.style.overflow = '';
    };
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') window.closePlayer();
    });

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
  })();
"""


def base_page(title: str, body: str, active: str = "", marquee_items=None, session: dict | None = None) -> str:
    if not marquee_items:
        marquee_items = [
            "YANGI QISMLAR MUNTAZAM YUKLANADI",
            "O'ZBEK TILIDA SIFATLI DUBLYAJ",
            "TELEGRAM BOT ORQALI ISTALGAN JOYDA TOMOSHA QILING",
        ]
    track = " &nbsp;&#10022;&nbsp; ".join(html.escape(m) for m in marquee_items)
    marquee_html = f'<span>{track}</span> &nbsp;&#10022;&nbsp; <span>{track}</span>'

    if session:
        display_name = html.escape(session.get("first_name") or session.get("username") or "Profil")
        avatar = session.get("photo_url") or ""
        avatar_tag = f'<img src="{html.escape(avatar)}" alt="">' if avatar else ""
        profile_chip = f'<a class="profile-chip" href="/profil">{avatar_tag}<span>{display_name}</span></a>'
    else:
        profile_chip = '<a class="profile-chip" href="/profil"><span>👤 Kirish</span></a>'

    return f"""<!DOCTYPE html>
<html lang="uz">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{html.escape(title)} — STAR DUBBING</title>
<link rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>⭐</text></svg>">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Oswald:wght@500;600;700&family=Inter:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<script>
  (function () {{
    try {{
      var t = localStorage.getItem('theme') || 'dark';
      document.documentElement.setAttribute('data-theme', t);
    }} catch (e) {{}}
  }})();
</script>
<style>{STYLES}</style>
</head>
<body>
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
      <a href="/tasodifiy" class="{'active' if active == 'tasodifiy' else ''}">Tasodifiy</a>
      <a href="https://t.me/{BOT_USERNAME}" class="{'active' if active == 'bot' else ''}">Telegram bot</a>
    </nav>
    <div class="search-wrap">
      <form class="search-box" action="/qidiruv" method="get" autocomplete="off">
        <span>&#10022;</span>
        <input id="live-search-input" type="text" name="q" placeholder="anime nomini yozing (masalan: naruto)..." />
      </form>
      <div id="live-results" class="live-results"></div>
    </div>
    <div class="header-actions">
      <button id="theme-toggle" class="icon-btn" onclick="toggleTheme()" title="Ko'rinishni almashtirish">🌙</button>
      {profile_chip}
    </div>
  </div>
</header>
<main>
{body}
</main>
<footer>
  <div class="f-logo">✦ STAR DUBBING</div>
  <div style="margin-top:6px">o'zbek tilidagi anime dublyaj jamoasi. Barcha epizodlarni
  <a href="https://t.me/{BOT_USERNAME}">Telegram botimiz</a> orqali tomosha qiling.</div>
</footer>
<div id="video-modal" class="video-modal">
  <div class="box">
    <div class="box-head">
      <span>▶ TOMOSHA QILISH</span>
      <button onclick="closePlayer()">✕</button>
    </div>
    <iframe id="video-modal-frame" src="" allowfullscreen></iframe>
  </div>
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
    marquee_items = [a["title"] for a in featured] or None

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
        text=base_page("Bosh sahifa", body, active="home", marquee_items=marquee_items, session=get_session(request)),
        content_type="text/html",
    )


async def genres_page(request):
    genres = await db.get_all_genres()
    links = "".join(f'<a href="/janr/{quote(g)}">{html.escape(g)}</a>' for g in genres)
    body = f"""
<h2 class="section"><span class="ic">&#10022;</span> Janrlar <span class="count">{len(genres)}</span></h2>
<div class="genres">{links or "<p class='empty'>Janrlar topilmadi.</p>"}</div>
"""
    return web.Response(text=base_page("Janrlar", body, active="janrlar", session=get_session(request)), content_type="text/html")


async def genre_detail(request):
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
    return web.Response(text=base_page(genre, body, session=get_session(request)), content_type="text/html")


async def _smart_search(q: str, limit: int = 60):
    """Ham nom (LIKE, qisman moslik bilan), ham kod (ID) bo'yicha qidiradi.
    Nom ustuvor -- foydalanuvchi anime nomining faqat bir qismini yozsa ham topiladi.
    Agar anime nomi raqamlardan iborat bo'lsa (masalan '111'), bu ham to'g'ri ishlaydi,
    chunki avval nom bo'yicha LIKE qidiruv, keyin (agar kerak bo'lsa) ID bo'yicha
    qo'shimcha moslik qo'shiladi."""
    q = q.strip()
    seen = set()
    results = []

    title_matches = await db.search_anime(q, limit=limit)
    for a in title_matches:
        if a["id"] not in seen:
            results.append(a)
            seen.add(a["id"])

    if q.isdigit() and len(results) < limit:
        anime = await db.get_anime(int(q))
        if anime and anime["id"] not in seen:
            results.append(anime)
            seen.add(anime["id"])

    return results


async def search_page(request):
    q = request.query.get("q", "").strip()
    if not q:
        return web.HTTPFound("/")

    rows = await _smart_search(q, limit=60)

    if rows:
        grid = f'<div class="grid">{"".join(anime_card_html(a) for a in rows)}</div>'
    else:
        grid = '<p class="empty">Hech narsa topilmadi. Nomning bir qismini yozib ko\'ring.</p>'

    body = f'<h2 class="section"><span class="ic">&gt;_</span> "{html.escape(q)}" bo\'yicha natijalar <span class="count">{len(rows)}</span></h2>{grid}'
    return web.Response(text=base_page(f"Qidiruv: {q}", body, session=get_session(request)), content_type="text/html")


async def api_search(request):
    """Live-qidiruv uchun JSON API — foydalanuvchi yozayotganda ishlaydi."""
    q = request.query.get("q", "").strip()
    if len(q) < 1:
        return web.json_response([])

    rows = await _smart_search(q, limit=8)

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
    try:
        anime_id = int(request.match_info["id"])
    except ValueError:
        raise web.HTTPNotFound()

    anime = await db.get_anime(anime_id)
    if not anime:
        raise web.HTTPNotFound()

    session = get_session(request)
    user_is_vip = await db.is_vip(session["id"]) if session else False

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

    if anime["vip_only"] and not user_is_vip:
        if session:
            lock_msg = (
                "🔒 Bu anime faqat <b>VIP</b> foydalanuvchilar uchun. Sizda hozircha VIP "
                f'status yo\'q — olish uchun <a href="https://t.me/{BOT_USERNAME}">botga</a> yozing.'
            )
        else:
            lock_msg = (
                '🔒 Bu anime faqat <b>VIP</b> foydalanuvchilar uchun. '
                f'<a href="/profil">Profilingizga kiring</a>, agar VIP statusingiz bo\'lsa shu yerda ko\'rasiz, '
                f'aks holda VIP olish uchun <a href="https://t.me/{BOT_USERNAME}">botga</a> yozing.'
            )
        body_episodes = f'<div class="lock-notice">{lock_msg}</div>'
    elif episodes:
        btns = []
        for ep in episodes:
            if ep["channel_message_id"] and STORAGE_CHANNEL_USERNAME:
                embed_url = f"https://t.me/{STORAGE_CHANNEL_USERNAME}/{ep['channel_message_id']}?embed=1"
                btns.append(
                    f'<button type="button" class="ep-btn" onclick="openPlayer(\'{embed_url}\')">'
                    f'<span class="play-ic">▶</span><span class="num">{ep["episode_number"]:02d}</span> '
                    f'{ep["episode_number"]}-qism</button>'
                )
            else:
                btns.append(
                    f'<a class="ep-btn" href="https://t.me/{BOT_USERNAME}?start=ep_{anime_id}_{ep["episode_number"]}">'
                    f'<span class="play-ic">▶</span><span class="num">{ep["episode_number"]:02d}</span> '
                    f'{ep["episode_number"]}-qism</a>'
                )
        body_episodes = f'<div class="episodes">{"".join(btns)}</div>'
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
    return web.Response(text=base_page(anime["title"], body, session=session), content_type="text/html")


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


async def ping(request):
    return web.Response(text="STAR DUBBING bot va sayt ishlayapti ✅")


# ---------- PROFIL (TELEGRAM LOGIN WIDGET) ----------

async def profile_page(request):
    session = get_session(request)

    if session:
        vip = await db.get_vip(session["id"])
        if vip:
            vip_text = f"👑 VIP faol — muddati: {vip['expires_at'][:10]}" if vip["expires_at"] else "👑 VIP faol — umrbod ♾"
            vip_html = f'<div class="vip-pill active">{html.escape(vip_text)}</div>'
        else:
            vip_html = '<div class="vip-pill inactive">VIP emas</div>'

        avatar = session.get("photo_url") or ""
        avatar_tag = (
            f'<img class="avatar" src="{html.escape(avatar)}" alt="">'
            if avatar else '<div class="avatar" style="background:var(--panel-hi)"></div>'
        )
        uname = f"@{session['username']}" if session.get("username") else f"ID: {session['id']}"

        body = f"""
<div class="profile-card">
  {avatar_tag}
  <h1>{html.escape(session.get('first_name') or 'Foydalanuvchi')}</h1>
  <div class="uname mono">{html.escape(uname)}</div>
  {vip_html}
  <div class="profile-actions">
    <a class="cta-secondary" href="https://t.me/{BOT_USERNAME}">📲 Botni ochish</a>
    <a class="cta-secondary" href="/logout">🚪 Chiqish</a>
  </div>
</div>
"""
    else:
        body = f"""
<div class="profile-card">
  <h1>Profilga kirish</h1>
  <p style="color:var(--muted); font-size:14px; margin-bottom:22px; max-width:340px; margin-left:auto; margin-right:auto">
    Telegram hisobingiz orqali kiring — VIP holatingizni shu yerdan ko'rib turasiz.
  </p>
  <div class="login-widget-wrap">
    <script async src="https://telegram.org/js/telegram-widget.js?22"
      data-telegram-login="{BOT_USERNAME}"
      data-size="large"
      data-userpic="true"
      data-radius="10"
      data-auth-url="/profil/callback"
      data-request-access="write"></script>
  </div>
</div>
"""
    return web.Response(text=base_page("Profil", body, active="profil", session=session), content_type="text/html")


async def profile_callback(request):
    data = dict(request.query)
    if not data.get("hash") or not _telegram_check_hash(data):
        return web.Response(
            text=base_page(
                "Xatolik",
                '<div class="profile-card"><h1>Tasdiqlash muvaffaqiyatsiz</h1>'
                '<p style="color:var(--muted)">Iltimos, qaytadan urining.</p>'
                '<div class="profile-actions"><a class="cta-secondary" href="/profil">⬅ Qaytish</a></div></div>',
            ),
            content_type="text/html",
            status=403,
        )

    session_payload = {
        "id": int(data["id"]),
        "first_name": data.get("first_name", ""),
        "username": data.get("username", ""),
        "photo_url": data.get("photo_url", ""),
    }
    resp = web.HTTPFound("/profil")
    resp.set_cookie(
        "session", make_session_cookie(session_payload),
        max_age=SESSION_MAX_AGE, httponly=True, samesite="Lax",
    )
    return resp


async def logout(request):
    resp = web.HTTPFound("/")
    resp.del_cookie("session")
    return resp


def create_app(bot) -> web.Application:
    app = web.Application()
    app["bot"] = bot
    app.router.add_get("/", home)
    app.router.add_get("/ping", ping)
    app.router.add_get("/janrlar", genres_page)
    app.router.add_get("/janr/{name}", genre_detail)
    app.router.add_get("/qidiruv", search_page)
    app.router.add_get("/profil", profile_page)
    app.router.add_get("/profil/callback", profile_callback)
    app.router.add_get("/logout", logout)
    app.router.add_get("/api/search", api_search)
    app.router.add_get("/tasodifiy", random_anime)
    app.router.add_get("/anime/{id}", anime_detail)
    app.router.add_get("/poster/{id}", poster_proxy)
    return app