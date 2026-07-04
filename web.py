"""
AniSinus veb-sayti.

Bu -- botning o'zi bilan bir joyda (Render'da) ishlaydigan, o'sha SQLite
ma'lumotlar bazasidan foydalanadigan ochiq (public) katalog sayti.

MUHIM TEXNIK IZOH: epizod videolari Telegram serverida (file_id orqali)
saqlanadi, veb-brauzerda to'g'ridan-to'g'ri ijro etib bo'lmaydi (bot API
orqali katta fayllarni yuklab olish imkoni cheklangan). Shuning uchun sayt
videoni o'zida ko'rsatmaydi -- "Tomosha qilish" tugmasi Telegram botini
ochib, videoni o'sha yerda avtomatik yuboradi (deep-link orqali).
"""

import html
from urllib.parse import quote

from aiohttp import web

import database as db
from config import BOT_USERNAME, PAGE_SIZE

ACCENT = "#ffd23f"


# ---------- UMUMIY HTML QOLIP ----------
# Dizayn yo'nalishi: "efirda" -- dublyaj studiyasi / broadcast estetikasi.
# Signature element: burned-in subtitle satrlari, REC/ON-AIR belgisi va
# timecode uslubidagi monospace raqamlar -- fansub/dublyaj dunyosidan.

def base_page(title: str, body: str, active: str = "") -> str:
    return f"""<!DOCTYPE html>
<html lang="uz">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{html.escape(title)} — STAR DUBBING</title>
<link rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>⭐</text></svg>">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Oswald:wght@500;600;700&family=Inter:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<style>
  :root {{
    --bg: #0a0b0f;
    --panel: #12131a;
    --panel-hi: #191a23;
    --line: #24252f;
    --ink: #f2f1ec;
    --muted: #83848f;
    --sub: #ffd23f;     /* subtitle yellow -- signature accent */
    --rec: #ff4438;     /* recording red */
    --ok: #38d9a9;      /* transmit teal, secondary accent */
  }}
  * {{ box-sizing: border-box; }}
  html {{ scroll-behavior: smooth; }}
  @media (prefers-reduced-motion: reduce) {{
    * {{ animation: none !important; transition: none !important; }}
  }}
  body {{
    margin: 0;
    background:
      radial-gradient(900px 500px at 12% -8%, #ffd23f0d, transparent 60%),
      radial-gradient(800px 480px at 92% 4%, #ff443814, transparent 60%),
      var(--bg);
    color: var(--ink);
    font-family: 'Inter', 'Segoe UI', sans-serif;
    line-height: 1.6;
    min-height: 100vh;
  }}
  ::selection {{ background: var(--sub); color: #14140d; }}
  ::-webkit-scrollbar {{ width: 10px; }}
  ::-webkit-scrollbar-track {{ background: var(--bg); }}
  ::-webkit-scrollbar-thumb {{ background: #2a2b35; border-radius: 10px; }}
  a {{ color: inherit; text-decoration: none; }}
  .mono {{ font-family: 'IBM Plex Mono', monospace; }}

  /* ---- broadcast header ---- */
  header {{
    position: sticky; top: 0; z-index: 20;
    background: rgba(10,11,15,0.82);
    backdrop-filter: blur(14px) saturate(140%);
    border-bottom: 1px solid var(--line);
  }}
  .rail {{
    display: flex; align-items: center; justify-content: space-between;
    gap: 10px; padding: 6px 32px;
    font-family: 'IBM Plex Mono', monospace; font-size: 11px;
    color: var(--muted); border-bottom: 1px dashed var(--line);
    letter-spacing: 0.5px;
  }}
  .rail .on-air {{ display: flex; align-items: center; gap: 7px; color: var(--ok); }}
  .rec-dot {{
    width: 7px; height: 7px; border-radius: 50%; background: var(--rec);
    box-shadow: 0 0 0 0 #ff443870;
    animation: pulse 1.6s infinite;
  }}
  @keyframes pulse {{
    0% {{ box-shadow: 0 0 0 0 #ff443870; }}
    70% {{ box-shadow: 0 0 0 6px transparent; }}
    100% {{ box-shadow: 0 0 0 0 transparent; }}
  }}
  header .bar {{
    padding: 14px 32px;
    display: flex; align-items: center; justify-content: space-between;
    gap: 20px; flex-wrap: wrap;
  }}
  .logo {{
    font-family: 'Oswald', sans-serif; font-weight: 700; font-size: 22px;
    letter-spacing: 0.5px; text-transform: uppercase;
    display: flex; align-items: center; gap: 9px; color: var(--ink);
  }}
  .logo .star {{ color: var(--sub); }}
  nav {{ display: flex; gap: 4px; font-size: 13px; font-weight: 600; }}
  nav a {{
    color: var(--muted); padding: 8px 15px; border-radius: 3px;
    text-transform: uppercase; letter-spacing: 0.6px; font-size: 12px;
    border-bottom: 2px solid transparent;
    transition: all .2s;
  }}
  nav a.active, nav a:hover {{ color: var(--ink); border-bottom-color: var(--sub); }}
  .search-box {{
    display: flex; align-items: center; gap: 9px;
    background: var(--panel); border: 1px solid var(--line); border-radius: 4px;
    padding: 10px 16px; min-width: 240px;
    transition: border-color .2s;
  }}
  .search-box:focus-within {{ border-color: var(--sub); }}
  .search-box span {{ color: var(--muted); font-size: 13px; }}
  .search-box input {{
    background: transparent; border: none; outline: none; color: var(--ink);
    font-size: 13.5px; width: 100%; font-family: 'IBM Plex Mono', monospace;
  }}
  .search-box input::placeholder {{ color: var(--muted); }}

  main {{ max-width: 1180px; margin: 0 auto; padding: 0 28px 70px; }}

  /* ---- hero: burned-in subtitle motif ---- */
  .hero {{ text-align: center; padding: 68px 16px 40px; position: relative; }}
  .hero .eyebrow {{
    display: inline-flex; align-items: center; gap: 8px;
    font-family: 'IBM Plex Mono', monospace; font-size: 11.5px; font-weight: 500;
    color: var(--ok); letter-spacing: 1px; margin-bottom: 20px;
    padding: 6px 14px; border: 1px solid #38d9a940; border-radius: 3px;
    background: #38d9a90d;
  }}
  .hero h1 {{
    font-family: 'Oswald', sans-serif;
    font-size: clamp(30px, 5.4vw, 48px); margin: 0 0 22px; font-weight: 700;
    letter-spacing: 0.2px; text-transform: uppercase; line-height: 1.15;
  }}
  .subtitle-bar {{
    display: inline-block; background: #000000cc; border-radius: 3px;
    padding: 10px 22px; margin: 0 auto; max-width: 560px;
    border: 1px solid var(--line);
  }}
  .subtitle-bar p {{
    margin: 0; color: var(--sub); font-size: 15px; font-weight: 500;
    font-family: 'IBM Plex Mono', monospace;
  }}
  .subtitle-bar p.small {{ color: #cfcfcf; font-size: 12.5px; margin-top: 4px; }}
  .cta {{
    display: inline-flex; align-items: center; gap: 10px;
    margin-top: 28px; padding: 15px 30px;
    background: var(--sub); color: #14140d; border-radius: 3px;
    font-weight: 700; font-size: 14px; text-transform: uppercase; letter-spacing: 0.5px;
    box-shadow: 0 8px 26px -8px #ffd23f70;
    transition: transform .2s, box-shadow .2s;
  }}
  .cta:hover {{ transform: translateY(-2px); box-shadow: 0 12px 32px -6px #ffd23f90; }}
  .cta .play {{
    width: 20px; height: 20px; border-radius: 50%; background: #14140d;
    color: var(--sub); display: inline-flex; align-items: center; justify-content: center;
    font-size: 10px;
  }}

  /* ---- filmstrip section divider ---- */
  h2.section {{
    font-family: 'IBM Plex Mono', monospace;
    font-size: 12px; color: var(--muted); font-weight: 500;
    margin: 50px 0 20px; letter-spacing: 1px;
    display: flex; align-items: center; gap: 12px;
  }}
  h2.section .tc {{ color: var(--sub); }}
  h2.section::after {{
    content: ""; flex: 1; height: 1px;
    background: repeating-linear-gradient(90deg, var(--line) 0 6px, transparent 6px 10px);
  }}

  .grid {{
    display: grid; grid-template-columns: repeat(auto-fill, minmax(168px, 1fr));
    gap: 20px;
  }}
  .card {{
    background: var(--panel); border-radius: 6px; overflow: hidden;
    border: 1px solid var(--line);
    transition: transform .22s cubic-bezier(.2,.8,.2,1), box-shadow .22s, border-color .22s;
    position: relative; display: block;
  }}
  .card:hover {{
    transform: translateY(-5px);
    border-color: #3a3b47;
    box-shadow: 0 20px 40px -18px #00000090;
  }}
  .card .poster-wrap {{
    position: relative; overflow: hidden; aspect-ratio: 2/3; background: #191a23;
  }}
  .card .poster-wrap::before, .card .poster-wrap::after {{
    content: ""; position: absolute; width: 14px; height: 14px; z-index: 3;
    border-color: #ffffff55; opacity: 0; transition: opacity .2s;
  }}
  .card .poster-wrap::before {{ top: 8px; left: 8px; border-top: 2px solid; border-left: 2px solid; }}
  .card .poster-wrap::after {{ top: 8px; right: 8px; border-top: 2px solid; border-right: 2px solid; }}
  .card:hover .poster-wrap::before, .card:hover .poster-wrap::after {{ opacity: 1; }}
  .card .poster {{
    width: 100%; height: 100%; object-fit: cover; display: block;
    transition: transform .4s;
  }}
  .card:hover .poster {{ transform: scale(1.05); }}
  .card .poster-wrap.empty::before {{
    content: "▶"; position: absolute; inset: 0; display: flex; border: none;
    align-items: center; justify-content: center; font-size: 30px; opacity: .2;
  }}
  .card .scanline {{
    position: absolute; left: 0; right: 0; height: 40%; z-index: 2;
    background: linear-gradient(180deg, transparent, #ffd23f18, transparent);
    top: -50%; transition: top .5s ease;
  }}
  .card:hover .scanline {{ top: 110%; }}
  .card .sub-strip {{
    position: absolute; left: 0; right: 0; bottom: 0; z-index: 2;
    background: linear-gradient(180deg, transparent, #000000d0 45%);
    padding: 22px 12px 10px;
  }}
  .card .sub-strip .t {{
    font-size: 13.5px; font-weight: 600; margin: 0 0 3px; color: var(--ink);
    overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
  }}
  .card .sub-strip .m {{
    font-size: 11px; color: var(--sub); font-family: 'IBM Plex Mono', monospace;
  }}
  .badge-vip {{
    position: absolute; top: 9px; left: 9px; z-index: 3;
    background: #000000b0; border: 1px solid var(--rec); color: var(--rec);
    font-family: 'IBM Plex Mono', monospace;
    font-size: 10px; font-weight: 600; padding: 4px 9px 4px 7px; border-radius: 3px;
    display: flex; align-items: center; gap: 5px; letter-spacing: 0.5px;
  }}
  .badge-vip .rec-dot {{ width: 6px; height: 6px; }}
  .empty {{ color: var(--muted); text-align: center; padding: 70px 0; font-size: 14px; }}
  .pager {{ display: flex; justify-content: center; gap: 12px; margin-top: 38px; }}
  .pager a {{
    background: var(--panel); border: 1px solid var(--line); padding: 10px 20px;
    border-radius: 3px; font-size: 13px; font-weight: 600;
    font-family: 'IBM Plex Mono', monospace;
    transition: all .2s;
  }}
  .pager a:hover {{ border-color: var(--sub); background: var(--panel-hi); color: var(--sub); }}
  .genres {{ display: flex; flex-wrap: wrap; gap: 9px; margin: 16px 0 0; }}
  .genres a {{
    background: var(--panel); border: 1px solid var(--line); padding: 8px 17px;
    border-radius: 3px; font-size: 12.5px; color: var(--muted); font-weight: 600;
    transition: all .2s;
  }}
  .genres a:hover {{ color: var(--sub); border-color: var(--sub); background: var(--panel-hi); }}

  /* ---- Anime detail page: viewfinder / playlist ---- */
  .detail {{ display: flex; gap: 38px; flex-wrap: wrap; padding-top: 22px; }}
  .detail .poster-big-wrap {{
    width: 260px; flex-shrink: 0; border-radius: 6px; overflow: hidden;
    aspect-ratio: 2/3; background: #191a23;
    box-shadow: 0 30px 60px -24px #000000a0;
    border: 1px solid var(--line); position: relative;
  }}
  .detail .poster-big-wrap::before, .detail .poster-big-wrap::after,
  .detail .poster-big-wrap .tick-r::before, .detail .poster-big-wrap .tick-r::after {{
    content: ""; position: absolute; width: 18px; height: 18px; z-index: 2;
    border-color: var(--sub); opacity: .8;
  }}
  .detail .poster-big-wrap::before {{ top: 10px; left: 10px; border-top: 2px solid; border-left: 2px solid; }}
  .detail .poster-big-wrap::after {{ bottom: 10px; right: 10px; border-bottom: 2px solid; border-right: 2px solid; }}
  .detail .poster-big {{ width: 100%; height: 100%; object-fit: cover; display: block; }}
  .detail .meta {{ flex: 1; min-width: 260px; }}
  .detail .meta .eyebrow-tc {{
    font-family: 'IBM Plex Mono', monospace; font-size: 11.5px; color: var(--sub);
    letter-spacing: 1px; margin-bottom: 10px; display: block;
  }}
  .detail .meta h1 {{
    font-family: 'Oswald', sans-serif;
    margin: 0 0 16px; font-size: 32px; font-weight: 700; letter-spacing: 0.3px;
    text-transform: uppercase; line-height: 1.2;
  }}
  .detail .meta .tags {{ display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 20px; }}
  .tag {{
    background: var(--panel); border: 1px solid var(--line); padding: 5px 13px;
    border-radius: 3px; font-size: 12px; color: var(--muted); font-weight: 500;
    font-family: 'IBM Plex Mono', monospace;
  }}
  .detail .meta p.desc {{
    color: #c9c9d2; max-width: 640px; font-size: 15px;
    border-left: 2px solid var(--sub); padding-left: 16px;
  }}
  .episodes {{ display: flex; flex-direction: column; gap: 8px; margin-top: 24px; max-width: 480px; }}
  .ep-btn {{
    background: var(--panel); border: 1px solid var(--line); padding: 13px 18px;
    border-radius: 4px; font-size: 14px; font-weight: 600;
    display: flex; align-items: center; gap: 12px;
    transition: all .18s;
  }}
  .ep-btn .num {{
    font-family: 'IBM Plex Mono', monospace; color: var(--muted); font-size: 13px;
    min-width: 26px;
  }}
  .ep-btn .play-ic {{
    width: 26px; height: 26px; border-radius: 50%; background: var(--line);
    display: flex; align-items: center; justify-content: center; font-size: 10px;
    flex-shrink: 0; transition: background .18s, color .18s; color: var(--muted);
  }}
  .ep-btn:hover {{
    border-color: var(--sub); background: var(--panel-hi); transform: translateX(4px);
  }}
  .ep-btn:hover .play-ic {{ background: var(--sub); color: #14140d; }}
  .lock-notice {{
    background: repeating-linear-gradient(135deg, #1a0f0d 0 10px, #1c1010 10px 20px);
    border: 1px solid #ff443850; color: #ffb3ac;
    padding: 18px 22px; border-radius: 4px; margin-top: 22px; font-size: 13.5px;
    font-family: 'IBM Plex Mono', monospace;
  }}
  .lock-notice a {{ color: var(--sub); font-weight: 700; text-decoration: underline; }}

  footer {{
    text-align: center; color: var(--muted); font-size: 12.5px;
    padding: 40px 16px 30px; margin-top: 54px;
    font-family: 'IBM Plex Mono', monospace;
    background: repeating-linear-gradient(90deg, var(--line) 0 6px, transparent 6px 14px) top left / 100% 1px no-repeat;
  }}
  footer a {{ color: var(--sub); font-weight: 600; }}

  @media (max-width: 560px) {{
    .rail {{ padding: 5px 16px; }}
    header .bar {{ padding: 12px 16px; }}
    main {{ padding: 0 16px 50px; }}
    .search-box {{ min-width: 0; width: 100%; order: 3; }}
    .detail {{ gap: 22px; }}
    .detail .poster-big-wrap {{ width: 170px; }}
  }}
</style>
</head>
<body>
<header>
  <div class="rail">
    <span class="on-air"><span class="rec-dot"></span> ON AIR</span>
    <span id="tc" class="mono">00:00:00</span>
  </div>
  <div class="bar">
    <a class="logo" href="/"><span class="star">⭐</span> STAR DUBBING</a>
    <nav>
      <a href="/" class="{'active' if active=='home' else ''}">Bosh sahifa</a>
      <a href="/janrlar" class="{'active' if active=='janrlar' else ''}">Janrlar</a>
      <a href="https://t.me/{BOT_USERNAME}" class="{'active' if active=='bot' else ''}">Telegram bot</a>
    </nav>
    <form class="search-box" action="/qidiruv" method="get">
      <span>&gt;_</span>
      <input type="text" name="q" placeholder="qidiruv: anime nomi yoki kodi..." />
    </form>
  </div>
</header>
<main>
{body}
</main>
<footer>
  © STAR DUBBING — o'zbek tilidagi anime dublyaj jamoasi. Barcha epizodlarni
  <a href="https://t.me/{BOT_USERNAME}">Telegram botimiz</a> orqali tomosha qiling.
</footer>
<script>
  (function() {{
    var el = document.getElementById('tc');
    if (!el) return;
    var s = 0;
    setInterval(function() {{
      s++;
      var h = String(Math.floor(s/3600)).padStart(2,'0');
      var m = String(Math.floor((s%3600)/60)).padStart(2,'0');
      var ss = String(s%60).padStart(2,'0');
      el.textContent = h+':'+m+':'+ss;
    }}, 1000);
  }})();
</script>
</body>
</html>"""


def anime_card_html(a) -> str:
    poster = f"/poster/{a['id']}" if a["poster_file_id"] else ""
    poster_tag = (
        f'<div class="poster-wrap"><img class="poster" src="{poster}" alt="{html.escape(a["title"])}" loading="lazy"><div class="scanline"></div></div>'
        if poster else '<div class="poster-wrap empty"><div class="scanline"></div></div>'
    )
    vip_badge = '<span class="badge-vip"><span class="rec-dot"></span>REC</span>' if a["vip_only"] else ""
    meta = html.escape(a['genre'] or '')
    if a["year"]:
        meta += f' · {html.escape(a["year"])}'
    return f"""<a class="card" href="/anime/{a['id']}">
  {vip_badge}
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

    if rows:
        grid = f'<div class="grid">{"".join(anime_card_html(a) for a in rows)}</div>'
        grid += pager_html("/", offset, total)
    else:
        grid = '<p class="empty">Hozircha animelar qo\'shilmagan.</p>'

    genre_links = "".join(f'<a href="/janr/{quote(g)}">{html.escape(g)}</a>' for g in genres[:12])

    body = f"""
<section class="hero">
  <span class="eyebrow"><span class="mono">●</span> O'ZBEK TILIDA DUBLYAJ</span>
  <h1>Sevimli animelaringizni<br>sifatli dublyaj bilan tomosha qiling</h1>
  <div class="subtitle-bar">
    <p>"Yangi qismlar muntazam qo'shib boriladi."</p>
    <p class="small">— Telegram botimiz orqali istalgan joyda tomosha qiling</p>
  </div>
  <div><a class="cta" href="https://t.me/{BOT_USERNAME}"><span class="play">▶</span> Telegram botni ochish</a></div>
  <div class="genres" style="justify-content:center; margin-top:30px">{genre_links}</div>
</section>
<h2 class="section"><span class="tc mono">EP.{total:03d}</span> Barcha animelar</h2>
{grid}
"""
    return web.Response(text=base_page("Bosh sahifa", body, active="home"), content_type="text/html")


async def genres_page(request):
    genres = await db.get_all_genres()
    links = "".join(f'<a href="/janr/{quote(g)}">{html.escape(g)}</a>' for g in genres)
    body = f"""
<h2 class="section"><span class="tc mono">{len(genres):03d}</span> Janrlar</h2>
<div class="genres">{links or "<p class='empty'>Janrlar topilmadi.</p>"}</div>
"""
    return web.Response(text=base_page("Janrlar", body, active="janrlar"), content_type="text/html")


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

    body = f'<h2 class="section"><span class="tc mono">{total:03d}</span> {html.escape(genre)}</h2>{grid}'
    return web.Response(text=base_page(genre, body), content_type="text/html")


async def search_page(request):
    q = request.query.get("q", "").strip()
    if not q:
        return web.HTTPFound("/")

    if q.isdigit():
        anime = await db.get_anime(int(q))
        rows = [anime] if anime else []
    else:
        rows = await db.search_anime(q, limit=60)

    if rows:
        grid = f'<div class="grid">{"".join(anime_card_html(a) for a in rows)}</div>'
    else:
        grid = '<p class="empty">Hech narsa topilmadi.</p>'

    body = f'<h2 class="section"><span class="tc mono">&gt;_</span> "{html.escape(q)}" bo\'yicha natijalar</h2>{grid}'
    return web.Response(text=base_page(f"Qidiruv: {q}", body), content_type="text/html")


async def anime_detail(request):
    try:
        anime_id = int(request.match_info["id"])
    except ValueError:
        raise web.HTTPNotFound()

    anime = await db.get_anime(anime_id)
    if not anime:
        raise web.HTTPNotFound()

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
        tags += '<span class="tag" style="border-color:#ff4438;color:#ff4438">🔴 VIP-only</span>'

    if anime["vip_only"]:
        body_episodes = (
            '<div class="lock-notice">🔒 SIGNAL RESTRICTED — bu anime faqat <b>VIP</b> foydalanuvchilar uchun. '
            f'VIP status olish uchun <a href="https://t.me/{BOT_USERNAME}">botga</a> '
            'yozing.</div>'
        )
    elif episodes:
        buttons = "".join(
            f'<a class="ep-btn" href="https://t.me/{BOT_USERNAME}?start=ep_{anime_id}_{ep["episode_number"]}">'
            f'<span class="play-ic">▶</span><span class="num">{ep["episode_number"]:02d}</span> {ep["episode_number"]}-qism</a>'
            for ep in episodes
        )
        body_episodes = f'<div class="episodes">{buttons}</div>'
    else:
        body_episodes = '<p class="empty" style="text-align:left">Hali epizod qo\'shilmagan.</p>'

    body = f"""
<div class="detail">
  {poster_tag}
  <div class="meta">
    <span class="eyebrow-tc mono">// NOW SCREENING</span>
    <h1>{html.escape(anime['title'])}</h1>
    <div class="tags">{tags}</div>
    <p class="desc">{html.escape(anime['description'] or '')}</p>
    {body_episodes}
  </div>
</div>
"""
    return web.Response(text=base_page(anime["title"], body), content_type="text/html")


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
    return web.Response(text="AniSinus bot va sayt ishlayapti ✅")


def create_app(bot) -> web.Application:
    app = web.Application()
    app["bot"] = bot
    app.router.add_get("/", home)
    app.router.add_get("/ping", ping)
    app.router.add_get("/janrlar", genres_page)
    app.router.add_get("/janr/{name}", genre_detail)
    app.router.add_get("/qidiruv", search_page)
    app.router.add_get("/anime/{id}", anime_detail)
    app.router.add_get("/poster/{id}", poster_proxy)
    return app
