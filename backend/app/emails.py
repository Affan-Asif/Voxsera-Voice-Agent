"""Resend transactional email — booking confirmations to the business owner."""
import httpx

from . import config

RESEND_URL = "https://api.resend.com/emails"


async def send_booking_email(business: dict, name: str, phone: str,
                             date: str, time: str, reason: str):
    """Fire-and-forget booking confirmation to the business owner.
    Never raises — a failed email must never break a live call."""
    to = business.get("owner_email")
    if not (config.RESEND_API_KEY and to):
        print("email skipped (no RESEND_API_KEY or owner_email)")
        return
    agent = (business.get("persona") or {}).get("agent_name", "your AI agent")
    html = f"""
    <div style="font-family:Inter,Arial,sans-serif;max-width:520px;margin:auto;
                background:#0f172a;color:#e2e8f0;border-radius:12px;padding:32px">
      <h2 style="margin:0 0 4px;color:#fff">New appointment booked 🎉</h2>
      <p style="color:#94a3b8;margin:0 0 24px">{agent} just booked this over the phone
         for <b style="color:#e2e8f0">{business.get('name','your business')}</b>.</p>
      <table style="width:100%;border-collapse:collapse;font-size:14px">
        <tr><td style="padding:8px 0;color:#94a3b8">Customer</td><td style="text-align:right">{name}</td></tr>
        <tr><td style="padding:8px 0;color:#94a3b8">Phone</td><td style="text-align:right">{phone}</td></tr>
        <tr><td style="padding:8px 0;color:#94a3b8">Date</td><td style="text-align:right">{date}</td></tr>
        <tr><td style="padding:8px 0;color:#94a3b8">Time</td><td style="text-align:right">{time}</td></tr>
        <tr><td style="padding:8px 0;color:#94a3b8">Reason</td><td style="text-align:right">{reason or '—'}</td></tr>
      </table>
      <p style="color:#64748b;font-size:12px;margin-top:24px">
        Added to your Google Calendar and appointment sheet automatically · Voxsera AI</p>
    </div>"""
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.post(RESEND_URL, headers={
                "Authorization": f"Bearer {config.RESEND_API_KEY}",
                "Content-Type": "application/json",
            }, json={
                "from": f"Voxsera AI <{config.RESEND_FROM}>",
                "to": [to],
                "subject": f"New booking: {name} — {date} {time}",
                "html": html,
            })
            if r.status_code >= 300:
                print(f"resend error {r.status_code}: {r.text[:200]}")
            else:
                print(f"booking email sent to {to}")
    except Exception as e:
        print(f"resend failed: {type(e).__name__}: {e}")
