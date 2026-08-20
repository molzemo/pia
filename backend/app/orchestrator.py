"""
The orchestrator is the fix for the two bugs the product owner flagged:

  1. "Don't create a new agent every message." An agent is a singleton per
     (user, domain) — see repo.create_agent's `on conflict (user_id, domain)
     do update`. Every message first asks the LLM to classify intent
     against the list of the user's EXISTING agents; if a domain already
     has an agent, new information is PATCHed into its memory, never
     inserted as a second agent.

  2. "Don't silently reuse one-off details." For on-demand domains (taxi,
     flight) we distinguish durable preferences (which app to book
     through — asked once, remembered) from per-transaction slots
     (destination, travel date, pickup address) which are NEVER pulled
     from memory automatically. `ONE_OFF_SLOT_KEYS` below is the allow-list
     of fields that must come from the *current* message; if missing, we
     ask a clarifying question instead of guessing — this is what makes
     the taxi agent ask "home address or a new address?" on every booking.
"""
import json

from . import repo
from .connectors import CONNECTORS
from .llm import LLMConfig, complete_json

SUPPORTED_DOMAINS = ["grocery", "taxi", "flight", "shopping"]

# Fields that must always be re-confirmed for this specific transaction —
# never silently copied from agent memory even if a similar value exists.
ONE_OFF_SLOT_KEYS = {
    "taxi": ["destination", "address_choice", "pickup_address"],
    "flight": ["origin", "destination", "date"],
}

# Fields that are durable preferences worth remembering across messages.
PREFERENCE_KEYS = {
    "taxi": ["preferred_app", "home_address", "preferred_vehicle"],
    "flight": ["preferred_app", "budget_cap"],
    "grocery": ["preferred_app", "preferred_brands", "budget_cap", "items"],
    "shopping": ["preferred_app", "preferred_brands", "budget_cap"],
}

SYSTEM_PROMPT = """You are the intent-analysis brain of a Personal AI Operations Platform.
Users delegate everyday tasks (groceries, taxi rides, flights, shopping) to persistent
per-domain agents. You do NOT execute anything yourself — you only classify the user's
intent and extract structured slots. A separate deterministic system performs the actual
booking after your classification.

Currently supported domains: grocery, taxi, flight, shopping. Anything else (bills,
appointments, etc.) should be classified as domain "other" with intent "general_chat" and
a reply saying that agent type is not available yet in this demo.

CRITICAL RULES (this is a product requirement, not a suggestion):
1. NEVER propose creating a new agent for a domain that already appears in
   "existing_agents" below. If it already exists, the intent must be "update_memory",
   "one_off_task", "delete_memory", "stop_agent" or "general_chat" — never "create_agent".
2. "create_agent" is only correct the FIRST time a domain is mentioned for this user.
3. For domains "taxi" and "flight" (on-demand/transactional), a request like "book a taxi"
   or "find me a flight" is intent "one_off_task", NOT "create_agent" — even the first
   time. The underlying agent record is created automatically behind the scenes purely to
   hold durable preferences (which app to use, home address); do not describe this to the
   user as "I created an agent". Just help them get the task done.
4. For "taxi" and "flight", these fields must be supplied FRESH in the current message and
   must NEVER be filled in from memory/history, even if a similar value was used before:
   taxi -> destination, address_choice ("home" or "new"), and if address_choice is "new"
   then pickup_address or drop address text; flight -> origin, destination, date.
   If any required one-off field is missing, set intent "clarify" (not "one_off_task"),
   set action_ready false, list the missing fields in missing_slots, and write a reply
   that asks for exactly those fields. Always explicitly ask "your home address or a new
   address?" when address_choice is missing for a taxi booking.
5. Durable preferences (preferred_app/provider, preferred_vehicle, home_address,
   preferred_brands, budget_cap) SHOULD be reused from memory once known, and should be
   asked for (once) if missing before the first booking/order can proceed. Put newly
   stated preferences in memory_patch so they are remembered for next time.
6. For "grocery" and "shopping" (recurring domains), simple additions like "add milk to
   the list" or "change my budget to 4000" are "update_memory" against the existing
   agent — do not treat these as a new task needing approval unless the user is asking to
   actually place/re-place an order now.
7. Only set action_ready true when you have every required slot AND (for taxi/flight) the
   one-off fields were given in THIS message. When action_ready is true and the domain is
   one of grocery/taxi/flight/shopping, a cart will be generated and the user will be asked
   to approve it — you do not compute prices yourself.
8. Keep "reply" short, warm, and specific — it is shown directly to the user in a chat UI.
9. If the user volunteers a durable preference WHILE you're still missing other required
   fields (e.g. they say "use Uber" before you know the destination), still use intent
   "clarify", but put that preference in memory_patch so it's remembered immediately —
   you won't need to ask for it again on the next message.

Respond with ONLY a single JSON object, no prose outside it, matching this shape:
{
  "intent": "create_agent" | "update_memory" | "one_off_task" | "delete_memory" | "stop_agent" | "clarify" | "general_chat",
  "domain": "grocery" | "taxi" | "flight" | "shopping" | "other",
  "reasoning": "one short sentence, internal, not shown to user",
  "memory_patch": {"key": "value, or nested object/array"},
  "memory_delete": ["key1"],
  "schedule_patch": {},
  "permissions_patch": {},
  "one_off_slots": {"destination": "...", "address_choice": "home"},
  "missing_slots": ["address_choice"],
  "action_ready": true,
  "reply": "text shown to the user"
}
Omit keys you don't need rather than sending null. Use empty objects/arrays for "none".
"""


def _build_user_prompt(message: str, history: list[dict], existing_agents: list[dict]) -> str:
    agents_summary = []
    for a in existing_agents:
        memory = repo.get_memory(a["id"])
        agents_summary.append({
            "domain": a["domain"],
            "status": a["status"],
            "kind": a["kind"],
            "permissions": a["permissions"],
            "schedule": a["schedule"],
            "memory": memory,
        })
    history_lines = [f"{h['role']}: {h['content']}" for h in history[-8:]]
    return json.dumps({
        "existing_agents": agents_summary,
        "recent_conversation": history_lines,
        "current_message": message,
    }, default=str, indent=2)


def analyze(cfg: LLMConfig, message: str, history: list[dict], existing_agents: list[dict]) -> dict:
    user_prompt = _build_user_prompt(message, history, existing_agents)
    result = complete_json(cfg, SYSTEM_PROMPT, user_prompt)
    result.setdefault("intent", "general_chat")
    result.setdefault("domain", "other")
    result.setdefault("memory_patch", {})
    result.setdefault("memory_delete", [])
    result.setdefault("schedule_patch", {})
    result.setdefault("permissions_patch", {})
    result.setdefault("one_off_slots", {})
    result.setdefault("missing_slots", [])
    result.setdefault("action_ready", False)
    result.setdefault("reply", "Okay.")
    return result


def handle_message(user: dict, cfg: LLMConfig, message: str) -> dict:
    """Returns {reply, agent_action, approval, activity} for the /api/chat response."""
    history = repo.recent_conversation(user["id"])
    existing_agents = repo.list_agents(user["id"])
    repo.add_conversation(user["id"], "user", message)

    analysis = analyze(cfg, message, history, existing_agents)
    intent = analysis["intent"]
    domain = analysis["domain"]

    response = {
        "reply": analysis["reply"],
        "agent_action": None,   # 'created' | 'updated' | 'stopped' | None
        "approval": None,
        "activity": [],
        "domain": domain,
        "intent": intent,
    }

    if domain not in SUPPORTED_DOMAINS or intent == "general_chat":
        repo.add_conversation(user["id"], "assistant", analysis["reply"])
        return response

    agent = repo.get_agent(user["id"], domain)
    is_recurring = domain in repo.RECURRING_DOMAINS

    if intent == "stop_agent":
        if agent:
            repo.patch_agent(agent["id"], status="stopped")
            entry = repo.log_activity(user["id"], agent["id"], f"{repo.DOMAIN_LABELS[domain]} paused by user request.")
            response["activity"].append(entry)
            response["agent_action"] = "stopped"
        repo.add_conversation(user["id"], "assistant", analysis["reply"])
        return response

    # "clarify" (e.g. "which app should I use?") is folded in here too, but only
    # when the reply actually captured something worth remembering (a durable
    # preference volunteered mid-clarification, like "Uber" before the
    # destination is known) — a bare clarifying question with nothing new
    # learned yet must not spin up an agent on its own.
    has_something_to_remember = bool(
        analysis.get("memory_patch") or analysis.get("permissions_patch")
        or analysis.get("schedule_patch") or analysis.get("memory_delete")
    )
    if intent in ("create_agent", "update_memory", "one_off_task", "delete_memory") or (
        intent == "clarify" and has_something_to_remember
    ):
        created = False
        if not agent:
            kind = "recurring" if is_recurring else "on_demand"
            agent = repo.create_agent(
                user["id"], domain, kind,
                permissions=analysis.get("permissions_patch") or {},
                schedule=analysis.get("schedule_patch") or {},
            )
            created = True
            entry = repo.log_activity(
                user["id"], agent["id"],
                f"{repo.DOMAIN_LABELS[domain]} activated." if is_recurring else
                f"{repo.DOMAIN_LABELS[domain]} set up to remember your preferences.",
            )
            response["activity"].append(entry)
        else:
            if analysis.get("permissions_patch") or analysis.get("schedule_patch"):
                agent = repo.patch_agent(
                    agent["id"],
                    permissions_patch=analysis.get("permissions_patch"),
                    schedule_patch=analysis.get("schedule_patch"),
                )

        # Only durable preference keys are allowed to persist for on-demand
        # domains; one-off slots (destination, date, address_choice) never
        # get written into long-term memory.
        memory_patch = dict(analysis.get("memory_patch") or {})
        if domain in ONE_OFF_SLOT_KEYS:
            for k in ONE_OFF_SLOT_KEYS[domain]:
                memory_patch.pop(k, None)

        if memory_patch:
            repo.patch_memory(agent["id"], memory_patch)
            entry = repo.log_activity(
                user["id"], agent["id"],
                f"Remembered: {', '.join(memory_patch.keys())}.",
                meta={"memory_patch": memory_patch},
            )
            response["activity"].append(entry)

        if analysis.get("memory_delete"):
            repo.delete_memory_keys(agent["id"], analysis["memory_delete"])
            entry = repo.log_activity(
                user["id"], agent["id"], f"Forgot: {', '.join(analysis['memory_delete'])}.",
            )
            response["activity"].append(entry)

        response["agent_action"] = "created" if created else "updated"

        if intent == "one_off_task" and analysis.get("action_ready"):
            memory = repo.get_memory(agent["id"])
            slots = analysis.get("one_off_slots") or {}
            connector = CONNECTORS[domain]
            cart = connector.quote(memory, slots)
            amount = cart.total
            action_type = f"{domain}_booking" if domain in repo.ON_DEMAND_DOMAINS else f"{domain}_order"
            approval = repo.create_approval(
                user["id"], agent["id"], action_type,
                description=cart.title, cart={"items": cart.items, "notes": cart.notes, "currency": cart.currency, "slots": slots},
                amount=amount,
            )
            entry = repo.log_activity(
                user["id"], agent["id"],
                f"{cart.title}: ₹{amount:.0f} — awaiting your approval.",
                meta={"approval_id": str(approval["id"])},
            )
            response["activity"].append(entry)
            response["approval"] = _serialize_approval(approval)

        agent_final = repo.get_agent_by_id(agent["id"])
        response["agent"] = _serialize_agent(agent_final)

    repo.add_conversation(user["id"], "assistant", analysis["reply"])
    return response


def execute_approval(approval_id: str, decision: str, modified_amount: float | None = None) -> dict:
    approval = repo.get_approval(approval_id)
    if not approval:
        raise ValueError("Approval not found")
    agent = repo.get_agent_by_id(approval["agent_id"])
    connector = CONNECTORS.get(agent["domain"])

    if decision == "reject":
        approval = repo.decide_approval(approval_id, "rejected")
        entry = repo.log_activity(approval["user_id"], agent["id"], f"Payment rejected: {approval['description']}.")
        return {"approval": _serialize_approval(approval), "activity": [entry], "result": None}

    amount = modified_amount if modified_amount is not None else float(approval["amount"])
    status = "modified" if modified_amount is not None else "approved"
    approval = repo.decide_approval(approval_id, status, amount=amount)

    memory = repo.get_memory(agent["id"])
    slots = (approval["cart"] or {}).get("slots", {})
    from .connectors.base import Cart, PaymentRail
    cart = Cart(title=approval["description"], items=(approval["cart"] or {}).get("items", []), total=amount)
    result = connector.execute(memory, slots, cart)

    user_settings = repo.get_user_settings(approval["user_id"])
    rail = PaymentRail((user_settings or {}).get("payment_rail") or "simulated_upi")
    payment = rail.charge(amount, cart.currency, reference=str(approval["id"]))

    repo.decide_approval(approval_id, "completed", amount=amount)
    entries = [
        repo.log_activity(approval["user_id"], agent["id"], f"Payment approved: ₹{amount:.0f} via {payment['rail']}."),
        repo.log_activity(approval["user_id"], agent["id"], f"{approval['description']} completed. {result}"),
    ]
    return {"approval": _serialize_approval(repo.get_approval(approval_id)), "activity": entries, "result": result, "payment": payment}


def _serialize_agent(agent: dict) -> dict:
    return {
        "id": str(agent["id"]),
        "domain": agent["domain"],
        "name": agent["name"],
        "status": agent["status"],
        "kind": agent["kind"],
        "permissions": agent["permissions"],
        "schedule": agent["schedule"],
        "memory": repo.get_memory(agent["id"]),
    }


def _serialize_approval(approval: dict) -> dict:
    return {
        "id": str(approval["id"]),
        "agent_id": str(approval["agent_id"]),
        "action_type": approval["action_type"],
        "description": approval["description"],
        "cart": approval["cart"],
        "amount": float(approval["amount"]) if approval["amount"] is not None else None,
        "status": approval["status"],
    }
