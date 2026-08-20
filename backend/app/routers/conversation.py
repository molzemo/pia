from fastapi import APIRouter

from .. import repo

router = APIRouter(prefix="/api/conversation", tags=["conversation"])


@router.get("")
def get_conversation(user_email: str, limit: int = 50):
    user = repo.get_or_create_user(user_email)
    rows = repo.recent_conversation(user["id"], limit=limit)
    return rows
