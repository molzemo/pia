from fastapi import APIRouter
from pydantic import BaseModel

from .. import repo
from ..llm import PROVIDERS
from ..security import decrypt_api_key, encrypt_api_key, mask_key

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("/providers")
def providers():
    return PROVIDERS


@router.get("")
def get_settings(user_email: str):
    user = repo.get_or_create_user(user_email)
    row = repo.get_user_settings(user["id"])
    if not row:
        return {"llm_provider": "anthropic", "llm_model": "claude-sonnet-5", "api_key_masked": None, "payment_rail": "simulated_upi", "configured": False}
    masked = None
    if row.get("encrypted_api_key"):
        masked = mask_key(decrypt_api_key(row["encrypted_api_key"]))
    return {
        "llm_provider": row["llm_provider"],
        "llm_model": row["llm_model"],
        "api_key_masked": masked,
        "payment_rail": row["payment_rail"],
        "configured": bool(masked),
    }


class SettingsUpdate(BaseModel):
    user_email: str
    llm_provider: str
    llm_model: str
    api_key: str | None = None  # omit to keep existing key
    payment_rail: str = "simulated_upi"


@router.post("")
def save_settings(body: SettingsUpdate):
    user = repo.get_or_create_user(body.user_email)
    encrypted = encrypt_api_key(body.api_key) if body.api_key else None
    row = repo.upsert_user_settings(user["id"], body.llm_provider, body.llm_model, encrypted, body.payment_rail)
    masked = mask_key(decrypt_api_key(row["encrypted_api_key"])) if row.get("encrypted_api_key") else None
    return {
        "llm_provider": row["llm_provider"],
        "llm_model": row["llm_model"],
        "api_key_masked": masked,
        "payment_rail": row["payment_rail"],
        "configured": bool(masked),
    }
