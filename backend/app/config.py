"""
Central configuration for the Personal AI Operations Platform backend.

All values are read from environment variables so the same code runs
locally, on Railway/Render, and against a local Postgres or Supabase.
"""
import os


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


class Settings:
    # --- Database (Supabase Postgres or any Postgres) ---
    DATABASE_URL: str = _env("DATABASE_URL")

    # --- CORS ---
    FRONTEND_ORIGIN: str = _env("FRONTEND_ORIGIN", "*")

    # --- Secret used to encrypt user-supplied LLM API keys at rest ---
    # Must be a urlsafe-base64 32 byte key (Fernet.generate_key()).
    # A fixed fallback is provided ONLY for first local boot; the app
    # generates and persists one automatically if not set (see security.py).
    APP_ENCRYPTION_KEY: str = _env("APP_ENCRYPTION_KEY")

    # --- Optional platform-level default LLM credentials ---
    # These are ONLY used if a given user has not supplied their own key
    # in Settings. In production this should stay empty and every user
    # brings their own key (BYOK), which is the platform's default mode.
    DEFAULT_ANTHROPIC_API_KEY: str = _env("ANTHROPIC_API_KEY")
    DEFAULT_OPENAI_API_KEY: str = _env("OPENAI_API_KEY")
    DEFAULT_LLM_PROVIDER: str = _env("DEFAULT_LLM_PROVIDER", "anthropic")
    DEFAULT_LLM_MODEL: str = _env("DEFAULT_LLM_MODEL", "claude-sonnet-5")

    PORT: int = int(_env("PORT", "8000"))


settings = Settings()
