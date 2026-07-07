"""Outbound reminder scheduler.

Every CHECK_INTERVAL seconds, for each business with Google connected:
read the appointment sheet, find rows whose appointment starts within the
next REMINDER_WINDOW_MIN minutes and haven't been reminded, then place an
outbound Twilio call. The /media websocket handles the conversation.
"""
import asyncio
from datetime import datetime
from urllib.parse import urlencode
from zoneinfo import ZoneInfo

from twilio.rest import Client as TwilioClient

from . import config, db, google_service

CHECK_INTERVAL = 60          # seconds between sheet scans
REMINDER_WINDOW_MIN = 30     # call when appointment is <= 30 min away

_twilio: TwilioClient | None = None


def twilio() -> TwilioClient:
    global _twilio
    if _twilio is None:
        _twilio = TwilioClient(config.TWILIO_ACCOUNT_SID, config.TWILIO_AUTH_TOKEN)
    return _twilio


def _normalize(phone: str) -> str:
    digits = "".join(c for c in phone if c.isdigit())
    return phone.strip() if phone.strip().startswith("+") else "+" + digits


async def dial_reminder(business: dict, appt: dict) -> str | None:
    """Place the outbound call; conversation context rides in query params
    which /twilio/voice-outbound turns into <Parameter> tags."""
    to = _normalize(appt["phone"])
    qs = urlencode({
        "business_id": business["id"],
        "to": to,
        "appt_name": appt["name"],
        "appt_date": appt["date"],
        "appt_time": appt["time"],
        "appt_reason": appt["reason"] or "your appointment",
    })
    voice_url = f"{config.BASE_URL}/twilio/voice-outbound?{qs}"

    def _create():
        return twilio().calls.create(
            to=to,
            from_=config.TWILIO_PHONE_NUMBER,
            url=voice_url,
            method="POST",
        )
    try:
        call = await asyncio.to_thread(_create)
        print(f"reminder dialed {to} for {appt['date']} {appt['time']} sid={call.sid}")
        return call.sid
    except Exception as e:
        print(f"reminder dial failed for {to}: {e}")
        return None


async def scan_once():
    try:
        businesses = await db.list_businesses()
    except Exception as e:
        print(f"reminder scan: db error {e}")
        return

    for biz in businesses:
        if not (biz.get("google_refresh_token") and biz.get("google_sheet_id")):
            continue
        tz = ZoneInfo(biz.get("timezone") or "UTC")
        now = datetime.now(tz)
        try:
            appts = await google_service.read_appointments(biz)
        except Exception as e:
            print(f"reminder scan: sheet error for {biz['name']}: {e}")
            continue

        for a in appts:
            if (a["reminder_sent"] or "").strip().upper() == "YES":
                continue
            if (a["status"] or "").lower() == "cancelled":
                continue
            try:
                start = datetime.strptime(f'{a["date"]} {a["time"]}',
                                          "%Y-%m-%d %H:%M").replace(tzinfo=tz)
            except ValueError:
                continue
            delta_min = (start - now).total_seconds() / 60.0
            if 0 < delta_min <= REMINDER_WINDOW_MIN:
                # mark first so a crash can't cause repeat calls
                await google_service.mark_reminder_sent(biz, a["row"])
                await dial_reminder(biz, a)


async def reminder_loop():
    print("reminder scheduler started")
    while True:
        try:
            await scan_once()
        except Exception as e:
            print(f"reminder loop err: {e}")
        await asyncio.sleep(CHECK_INTERVAL)
