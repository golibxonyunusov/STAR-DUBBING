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
<style>
  :root {{
    --bg: #0f0f14;
    --card: #1a1a24;
    --card-hover: #22222f;
    --text: #eaeaf0;
    --muted: #9a9aad;
    --accent: {ACCENT};
    --accent2: #ff5c9d;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0;
    background: var(--bg);
    color: var(--text);
    font-family: 'Segoe UI', Tahoma, sans-serif;
    line-height: 1.5;
  }}
  a {{ color: inherit; text-decoration: none; }}
  header {{
    position: sticky; top: 0; z-index: 10;
    background: rgba(15,15,20,0.9);
    backdrop-filter: blur(8px);
    border-bottom: 1px solid #26263a;
    padding: 14px 24px;
    display: flex; align-items: center; justify-content: space-between;
    gap: 16px; flex-wrap: wrap;
  }}
  .logo {{
    font-weight: 800; font-size: 20px; letter-spacing: 0.5px;
    background: linear-gradient(90deg, var(--accent), var(--accent2));
    -webkit-background-clip: text; background-clip: text; color: transparent;
  }}
  nav {{ display: flex; gap: 18px; font-size: 14px; }}
  nav a {{ color: var(--muted); padding: 6px 0; border-bottom: 2px solid transparent; }}
  nav a.active, nav a:hover {{ color: var(--text); border-color: var(--accent); }}
  .search-box {{
    display: flex; align-items: center; gap: 8px;
    background: var(--card); border: 1px solid #2c2c3d; border-radius: 999px;
    padding: 8px 16px; min-width: 220px;
  }}
  .search-box input {{
    background: transparent; border: none; outline: none; color: var(--text);
    font-size: 14px; width: 100%;
  }}
  main {{ max-width: 1100px; margin: 0 auto; padding: 28px 24px 60px; }}
  .hero {{
    text-align: center; padding: 40px 16px 32px;
  }}
  .hero h1 {{
    font-size: 30px; margin: 0 0 8px;
  }}
  .hero p {{ color: var(--muted); margin: 0; }}
  .cta {{
    display: inline-block; margin-top: 18px; padding: 12px 26px;
    background: linear-gradient(90deg, var(--accent), var(--accent2));
    color: white; border-radius: 999px; font-weight: 600; font-size: 14px;
  }}
  h2.section {{ font-size: 18px; color: var(--muted); font-weight: 600;
    margin: 32px 0 16px; text-transform: uppercase; letter-spacing: 1px; }}
  .grid {{
    display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
    gap: 18px;
  }}
  .card {{
    background: var(--card); border-radius: 14px; overflow: hidden;
    border: 1px solid #24243350; transition: transform .15s, background .15s;
    position: relative;
  }}
  .card:hover {{ transform: translateY(-4px); background: var(--card-hover); }}
  .card .poster {{
    width: 100%; aspect-ratio: 2/3; object-fit: cover; display: block;
    background: #26263a;
  }}
  .card .info {{ padding: 10px 12px 14px; }}
  .card .info .t {{ font-size: 14px; font-weight: 600; margin: 0 0 4px;
    overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
  .card .info .m {{ font-size: 12px; color: var(--muted); }}
  .badge-vip {{
    position: absolute; top: 8px; left: 8px; background: #ffb42e; color: #211900;
    font-size: 11px; font-weight: 700; padding: 3px 8px; border-radius: 999px;
  }}
  .empty {{ color: var(--muted); text-align: center; padding: 60px 0; }}
  .pager {{ display: flex; justify-content: center; gap: 10px; margin-top: 28px; }}
  .pager a {{
    background: var(--card); border: 1px solid #2c2c3d; padding: 8px 16px;
    border-radius: 10px; font-size: 14px;
  }}
  .pager a:hover {{ border-color: var(--accent); }}
  .genres {{ display: flex; flex-wrap: wrap; gap: 8px; margin: 10px 0 0; }}
  .genres a {{
    background: var(--card); border: 1px solid #2c2c3d; padding: 6px 14px;
    border-radius: 999px; font-size: 13px; color: var(--muted);
  }}
  .genres a:hover {{ color: var(--text); border-color: var(--accent); }}

  /* Anime detail page */
  .detail {{ display: flex; gap: 28px; flex-wrap: wrap; }}
  .detail .poster-big {{ width: 240px; border-radius: 16px; flex-shrink: 0;
    aspect-ratio: 2/3; object-fit: cover; background: #26263a; }}
  .detail .meta h1 {{ margin: 0 0 8px; font-size: 26px; }}
  .detail .meta .tags {{ display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 14px; }}
  .tag {{ background: var(--card); border: 1px solid #2c2c3d; padding: 4px 12px;
    border-radius: 999px; font-size: 12px; color: var(--muted); }}
  .detail .meta p.desc {{ color: #cfcfe0; max-width: 640px; }}
  .episodes {{ display: flex; flex-wrap: wrap; gap: 10px; margin-top: 18px; }}
  .ep-btn {{
    background: var(--card); border: 1px solid #2c2c3d; padding: 10px 18px;
    border-radius: 10px; font-size: 14px; font-weight: 600;
    display: flex; align-items: center; gap: 6px;
  }}
  .ep-btn:hover {{ border-color: var(--accent); background: var(--card-hover); }}
  .lock-notice {{
    background: #241a10; border: 1px solid #ffb42e40; color: #ffcf7d;
    padding: 16px 20px; border-radius: 12px; margin-top: 18px; font-size: 14px;
  }}
  footer {{
    text-align: center; color: var(--muted); font-size: 13px;
    padding: 30px 16px; border-top: 1px solid #24243350; margin-top: 40px;
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
  <a href="https://t.me/{BOT_USERNAME}" style="color:var(--accent)">Telegram botimiz</a> orqali tomosha qiling.
</footer>
</body>
</html>"""


def anime_card_html(a) -> str:
    poster = f"/poster/{a['id']}" if a["poster_file_id"] else ""
    poster_tag = (
        f'<img class="poster" src="{poster}" alt="{html.escape(a["title"])}" loading="lazy">'
        if poster else '<div class="poster"></div>'
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
  <h1>O'zbek tilidagi anime dublyajlari</h1>
  <p>Sevimli animelaringizni sifatli dublyaj bilan tomosha qiling</p>
  <a class="cta" href="https://t.me/{BOT_USERNAME}">📲 Telegram botni ochish</a>
  <div class="genres" style="justify-content:center; margin-top:20px">{genre_links}</div>
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
        f'<img class="poster-big" src="{poster}" alt="">' if poster else '<div class="poster-big"></div>'
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
