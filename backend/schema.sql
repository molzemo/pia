-- Personal AI Operations Platform — core schema
-- Applied to a Supabase Postgres project. Safe to re-run (IF NOT EXISTS everywhere).

create extension if not exists "pgcrypto";

-- One row per human user of the platform.
create table if not exists users (
    id uuid primary key default gen_random_uuid(),
    email text unique not null,
    display_name text,
    created_at timestamptz not null default now()
);

-- Per-user LLM + payment-rail configuration. API keys are stored
-- Fernet-encrypted (never plaintext, never shipped to the frontend).
create table if not exists user_settings (
    user_id uuid primary key references users(id) on delete cascade,
    llm_provider text not null default 'anthropic',   -- 'anthropic' | 'openai'
    llm_model text not null default 'claude-sonnet-5',
    encrypted_api_key text,                            -- null => platform default key (if any) is used
    payment_rail text not null default 'simulated_upi', -- pluggable payment rail identifier
    updated_at timestamptz not null default now()
);

-- One agent per (user, domain). This is the fix for "don't spawn a new
-- agent every message": the orchestrator upserts on (user_id, domain).
create table if not exists agents (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references users(id) on delete cascade,
    domain text not null,               -- 'grocery' | 'taxi' | 'flight' | 'shopping' | ...
    name text not null,                 -- human label, e.g. "Grocery Agent"
    status text not null default 'active', -- 'active' | 'paused' | 'stopped'
    kind text not null default 'recurring', -- 'recurring' (has schedule) | 'on_demand' (one-off tasks)
    permissions jsonb not null default '{}'::jsonb,   -- spending limits, approval thresholds, etc.
    schedule jsonb not null default '{}'::jsonb,      -- cron-like recurrence, e.g. weekly Sunday
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    unique (user_id, domain)
);

-- Key/value memory store per agent. The orchestrator PATCHes keys in place
-- instead of creating duplicate rows/agents when the user adds information.
create table if not exists agent_memory (
    id uuid primary key default gen_random_uuid(),
    agent_id uuid not null references agents(id) on delete cascade,
    key text not null,                  -- e.g. 'preferred_brands', 'budget_cap', 'preferred_app'
    value jsonb not null,
    updated_at timestamptz not null default now(),
    unique (agent_id, key)
);

-- Every agent action, visible in the activity timeline.
create table if not exists activity_log (
    id uuid primary key default gen_random_uuid(),
    agent_id uuid references agents(id) on delete cascade,
    user_id uuid not null references users(id) on delete cascade,
    message text not null,
    meta jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now()
);

-- Pending / decided human-approval actions (cart, payment, appointment...).
create table if not exists approvals (
    id uuid primary key default gen_random_uuid(),
    agent_id uuid not null references agents(id) on delete cascade,
    user_id uuid not null references users(id) on delete cascade,
    action_type text not null,          -- 'grocery_order' | 'taxi_booking' | 'flight_booking' | 'shopping_order'
    description text not null,
    cart jsonb not null default '{}'::jsonb,
    amount numeric(12,2),
    status text not null default 'pending', -- 'pending' | 'approved' | 'rejected' | 'modified' | 'completed'
    created_at timestamptz not null default now(),
    decided_at timestamptz
);

-- Full conversation transcript, used to give the LLM short-term context.
create table if not exists conversations (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references users(id) on delete cascade,
    role text not null,                 -- 'user' | 'assistant'
    content text not null,
    created_at timestamptz not null default now()
);

create index if not exists idx_agent_memory_agent on agent_memory(agent_id);
create index if not exists idx_activity_log_user on activity_log(user_id, created_at desc);
create index if not exists idx_approvals_user_status on approvals(user_id, status);
create index if not exists idx_conversations_user on conversations(user_id, created_at);
