import os
from dotenv import load_dotenv

load_dotenv()

# Google may return scopes in a different order/set than requested
# (esp. with include_granted_scopes) — don't let oauthlib crash on it.
os.environ.setdefault("OAUTHLIB_RELAX_TOKEN_SCOPE", "1")

GEMINI_API_KEY   = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL     = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY", "")
SARVAM_API_KEY   = os.getenv("SARVAM_API_KEY", "")

TWILIO_ACCOUNT_SID  = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN   = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER", "")

SUPABASE_URL         = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")

RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
RESEND_FROM    = os.getenv("RESEND_FROM", "onboarding@resend.dev")

GOOGLE_CLIENT_ID     = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")

BASE_URL     = os.getenv("BASE_URL", "").rstrip("/")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173").rstrip("/")

# wss:// URL Twilio connects its media stream to
WSS_URL = (
    BASE_URL.replace("https://", "wss://").replace("http://", "ws://") + "/media"
    if BASE_URL else "wss://localhost/media"
)

GOOGLE_REDIRECT_URI = f"{BASE_URL}/api/google/callback"
GOOGLE_SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/spreadsheets",
]

# Voices offered in the onboarding picker.
# provider "deepgram": English accent (Aura). provider "sarvam": Indian accent,
# multilingual (Bulbul v2) — speaks Hindi and 10+ Indian languages natively.
VOICE_CATALOG = [
    {"id": "aura-2-thalia-en",    "name": "Thalia",    "gender": "female", "provider": "deepgram", "style": "Clear, confident, energetic"},
    {"id": "aura-2-andromeda-en", "name": "Andromeda", "gender": "female", "provider": "deepgram", "style": "Warm, calm, reassuring"},
    {"id": "aura-2-helena-en",    "name": "Helena",    "gender": "female", "provider": "deepgram", "style": "Friendly, natural, caring"},
    {"id": "aura-2-luna-en",      "name": "Luna",      "gender": "female", "provider": "deepgram", "style": "Soft, polite, youthful"},
    {"id": "aura-2-asteria-en",   "name": "Asteria",   "gender": "female", "provider": "deepgram", "style": "Crisp, professional"},
    {"id": "aura-2-apollo-en",    "name": "Apollo",    "gender": "male",   "provider": "deepgram", "style": "Confident, comfortable"},
    {"id": "aura-2-arcas-en",     "name": "Arcas",     "gender": "male",   "provider": "deepgram", "style": "Natural, smooth, casual"},
    {"id": "aura-2-orion-en",     "name": "Orion",     "gender": "male",   "provider": "deepgram", "style": "Approachable, deep"},
    {"id": "sarvam:anushka",  "name": "Anushka",  "gender": "female", "provider": "sarvam", "style": "Indian accent · warm, professional"},
    {"id": "sarvam:manisha",  "name": "Manisha",  "gender": "female", "provider": "sarvam", "style": "Indian accent · friendly, upbeat"},
    {"id": "sarvam:vidya",    "name": "Vidya",    "gender": "female", "provider": "sarvam", "style": "Indian accent · calm, mature"},
    {"id": "sarvam:arya",     "name": "Arya",     "gender": "female", "provider": "sarvam", "style": "Indian accent · crisp, modern"},
    {"id": "sarvam:abhilash", "name": "Abhilash", "gender": "male",   "provider": "sarvam", "style": "Indian accent · deep, courteous"},
    {"id": "sarvam:karun",    "name": "Karun",    "gender": "male",   "provider": "sarvam", "style": "Indian accent · natural, easygoing"},
    {"id": "sarvam:hitesh",   "name": "Hitesh",   "gender": "male",   "provider": "sarvam", "style": "Indian accent · energetic"},
]

# Agent language -> (Deepgram STT params, Sarvam target_language_code)
LANGUAGES = {
    "en": {"dg_model": "nova-2-phonecall", "dg_lang": "en-US", "sarvam_code": "en-IN", "label": "English"},
    "hi": {"dg_model": "nova-2",           "dg_lang": "hi",    "sarvam_code": "hi-IN", "label": "Hindi"},
}

def require(*names: str):
    missing = [n for n in names if not globals().get(n)]
    if missing:
        raise RuntimeError(f"Missing required env vars: {', '.join(missing)} — fill them in backend/.env")
