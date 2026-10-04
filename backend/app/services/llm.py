"""Text LLM helper (Groq), ported from prototype cell 2's llm()/llm_json().

Used by the API's summarizer/critic/QA until the full agent ports land.
Returns None-safe results: callers must handle a missing API key.
"""
from typing import Optional

from ..config import Settings
from ..utils.json_utils import safe_json
from ..utils.retry import with_retry

_client = None


def llm_available(settings: Settings) -> bool:
    return bool(settings.groq_api_key)


def _get_client(settings: Settings):
    global _client
    if _client is None:
        from groq import Groq
        _client = Groq(api_key=settings.groq_api_key, max_retries=0)
    return _client


def llm_json(settings: Settings, prompt: str, system: Optional[str] = None,
             max_tokens: int = 3000) -> dict:
    """One JSON-mode chat call with rate-limit retry and tolerant parsing."""
    client = _get_client(settings)
    messages = ([{"role": "system", "content": system}] if system else [])
    messages.append({"role": "user", "content": prompt})

    def go(json_mode: bool = True):
        kw = {"response_format": {"type": "json_object"}} if json_mode else {}
        r = client.chat.completions.create(
            model=settings.llm_model_groq, messages=messages,
            temperature=0.1, max_tokens=max_tokens, **kw)
        return r.choices[0].message.content

    try:
        return safe_json(with_retry(go, label="llm"))
    except Exception as e:
        if "json_validate_failed" in str(e) or "Failed to validate JSON" in str(e):
            return safe_json(with_retry(lambda: go(json_mode=False), label="llm-fallback"))
        raise
