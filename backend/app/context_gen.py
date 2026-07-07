"""Auto-generate the receptionist 'business knowledge' block from a
website URL or an uploaded PDF (brochure / price list / service menu)."""
import asyncio
import io
import re

import httpx
import google.generativeai as genai

from . import config

genai.configure(api_key=config.GEMINI_API_KEY)
_model = genai.GenerativeModel(config.GEMINI_MODEL)

MAX_SOURCE_CHARS = 18000
COMMON_PAGES = ["", "/about", "/about-us", "/services", "/treatments",
                "/pricing", "/contact", "/contact-us", "/faq"]

_SCRIPT_RE = re.compile(r"<(script|style|noscript)[^>]*>.*?</\1>",
                        re.IGNORECASE | re.DOTALL)
_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"[ \t]{2,}|\r")
_NL_RE = re.compile(r"\n{3,}")


def _strip_html(html: str) -> str:
    text = _SCRIPT_RE.sub(" ", html)
    text = re.sub(r"<br\s*/?>|</p>|</div>|</li>|</h[1-6]>", "\n", text, flags=re.I)
    text = _TAG_RE.sub(" ", text)
    text = (text.replace("&amp;", "&").replace("&nbsp;", " ")
                .replace("&lt;", "<").replace("&gt;", ">").replace("&#39;", "'"))
    text = _WS_RE.sub(" ", text)
    return _NL_RE.sub("\n\n", text).strip()


async def fetch_site_text(url: str) -> str:
    """Fetch the given page plus common subpages, return combined plain text."""
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    base = url.rstrip("/")
    headers = {"User-Agent": "Mozilla/5.0 (compatible; VoxseraBot/1.0)"}
    chunks, seen = [], set()
    async with httpx.AsyncClient(follow_redirects=True, timeout=12.0,
                                 headers=headers) as client:
        for path in COMMON_PAGES:
            target = base + path
            if target in seen:
                continue
            seen.add(target)
            try:
                r = await client.get(target)
                if r.status_code == 200 and "text/html" in r.headers.get("content-type", ""):
                    chunks.append(_strip_html(r.text))
            except Exception:
                continue
            if sum(len(c) for c in chunks) > MAX_SOURCE_CHARS:
                break
    text = "\n\n".join(c for c in chunks if c)
    if len(text) < 200:
        raise RuntimeError("Could not read enough text from that website — "
                           "check the URL is correct and publicly accessible")
    return text[:MAX_SOURCE_CHARS]


def pdf_text(data: bytes) -> str:
    from pypdf import PdfReader  # lazy import
    reader = PdfReader(io.BytesIO(data))
    out = []
    for page in reader.pages[:30]:
        try:
            out.append(page.extract_text() or "")
        except Exception:
            continue
    text = "\n".join(out).strip()
    if len(text) < 100:
        raise RuntimeError("Could not extract text from that PDF — it may be a "
                           "scanned image. Try a text-based PDF or the website option")
    return text[:MAX_SOURCE_CHARS]


async def generate_context(source_text: str, business_name: str = "",
                           industry: str = "") -> str:
    prompt = f"""You write the "business knowledge" block used in the system prompt of an AI PHONE receptionist.

Business: {business_name or 'unknown'} ({industry or 'unknown industry'}).
Below is raw text extracted from the business's website or brochure PDF.

From it, extract and organize ONLY facts that a phone receptionist needs:
- Services offered (with prices if mentioned)
- Opening hours and days
- Doctors/staff names and specialities (if any)
- Location/address and parking/landmark info
- Policies (cancellation, new-patient rules, insurance, payment methods)
- Common questions callers might ask, with answers

Write it as a compact plain-text briefing (max 350 words) in second person
("We offer...", "Our clinic is at..."). No markdown, no headings with #,
no invented facts — if something isn't in the text, leave it out.

RAW TEXT:
{source_text}"""
    resp = await asyncio.to_thread(_model.generate_content, prompt)
    text = (resp.text or "").strip().replace("*", "").replace("#", "")
    if not text:
        raise RuntimeError("AI returned an empty draft — try again")
    return text
