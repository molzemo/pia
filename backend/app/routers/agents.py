from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .. import repo

router = APIRouter(prefix="/api/agents", tags=["agents"])


def _serialize_agent(agent: dict) -> dict:
    return {
        "id": str(agent["id"]),
        "domain": agent["domain"],
        "name": agent["name"],
        "status": agent["status"],
        "kind": agent["kind"],
        "permissions": agent["permissions"],
        "schedule": agent["schedule"],
        "created_at": agent["created_at"].isoformat() if agent["created_at"] else None,
    }


@router.get("")
def list_agents(user_email: str):
    user = repo.get_or_create_user(user_email)
    agents = repo.list_agents(user["id"])
    return [_serialize_agent(a) for a in agents]


@router.get("/{agent_id}/memory")
def get_memory(agent_id: str):
    rows = repo.list_memory_rows(agent_id)
    return [
        {"key": r["key"], "value": r["value"], "updated_at": r["updated_at"].isoformat()}
        for r in rows
    ]


class MemoryUpsert(BaseModel):
    value: dict | list | str | float | int | bool | None


@router.put("/{agent_id}/memory/{key}")
def upsert_memory(agent_id: str, key: str, body: MemoryUpsert):
    repo.patch_memory(agent_id, {key: body.value})
    return {"ok": True}


@router.delete("/{agent_id}/memory/{key}")
def delete_memory(agent_id: str, key: str):
    repo.delete_memory_key(agent_id, key)
    return {"ok": True}


@router.get("/{agent_id}/activity")
def agent_activity(agent_id: str):
    agent = repo.get_agent_by_id(agent_id)
    if not agent:
        raise HTTPException(404, "Agent not found")
    rows = repo.list_activity(agent["user_id"], agent_id=agent_id)
    return [
        {"id": str(r["id"]), "message": r["message"], "meta": r["meta"], "created_at": r["created_at"].isoformat()}
        for r in rows
    ]


class StatusUpdate(BaseModel):
    status: str


@router.patch("/{agent_id}/status")
def update_status(agent_id: str, body: StatusUpdate):
    agent = repo.patch_agent(agent_id, status=body.status)
    if not agent:
        raise HTTPException(404, "Agent not found")
    return _serialize_agent(agent)


@router.delete("/{agent_id}")
def remove_agent(agent_id: str):
    repo.delete_agent(agent_id)
    return {"ok": True}
