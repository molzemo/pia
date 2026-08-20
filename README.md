# Personal AI Operations Platform

> Ask once. Delegate permanently. Stay in control.

A consumer-first platform that turns a chat interface into an execution layer for
everyday life. Users state a goal in plain language; the platform's orchestrator
decides whether that goal belongs to an **existing** persistent agent or needs a
**new** one, updates that agent's memory/schedule/permissions, and — for anything
that spends money — always stops for your explicit approval before paying.

This repo ships four working agent domains end-to-end: **Grocery**, **Taxi**,
**Flight**, **Shopping**.

## Architecture

```
React (Vite) frontend  ──HTTP──▶  FastAPI backend  ──SQL──▶  Postgres (Supabase)
   chat / agents /                 orchestrator                users, agents,
   approvals / settings            + connectors                agent_memory,
                                    + LLM (BYOK)                activity_log,
                                                                 approvals,
                                                                 conversations
```

- **Frontend** — `frontend/`, React 18 + Vite, plain CSS (white/blue theme, no dark mode).
- **Backend** — `backend/`, FastAPI (Python), SQLAlchemy Core over raw SQL.
- **Database** — Postgres via Supabase, schema in `backend/schema.sql`.
- **LLM** — BYOK (bring your own key). Each user picks a provider (Anthropic Claude
  or OpenAI) + model + API key in Settings; the key is Fernet-encrypted at rest and
  never sent back to the browser.
- **Connectors** — `backend/app/connectors/`. Each domain (grocery/taxi/flight/shopping)
  implements the same `search → quote → execute` interface against **simulated**
  providers (no live Uber/Amadeus/BigBasket credentials exist for this demo), written
  so a real provider SDK is a drop-in replacement — nothing else in the platform
  changes when a real connector replaces a simulated one.
- **Payments** — `connectors/base.py: PaymentRail`. The platform never asks for or
  stores a UPI PIN, card number or OTP. It hands the payment rail a final approved
  amount + reference; authentication happens inside the rail's own regulated flow.
  This demo ships a simulated rail so you can see the full approve → pay → confirm
  loop; swapping in a real UPI AutoPay / card network integration only touches this
  one class.

## The two architecture bugs this build fixes

**1. "Don't create a new agent every message."**
`agents` has a `unique (user_id, domain)` constraint, and every write goes through
`repo.create_agent(...)` which is an `ON CONFLICT ... DO UPDATE`. Before touching the
database, every chat message is run through a single LLM call
(`backend/app/orchestrator.py: analyze`) whose system prompt is given the user's
**existing agents** and is explicitly instructed: never propose `create_agent` for a
domain that already appears there — classify it as `update_memory` /
`one_off_task` / `delete_memory` / `general_chat` instead. "Add milk to the list" on
an existing Grocery Agent patches `agent_memory`; it never inserts a second grocery
agent. This is covered by an integration test (see below) that asserts exactly one
row exists per domain after repeated messages.

**2. "Don't silently reuse one-off details like an address."**
Memory is split into two categories:
- **Durable preferences** (`preferred_app`, `home_address`, `preferred_vehicle`,
  `budget_cap`, `preferred_brands`, …) — asked once, then remembered and reused.
- **One-off slots** (`ONE_OFF_SLOT_KEYS` in `orchestrator.py`: taxi →
  `destination`/`address_choice`/`pickup_address`; flight → `origin`/`destination`/`date`)
  — these are *stripped out of every memory patch* before it's written to the
  database, so they can never leak into long-term memory. The system prompt requires
  the model to ask "your home address or a new address?" and the concrete
  destination/date fresh on every booking; if they're missing, the response is a
  clarifying question (`intent: "clarify"`) instead of a booking.

## Repository layout

```
backend/
  app/
    main.py            FastAPI app + routers
    config.py           env-driven settings
    db.py                SQLAlchemy engine + query helpers
    security.py          Fernet encryption for user API keys
    llm.py                Anthropic/OpenAI provider abstraction
    orchestrator.py      intent analysis + agent/memory upsert (the core logic)
    repo.py               all SQL lives here
    connectors/           grocery.py, taxi.py, flight.py, shopping.py, base.py
    routers/               chat.py, agents.py, approvals.py, settings.py, activity.py, conversation.py
  schema.sql             Postgres schema (apply once to Supabase)
  requirements.txt
  Procfile                for Railway/Render
frontend/
  src/
    App.jsx               top-level layout + chat loop
    api.js                  fetch wrapper
    theme.css               white/blue design tokens
    components/
      AgentSidebar.jsx, AgentDetail.jsx, ApprovalCard.jsx, SettingsModal.jsx
```

## Running locally

### 1. Database
Create a free [Supabase](https://supabase.com) project (or use any Postgres 14+),
then run `backend/schema.sql` against it — either paste it into the Supabase SQL
editor, or:
```bash
psql "$DATABASE_URL" -f backend/schema.sql
```

### 2. Backend
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in DATABASE_URL at minimum
uvicorn app.main:app --reload --port 8000
```

### 3. Frontend
```bash
cd frontend
npm install
cp .env.example .env   # VITE_API_BASE_URL=http://localhost:8000
npm run dev
```

Open http://localhost:5173, sign in with any email (demo auth, no password), open
**Settings** and paste your Anthropic or OpenAI API key, then try:

- *"Every Sunday plan our groceries for the week, keep the budget below ₹3,000 and ask me before ordering"*
- *"Add paneer and coffee to the list"* → watch the Grocery Agent's memory update, not duplicate.
- *"Book me a taxi to the airport"* → it will ask which app + home or new address, every time.
- *"Find a flight to Mumbai under ₹15,000"*

Every reply that spends money renders an **approval card** with an itemized
description — nothing is ever paid without an explicit Approve click.

## Testing

The orchestration logic (agent upsert, one-off slot isolation, approvals, connector
execution, simulated payment) is covered by a real-Postgres integration test with the
LLM call stubbed to canned analyses, so it runs deterministically without spending
API tokens:
```bash
createdb pia_test  # or: psql -c "CREATE DATABASE pia_test;"
psql "postgresql://postgres:postgres@localhost:5432/pia_test" -f backend/schema.sql
DATABASE_URL="postgresql://postgres:postgres@localhost:5432/pia_test" \
  python backend_tests/test_orchestrator.py
```
It asserts: exactly one agent row per `(user, domain)` after repeated messages,
one-off slots (destination/address_choice) never leak into `agent_memory`, and a
second taxi booking reuses the existing agent while still requiring a fresh address
choice.

## Deployment

- **Database**: Supabase (already provisioned for this project).
- **Backend**: Railway/Render, root directory `backend/`, start command from
  `Procfile` (`uvicorn app.main:app --host 0.0.0.0 --port $PORT`). Required env vars:
  `DATABASE_URL`, `FRONTEND_ORIGIN`, `APP_ENCRYPTION_KEY`.
- **Frontend**: Railway/Render static/Node service, root directory `frontend/`,
  build `npm run build`, serve `dist/`. Required env var: `VITE_API_BASE_URL`
  pointing at the backend's public URL.

## Trust & safety notes

- No agent can spend beyond `permissions.budget_cap`; anything with a cost always
  produces a pending `approvals` row and waits for a human decision.
- Every action an agent takes is written to `activity_log` and visible in the UI's
  per-agent timeline, in plain language.
- Users can inspect, edit, or delete any memory key from the Agent detail panel at
  any time; deleting an agent cascades its memory and history.
- API keys are Fernet-encrypted at rest (`APP_ENCRYPTION_KEY`); the API only ever
  returns a masked preview (`sk-a••••••••7890`), never the plaintext key, after saving.
- RLS is enabled on every table with no policies, so the Supabase `anon`/`authenticated`
  client roles have zero access even if that key were ever exposed — the backend
  reaches Postgres through its own direct connection instead.
