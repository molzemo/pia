from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .. import repo
from ..orchestrator import execute_approval, _serialize_approval

router = APIRouter(prefix="/api/approvals", tags=["approvals"])


@router.get("")
def list_approvals(user_email: str, status: str | None = None):
    user = repo.get_or_create_user(user_email)
    rows = repo.list_approvals(user["id"], status=status)
    return [_serialize_approval(r) for r in rows]


class Decision(BaseModel):
    decision: str  # 'approve' | 'reject' | 'modify'
    modified_amount: float | None = None


@router.post("/{approval_id}/decision")
def decide(approval_id: str, body: Decision):
    if body.decision not in ("approve", "reject", "modify"):
        raise HTTPException(400, "decision must be approve, reject or modify")
    try:
        result = execute_approval(
            approval_id,
            "reject" if body.decision == "reject" else "approve",
            modified_amount=body.modified_amount if body.decision == "modify" else None,
        )
    except ValueError as e:
        raise HTTPException(404, str(e)) from e
    return result
