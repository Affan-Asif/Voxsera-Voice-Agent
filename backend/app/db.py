"""Supabase persistence layer. supabase-py is sync, so every call is
wrapped in asyncio.to_thread from async code."""
import asyncio
from functools import lru_cache

from supabase import create_client, Client

from . import config


@lru_cache(maxsize=1)
def sb() -> Client:
    if not (config.SUPABASE_URL and config.SUPABASE_SERVICE_KEY):
        raise RuntimeError("SUPABASE_URL / SUPABASE_SERVICE_KEY not set in .env")
    return create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)


# ---------------- businesses ----------------

async def create_business(row: dict) -> dict:
    def _q():
        return sb().table("businesses").insert(row).execute().data[0]
    return await asyncio.to_thread(_q)


async def update_business(business_id: str, patch: dict) -> dict:
    def _q():
        return sb().table("businesses").update(patch).eq("id", business_id).execute().data[0]
    return await asyncio.to_thread(_q)


async def get_business(business_id: str) -> dict | None:
    def _q():
        data = sb().table("businesses").select("*").eq("id", business_id).limit(1).execute().data
        return data[0] if data else None
    return await asyncio.to_thread(_q)


async def get_business_by_number(twilio_number: str) -> dict | None:
    def _q():
        data = (sb().table("businesses").select("*")
                .eq("twilio_number", twilio_number)
                .order("created_at", desc=True).limit(1).execute().data)
        if data:
            return data[0]
        # single-number MVP fallback: latest registered business
        data = (sb().table("businesses").select("*")
                .order("created_at", desc=True).limit(1).execute().data)
        return data[0] if data else None
    return await asyncio.to_thread(_q)


async def list_businesses() -> list[dict]:
    def _q():
        return sb().table("businesses").select("*").order("created_at", desc=True).execute().data
    return await asyncio.to_thread(_q)


# ---------------- owners (auth) ----------------

async def create_owner(email: str, password_hash: str) -> dict:
    def _q():
        return sb().table("owners").insert(
            {"email": email, "password_hash": password_hash}).execute().data[0]
    return await asyncio.to_thread(_q)


async def get_owner(email: str) -> dict | None:
    def _q():
        data = (sb().table("owners").select("*")
                .eq("email", email).limit(1).execute().data)
        return data[0] if data else None
    return await asyncio.to_thread(_q)


async def get_business_by_owner(email: str) -> dict | None:
    def _q():
        data = (sb().table("businesses").select("*")
                .eq("owner_email", email)
                .order("created_at", desc=True).limit(1).execute().data)
        return data[0] if data else None
    return await asyncio.to_thread(_q)


# ---------------- calls ----------------

async def save_call(row: dict) -> dict:
    def _q():
        return sb().table("calls").insert(row).execute().data[0]
    return await asyncio.to_thread(_q)


async def list_calls(business_id: str | None = None,
                     direction: str | None = None,
                     limit: int = 100,
                     owner_email: str | None = None) -> list[dict]:
    def _q():
        biz_ids = None
        if owner_email:
            rows = (sb().table("businesses").select("id")
                    .eq("owner_email", owner_email).execute().data)
            biz_ids = [r["id"] for r in rows]
            if not biz_ids:
                return []
        q = sb().table("calls").select("*").order("created_at", desc=True).limit(limit)
        if biz_ids is not None:
            q = q.in_("business_id", biz_ids)
        elif business_id:
            q = q.eq("business_id", business_id)
        if direction:
            q = q.eq("direction", direction)
        return q.execute().data
    return await asyncio.to_thread(_q)
