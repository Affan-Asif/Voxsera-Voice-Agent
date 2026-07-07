"""Google OAuth (per business) + Calendar availability/booking + Sheets
appointment log. All googleapiclient calls are sync -> wrap in to_thread."""
import asyncio
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

from . import config

# Sheet layout (tab "Appointments", row 1 = header):
# A: Name | B: Phone | C: Date | D: Time | E: Reason | F: Status | G: ReminderSent | H: Age
# (Age lives in H so columns A-G stay compatible with the reminder scanner.)
SHEET_TAB = "Appointments"
SHEET_HEADER = ["Name", "Phone", "Date", "Time", "Reason", "Status", "ReminderSent", "Age"]
SLOT_MINUTES = 30


# ---------------- OAuth ----------------

def _flow(state: str | None = None) -> Flow:
    cfg = {
        "web": {
            "client_id": config.GOOGLE_CLIENT_ID,
            "client_secret": config.GOOGLE_CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [config.GOOGLE_REDIRECT_URI],
        }
    }
    return Flow.from_client_config(
        cfg, scopes=config.GOOGLE_SCOPES,
        redirect_uri=config.GOOGLE_REDIRECT_URI, state=state,
        autogenerate_code_verifier=False, code_verifier=None,
    )


def auth_url(business_id: str) -> str:
    """URL the admin visits to grant Calendar + Sheets access.
    business_id rides along in `state`."""
    flow = _flow()
    url, _ = flow.authorization_url(
        access_type="offline",
        prompt="consent",            # force refresh_token on every connect
        include_granted_scopes="true",
        state=business_id,
    )
    return url


def exchange_code(code: str, state: str) -> str:
    """Exchange auth code -> refresh token."""
    flow = _flow(state=state)
    flow.fetch_token(code=code)
    if not flow.credentials.refresh_token:
        raise RuntimeError("Google did not return a refresh token; remove app access at "
                           "https://myaccount.google.com/permissions and reconnect.")
    return flow.credentials.refresh_token


def _creds(refresh_token: str) -> Credentials:
    return Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=config.GOOGLE_CLIENT_ID,
        client_secret=config.GOOGLE_CLIENT_SECRET,
        scopes=config.GOOGLE_SCOPES,
    )


def _calendar(refresh_token: str):
    return build("calendar", "v3", credentials=_creds(refresh_token), cache_discovery=False)


def _sheets(refresh_token: str):
    return build("sheets", "v4", credentials=_creds(refresh_token), cache_discovery=False)


# ---------------- Calendar: availability + booking ----------------

def _day_slots(business: dict, date_str: str) -> list[str]:
    """All possible slot start times ("HH:MM") for that date per business hours."""
    hours = business.get("business_hours") or {}
    days = [d.lower() for d in hours.get("days", [])]
    tz = ZoneInfo(business.get("timezone") or "UTC")
    day = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=tz)
    if days and day.strftime("%a").lower()[:3] not in days:
        return []
    open_h, open_m = map(int, (hours.get("open") or "09:00").split(":"))
    close_h, close_m = map(int, (hours.get("close") or "18:00").split(":"))
    t = day.replace(hour=open_h, minute=open_m)
    end = day.replace(hour=close_h, minute=close_m)
    out = []
    while t + timedelta(minutes=SLOT_MINUTES) <= end:
        out.append(t.strftime("%H:%M"))
        t += timedelta(minutes=SLOT_MINUTES)
    return out


async def get_available_slots(business: dict, date_str: str) -> list[str]:
    """Slots inside business hours minus calendar busy times. Past slots removed."""
    slots = _day_slots(business, date_str)
    if not slots:
        return []
    tz = ZoneInfo(business.get("timezone") or "UTC")
    day = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=tz)
    t_min = day.isoformat()
    t_max = (day + timedelta(days=1)).isoformat()
    cal_id = business.get("google_calendar_id") or "primary"
    rt = business.get("google_refresh_token")

    def _busy():
        svc = _calendar(rt)
        resp = svc.freebusy().query(body={
            "timeMin": t_min, "timeMax": t_max,
            "items": [{"id": cal_id}],
        }).execute()
        return resp["calendars"].get(cal_id, {}).get("busy", [])

    busy = await asyncio.to_thread(_busy) if rt else []
    now = datetime.now(tz)
    free = []
    for s in slots:
        h, m = map(int, s.split(":"))
        start = day.replace(hour=h, minute=m)
        end = start + timedelta(minutes=SLOT_MINUTES)
        if start <= now:
            continue
        clash = any(
            start < datetime.fromisoformat(b["end"]) and end > datetime.fromisoformat(b["start"])
            for b in busy
        )
        if not clash:
            free.append(s)
    return free


async def book_appointment(business: dict, name: str, phone: str,
                           date_str: str, time_str: str, reason: str = "",
                           age: str = "") -> dict:
    """Create a calendar event AND append a row to the appointment sheet."""
    tz = ZoneInfo(business.get("timezone") or "UTC")
    start = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M").replace(tzinfo=tz)
    end = start + timedelta(minutes=SLOT_MINUTES)
    rt = business.get("google_refresh_token")
    cal_id = business.get("google_calendar_id") or "primary"

    def _create_event():
        svc = _calendar(rt)
        return svc.events().insert(calendarId=cal_id, body={
            "summary": f"{name} — {reason or 'Appointment'}",
            "description": ("Booked by Voxsera AI voice agent.\n"
                            f"Name: {name}\n"
                            f"Age: {age or '—'}\n"
                            f"Phone: {phone}\n"
                            f"Symptoms/Reason: {reason or '—'}"),
            "start": {"dateTime": start.isoformat()},
            "end":   {"dateTime": end.isoformat()},
        }).execute()

    event = await asyncio.to_thread(_create_event)
    await append_appointment_row(business, [name, phone, date_str, time_str,
                                            reason, "confirmed", "", age])
    return {"event_id": event.get("id"), "date": date_str, "time": time_str,
            "name": name, "age": age, "reason": reason}


# ---------------- Inbound call-log sheet (auto-created) ----------------

INBOUND_TAB = "Calls"
INBOUND_HEADER = ["Timestamp", "Phone", "Outcome", "Sentiment",
                  "Turns", "Duration (s)", "Transcript"]


async def create_workspace_sheet(refresh_token: str, business_name: str) -> str:
    """Create ONE spreadsheet in the connected Drive with two tabs:
    - 'Appointments': bookings made by the inbound agent; the outbound
      reminder scanner and Call-now read from this same tab.
    - 'Calls': the inbound call log (transcripts, outcomes).
    Returns the spreadsheet ID."""
    def _q():
        svc = _sheets(refresh_token)
        ss = svc.spreadsheets().create(body={
            "properties": {"title": f"Voxsera — {business_name}"},
            "sheets": [{"properties": {"title": SHEET_TAB}},
                       {"properties": {"title": INBOUND_TAB}}],
        }).execute()
        sid = ss["spreadsheetId"]
        svc.spreadsheets().values().update(
            spreadsheetId=sid, range=f"{SHEET_TAB}!A1",
            valueInputOption="RAW", body={"values": [SHEET_HEADER]}).execute()
        svc.spreadsheets().values().update(
            spreadsheetId=sid, range=f"{INBOUND_TAB}!A1",
            valueInputOption="RAW", body={"values": [INBOUND_HEADER]}).execute()
        return sid
    return await asyncio.to_thread(_q)


async def append_inbound_log(business: dict, row: list):
    """Append one finished inbound call to the auto-created log sheet."""
    rt, sid = business.get("google_refresh_token"), business.get("inbound_sheet_id")
    if not (rt and sid):
        return

    def _q():
        _sheets(rt).spreadsheets().values().append(
            spreadsheetId=sid, range=f"{INBOUND_TAB}!A:G",
            valueInputOption="USER_ENTERED", body={"values": [row]}).execute()
    await asyncio.to_thread(_q)


# ---------------- Sheets ----------------

async def ensure_sheet_header(business: dict):
    rt, sid = business.get("google_refresh_token"), business.get("google_sheet_id")
    if not (rt and sid):
        return

    def _q():
        svc = _sheets(rt)
        got = svc.spreadsheets().values().get(
            spreadsheetId=sid, range=f"{SHEET_TAB}!A1:H1").execute().get("values")
        if not got:
            svc.spreadsheets().values().update(
                spreadsheetId=sid, range=f"{SHEET_TAB}!A1",
                valueInputOption="RAW", body={"values": [SHEET_HEADER]}).execute()
    try:
        await asyncio.to_thread(_q)
    except Exception as e:
        # tab probably missing — try to create it
        def _add_tab():
            svc = _sheets(rt)
            svc.spreadsheets().batchUpdate(spreadsheetId=sid, body={
                "requests": [{"addSheet": {"properties": {"title": SHEET_TAB}}}]}).execute()
            svc.spreadsheets().values().update(
                spreadsheetId=sid, range=f"{SHEET_TAB}!A1",
                valueInputOption="RAW", body={"values": [SHEET_HEADER]}).execute()
        try:
            await asyncio.to_thread(_add_tab)
        except Exception as e2:
            print(f"sheet header err: {e} / {e2}")


async def append_appointment_row(business: dict, row: list):
    rt, sid = business.get("google_refresh_token"), business.get("google_sheet_id")
    if not (rt and sid):
        return

    def _q():
        _sheets(rt).spreadsheets().values().append(
            spreadsheetId=sid, range=f"{SHEET_TAB}!A:H",
            valueInputOption="USER_ENTERED",
            body={"values": [row]}).execute()
    await asyncio.to_thread(_q)


async def read_appointments(business: dict) -> list[dict]:
    """Rows from the sheet as dicts, with the sheet row number attached."""
    rt, sid = business.get("google_refresh_token"), business.get("google_sheet_id")
    if not (rt and sid):
        return []

    def _q():
        return _sheets(rt).spreadsheets().values().get(
            spreadsheetId=sid, range=f"{SHEET_TAB}!A2:G").execute().get("values", [])

    rows = await asyncio.to_thread(_q)
    out = []
    for i, r in enumerate(rows):
        r = r + [""] * (7 - len(r))
        out.append({
            "row": i + 2, "name": r[0], "phone": r[1], "date": r[2],
            "time": r[3], "reason": r[4], "status": r[5], "reminder_sent": r[6],
        })
    return out


async def mark_reminder_sent(business: dict, row_number: int):
    rt, sid = business.get("google_refresh_token"), business.get("google_sheet_id")
    if not (rt and sid):
        return

    def _q():
        _sheets(rt).spreadsheets().values().update(
            spreadsheetId=sid, range=f"{SHEET_TAB}!G{row_number}",
            valueInputOption="RAW", body={"values": [["YES"]]}).execute()
    await asyncio.to_thread(_q)


async def find_appointment_by_phone(business: dict, phone: str) -> dict | None:
    digits = "".join(c for c in phone if c.isdigit())[-10:]
    for a in await read_appointments(business):
        row_digits = "".join(c for c in a["phone"] if c.isdigit())[-10:]
        if digits and row_digits == digits and (a["status"] or "").lower() != "cancelled":
            return a
    return None
