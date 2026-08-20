"""
Integration test against a real Postgres database, with the LLM call stubbed
out by canned analyses (so we test the deterministic orchestration logic —
agent upsert, memory patch, one-off slot handling, approvals, execution —
without spending real API tokens).

Usage:
    createdb pia_test   # or: psql -c "CREATE DATABASE pia_test;"
    psql "$DATABASE_URL" -f backend/schema.sql
    DATABASE_URL="postgresql://postgres:postgres@localhost:5432/pia_test" \
        python backend_tests/test_orchestrator.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

if "DATABASE_URL" not in os.environ:
    raise SystemExit("Set DATABASE_URL to a scratch Postgres database before running this test.")

from app import repo, orchestrator  # noqa: E402
from app.llm import LLMConfig  # noqa: E402

# ---- stub the LLM analysis step ----
CANNED = []


def fake_analyze(cfg, message, history, existing_agents):
    return CANNED.pop(0)


orchestrator.analyze = fake_analyze

cfg = LLMConfig(provider="anthropic", model="claude-sonnet-5", api_key="test-key")
user = repo.get_or_create_user("demo@example.com")

print("=== 1) First grocery message -> should CREATE agent ===")
CANNED.append({
    "intent": "create_agent", "domain": "grocery",
    "memory_patch": {"budget_cap": 3000, "items": ["milk", "eggs", "bread"]},
    "memory_delete": [], "schedule_patch": {"recurrence": "weekly", "day": "Sunday"},
    "permissions_patch": {"budget_cap": 3000, "approval_required": True},
    "one_off_slots": {}, "missing_slots": [], "action_ready": False,
    "reply": "Got it — I'll plan groceries every Sunday, budget capped at ₹3,000.",
})
r1 = orchestrator.handle_message(user, cfg, "Every Sunday plan our groceries, budget below 3000, ask before ordering")
print(r1["agent_action"], "->", r1["reply"])
assert r1["agent_action"] == "created"

print("\n=== 2) Second grocery message (add item) -> should UPDATE, not duplicate ===")
CANNED.append({
    "intent": "update_memory", "domain": "grocery",
    "memory_patch": {"items": ["milk", "eggs", "bread", "paneer"]},
    "memory_delete": [], "schedule_patch": {}, "permissions_patch": {},
    "one_off_slots": {}, "missing_slots": [], "action_ready": False,
    "reply": "Added paneer to your weekly grocery list.",
})
r2 = orchestrator.handle_message(user, cfg, "Add paneer to the list")
print(r2["agent_action"], "->", r2["reply"])
assert r2["agent_action"] == "updated"

agents = repo.list_agents(user["id"])
grocery_agents = [a for a in agents if a["domain"] == "grocery"]
print(f"\nGrocery agents in DB: {len(grocery_agents)} (must be exactly 1)")
assert len(grocery_agents) == 1, "BUG: duplicate agent created!"

print("\n=== 3) First taxi message with no preferences -> should CLARIFY, not book ===")
CANNED.append({
    "intent": "clarify", "domain": "taxi",
    "memory_patch": {}, "memory_delete": [], "schedule_patch": {}, "permissions_patch": {},
    "one_off_slots": {}, "missing_slots": ["preferred_app", "destination", "address_choice"],
    "action_ready": False,
    "reply": "Which app should I book through (Uber/Ola/Rapido), and where are you headed — your home address or a new address?",
})
r3 = orchestrator.handle_message(user, cfg, "Book me a taxi")
print(r3["agent_action"], "->", r3["reply"])
assert r3["approval"] is None, "BUG: booked without required info!"

print("\n=== 4) Taxi message with full info -> should ask home vs new address explicitly, then quote ===")
CANNED.append({
    "intent": "one_off_task", "domain": "taxi",
    "memory_patch": {"preferred_app": "Uber", "home_address": "12 MG Road, Bengaluru"},
    "memory_delete": [], "schedule_patch": {}, "permissions_patch": {},
    "one_off_slots": {"destination": "Kempegowda Airport", "address_choice": "home", "pickup_address": "12 MG Road, Bengaluru"},
    "missing_slots": [], "action_ready": True,
    "reply": "Booking a Uber ride from your home address to Kempegowda Airport.",
})
r4 = orchestrator.handle_message(user, cfg, "Uber, from my home address to the airport")
print(r4["agent_action"], "->", r4["reply"])
print("Approval created:", r4["approval"])
assert r4["approval"] is not None
approval_id = r4["approval"]["id"]

taxi_agents = [a for a in repo.list_agents(user["id"]) if a["domain"] == "taxi"]
assert len(taxi_agents) == 1
taxi_memory = repo.get_memory(taxi_agents[0]["id"])
print("Taxi agent memory (should hold ONLY durable prefs, no destination):", taxi_memory)
assert "destination" not in taxi_memory, "BUG: one-off destination leaked into durable memory!"
assert "address_choice" not in taxi_memory

print("\n=== 5) Approve payment -> should execute via connector + simulated payment rail ===")
result = orchestrator.execute_approval(approval_id, "approve")
print("Approval status:", result["approval"]["status"])
print("Execution result:", result["result"])
print("Payment:", result["payment"])
assert result["approval"]["status"] == "completed"

print("\n=== 6) Second taxi booking -> the SAME agent must be reused, no auto-reuse of destination ===")
CANNED.append({
    "intent": "one_off_task", "domain": "taxi",
    "memory_patch": {}, "memory_delete": [], "schedule_patch": {}, "permissions_patch": {},
    "one_off_slots": {"destination": "MG Road Mall", "address_choice": "new", "pickup_address": "221B Residency Road"},
    "missing_slots": [], "action_ready": True,
    "reply": "Booking your Uber from 221B Residency Road to MG Road Mall.",
})
r6 = orchestrator.handle_message(user, cfg, "Book another taxi, new pickup address 221B Residency Road, going to MG Road Mall")
print(r6["agent_action"], "->", r6["reply"])
assert r6["agent_action"] == "updated", "BUG: should reuse the same taxi agent, not create a new one"
taxi_agents2 = [a for a in repo.list_agents(user["id"]) if a["domain"] == "taxi"]
assert len(taxi_agents2) == 1, "BUG: duplicate taxi agent created on second booking!"

print("\nAll orchestrator invariants hold.")
