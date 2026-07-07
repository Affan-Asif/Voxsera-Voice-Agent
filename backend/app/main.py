"""Voice Agent Platform — FastAPI entrypoint.

Run:
    uvicorn app.main:app --host 0.0.0.0 --port 8000
"""
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from . import config
from .live import LIVE_CLIENTS
from .media_ws import media_endpoint
from .reminders import reminder_loop
from .routes_api import router as api_router
from .routes_twilio import router as twilio_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(reminder_loop())
    print(f"BASE_URL={config.BASE_URL or '(not set — Twilio webhooks will fail)'}")
    yield
    task.cancel()


app = FastAPI(title="Voice Agent Platform", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[config.FRONTEND_URL, "http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)
app.include_router(twilio_router)


@app.websocket("/media")
async def media(ws: WebSocket):
    await media_endpoint(ws)


@app.websocket("/live")
async def live(ws: WebSocket):
    await ws.accept()
    LIVE_CLIENTS.add(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        LIVE_CLIENTS.discard(ws)
