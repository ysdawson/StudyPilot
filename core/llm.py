"""Claude API access with local JSON response caching."""

import hashlib
import json
import os
from pathlib import Path
import tomllib
from typing import Any

import anthropic


_ROOT = Path(__file__).resolve().parent.parent
_CACHE_DIR = _ROOT / "cache"
_CACHE_DIR.mkdir(exist_ok=True)


def _read_file_secrets() -> dict[str, Any]:
    secrets_path = _ROOT / ".streamlit" / "secrets.toml"
    if not secrets_path.exists():
        return {}
    with secrets_path.open("rb") as secrets_file:
        return tomllib.load(secrets_file)


def _read_setting(name: str, secrets: dict[str, Any]) -> str | None:
    """Read Streamlit secrets first, then the local TOML fallback."""
    try:
        import streamlit as st

        value = st.secrets.get(name)
    except (ImportError, KeyError, FileNotFoundError, RuntimeError):
        value = None

    if value:
        return str(value)
    value = secrets.get(name) or os.getenv(name)
    return str(value) if value else None


_FILE_SECRETS = _read_file_secrets()
MODEL = _read_setting("CLAUDE_MODEL", _FILE_SECRETS) or "claude-haiku-5-5"
_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    """Create the client on the first real API call, so the app (and mock
    mode) can start without an API key."""
    global _client
    if _client is None:
        api_key = _read_setting("ANTHROPIC_API_KEY", _FILE_SECRETS)
        if not api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY is not configured in Streamlit secrets, "
                ".streamlit/secrets.toml, or the environment."
            )
        _client = anthropic.Anthropic(api_key=api_key)
    return _client


def _strip_code_fence(raw_response: str) -> str:
    cleaned = raw_response.strip()
    if not cleaned.startswith("```"):
        return cleaned

    lines = cleaned.splitlines()
    if len(lines) < 3 or not lines[-1].strip().startswith("```"):
        return cleaned
    return "\n".join(lines[1:-1]).strip()


def _parse_json(raw_response: str) -> dict | list:
    try:
        value = json.loads(_strip_code_fence(raw_response))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Claude did not return valid JSON: {exc}") from exc
    if not isinstance(value, (dict, list)):
        raise ValueError("Claude did not return a JSON object or array")
    return value


def _print_usage(response: Any) -> None:
    print(f"[usage] in={response.usage.input_tokens} out={response.usage.output_tokens}")


def call_claude_json(
    system: str,
    content: str | list,
    max_tokens: int = 4000,
) -> dict | list:
    """Call Claude for a JSON response, retrying once after invalid JSON."""
    serialized_content = json.dumps(content, sort_keys=True, default=str)
    cache_key = hashlib.sha256(
        (MODEL + system + serialized_content).encode("utf-8")
    ).hexdigest()
    cache_path = _CACHE_DIR / f"{cache_key}.json"

    if cache_path.exists():
        with cache_path.open(encoding="utf-8") as cache_file:
            return json.load(cache_file)

    request_system = system + "\n\nAnswer with JSON only, no prose."
    messages = [{"role": "user", "content": content}]
    response = _get_client().messages.create(
        model=MODEL,
        max_tokens=max_tokens,
        system=request_system,
        messages=messages,
    )
    _print_usage(response)
    raw_response = response.content[0].text

    try:
        parsed = _parse_json(raw_response)
    except ValueError as first_error:
        retry_messages = messages + [
            {"role": "assistant", "content": raw_response},
            {
                "role": "user",
                "content": "Your last answer was not valid JSON. Return only the JSON.",
            },
        ]
        retry_response = _get_client().messages.create(
            model=MODEL,
            max_tokens=max_tokens,
            system=request_system,
            messages=retry_messages,
        )
        _print_usage(retry_response)
        try:
            parsed = _parse_json(retry_response.content[0].text)
        except ValueError as retry_error:
            raise ValueError(
                f"Claude did not return valid JSON: {retry_error}"
            ) from first_error

    with cache_path.open("w", encoding="utf-8") as cache_file:
        json.dump(parsed, cache_file, indent=2)
    return parsed


if __name__ == "__main__":
    print(call_claude_json(
        "Return a small hello-world JSON object.",
        "Say hello.",
    ))
