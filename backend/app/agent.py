"""Gemini brain: persona-driven system prompt + function calling against
Google Calendar / Sheets, plus VADER sentiment tracking per turn."""
import asyncio
import json
import re
from datetime import datetime
from zoneinfo import ZoneInfo

import google.generativeai as genai
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

from . import config, emails, google_service

genai.configure(api_key=config.GEMINI_API_KEY)
VADER = SentimentIntensityAnalyzer()

_GEMINI_COOLDOWN_UNTIL = 0.0
MAX_TOOL_ROUNDS = 3

TOOLS = [{
    "function_declarations": [
        {
            "name": "get_available_slots",
            "description": "Get open appointment slots for a given date. Always call this before offering or booking a time.",
            "parameters": {
                "type": "object",
                "properties": {"date": {"type": "string", "description": "Date in YYYY-MM-DD"}},
                "required": ["date"],
            },
        },
        {
            "name": "book_appointment",
            "description": "Book an appointment once the caller has confirmed name, age, symptoms/reason, date and time. Only book slots returned by get_available_slots.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name":   {"type": "string", "description": "Caller's full name"},
                    "age":    {"type": "string", "description": "Caller's age, e.g. '34'"},
                    "date":   {"type": "string", "description": "YYYY-MM-DD"},
                    "time":   {"type": "string", "description": "HH:MM 24-hour"},
                    "reason": {"type": "string", "description": "Symptoms / reason for the visit"},
                },
                "required": ["name", "date", "time"],
            },
        },
        {
            "name": "find_my_appointment",
            "description": "Look up the caller's existing appointment using their phone number.",
            "parameters": {"type": "object", "properties": {}},
        },
    ]
}]


def _parse_retry_delay(err_msg: str) -> float:
    m = re.search(r"retry_delay\s*\{\s*seconds:\s*(\d+)", err_msg)
    if m:
        return float(m.group(1))
    m = re.search(r"retry in\s+([\d.]+)s", err_msg)
    return float(m.group(1)) if m else 20.0


def build_system_prompt(business: dict, direction: str, appt: dict | None) -> str:
    p = business.get("persona") or {}
    hours = business.get("business_hours") or {}
    tz = ZoneInfo(business.get("timezone") or "UTC")
    now = datetime.now(tz)
    agent_name = p.get("agent_name") or "Maya"
    friendliness = int(p.get("friendliness", 7))
    formality = int(p.get("formality", 5))
    verbosity = int(p.get("verbosity", 3))

    tone_bits = []
    tone_bits.append("Be very warm, upbeat and friendly." if friendliness >= 7
                     else "Be polite and pleasant." if friendliness >= 4
                     else "Be efficient and matter-of-fact.")
    tone_bits.append("Speak formally and professionally." if formality >= 7
                     else "Keep a natural, conversational register." if formality >= 4
                     else "Be casual and relaxed.")
    tone_bits.append(
        "Keep every reply to ONE short sentence when possible."
        if verbosity <= 3 else
        "Reply in 1-2 short sentences." if verbosity <= 7 else
        "You may use up to 3 short sentences when explaining."
    )

    base = (
        f"You are {agent_name}, the AI phone receptionist for {business['name']} "
        f"({business.get('industry') or 'local business'}).\n"
        f"Current date/time: {now.strftime('%A, %Y-%m-%d %H:%M')} ({business.get('timezone')}).\n"
        f"Business hours: {hours.get('open','09:00')}-{hours.get('close','18:00')} "
        f"on {', '.join(hours.get('days', []))}.\n"
        f"{' '.join(tone_bits)}\n"
        "This is a live PHONE call: plain spoken text only — no markdown, no lists, "
        "no emojis, no stage directions. Say times naturally (e.g. 'two thirty PM'). "
        "Never invent availability — always use get_available_slots first. "
        "Before booking, collect: (1) the caller's full name, (2) their age, and "
        "(3) their symptoms or reason for the visit — one question at a time; "
        "you already know their phone number from caller ID. "
        "If asked something unrelated to the business, politely steer back.\n"
    )
    if (p.get("language") or "en") == "hi":
        base += ("IMPORTANT: This call is in HINDI. Reply ONLY in natural, spoken "
                 "Hindi (Devanagari script). Keep numbers and times easy to say aloud. "
                 "You may mix common English words the way people naturally do (Hinglish).\n")
    if p.get("custom_context"):
        base += f"Business-specific instructions: {p['custom_context']}\n"

    if direction == "outbound" and appt:
        base += (
            "\nTHIS IS AN OUTBOUND REMINDER CALL placed by the business. "
            f"You are calling {appt.get('name')} to remind them of their appointment "
            f"({appt.get('reason')}) today at {appt.get('time')} on {appt.get('date')}. "
            "Confirm they can make it, answer quick questions, and if they want to "
            "reschedule, check availability and rebook. Keep the call brief."
        )
    return base


class AgentBrain:
    def __init__(self, business: dict, direction: str, caller_phone: str,
                 appt: dict | None = None):
        self.business = business
        self.direction = direction
        self.caller_phone = caller_phone
        self.appt = appt
        self.state = {"sentiment": 0.0, "sentiment_sum": 0.0, "turns": 0}
        self.model = genai.GenerativeModel(
            config.GEMINI_MODEL,
            tools=TOOLS,
            system_instruction=build_system_prompt(business, direction, appt),
        )
        self.chat = self.model.start_chat()

    def greeting(self) -> str:
        p = self.business.get("persona") or {}
        agent_name = p.get("agent_name") or "Maya"
        hindi = (p.get("language") or "en") == "hi"
        if self.direction == "outbound" and self.appt:
            text = (f"नमस्ते, मैं {agent_name} बोल रही हूँ {self.business['name']} से। "
                    f"आज {self.appt.get('time')} बजे आपका अपॉइंटमेंट है, बस उसकी याद दिलाने के लिए कॉल किया। "
                    f"क्या आप आ पाएँगे?") if hindi else \
                   (f"Hi, this is {agent_name} calling from {self.business['name']}. "
                    f"Just a quick reminder about your appointment today at "
                    f"{self.appt.get('time')}. Can you still make it?")
        else:
            text = (f"नमस्ते! {self.business['name']} में आपका स्वागत है, मैं {agent_name} हूँ। "
                    f"मैं आपकी क्या मदद कर सकती हूँ?") if hindi else \
                   (f"Thank you for calling {self.business['name']}, this is {agent_name}. "
                    f"How can I help you today?")
        # Seed the greeting into Gemini's chat memory so the model knows it has
        # already introduced itself and never greets twice.
        try:
            self.chat = self.model.start_chat(history=[
                {"role": "user", "parts": ["(call connected — the line is now open)"]},
                {"role": "model", "parts": [text]},
            ])
        except Exception as e:
            print(f"greeting seed failed (non-fatal): {e}")
        return text

    def analyze_sentiment(self, text: str) -> float:
        s = VADER.polarity_scores(text.lower())["compound"]
        self.state["sentiment"] = s
        self.state["sentiment_sum"] += s
        return s

    @property
    def avg_sentiment(self) -> float:
        t = max(self.state["turns"], 1)
        return self.state["sentiment_sum"] / t

    # ---------------- tool execution ----------------

    async def _run_tool(self, name: str, args: dict) -> dict:
        try:
            if name == "get_available_slots":
                slots = await google_service.get_available_slots(
                    self.business, args["date"])
                return {"date": args["date"], "available_slots": slots[:12],
                        "note": "no slots" if not slots else "offer 2-3 options, not all"}
            if name == "book_appointment":
                res = await google_service.book_appointment(
                    self.business, args.get("name", "Customer"),
                    self.caller_phone, args["date"], args["time"],
                    args.get("reason", ""), args.get("age", ""))
                # fire-and-forget booking confirmation to the owner
                asyncio.create_task(emails.send_booking_email(
                    self.business, args.get("name", "Customer"),
                    self.caller_phone, args["date"], args["time"],
                    args.get("reason", "")))
                return {"booked": True, **res}
            if name == "find_my_appointment":
                a = await google_service.find_appointment_by_phone(
                    self.business, self.caller_phone)
                return {"appointment": a} if a else {
                    "appointment": None, "note": "no appointment found for this number"}
            return {"error": f"unknown tool {name}"}
        except Exception as e:
            print(f"tool {name} error: {e}")
            return {"error": str(e)[:200]}

    # ---------------- main reply ----------------

    async def reply(self, user_text: str) -> str:
        global _GEMINI_COOLDOWN_UNTIL
        self.state["turns"] += 1
        self.analyze_sentiment(user_text)

        loop_now = asyncio.get_event_loop().time()
        if loop_now < _GEMINI_COOLDOWN_UNTIL:
            return ("I'm sorry, could you give me just a moment and say that again?")

        try:
            resp = await asyncio.to_thread(self.chat.send_message, user_text)
            for _ in range(MAX_TOOL_ROUNDS):
                calls = [p.function_call for p in resp.candidates[0].content.parts
                         if getattr(p, "function_call", None) and p.function_call.name]
                if not calls:
                    break
                responses = []
                for fc in calls:
                    args = {k: v for k, v in (fc.args or {}).items()}
                    print(f"tool call: {fc.name}({json.dumps(args, default=str)})")
                    result = await self._run_tool(fc.name, args)
                    responses.append(genai.protos.Part(
                        function_response=genai.protos.FunctionResponse(
                            name=fc.name, response={"result": result})))
                resp = await asyncio.to_thread(
                    self.chat.send_message,
                    genai.protos.Content(parts=responses))

            text = ""
            try:
                text = (resp.text or "").strip()
            except Exception:
                pass
            text = text.replace("*", "").replace("#", "")
            return text or "Sorry, could you repeat that?"

        except Exception as e:
            msg = str(e)
            if "429" in msg or "quota" in msg.lower() or "rate" in msg.lower():
                delay = _parse_retry_delay(msg)
                _GEMINI_COOLDOWN_UNTIL = loop_now + min(delay + 1.0, 60.0)
                print(f"Gemini 429 — cooldown {delay:.0f}s")
            else:
                print(f"Gemini error: {type(e).__name__}: {msg[:160]}")
            return ("I'm sorry, I'm having a little trouble right now. "
                    "Could you say that once more?")
