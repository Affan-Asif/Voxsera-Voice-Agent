"""TTS — two providers behind one interface.

- Deepgram Aura  (voice ids like "aura-2-thalia-en"): English accent, streamed.
- Sarvam Bulbul  (voice ids like "sarvam:anushka"): Indian accent, multilingual
  (Hindi + Indian languages). Synthesized as 8k WAV then converted to μ-law.

stream_tts_to_twilio: μ-law 8k chunks into the Twilio media stream,
barge-in aware via session.ai_speaking flag.
synthesize_preview: audio bytes for the onboarding voice picker.
"""
import audioop
import base64
import json

import httpx

from . import config

DG_SPEAK = "https://api.deepgram.com/v1/speak"
SARVAM_TTS = "https://api.sarvam.ai/text-to-speech"


def is_sarvam(voice_model: str) -> bool:
    return (voice_model or "").startswith("sarvam:")


def _sarvam_lang(language: str) -> str:
    return config.LANGUAGES.get(language or "en", config.LANGUAGES["en"])["sarvam_code"]


async def _sarvam_wav(voice_model: str, text: str, language: str, sample_rate: int) -> bytes:
    """Call Sarvam Bulbul v2, return raw WAV bytes."""
    if not config.SARVAM_API_KEY:
        raise RuntimeError("SARVAM_API_KEY is missing — add it to backend/.env and restart")
    speaker = voice_model.split(":", 1)[1]
    base = {
        "model": "bulbul:v2",
        "speaker": speaker,
        "target_language_code": _sarvam_lang(language),
        "speech_sample_rate": sample_rate,
        "enable_preprocessing": True,
    }
    headers = {"api-subscription-key": config.SARVAM_API_KEY,
               "Content-Type": "application/json"}
    last_err = "unknown"
    async with httpx.AsyncClient(timeout=30.0) as client:
        # v2 API uses "text"; some deployments still expect "inputs" — try both
        for body in ({**base, "text": text[:1400]},
                     {**base, "inputs": [text[:1400]]}):
            r = await client.post(SARVAM_TTS, headers=headers, json=body)
            if r.status_code == 200:
                audios = r.json().get("audios") or []
                if not audios:
                    raise RuntimeError("Sarvam TTS returned no audio")
                return base64.b64decode(audios[0])
            last_err = f"{r.status_code}: {r.text[:300]}"
            print(f"Sarvam TTS attempt failed -> {last_err}")
    raise RuntimeError(f"Sarvam TTS {last_err}")


def _wav_to_mulaw8k(wav: bytes) -> bytes:
    """Strip WAV header, convert 16-bit PCM 8k mono -> μ-law 8k."""
    # find the 'data' chunk rather than assuming a 44-byte header
    idx = wav.find(b"data")
    pcm = wav[idx + 8:] if idx != -1 else wav[44:]
    return audioop.lin2ulaw(pcm, 2)


async def synthesize_preview(voice_model: str, text: str) -> tuple[bytes, str]:
    """Returns (audio_bytes, media_type) for the onboarding voice picker."""
    if is_sarvam(voice_model):
        wav = await _sarvam_wav(voice_model, text, "en", 22050)
        return wav, "audio/wav"
    params = {"model": voice_model, "encoding": "mp3"}
    headers = {"Authorization": f"Token {config.DEEPGRAM_API_KEY}",
               "Content-Type": "application/json"}
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.post(DG_SPEAK, params=params, headers=headers,
                              json={"text": text})
        r.raise_for_status()
        return r.content, "audio/mpeg"


async def _send_mulaw(session, mulaw: bytes):
    """Send μ-law bytes to Twilio in chunks, honouring barge-in."""
    sent = 0
    for i in range(0, len(mulaw), 4096):
        if not session.ai_speaking:
            return
        chunk = mulaw[i:i + 4096]
        await session.twilio_ws.send_text(json.dumps({
            "event": "media",
            "streamSid": session.stream_sid,
            "media": {"payload": base64.b64encode(chunk).decode()},
        }))
        sent += len(chunk)
    print(f"TTS done: {sent} bytes -> twilio (sarvam)")


async def stream_tts_to_twilio(session, text: str):
    """Route to the right provider based on the selected voice."""
    if is_sarvam(session.voice_model):
        try:
            wav = await _sarvam_wav(session.voice_model, text,
                                    getattr(session, "language", "en"), 8000)
            await _send_mulaw(session, _wav_to_mulaw8k(wav))
        except Exception as e:
            if type(e).__name__ != "CancelledError":
                print(f"Sarvam TTS error: {e}")
            raise
        finally:
            session.ai_speaking = False
        return
    await _deepgram_stream(session, text)


async def _deepgram_stream(session, text: str):
    """Stream μ-law 8k audio to the Twilio websocket as fast as it arrives.
    Stops immediately if session.ai_speaking is flipped off (barge-in)."""
    params = {"model": session.voice_model, "encoding": "mulaw",
              "sample_rate": "8000", "container": "none"}
    headers = {"Authorization": f"Token {config.DEEPGRAM_API_KEY}",
               "Content-Type": "application/json"}
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            async with client.stream("POST", DG_SPEAK, params=params,
                                     headers=headers, json={"text": text}) as resp:
                if resp.status_code != 200:
                    err = await resp.aread()
                    print(f"Deepgram TTS {resp.status_code}: {err[:200]!r}")
                    return
                sent = 0
                async for chunk in resp.aiter_bytes(chunk_size=4096):
                    if not session.ai_speaking:
                        return
                    if not chunk:
                        continue
                    await session.twilio_ws.send_text(json.dumps({
                        "event": "media",
                        "streamSid": session.stream_sid,
                        "media": {"payload": base64.b64encode(chunk).decode()},
                    }))
                    sent += len(chunk)
                print(f"TTS done: {sent} bytes -> twilio")
                # mark lets Twilio tell us playback finished (optional)
                try:
                    await session.twilio_ws.send_text(json.dumps({
                        "event": "mark",
                        "streamSid": session.stream_sid,
                        "mark": {"name": "tts_done"},
                    }))
                except Exception:
                    pass
    except Exception as e:
        if type(e).__name__ != "CancelledError":
            print(f"TTS stream error: {type(e).__name__}: {e}")
        raise
    finally:
        session.ai_speaking = False
