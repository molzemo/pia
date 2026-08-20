from fastapi import APIRouter

from .. import repo

router = APIRouter(prefix="/api/activity", tags=["activity"])


@router.get("")
def list_activity(user_email: str, limit: int = 100):
    user = repo.get_or_create_user(user_email)
    rows = repo.list_activity(user["id"], limit=limit)
    return [
        {
            "id": str(r["id"]),
            "agent_id": str(r["agent_id"]) if r["agent_id"] else None,
            "message": r["message"],
            "meta": r["meta"],
            "created_at": r["created_at"].isoformat(),
        }
        for r in rows
    ]
