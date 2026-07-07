"""Full-duplex Twilio Media Stream handler (inbound + outbound).

Twilio <Connect><Stream> -> this websocket (μ-law 8k both ways)
Deepgram streaming ASR   -> always-on transcription + VAD (SpeechStarted)
Deepgram Aura TTS        -> streamed straight back into the call
Barge-in                 -> on SpeechStarted: cancel TTS + Twilio `clear`
Gemini + tools           -> replies, checks calendar, books, reminds
Supabase                 -> transcript + sentiment persisted on hangup
"""
import asyncio
import base64
import json
from datetime import datetime, timezone

import websockets
from fastapi import WebSocket, WebSocketDisconnect

from . import config, db, google_service, tts
from .agent import AgentBrain
from .live import live_broadcast


class Session:
    def __init__(self, twilio_ws: WebSocket):
        self.twilio_ws = twilio_ws
        self.stream_sid = None
        self.call_sid = None
        self.direction = "inbound"
        self.phone = "unknown"
        self.business: dict | None = None
        self.brain: AgentBrain | None = None
        self.voice_model = "aura-2-thalia-en"
        self.language = "en"                   # persona.language: en | hi
        self.started_at = None
        self.start_ts = None
        self.dg_ws = None
        self.history: list[dict] = []          # {"role","text","ts"}
        self.ai_speaking = False
        self.tts_task: asyncio.Task | None = None
        self.closing = False
        self.thinking = False                  # guard double-replies
        self.greet_guard_until = 0.0           # barge-in disabled until this time
                                               # (callee's "Hello?" must not kill the greeting)

    # ---------- Deepgram ASR ----------

    async def connect_deepgram(self):
        lang = config.LANGUAGES.get(self.language, config.LANGUAGES["en"])
        url = (
            "wss://api.deepgram.com/v1/listen"
            "?encoding=mulaw&sample_rate=8000&channels=1"
            f"&model={lang['dg_model']}&language={lang['dg_lang']}"
            "&punctuate=true&smart_format=true"
            "&interim_results=true&endpointing=200"
            "&vad_events=true&utterance_end_ms=1000"
        )
        hdr = {"Authorization": f"Token {config.DEEPGRAM_API_KEY}"}
        try:
            self.dg_ws = await websockets.connect(url, additional_headers=hdr)
        except TypeError:  # websockets < 12
            self.dg_ws = await websockets.connect(url, extra_headers=hdr)
        print("Deepgram connected")

    async def deepgram_keepalive(self):
        try:
            while not self.closing and self.dg_ws:
                await asyncio.sleep(7)
                try:
                    await self.dg_ws.send(json.dumps({"type": "KeepAlive"}))
                except Exception:
                    return
        except asyncio.CancelledError:
            return

    # ---------- barge-in ----------

    async def send_twilio_clear(self):
        if self.stream_sid:
            try:
                await self.twilio_ws.send_text(json.dumps(
                    {"event": "clear", "streamSid": self.stream_sid}))
            except Exception:
                pass

    async def cancel_tts(self):
        self.ai_speaking = False
        if self.tts_task and not self.tts_task.done():
            self.tts_task.cancel()
            try:
                await self.tts_task
            except (asyncio.CancelledError, Exception):
                pass
        self.tts_task = None

    async def barge_in(self):
        if asyncio.get_event_loop().time() < self.greet_guard_until:
            return  # let the opening greeting finish
        if self.ai_speaking:
            print("barge-in: user interrupting TTS")
            await self.cancel_tts()
            await self.send_twilio_clear()
            await live_broadcast({"type": "barge_in", "call_sid": self.call_sid})

    # ---------- speak ----------

    async def speak(self, text: str, clear_first: bool = True):
        await self.cancel_tts()
        if clear_first:
            await self.send_twilio_clear()
        self.ai_speaking = True
        self.tts_task = asyncio.create_task(tts.stream_tts_to_twilio(self, text))

    def log_turn(self, role: str, text: str):
        self.history.append({"role": role, "text": text,
                             "ts": datetime.now(timezone.utc).isoformat()})

    async def handle_user_utterance(self, user_text: str):
        if self.thinking:
            return
        self.thinking = True
        try:
            self.log_turn("USER", user_text)
            await live_broadcast({"type": "user_final", "text": user_text,
                                  "call_sid": self.call_sid})
            reply = await self.brain.reply(user_text)
            await live_broadcast({
                "type": "state",
                "sentiment": round(self.brain.state["sentiment"], 3),
                "turns": self.brain.state["turns"],
                "call_sid": self.call_sid,
            })
            self.log_turn("AGENT", reply)
            print(f"AGENT: {reply}")
            await live_broadcast({"type": "agent_speak", "text": reply,
                                  "call_sid": self.call_sid})
            await self.speak(reply)
        finally:
            self.thinking = False


async def deepgram_loop(sess: Session):
    loop = asyncio.get_event_loop()
    st = {"pending": "", "interim": "", "last_ts": loop.time()}

    def _take() -> str:
        """Grab whatever speech we have (finals first, else last interim)."""
        text = (st["pending"] or st["interim"]).strip()
        st["pending"] = ""
        st["interim"] = ""
        return text

    async def _commit(text: str, src: str):
        if text:
            print(f"USER ({src}): {text}")
            asyncio.create_task(sess.handle_user_utterance(text))

    async def watchdog():
        """Safety net: if Deepgram never sends speech_final/UtteranceEnd,
        commit the utterance after 1.2s of transcript silence."""
        try:
            while not sess.closing:
                await asyncio.sleep(0.25)
                if sess.thinking or sess.ai_speaking:
                    continue
                if (st["pending"] or st["interim"]) and \
                        loop.time() - st["last_ts"] > 0.9:
                    await _commit(_take(), "watchdog")
        except asyncio.CancelledError:
            pass

    wd_task = asyncio.create_task(watchdog())
    try:
        async for raw in sess.dg_ws:
            if sess.closing:
                break
            data = json.loads(raw)
            typ = data.get("type")

            if typ == "SpeechStarted":
                await sess.barge_in()

            elif typ == "Results":
                alt = data.get("channel", {}).get("alternatives", [{}])[0]
                transcript = (alt.get("transcript") or "").strip()
                is_final = data.get("is_final", False)
                speech_final = data.get("speech_final", False)
                if transcript:
                    st["last_ts"] = loop.time()

                if transcript and is_final:
                    st["pending"] = (st["pending"] + " " + transcript).strip()
                    st["interim"] = ""
                if transcript and not is_final:
                    st["interim"] = (st["pending"] + " " + transcript).strip()
                    await live_broadcast({"type": "user_interim",
                                          "text": st["interim"],
                                          "call_sid": sess.call_sid})
                if speech_final and st["pending"]:
                    await _commit(_take(), "final")

            elif typ == "UtteranceEnd":
                await _commit(_take(), "utt_end")
    except Exception as e:
        if not sess.closing:
            print(f"deepgram loop err: {type(e).__name__}: {e}")
    finally:
        wd_task.cancel()
        if not sess.closing:
            print("WARNING: Deepgram socket closed mid-call "
                  "(check API credits / key) — agent can no longer hear")


async def media_endpoint(ws: WebSocket):
    await ws.accept()
    sess = Session(ws)
    # Deepgram is connected inside the `start` event, once we know the
    # business's language (needed to pick the right STT model).
    dg_task = None
    ka_task = None

    try:
        while True:
            msg = await ws.receive_text()
            data = json.loads(msg)
            ev = data.get("event")

            if ev == "start":
                info = data["start"]
                sess.stream_sid = info["streamSid"]
                sess.call_sid = info.get("callSid")
                cp = info.get("customParameters") or {}
                sess.direction = cp.get("direction", "inbound")
                sess.phone = cp.get("phone") or "unknown"
                business_id = cp.get("business_id")
                sess.business = (await db.get_business(business_id)
                                 if business_id else
                                 await db.get_business_by_number(config.TWILIO_PHONE_NUMBER))
                if not sess.business:
                    print("no business registered — hanging up")
                    break
                sess.voice_model = sess.business.get("voice_model") or sess.voice_model
                sess.language = ((sess.business.get("persona") or {})
                                 .get("language") or "en")
                try:
                    await sess.connect_deepgram()
                except Exception as e:
                    print(f"Deepgram connect failed: {e}")
                    break
                dg_task = asyncio.create_task(deepgram_loop(sess))
                ka_task = asyncio.create_task(sess.deepgram_keepalive())
                appt = None
                if sess.direction == "outbound":
                    appt = {"name": cp.get("appt_name"), "date": cp.get("appt_date"),
                            "time": cp.get("appt_time"), "reason": cp.get("appt_reason")}
                sess.brain = AgentBrain(sess.business, sess.direction,
                                        sess.phone, appt)
                sess.started_at = datetime.now(timezone.utc)
                sess.start_ts = asyncio.get_event_loop().time()
                print(f"stream started dir={sess.direction} phone={sess.phone} "
                      f"biz={sess.business['name']}")
                await live_broadcast({
                    "type": "call_start", "direction": sess.direction,
                    "phone": sess.phone, "call_sid": sess.call_sid,
                    "business": sess.business["name"],
                })
                greeting = sess.brain.greeting()
                sess.log_turn("AGENT", greeting)
                await live_broadcast({"type": "agent_speak", "text": greeting,
                                      "call_sid": sess.call_sid})
                # outbound callees say "Hello?" immediately — give the greeting
                # a protected window so it can't be barge-in cancelled
                guard = 8.0 if sess.direction == "outbound" else 3.0
                sess.greet_guard_until = asyncio.get_event_loop().time() + guard
                if sess.direction == "outbound":
                    await asyncio.sleep(0.8)   # let the phone audio path settle
                await sess.speak(greeting, clear_first=False)

            elif ev == "media":
                if sess.dg_ws is None:
                    continue  # start event not processed yet
                audio = base64.b64decode(data["media"]["payload"])
                try:
                    await sess.dg_ws.send(audio)
                except Exception:
                    pass

            elif ev == "stop":
                print("stream stopped by Twilio")
                break

    except WebSocketDisconnect:
        print("Twilio WS disconnected")
    except Exception as e:
        print(f"media handler err: {e}")
    finally:
        sess.closing = True
        await sess.cancel_tts()
        try:
            if sess.dg_ws:
                await sess.dg_ws.send(json.dumps({"type": "CloseStream"}))
                await sess.dg_ws.close()
        except Exception:
            pass
        if dg_task: dg_task.cancel()
        if ka_task: ka_task.cancel()
        try:
            await ws.close()
        except Exception:
            pass
        await _persist(sess)


def _classify(sess: Session) -> tuple[str, str]:
    user_text = " ".join(t["text"].lower() for t in sess.history
                         if t["role"] == "USER")
    if not user_text:
        return "no_answer", "No user speech captured"
    if sess.direction == "outbound":
        return "reminded", "Reminder call delivered"
    booked_kws = ("booked", "confirmed", "see you", "appointment is set",
                  "you're all set", "scheduled you")
    agent_text = " ".join(t["text"].lower() for t in sess.history
                          if t["role"] == "AGENT")
    if any(k in agent_text for k in booked_kws):
        return "booked", "Appointment booked during call"
    return "info", "Enquiry handled"


async def _log_inbound_sheet(business: dict, row: list):
    try:
        await google_service.append_inbound_log(business, row)
        print("inbound call logged to Google Sheet")
    except Exception as e:
        print(f"inbound sheet log failed: {type(e).__name__}: {e}")


async def _persist(sess: Session):
    if not sess.business:
        return
    try:
        ended = datetime.now(timezone.utc)
        duration = (asyncio.get_event_loop().time() - sess.start_ts
                    if sess.start_ts else 0.0)
        outcome, notes = _classify(sess)
        row = await db.save_call({
            "business_id": sess.business["id"],
            "direction": sess.direction,
            "phone": sess.phone,
            "call_sid": sess.call_sid,
            "stream_sid": sess.stream_sid,
            "transcript": sess.history,
            "sentiment": round(sess.brain.avg_sentiment, 3) if sess.brain else 0.0,
            "outcome": outcome,
            "turns": sess.brain.state["turns"] if sess.brain else 0,
            "duration_sec": round(duration, 2),
            "notes": notes,
            "started_at": sess.started_at.isoformat() if sess.started_at else None,
            "ended_at": ended.isoformat(),
        })
        print(f"call saved id={row['id']} dir={sess.direction} outcome={outcome}")
        # log inbound calls to the auto-created Google Sheet (fire-and-forget)
        if sess.direction == "inbound" and sess.business.get("inbound_sheet_id"):
            transcript_text = " | ".join(
                f"{t['role']}: {t['text']}" for t in sess.history)
            asyncio.create_task(_log_inbound_sheet(sess.business, [
                (sess.started_at.strftime("%Y-%m-%d %H:%M:%S")
                 if sess.started_at else ""),
                sess.phone, outcome,
                round(sess.brain.avg_sentiment, 2) if sess.brain else 0,
                sess.brain.state["turns"] if sess.brain else 0,
                round(duration), transcript_text[:45000],
            ]))
        await live_broadcast({
            "type": "call_end", "direction": sess.direction, "phone": sess.phone,
            "outcome": outcome, "duration_sec": round(duration, 2),
        })
    except Exception as e:
        print(f"failed to save call: {type(e).__name__}: {e}")
