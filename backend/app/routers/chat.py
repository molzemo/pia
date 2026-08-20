from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .. import repo
from ..llm import LLMError, resolve_config
from ..orchestrator import handle_message
from ..security import decrypt_api_key

router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatRequest(BaseModel):
    user_email: str
    message: str


@router.post("")
def chat(req: ChatRequest):
    user = repo.get_or_create_user(req.user_email)
    settings_row = repo.get_user_settings(user["id"])

    provider = settings_row["llm_provider"] if settings_row else None
    model = settings_row["llm_model"] if settings_row else None
    api_key = None
    if settings_row and settings_row.get("encrypted_api_key"):
        api_key = decrypt_api_key(settings_row["encrypted_api_key"])

    try:
        cfg = resolve_config(provider, model, api_key)
    except LLMError as e:
        raise HTTPException(status_code=428, detail=str(e)) from e

    try:
        result = handle_message(user, cfg, req.message)
    except LLMError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e

    return result
