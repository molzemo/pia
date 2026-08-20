"""
LLM provider abstraction.

The platform is BYOK (bring your own key) by default: each user picks a
provider + model + API key in Settings. If they haven't set one, we fall
back to a platform default key (if the operator configured one via env
vars) so the demo still works out of the box.
"""
import json
import re
from dataclasses import dataclass

from .config import settings

ANTHROPIC_MODELS = [
    {"id": "claude-sonnet-5", "label": "Claude Sonnet 5 (recommended, balanced)"},
    {"id": "claude-opus-5", "label": "Claude Opus 5 (most capable)"},
    {"id": "claude-haiku-4-5-20251001", "label": "Claude Haiku 4.5 (fastest, cheapest)"},
]

OPENAI_MODELS = [
    {"id": "gpt-4o", "label": "GPT-4o"},
    {"id": "gpt-4o-mini", "label": "GPT-4o mini"},
]

PROVIDERS = {
    "anthropic": {"label": "Anthropic Claude", "models": ANTHROPIC_MODELS},
    "openai": {"label": "OpenAI", "models": OPENAI_MODELS},
}


@dataclass
class LLMConfig:
    provider: str
    model: str
    api_key: str


class LLMError(RuntimeError):
    pass


def _extract_json(text: str) -> dict:
    """LLMs sometimes wrap JSON in prose or code fences; pull the object out."""
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fence:
        text = fence.group(1)
    else:
        brace = re.search(r"\{.*\}", text, re.DOTALL)
        if brace:
            text = brace.group(0)
    return json.loads(text)


def resolve_config(user_provider: str, user_model: str, user_api_key: str | None) -> LLMConfig:
    provider = user_provider or settings.DEFAULT_LLM_PROVIDER
    model = user_model or settings.DEFAULT_LLM_MODEL
    api_key = user_api_key
    if not api_key:
        if provider == "anthropic":
            api_key = settings.DEFAULT_ANTHROPIC_API_KEY
        elif provider == "openai":
            api_key = settings.DEFAULT_OPENAI_API_KEY
    if not api_key:
        raise LLMError(
            "No API key configured. Add your Anthropic or OpenAI API key in "
            "Settings to activate your agents."
        )
    return LLMConfig(provider=provider, model=model, api_key=api_key)


def complete_json(cfg: LLMConfig, system_prompt: str, user_prompt: str, max_tokens: int = 1200) -> dict:
    """Call the configured provider and parse a JSON object out of the reply."""
    if cfg.provider == "anthropic":
        raw = _call_anthropic(cfg, system_prompt, user_prompt, max_tokens)
    elif cfg.provider == "openai":
        raw = _call_openai(cfg, system_prompt, user_prompt, max_tokens)
    else:
        raise LLMError(f"Unknown provider: {cfg.provider}")
    try:
        return _extract_json(raw)
    except Exception as e:  # noqa: BLE001
        raise LLMError(f"Model did not return valid JSON: {e}\nRaw: {raw[:500]}") from e


def _call_anthropic(cfg: LLMConfig, system_prompt: str, user_prompt: str, max_tokens: int) -> str:
    import anthropic

    client = anthropic.Anthropic(api_key=cfg.api_key)
    try:
        resp = client.messages.create(
            model=cfg.model,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
    except anthropic.AuthenticationError as e:
        raise LLMError("Anthropic rejected your API key. Check it in Settings.") from e
    except anthropic.APIError as e:
        raise LLMError(f"Anthropic API error: {e}") from e
    return "".join(block.text for block in resp.content if block.type == "text")


def _call_openai(cfg: LLMConfig, system_prompt: str, user_prompt: str, max_tokens: int) -> str:
    from openai import OpenAI, AuthenticationError, APIError

    client = OpenAI(api_key=cfg.api_key)
    try:
        resp = client.chat.completions.create(
            model=cfg.model,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
    except AuthenticationError as e:
        raise LLMError("OpenAI rejected your API key. Check it in Settings.") from e
    except APIError as e:
        raise LLMError(f"OpenAI API error: {e}") from e
    return resp.choices[0].message.content or ""
