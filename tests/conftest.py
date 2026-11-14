"""Safety net: tests never call the real Claude API (a real key may be in secrets.toml)."""
import pytest


@pytest.fixture(autouse=True)
def _no_real_api(monkeypatch):
    def blocked(*args, **kwargs):
        raise AssertionError("Real Claude API call attempted in a test")
    import core.llm
    import core.ai_engine
    monkeypatch.setattr(core.llm, "call_claude_json", blocked)
    monkeypatch.setattr(core.ai_engine, "call_claude_json", blocked)
