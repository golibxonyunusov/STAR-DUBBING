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

ACCENT = "#7c5cff"


# ---------- UMUMIY HTML QOLIP ----------

def base_page(title: str, body: str, active: str = "") -> str:
    return f"""<!DOCTYPE html>
<html lang="uz">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{html.escape(title)} — STAR DUBBING</title>
<link rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>⭐</text></svg>">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>
  :root {{
    --bg: #0a0a0f;
    --bg2: #0d0d14;
    --card: #15151f;
    --card-hover: #1c1c29;
    --border: #24243a;
    --text: #f2f2f7;
    --muted: #8f8fa3;
    --accent: #8b6bff;
    --accent2: #ff5c9d;
    --accent3: #34e0c6;
  }}
  * {{ box-sizing: border-box; }}
  html {{ scroll-behavior: smooth; }}
  body {{
    margin: 0;
    background:
      radial-gradient(1200px 600px at 15% -10%, #241a4a55, transparent 60%),
      radial-gradient(1000px 500px at 90% 0%, #4a1a3855, transparent 60%),
      var(--bg);
    color: var(--text);
    font-family: 'Manrope', 'Segoe UI', sans-serif;
    line-height: 1.6;
    min-height: 100vh;
  }}
  ::selection {{ background: var(--accent); color: white; }}
  ::-webkit-scrollbar {{ width: 10px; }}
  ::-webkit-scrollbar-track {{ background: var(--bg); }}
  ::-webkit-scrollbar-thumb {{ background: #2c2c40; border-radius: 10px; }}
  a {{ color: inherit; text-decoration: none; }}

  header {{
    position: sticky; top: 0; z-index: 20;
    background: rgba(10,10,15,0.72);
    backdrop-filter: blur(14px) saturate(140%);
    border-bottom: 1px solid var(--border);
    padding: 16px 32px;
    display: flex; align-items: center; justify-content: space-between;
    gap: 20px; flex-wrap: wrap;
  }}
  .logo {{
    font-weight: 800; font-size: 21px; letter-spacing: 0.3px;
    display: flex; align-items: center; gap: 8px;
    background: linear-gradient(120deg, var(--accent), var(--accent2) 60%, var(--accent3));
    -webkit-background-clip: text; background-clip: text; color: transparent;
    background-size: 200% auto;
    animation: shine 6s linear infinite;
  }}
  @keyframes shine {{ to {{ background-position: 200% center; }} }}
  nav {{ display: flex; gap: 6px; font-size: 14px; }}
  nav a {{
    color: var(--muted); padding: 8px 16px; border-radius: 999px;
    transition: all .2s;
  }}
  nav a.active, nav a:hover {{ color: var(--text); background: var(--card); }}
  .search-box {{
    display: flex; align-items: center; gap: 10px;
    background: var(--card); border: 1px solid var(--border); border-radius: 999px;
    padding: 10px 18px; min-width: 240px;
    transition: border-color .2s;
  }}
  .search-box:focus-within {{ border-color: var(--accent); }}
  .search-box input {{
    background: transparent; border: none; outline: none; color: var(--text);
    font-size: 14px; width: 100%; font-family: inherit;
  }}
  .search-box input::placeholder {{ color: var(--muted); }}

  main {{ max-width: 1180px; margin: 0 auto; padding: 0 28px 70px; }}

  .hero {{
    text-align: center; padding: 72px 16px 44px; position: relative;
  }}
  .hero .eyebrow {{
    display: inline-block; font-size: 12px; font-weight: 700; letter-spacing: 1.5px;
    color: var(--accent3); text-transform: uppercase; margin-bottom: 14px;
    padding: 6px 14px; border: 1px solid #34e0c640; border-radius: 999px;
    background: #34e0c60d;
  }}
  .hero h1 {{
    font-size: clamp(28px, 5vw, 44px); margin: 0 0 14px; font-weight: 800;
    letter-spacing: -0.5px;
  }}
  .hero p {{ color: var(--muted); margin: 0 auto; max-width: 480px; font-size: 15px; }}
  .cta {{
    display: inline-flex; align-items: center; gap: 8px;
    margin-top: 26px; padding: 14px 30px;
    background: linear-gradient(120deg, var(--accent), var(--accent2));
    color: white; border-radius: 999px; font-weight: 700; font-size: 14px;
    box-shadow: 0 8px 30px -8px #8b6bff80;
    transition: transform .2s, box-shadow .2s;
  }}
  .cta:hover {{ transform: translateY(-2px); box-shadow: 0 12px 36px -6px #8b6bffa0; }}

  h2.section {{
    font-size: 13px; color: var(--muted); font-weight: 700;
    margin: 46px 0 18px; text-transform: uppercase; letter-spacing: 2px;
    display: flex; align-items: center; gap: 10px;
  }}
  h2.section::after {{ content: ""; flex: 1; height: 1px; background: var(--border); }}

  .grid {{
    display: grid; grid-template-columns: repeat(auto-fill, minmax(168px, 1fr));
    gap: 20px;
  }}
  .card {{
    background: var(--card); border-radius: 16px; overflow: hidden;
    border: 1px solid var(--border);
    transition: transform .22s cubic-bezier(.2,.8,.2,1), box-shadow .22s, border-color .22s;
    position: relative; display: block;
  }}
  .card:hover {{
    transform: translateY(-6px);
    border-color: #3a3a56;
    box-shadow: 0 20px 40px -18px #00000090;
  }}
  .card .poster-wrap {{ position: relative; overflow: hidden; aspect-ratio: 2/3; background: #1c1c29; }}
  .card .poster {{
    width: 100%; height: 100%; object-fit: cover; display: block;
    transition: transform .4s;
  }}
  .card:hover .poster {{ transform: scale(1.06); }}
  .card .poster-wrap.empty::before {{
    content: "🎬"; position: absolute; inset: 0; display: flex;
    align-items: center; justify-content: center; font-size: 40px; opacity: .25;
  }}
  .card .poster-wrap::after {{
    content: ""; position: absolute; inset: 0;
    background: linear-gradient(180deg, transparent 60%, #00000090);
  }}
  .card .info {{ padding: 12px 14px 16px; }}
  .card .info .t {{
    font-size: 14px; font-weight: 700; margin: 0 0 4px;
    overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
  }}
  .card .info .m {{ font-size: 12px; color: var(--muted); }}
  .badge-vip {{
    position: absolute; top: 10px; left: 10px; z-index: 2;
    background: linear-gradient(120deg, #ffb42e, #ff7b54); color: #211900;
    font-size: 10.5px; font-weight: 800; padding: 4px 10px; border-radius: 999px;
    box-shadow: 0 4px 14px -4px #ffb42e80;
  }}
  .empty {{ color: var(--muted); text-align: center; padding: 70px 0; font-size: 14px; }}
  .pager {{ display: flex; justify-content: center; gap: 12px; margin-top: 36px; }}
  .pager a {{
    background: var(--card); border: 1px solid var(--border); padding: 10px 20px;
    border-radius: 12px; font-size: 14px; font-weight: 600;
    transition: all .2s;
  }}
  .pager a:hover {{ border-color: var(--accent); background: var(--card-hover); }}
  .genres {{ display: flex; flex-wrap: wrap; gap: 10px; margin: 14px 0 0; }}
  .genres a {{
    background: var(--card); border: 1px solid var(--border); padding: 8px 18px;
    border-radius: 999px; font-size: 13px; color: var(--muted); font-weight: 600;
    transition: all .2s;
  }}
  .genres a:hover {{ color: var(--text); border-color: var(--accent); background: var(--card-hover); }}

  /* Anime detail page */
  .detail {{ display: flex; gap: 36px; flex-wrap: wrap; padding-top: 20px; }}
  .detail .poster-big-wrap {{
    width: 260px; flex-shrink: 0; border-radius: 20px; overflow: hidden;
    aspect-ratio: 2/3; background: #1c1c29;
    box-shadow: 0 30px 60px -24px #000000a0;
    border: 1px solid var(--border);
  }}
  .detail .poster-big {{ width: 100%; height: 100%; object-fit: cover; display: block; }}
  .detail .meta {{ flex: 1; min-width: 260px; }}
  .detail .meta h1 {{ margin: 0 0 14px; font-size: 30px; font-weight: 800; letter-spacing: -0.5px; }}
  .detail .meta .tags {{ display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 18px; }}
  .tag {{
    background: var(--card); border: 1px solid var(--border); padding: 5px 14px;
    border-radius: 999px; font-size: 12.5px; color: var(--muted); font-weight: 600;
  }}
  .detail .meta p.desc {{ color: #c7c7d8; max-width: 640px; font-size: 15px; }}
  .episodes {{ display: flex; flex-wrap: wrap; gap: 10px; margin-top: 22px; }}
  .ep-btn {{
    background: var(--card); border: 1px solid var(--border); padding: 12px 20px;
    border-radius: 12px; font-size: 14px; font-weight: 700;
    display: flex; align-items: center; gap: 8px;
    transition: all .2s;
  }}
  .ep-btn:hover {{
    border-color: var(--accent); background: linear-gradient(120deg, #8b6bff22, #ff5c9d22);
    transform: translateY(-2px);
  }}
  .lock-notice {{
    background: linear-gradient(120deg, #2a1f10, #241a10);
    border: 1px solid #ffb42e40; color: #ffcf7d;
    padding: 18px 22px; border-radius: 14px; margin-top: 22px; font-size: 14px;
  }}
  .lock-notice a {{ font-weight: 700; text-decoration: underline; }}

  footer {{
    text-align: center; color: var(--muted); font-size: 13px;
    padding: 40px 16px; border-top: 1px solid var(--border); margin-top: 50px;
  }}

  @media (max-width: 560px) {{
    header {{ padding: 12px 16px; }}
    main {{ padding: 0 16px 50px; }}
    .search-box {{ min-width: 0; width: 100%; order: 3; }}
    .detail {{ gap: 22px; }}
    .detail .poster-big-wrap {{ width: 180px; }}
  }}
</style>
</head>
<body>
<header>
  <a class="logo" href="/">⭐ STAR DUBBING</a>
  <nav>
    <a href="/" class="{'active' if active=='home' else ''}">Bosh sahifa</a>
    <a href="/janrlar" class="{'active' if active=='janrlar' else ''}">Janrlar</a>
    <a href="https://t.me/{BOT_USERNAME}" class="{'active' if active=='bot' else ''}">Telegram bot</a>
  </nav>
  <form class="search-box" action="/qidiruv" method="get">
    <span>🔍</span>
    <input type="text" name="q" placeholder="Anime nomi yoki kodi..." />
  </form>
</header>
<main>
{body}
</main>
<footer>
  © STAR DUBBING — o'zbek tilidagi anime dublyaj jamoasi. Barcha epizodlarni
  <a href="https://t.me/{BOT_USERNAME}" style="color:var(--accent); font-weight:700">Telegram botimiz</a> orqali tomosha qiling.
</footer>
</body>
</html>"""


def anime_card_html(a) -> str:
    poster = f"/poster/{a['id']}" if a["poster_file_id"] else ""
    poster_tag = (
        f'<div class="poster-wrap"><img class="poster" src="{poster}" alt="{html.escape(a["title"])}" loading="lazy"></div>'
        if poster else '<div class="poster-wrap empty"></div>'
    )
    vip_badge = '<span class="badge-vip">👑 VIP</span>' if a["vip_only"] else ""
    return f"""<a class="card" href="/anime/{a['id']}">
  {vip_badge}
  {poster_tag}
  <div class="info">
    <p class="t">{html.escape(a['title'])}</p>
    <p class="m">{html.escape(a['genre'] or '')} {('· ' + a['year']) if a['year'] else ''}</p>
  </div>
</a>"""


def pager_html(base_url: str, offset: int, total: int) -> str:
    parts = []
    if offset > 0:
        prev_offset = max(offset - PAGE_SIZE, 0)
        sep = "&" if "?" in base_url else "?"
        parts.append(f'<a href="{base_url}{sep}offset={prev_offset}">← Oldingi</a>')
    if offset + PAGE_SIZE < total:
        next_offset = offset + PAGE_SIZE
        sep = "&" if "?" in base_url else "?"
        parts.append(f'<a href="{base_url}{sep}offset={next_offset}">Keyingi →</a>')
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
  <span class="eyebrow">O'zbek tilida dublyaj</span>
  <h1>Sevimli animelaringizni<br>sifatli dublyaj bilan tomosha qiling</h1>
  <p>Yangi qismlar muntazam qo'shib boriladi — Telegram botimiz orqali istalgan joyda tomosha qiling</p>
  <a class="cta" href="https://t.me/{BOT_USERNAME}">📲 Telegram botni ochish</a>
  <div class="genres" style="justify-content:center; margin-top:26px">{genre_links}</div>
</section>
<h2 class="section">Barcha animelar ({total})</h2>
{grid}
"""
    return web.Response(text=base_page("Bosh sahifa", body, active="home"), content_type="text/html")


async def genres_page(request):
    genres = await db.get_all_genres()
    links = "".join(f'<a href="/janr/{quote(g)}">{html.escape(g)}</a>' for g in genres)
    body = f"""
<h2 class="section">Janrlar</h2>
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

    body = f'<h2 class="section">{html.escape(genre)} ({total})</h2>{grid}'
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

    body = f'<h2 class="section">"{html.escape(q)}" bo\'yicha natijalar</h2>{grid}'
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
        tags += '<span class="tag" style="border-color:#ffb42e;color:#ffb42e">👑 VIP-only</span>'

    if anime["vip_only"]:
        body_episodes = (
            '<div class="lock-notice">🔒 Bu anime faqat <b>VIP</b> foydalanuvchilar uchun. '
            f'VIP status olish uchun <a href="https://t.me/{BOT_USERNAME}" style="color:#ffcf7d">botga</a> '
            'yozing.</div>'
        )
    elif episodes:
        buttons = "".join(
            f'<a class="ep-btn" href="https://t.me/{BOT_USERNAME}?start=ep_{anime_id}_{ep["episode_number"]}">'
            f'▶️ {ep["episode_number"]}-qism</a>'
            for ep in episodes
        )
        body_episodes = f'<div class="episodes">{buttons}</div>'
    else:
        body_episodes = '<p class="empty" style="text-align:left">Hali epizod qo\'shilmagan.</p>'

    body = f"""
<div class="detail">
  {poster_tag}
  <div class="meta">
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
