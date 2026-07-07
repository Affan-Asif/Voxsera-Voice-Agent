-- ============================================================
-- Voice Agent Platform — Supabase schema
-- Run this in: Supabase Dashboard -> SQL Editor -> New query
-- ============================================================

create extension if not exists "pgcrypto";

-- ------------------------------------------------------------
-- businesses: one row per registered SMB (tenant)
-- ------------------------------------------------------------
create table if not exists businesses (
    id                   uuid primary key default gen_random_uuid(),
    name                 text not null,
    industry             text,
    timezone             text not null default 'Asia/Kolkata',   -- IANA tz
    -- {"open": "09:00", "close": "18:00", "days": ["mon","tue","wed","thu","fri","sat"]}
    business_hours       jsonb not null default '{"open":"09:00","close":"18:00","days":["mon","tue","wed","thu","fri"]}',
    -- {"agent_name":"Maya","friendliness":8,"formality":5,"verbosity":3,"custom_context":"..."}
    persona              jsonb not null default '{}',
    voice_model          text not null default 'aura-2-thalia-en',
    twilio_number        text,                    -- E.164, assigned at onboarding
    google_refresh_token text,                    -- set after OAuth
    google_calendar_id   text default 'primary',
    google_sheet_id      text,                    -- spreadsheet ID for appointments
    created_at           timestamptz not null default now()
);

-- ------------------------------------------------------------
-- calls: one row per finished call (inbound + outbound)
-- ------------------------------------------------------------
create table if not exists calls (
    id            uuid primary key default gen_random_uuid(),
    business_id   uuid references businesses(id) on delete cascade,
    direction     text not null check (direction in ('inbound','outbound')),
    phone         text,               -- customer number
    call_sid      text,
    stream_sid    text,
    transcript    jsonb not null default '[]',   -- [{"role":"USER|AGENT","text":"...","ts":"..."}]
    sentiment     real default 0,                -- avg VADER compound over the call
    outcome       text,                          -- booked | info | reminded | no_answer | undecided
    turns         int default 0,
    duration_sec  real default 0,
    notes         text,
    started_at    timestamptz,
    ended_at      timestamptz,
    created_at    timestamptz not null default now()
);

create index if not exists idx_calls_business  on calls(business_id);
create index if not exists idx_calls_direction on calls(direction);
create index if not exists idx_calls_phone     on calls(phone);

-- ------------------------------------------------------------
-- owners: business-owner accounts (simple email+password auth)
-- ------------------------------------------------------------
create table if not exists owners (
    id            uuid primary key default gen_random_uuid(),
    email         text not null unique,
    password_hash text not null,          -- salt$sha256
    created_at    timestamptz not null default now()
);

-- v2 columns (safe to re-run)
alter table businesses add column if not exists owner_email      text;
alter table businesses add column if not exists inbound_sheet_id text;  -- auto-created inbound call log

-- Backend uses the service_role key, which bypasses RLS.
-- Enable RLS so the anon key can't read anything directly.
alter table businesses enable row level security;
alter table calls      enable row level security;
alter table owners     enable row level security;
