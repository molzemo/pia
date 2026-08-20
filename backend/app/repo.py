"""
Repository layer: all SQL lives here so orchestrator.py and the routers
stay focused on behaviour, not queries.
"""
import json

from .db import conn, q, q_one

DOMAIN_LABELS = {
    "grocery": "Grocery Agent",
    "taxi": "Taxi Agent",
    "flight": "Flight Agent",
    "shopping": "Shopping Agent",
}
RECURRING_DOMAINS = {"grocery", "shopping"}
ON_DEMAND_DOMAINS = {"taxi", "flight"}


def get_or_create_user(email: str) -> dict:
    with conn() as c:
        user = q_one(c, "select * from users where email = :email", email=email)
        if user:
            return user
        return q_one(
            c,
            "insert into users (email) values (:email) returning *",
            email=email,
        )


def get_user_settings(user_id: str) -> dict | None:
    with conn() as c:
        return q_one(c, "select * from user_settings where user_id = :uid", uid=user_id)


def upsert_user_settings(user_id: str, provider: str, model: str, encrypted_api_key: str | None, payment_rail: str) -> dict:
    with conn() as c:
        existing = q_one(c, "select * from user_settings where user_id = :uid", uid=user_id)
        if existing:
            key_sql = "encrypted_api_key = :key," if encrypted_api_key is not None else ""
            return q_one(
                c,
                f"""
                update user_settings set
                    llm_provider = :provider,
                    llm_model = :model,
                    {key_sql}
                    payment_rail = :rail,
                    updated_at = now()
                where user_id = :uid
                returning *
                """,
                uid=user_id, provider=provider, model=model, key=encrypted_api_key, rail=payment_rail,
            )
        return q_one(
            c,
            """
            insert into user_settings (user_id, llm_provider, llm_model, encrypted_api_key, payment_rail)
            values (:uid, :provider, :model, :key, :rail)
            returning *
            """,
            uid=user_id, provider=provider, model=model, key=encrypted_api_key, rail=payment_rail,
        )


def list_agents(user_id: str) -> list[dict]:
    with conn() as c:
        return q(c, "select * from agents where user_id = :uid order by created_at", uid=user_id)


def get_agent(user_id: str, domain: str) -> dict | None:
    with conn() as c:
        return q_one(c, "select * from agents where user_id = :uid and domain = :domain", uid=user_id, domain=domain)


def get_agent_by_id(agent_id: str) -> dict | None:
    with conn() as c:
        return q_one(c, "select * from agents where id = :id", id=agent_id)


def create_agent(user_id: str, domain: str, kind: str, permissions: dict, schedule: dict) -> dict:
    with conn() as c:
        return q_one(
            c,
            """
            insert into agents (user_id, domain, name, kind, permissions, schedule)
            values (:uid, :domain, :name, :kind, cast(:perm as jsonb), cast(:sched as jsonb))
            on conflict (user_id, domain) do update set updated_at = now()
            returning *
            """,
            uid=user_id, domain=domain, name=DOMAIN_LABELS.get(domain, domain.title() + " Agent"),
            kind=kind, perm=json.dumps(permissions), sched=json.dumps(schedule),
        )


def patch_agent(agent_id: str, permissions_patch: dict | None = None, schedule_patch: dict | None = None, status: str | None = None) -> dict:
    with conn() as c:
        agent = q_one(c, "select * from agents where id = :id", id=agent_id)
        if not agent:
            return None
        permissions = {**(agent["permissions"] or {}), **(permissions_patch or {})}
        schedule = {**(agent["schedule"] or {}), **(schedule_patch or {})}
        new_status = status or agent["status"]
        return q_one(
            c,
            """
            update agents set permissions = cast(:perm as jsonb), schedule = cast(:sched as jsonb),
                   status = :status, updated_at = now()
            where id = :id
            returning *
            """,
            id=agent_id, perm=json.dumps(permissions), sched=json.dumps(schedule), status=new_status,
        )


def get_memory(agent_id: str) -> dict:
    with conn() as c:
        rows = q(c, "select key, value from agent_memory where agent_id = :aid", aid=agent_id)
        return {r["key"]: r["value"] for r in rows}


def list_memory_rows(agent_id: str) -> list[dict]:
    with conn() as c:
        return q(c, "select * from agent_memory where agent_id = :aid order by updated_at desc", aid=agent_id)


def patch_memory(agent_id: str, patch: dict) -> None:
    if not patch:
        return
    with conn() as c:
        for key, value in patch.items():
            q(
                c,
                """
                insert into agent_memory (agent_id, key, value)
                values (:aid, :key, cast(:value as jsonb))
                on conflict (agent_id, key) do update set value = cast(:value as jsonb), updated_at = now()
                """,
                aid=agent_id, key=key, value=json.dumps(value),
            )


def delete_memory_keys(agent_id: str, keys: list[str]) -> None:
    if not keys:
        return
    with conn() as c:
        for key in keys:
            q(c, "delete from agent_memory where agent_id = :aid and key = :key", aid=agent_id, key=key)


def delete_memory_key(agent_id: str, key: str) -> None:
    delete_memory_keys(agent_id, [key])


def delete_agent(agent_id: str) -> None:
    with conn() as c:
        q(c, "delete from agents where id = :id", id=agent_id)


def log_activity(user_id: str, agent_id: str | None, message: str, meta: dict | None = None) -> dict:
    with conn() as c:
        return q_one(
            c,
            """
            insert into activity_log (user_id, agent_id, message, meta)
            values (:uid, :aid, :msg, cast(:meta as jsonb))
            returning *
            """,
            uid=user_id, aid=agent_id, msg=message, meta=json.dumps(meta or {}),
        )


def list_activity(user_id: str, agent_id: str | None = None, limit: int = 100) -> list[dict]:
    with conn() as c:
        if agent_id:
            return q(
                c,
                "select * from activity_log where user_id = :uid and agent_id = :aid order by created_at desc limit :lim",
                uid=user_id, aid=agent_id, lim=limit,
            )
        return q(
            c,
            "select * from activity_log where user_id = :uid order by created_at desc limit :lim",
            uid=user_id, lim=limit,
        )


def create_approval(user_id: str, agent_id: str, action_type: str, description: str, cart: dict, amount: float) -> dict:
    with conn() as c:
        return q_one(
            c,
            """
            insert into approvals (user_id, agent_id, action_type, description, cart, amount)
            values (:uid, :aid, :atype, :desc, cast(:cart as jsonb), :amount)
            returning *
            """,
            uid=user_id, aid=agent_id, atype=action_type, desc=description, cart=json.dumps(cart), amount=amount,
        )


def get_approval(approval_id: str) -> dict | None:
    with conn() as c:
        return q_one(c, "select * from approvals where id = :id", id=approval_id)


def list_approvals(user_id: str, status: str | None = None) -> list[dict]:
    with conn() as c:
        if status:
            return q(c, "select * from approvals where user_id = :uid and status = :status order by created_at desc", uid=user_id, status=status)
        return q(c, "select * from approvals where user_id = :uid order by created_at desc", uid=user_id)


def decide_approval(approval_id: str, status: str, amount: float | None = None) -> dict:
    with conn() as c:
        amount_sql = "amount = :amount," if amount is not None else ""
        return q_one(
            c,
            f"""
            update approvals set status = :status, {amount_sql} decided_at = now()
            where id = :id
            returning *
            """,
            id=approval_id, status=status, amount=amount,
        )


def add_conversation(user_id: str, role: str, content: str) -> None:
    with conn() as c:
        q(c, "insert into conversations (user_id, role, content) values (:uid, :role, :content)", uid=user_id, role=role, content=content)


def recent_conversation(user_id: str, limit: int = 12) -> list[dict]:
    with conn() as c:
        rows = q(
            c,
            "select role, content from conversations where user_id = :uid order by created_at desc limit :lim",
            uid=user_id, lim=limit,
        )
        return list(reversed(rows))
