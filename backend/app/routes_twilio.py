"""Twilio webhooks: inbound voice, outbound reminder TwiML, status callback."""
from html import escape

from fastapi import APIRouter, Request
from fastapi.responses import Response

from . import config, db

router = APIRouter()


def _stream_twiml(params: dict) -> str:
    tags = "".join(
        f'<Parameter name="{escape(str(k))}" value="{escape(str(v or ""))}"/>'
        for k, v in params.items()
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f'<Response><Connect><Stream url="{config.WSS_URL}">{tags}</Stream></Connect></Response>'
    )


@router.post("/twilio/voice")
async def inbound_voice(request: Request):
    """Set as the Voice webhook on your Twilio number ('A call comes in')."""
    form = await request.form()
    caller = form.get("From") or "unknown"
    to = form.get("To") or config.TWILIO_PHONE_NUMBER
    biz = await db.get_business_by_number(to)
    twiml = _stream_twiml({
        "direction": "inbound",
        "phone": caller,
        "business_id": biz["id"] if biz else "",
    })
    return Response(content=twiml, media_type="application/xml")


@router.post("/twilio/voice-outbound")
async def outbound_voice(request: Request):
    """TwiML for reminder calls; context arrives as query params from reminders.py."""
    qp = request.query_params
    twiml = _stream_twiml({
        "direction": "outbound",
        "phone": qp.get("to", ""),
        "business_id": qp.get("business_id", ""),
        "appt_name": qp.get("appt_name", ""),
        "appt_date": qp.get("appt_date", ""),
        "appt_time": qp.get("appt_time", ""),
        "appt_reason": qp.get("appt_reason", ""),
    })
    return Response(content=twiml, media_type="application/xml")


@router.post("/twilio/status")
async def status_callback(request: Request):
    form = await request.form()
    print(f"twilio status sid={form.get('CallSid')} "
          f"status={form.get('CallStatus')} dur={form.get('CallDuration')}")
    return Response(content="", media_type="text/plain")
