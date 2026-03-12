import sys
import types

from src.config import load_config
from src.utils.pii_scrubber import scrub_text


def _install_dummy_groq_module() -> None:
    """Install a dummy groq module so GroqClient can be instantiated in tests."""
    dummy_groq = types.ModuleType("groq")

    class DummyChatCompletions:
        def create(self, **kwargs):
            class DummyResponse:
                def __init__(self):
                    self.choices = [
                        type(
                            "Choice",
                            (),
                            {"message": type("Msg", (), {"content": "ok"})()},
                        )
                    ]

                def to_dict(self):
                    return {"dummy": True, "kwargs": kwargs}

            return DummyResponse()

    class DummyClient:
        def __init__(self, api_key=None):
            self.chat = types.SimpleNamespace(completions=DummyChatCompletions())

    dummy_groq.Groq = DummyClient  # type: ignore[attr-defined]
    sys.modules["groq"] = dummy_groq


def test_phase1_end_to_end(monkeypatch):
    """Integration style test: config + GroqClient + PII scrubber."""
    # Ensure a dummy API key and dummy groq module exist
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    _install_dummy_groq_module()

    from src.llm.groq_client import GroqClient

    cfg = load_config()
    assert cfg.groq.api_key == "test-key"
    assert cfg.reviews.max_reviews == 200

    client = GroqClient()
    result = client.chat_completion(
        messages=[{"role": "user", "content": "Hello"}]
    )
    assert result.content == "ok"
    assert result.raw.get("dummy") is True

    # Ensure the PII scrubber can be used with the same phase
    text = "Reach me at user@example.com or +91 9876543210."
    cleaned = scrub_text(text)
    assert "example.com" not in cleaned
    assert "9876543210" not in cleaned
    assert "[email removed]" in cleaned
    assert "[phone removed]" in cleaned

