"""Live event fan-out: pushes transcript / state / call events to every
dashboard client connected on /live."""
import json
from datetime import datetime, timezone

from fastapi import WebSocket

LIVE_CLIENTS: set[WebSocket] = set()


async def live_broadcast(event: dict):
    event.setdefault("ts", datetime.now(timezone.utc).isoformat())
    msg = json.dumps(event, ensure_ascii=False)
    dead = []
    for ws in list(LIVE_CLIENTS):
        try:
            await ws.send_text(msg)
        except Exception:
            dead.append(ws)
    for ws in dead:
        LIVE_CLIENTS.discard(ws)
