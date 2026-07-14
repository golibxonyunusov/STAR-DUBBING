"""Google Gemini (bepul) API bilan ishlash uchun umumiy yordamchi modul.
Bu modul ham veb-sayt (web.py), ham Telegram bot (handlers/user.py) tomonidan
ishlatiladi -- shu sababli Gemini'ga so'rov yuborish kodi faqat bitta joyda."""

import asyncio
import html
import re

import aiohttp

from config import GEMINI_API_KEY, ASSISTANT_MODEL, ASSISTANT_FALLBACK_MODEL

GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

# Asosiy model band bo'lsa, shuncha soniya kutib qayta uriladi (har urinishda o'sib boradi).
RETRY_DELAYS = (1, 2)

# --- SAYTDAGI chat oynasi uchun tizim prompti ---
SITE_SYSTEM_PROMPT = (
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

# --- TELEGRAM BOTDA erkin yozilgan matnlar uchun tizim prompti ---
BOT_SYSTEM_PROMPT = (
    "Sen STAR DUBBING anime dublyaj Telegram botining AI yordamchisisan. Bot "
    "o'zbek tilida dublyaj qilingan anime epizodlarini taqdim etadi. "
    "Foydalanuvchi botdagi mavjud tugmalar (Qidirish, Barcha animelar, Janrlar, "
    "Profil va h.k.) orqali qilolmaydigan har qanday erkin savol yozganda "
    "(masalan umumiy savol, salomlashish, anime haqida fikr-mulohaza va hokazo) "
    "senga murojaat qilinadi -- chunki yozgan animeni bazadan topa olmadik. "
    "Agar savol aniq bir anime haqida bo'lsa va sen uni bilmasang, buni ochiq "
    "ayt va foydalanuvchiga anime nomini aniqroq yozishni yoki 🌌 \"Barcha "
    "animelar\" bo'limidan qidirishni tavsiya qil. Qisqa, do'stona va o'zbek "
    "tilida (agar foydalanuvchi boshqa tilda yozmasa) javob ber."
)


def _build_parts(message: str, files: list | None = None) -> list:
    """Xabar va (agar bo'lsa) fayllardan Gemini 'parts' ro'yxatini yasaydi."""
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


_BOLD_RE = re.compile(r"\*\*(.+?)\*\*", re.DOTALL)
_UNDERSCORE_BOLD_RE = re.compile(r"__(.+?)__", re.DOTALL)
_ITALIC_RE = re.compile(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", re.DOTALL)
_INLINE_CODE_RE = re.compile(r"`([^`\n]+)`")
_CODE_BLOCK_RE = re.compile(r"```[a-zA-Z0-9]*\n?([\s\S]*?)```")
_HEADING_RE = re.compile(r"^\s{0,3}#{1,6}\s*(.+)$", re.MULTILINE)


def _markdown_to_plain(text: str) -> str:
    """Sayt uchun -- Gemini ba'zan Markdown (** __ ` #) ishlatadi, lekin sayt
    javobni oddiy matn sifatida ko'rsatadi, shu sababli belgilarni olib
    tashlaymiz (matn mazmuni saqlanib qoladi)."""
    text = _CODE_BLOCK_RE.sub(lambda m: m.group(1), text)
    text = _HEADING_RE.sub(r"\1", text)
    text = _BOLD_RE.sub(r"\1", text)
    text = _UNDERSCORE_BOLD_RE.sub(r"\1", text)
    text = _ITALIC_RE.sub(r"\1", text)
    text = _INLINE_CODE_RE.sub(r"\1", text)
    return text


def _markdown_to_telegram_html(text: str) -> str:
    """Telegram uchun -- avval HTML maxsus belgilarini escape qiladi (xatoga
    yo'l qo'ymaslik uchun), so'ng Markdown (** __ * ` #) ni Telegram
    tushunadigan HTML teglariga aylantiradi."""
    text = html.escape(text, quote=False)
    text = _CODE_BLOCK_RE.sub(lambda m: f"<pre>{m.group(1)}</pre>", text)
    text = _HEADING_RE.sub(r"<b>\1</b>", text)
    text = _BOLD_RE.sub(r"<b>\1</b>", text)
    text = _UNDERSCORE_BOLD_RE.sub(r"<b>\1</b>", text)
    text = _ITALIC_RE.sub(r"<i>\1</i>", text)
    text = _INLINE_CODE_RE.sub(r"<code>\1</code>", text)
    return text


def _looks_overloaded(status: int, result: dict) -> bool:
    """Google serveri band bo'lganda qaytaradigan xatoliklarni aniqlaydi
    (429/503 yoki xabar matnida 'overloaded'/'high demand'/'unavailable')."""
    if status in (429, 503):
        return True
    msg = ((result or {}).get("error") or {}).get("message", "").lower()
    return "overloaded" in msg or "high demand" in msg or "unavailable" in msg


async def _call_model(model: str, payload: dict, headers: dict):
    """Bitta modelga bir marta so'rov yuboradi.
    Muvaffaqiyatli bo'lsa (status, result), tarmoq xatosida (None, None) qaytaradi."""
    url = GEMINI_API_URL.format(model=model)
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers,
                                     timeout=aiohttp.ClientTimeout(total=45)) as resp:
                result = await resp.json()
                return resp.status, result
    except Exception:
        return None, None


async def _call_with_retry_and_fallback(payload: dict, headers: dict):
    """Asosiy modelga 1-2 marta qayta urinadi (band bo'lsa), baribir
    ishlamasa zaxira modelga o'tadi. (status, result) qaytaradi."""
    models = [ASSISTANT_MODEL]
    if ASSISTANT_FALLBACK_MODEL and ASSISTANT_FALLBACK_MODEL != ASSISTANT_MODEL:
        models.append(ASSISTANT_FALLBACK_MODEL)

    status, result = None, None
    for i, model in enumerate(models):
        attempts = len(RETRY_DELAYS) + 1 if i == 0 else 1  # faqat asosiy modelga qayta uriladi
        for attempt in range(attempts):
            status, result = await _call_model(model, payload, headers)
            if status == 200 or status is None or not _looks_overloaded(status, result or {}):
                break
            if attempt < len(RETRY_DELAYS):
                await asyncio.sleep(RETRY_DELAYS[attempt])
        if status == 200:
            return status, result
        if status is not None and not _looks_overloaded(status, result or {}):
            # Band bo'lish emas, boshqa turdagi xato (masalan noto'g'ri kalit) --
            # zaxira modelga o'tishning ma'nosi yo'q.
            return status, result
    return status, result


async def _ask_gemini_raw(
    message: str,
    system_prompt: str,
    history: list | None = None,
    files: list | None = None,
) -> str:
    """Gemini API'ga so'rov yuboradi va xom (formatlanmagan) matnli javobni
    qaytaradi. Hech qachon exception ko'tarmaydi -- xatolik bo'lsa,
    foydalanuvchiga ko'rsatsa bo'ladigan (⚠️ bilan boshlanadigan) xabar
    qaytaradi."""
    if not GEMINI_API_KEY:
        return ("AI yordamchi hali sozlanmagan (server tomonida GEMINI_API_KEY yo'q). "
                "Bepul kalitni https://aistudio.google.com/apikey saytidan olsa bo'ladi.")

    contents = []
    for item in (history or [])[-12:]:
        if not isinstance(item, dict):
            continue
        role = "user" if item.get("role") == "user" else "model"
        text = str(item.get("text", ""))[:4000]
        if text:
            contents.append({"role": role, "parts": [{"text": text}]})
    contents.append({"role": "user", "parts": _build_parts(message, files)})

    payload = {
        "system_instruction": {"parts": [{"text": system_prompt}]},
        "contents": contents,
        "generationConfig": {"maxOutputTokens": 1024},
    }
    headers = {
        "x-goog-api-key": GEMINI_API_KEY,
        "content-type": "application/json",
    }

    status, result = await _call_with_retry_and_fallback(payload, headers)
    if status is None:
        return "⚠️ AI yordamchiga ulanib bo'lmadi, birozdan so'ng qayta urinib ko'ring."
    if status != 200:
        if _looks_overloaded(status, result or {}):
            return ("⚠️ AI hozir juda band (Google serverida yuklama ko'p). "
                    "Bir necha soniyadan so'ng qayta urinib ko'ring.")
        err_msg = ((result or {}).get("error") or {}).get("message", "Noma'lum xatolik")
        return f"⚠️ AI xatosi: {err_msg}"

    candidates = result.get("candidates") or []
    if candidates:
        finish_reason = candidates[0].get("finishReason")
        cand_parts = (candidates[0].get("content") or {}).get("parts") or []
        reply_parts = [p.get("text", "") for p in cand_parts if isinstance(p, dict) and p.get("text")]
        reply = "\n".join(p for p in reply_parts if p).strip()
        if finish_reason == "SAFETY":
            return "⚠️ Bu so'rovga javob berib bo'lmadi (xavfsizlik cheklovi)."
        return reply or "..."

    blocked = (result.get("promptFeedback") or {}).get("blockReason")
    if blocked:
        return "⚠️ Bu so'rovga javob berib bo'lmadi (xavfsizlik cheklovi)."
    return "..."


async def ask_gemini(
    message: str,
    system_prompt: str,
    history: list | None = None,
    files: list | None = None,
    output_format: str = "plain",
) -> str:
    """Gemini API'ga so'rov yuboradi va JAVOBNI CHIQISH JOYIGA MOS formatda
    qaytaradi:
    - output_format="plain"    -> sayt uchun (Markdown belgilari olib tashlanadi)
    - output_format="telegram" -> bot uchun (Markdown -> Telegram HTML teglariga o'giriladi)
    """
    reply = await _ask_gemini_raw(message, system_prompt, history, files)
    if output_format == "telegram":
        return _markdown_to_telegram_html(reply)
    return _markdown_to_plain(reply)