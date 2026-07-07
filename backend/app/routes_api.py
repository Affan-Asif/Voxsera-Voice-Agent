"""REST API for the React dashboard: onboarding, voices, Google OAuth, calls."""
import asyncio
import re

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import RedirectResponse, Response
from pydantic import BaseModel

from . import config, context_gen, db, google_service, tts, reminders

router = APIRouter(prefix="/api")


# ---------------- auth (simple email+password for the demo) ----------------

import hashlib
import secrets


def _hash_pw(password: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(8)
    return f"{salt}${hashlib.sha256((salt + password).encode()).hexdigest()}"


def _verify_pw(password: str, stored: str) -> bool:
    try:
        salt, _ = stored.split("$", 1)
    except ValueError:
        return False
    return secrets.compare_digest(_hash_pw(password, salt), stored)


class AuthBody(BaseModel):
    email: str
    password: str


@router.post("/auth/signup")
async def signup(body: AuthBody):
    email = body.email.strip().lower()
    if "@" not in email or len(body.password) < 6:
        raise HTTPException(400, "valid email and a password of 6+ characters required")
    if await db.get_owner(email):
        raise HTTPException(409, "account already exists — log in instead")
    await db.create_owner(email, _hash_pw(body.password))
    return {"email": email, "business": None}


@router.post("/auth/login")
async def login(body: AuthBody):
    email = body.email.strip().lower()
    owner = await db.get_owner(email)
    if not owner or not _verify_pw(body.password, owner["password_hash"]):
        raise HTTPException(401, "invalid email or password")
    biz = await db.get_business_by_owner(email)
    if biz:
        biz.pop("google_refresh_token_present", None)
        biz["google_connected"] = bool(biz.pop("google_refresh_token", None))
    return {"email": email, "business": biz}


# ---------------- onboarding ----------------

class RegisterBody(BaseModel):
    name: str
    industry: str = ""
    timezone: str = "Asia/Kolkata"
    business_hours: dict = {}
    persona: dict = {}
    voice_model: str = "aura-2-thalia-en"
    owner_email: str = ""


@router.post("/businesses")
async def register_business(body: RegisterBody):
    hours = {"open": "09:00", "close": "18:00",
             "days": ["mon", "tue", "wed", "thu", "fri"]}
    hours.update(body.business_hours or {})
    row = await db.create_business({
        "name": body.name.strip(),
        "industry": body.industry.strip(),
        "timezone": body.timezone,
        "business_hours": hours,
        "persona": body.persona or {},
        "voice_model": body.voice_model,
        "twilio_number": config.TWILIO_PHONE_NUMBER or None,  # single-number MVP
        "owner_email": body.owner_email.strip().lower() or None,
    })
    return row


class PatchBody(BaseModel):
    persona: dict | None = None
    voice_model: str | None = None
    google_sheet_id: str | None = None
    google_calendar_id: str | None = None
    business_hours: dict | None = None


@router.patch("/businesses/{business_id}")
async def patch_business(business_id: str, body: PatchBody):
    patch = {k: v for k, v in body.model_dump().items() if v is not None}
    if "google_sheet_id" in patch:
        # accept full URL or bare ID
        m = re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", patch["google_sheet_id"])
        if m:
            patch["google_sheet_id"] = m.group(1)
    if not patch:
        raise HTTPException(400, "nothing to update")
    row = await db.update_business(business_id, patch)
    if "google_sheet_id" in patch and row.get("google_refresh_token"):
        asyncio.create_task(google_service.ensure_sheet_header(row))
    return row


@router.get("/businesses/{business_id}")
async def get_business(business_id: str):
    row = await db.get_business(business_id)
    if not row:
        raise HTTPException(404, "business not found")
    row.pop("google_refresh_token", None)
    row["google_connected"] = bool((await db.get_business(business_id)).get("google_refresh_token"))
    return row


@router.get("/businesses")
async def list_businesses():
    rows = await db.list_businesses()
    for r in rows:
        r["google_connected"] = bool(r.pop("google_refresh_token", None))
    return rows


# ---------------- AI prompt generation (website / PDF) ----------------

class FromUrlBody(BaseModel):
    url: str
    business_name: str = ""
    industry: str = ""


@router.post("/context/from-url")
async def context_from_url(body: FromUrlBody):
    """Scrape the business website and draft the receptionist knowledge block."""
    try:
        text = await context_gen.fetch_site_text(body.url)
        context = await context_gen.generate_context(text, body.business_name, body.industry)
        return {"context": context, "source_chars": len(text)}
    except Exception as e:
        raise HTTPException(502, str(e))


@router.post("/context/from-pdf")
async def context_from_pdf(file: UploadFile = File(...),
                           business_name: str = Form(""),
                           industry: str = Form("")):
    """Extract a brochure/price-list PDF and draft the knowledge block."""
    data = await file.read()
    if len(data) > 10 * 1024 * 1024:
        raise HTTPException(400, "PDF too large (max 10 MB)")
    try:
        text = await asyncio.to_thread(context_gen.pdf_text, data)
        context = await context_gen.generate_context(text, business_name, industry)
        return {"context": context, "source_chars": len(text)}
    except Exception as e:
        raise HTTPException(502, str(e))


# ---------------- voices ----------------

@router.get("/voices")
async def voices():
    return config.VOICE_CATALOG


@router.get("/voices/{voice_id}/preview")
async def voice_preview(voice_id: str, text: str | None = None):
    sample = text or ("Hi! Thanks for calling. I'd be happy to help you "
                      "book an appointment today.")
    try:
        audio, media_type = await tts.synthesize_preview(voice_id, sample)
    except Exception as e:
        raise HTTPException(502, f"Voice preview failed: {e}")
    return Response(content=audio, media_type=media_type)


# ---------------- Google OAuth ----------------

@router.get("/google/auth")
async def google_auth(business_id: str):
    if not (config.GOOGLE_CLIENT_ID and config.GOOGLE_CLIENT_SECRET):
        raise HTTPException(500, "GOOGLE_CLIENT_ID / SECRET not set in .env")
    return {"url": google_service.auth_url(business_id)}


@router.get("/google/callback")
async def google_callback(request: Request):
    code = request.query_params.get("code")
    business_id = request.query_params.get("state")
    if not (code and business_id):
        raise HTTPException(400, "missing code/state")
    try:
        refresh_token = await asyncio.to_thread(
            google_service.exchange_code, code, business_id)
    except Exception as e:
        import traceback; traceback.print_exc()
        raise HTTPException(500, f"Google token exchange failed: {type(e).__name__}: {e}")
    try:
        row = await db.update_business(business_id,
                                       {"google_refresh_token": refresh_token})
    except Exception as e:
        import traceback; traceback.print_exc()
        raise HTTPException(500, f"Supabase update failed: {type(e).__name__}: {e}")
    if row.get("google_sheet_id"):
        asyncio.create_task(google_service.ensure_sheet_header(row))
    # auto-create ONE workspace sheet (Appointments + Calls tabs) — it serves
    # inbound bookings, the call log, AND outbound reminders. No URL needed.
    if not (row.get("google_sheet_id") and row.get("inbound_sheet_id")):
        try:
            sid = await google_service.create_workspace_sheet(
                refresh_token, row.get("name", "Business"))
            patch = {}
            if not row.get("google_sheet_id"):
                patch["google_sheet_id"] = sid       # bookings + reminders
            if not row.get("inbound_sheet_id"):
                patch["inbound_sheet_id"] = sid      # inbound call log
            row = await db.update_business(business_id, patch)
            print(f"workspace sheet created: {sid}")
        except Exception as e:
            print(f"workspace sheet creation failed: {type(e).__name__}: {e}")
    # back to the wizard
    return RedirectResponse(f"{config.FRONTEND_URL}/?business_id={business_id}&google=connected")


# ---------------- outbound: appointments + call-now ----------------

async def _reminder_ready_business(business_id: str) -> dict:
    biz = await db.get_business(business_id)
    if not biz:
        raise HTTPException(404, "business not found")
    if not biz.get("google_refresh_token"):
        raise HTTPException(400, "Google is not connected for this business")
    if not biz.get("google_sheet_id"):
        raise HTTPException(400, "No reminder sheet URL saved — add it in Agent setup → Integrations")
    return biz


@router.get("/appointments")
async def list_appointments(business_id: str):
    """Rows from the admin-provided reminder sheet, for the dashboard."""
    biz = await _reminder_ready_business(business_id)
    try:
        return await google_service.read_appointments(biz)
    except Exception as e:
        raise HTTPException(502, f"Could not read sheet: {type(e).__name__}: {e}")


class CallNowBody(BaseModel):
    business_id: str
    row: int


@router.post("/outbound/call-now")
async def outbound_call_now(body: CallNowBody):
    """Immediately place the reminder call for one sheet row,
    regardless of how far away the appointment is."""
    biz = await _reminder_ready_business(body.business_id)
    appts = await google_service.read_appointments(biz)
    appt = next((a for a in appts if a["row"] == body.row), None)
    if not appt:
        raise HTTPException(404, "appointment row not found in sheet")
    if not (appt.get("phone") or "").strip():
        raise HTTPException(400, "that row has no phone number")
    sid = await reminders.dial_reminder(biz, appt)
    if not sid:
        raise HTTPException(502, "Twilio dial failed — check the number is in +E.164 "
                                 "format (and verified, if on a Twilio trial account)")
    await google_service.mark_reminder_sent(biz, appt["row"])
    return {"ok": True, "call_sid": sid, "phone": appt["phone"], "name": appt["name"]}


# ---------------- calls dashboard ----------------

@router.get("/calls")
async def calls(business_id: str | None = None, direction: str | None = None,
                limit: int = 100, owner_email: str | None = None):
    """owner_email scopes history to all businesses owned by that account."""
    return await db.list_calls(business_id, direction, limit,
                               owner_email=(owner_email or "").strip().lower() or None)


# ---------------- utilities ----------------

@router.post("/reminders/scan")
async def trigger_reminder_scan():
    """Manually trigger one reminder sweep (handy for testing)."""
    await reminders.scan_once()
    return {"ok": True}


@router.get("/health")
async def health():
    return {
        "ok": True,
        "base_url": config.BASE_URL,
        "twilio_number": config.TWILIO_PHONE_NUMBER,
        "keys": {
            "gemini": bool(config.GEMINI_API_KEY),
            "deepgram": bool(config.DEEPGRAM_API_KEY),
            "twilio": bool(config.TWILIO_ACCOUNT_SID and config.TWILIO_AUTH_TOKEN),
            "supabase": bool(config.SUPABASE_URL and config.SUPABASE_SERVICE_KEY),
            "google": bool(config.GOOGLE_CLIENT_ID and config.GOOGLE_CLIENT_SECRET),
        },
    }
