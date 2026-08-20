"""
Encryption helpers for user-supplied LLM API keys.

We never store a user's API key in plaintext, and we never send it back to
the frontend after it has been saved (Settings GET only returns a masked
preview like 'sk-...ab12'). This is separate from — and does not touch —
payment credentials: the platform never asks for or stores a UPI PIN or
card number at all; payment authentication is delegated to the payment
rail's own regulated flow (see connectors/base.py PaymentRail).
"""
import os
from cryptography.fernet import Fernet

from .config import settings

_KEY_FILE = os.path.join(os.path.dirname(__file__), "..", ".encryption_key")


def _load_or_create_key() -> bytes:
    if settings.APP_ENCRYPTION_KEY:
        return settings.APP_ENCRYPTION_KEY.encode()
    # Dev/demo fallback: persist a generated key on disk so restarts can
    # still decrypt previously-saved keys. In production, set
    # APP_ENCRYPTION_KEY as a Railway/Render secret instead.
    if os.path.exists(_KEY_FILE):
        with open(_KEY_FILE, "rb") as f:
            return f.read().strip()
    key = Fernet.generate_key()
    with open(_KEY_FILE, "wb") as f:
        f.write(key)
    return key


_fernet = Fernet(_load_or_create_key())


def encrypt_api_key(plaintext: str) -> str:
    return _fernet.encrypt(plaintext.encode()).decode()


def decrypt_api_key(ciphertext: str) -> str:
    return _fernet.decrypt(ciphertext.encode()).decode()


def mask_key(plaintext: str) -> str:
    if not plaintext or len(plaintext) < 8:
        return "••••••••"
    return f"{plaintext[:4]}••••••••{plaintext[-4:]}"
