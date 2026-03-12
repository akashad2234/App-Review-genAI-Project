import sys
import types

import pytest


def test_groq_client_raises_without_api_key(monkeypatch):
    # Ensure env is clean
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    # Inject a dummy groq module before importing groq_client
    dummy_groq = types.ModuleType("groq")

    class DummyChatCompletions:
        def create(self, **kwargs):
            class DummyResponse:
                def __init__(self):
                    self.choices = [
                        type(
                            "Choice",
                            (),
                            {"message": type("Msg", (), {"content": "hello"})()},
                        )
                    ]

                def to_dict(self):
                    return {"dummy": True}

            return DummyResponse()

    class DummyClient:
        def __init__(self, api_key=None):
            self.chat = types.SimpleNamespace(completions=DummyChatCompletions())

    dummy_groq.Groq = DummyClient  # type: ignore
    sys.modules["groq"] = dummy_groq

    from src import config as config_module

    # Patch load_config to provide a fake api key to avoid ValueError
    def dummy_load_config():
        from dataclasses import dataclass

        @dataclass
        class GroqCfg:
            api_key: str = "test-key"
            model: str = "llama-3.3-70b-versatile"
            max_tokens: int = 16
            temperature: float = 0.1

        @dataclass
        class ReviewCfg:
            app_id: str = "com.groww.v2"
            review_window_weeks: int = 8
            max_reviews: int = 200

        @dataclass
        class EmailCfg:
            smtp_host: str = "smtp.gmail.com"
            smtp_port: int = 587
            smtp_user: str | None = None
            smtp_password: str | None = None
            email_from: str | None = None
            email_to: str | None = None

        @dataclass
        class AppCfg:
            groq: GroqCfg
            reviews: ReviewCfg
            email: EmailCfg

        return AppCfg(
            groq=GroqCfg(), reviews=ReviewCfg(), email=EmailCfg()
        )

    monkeypatch.setattr(config_module, "load_config", dummy_load_config)

    from src.llm.groq_client import GroqClient

    client = GroqClient()
    result = client.chat_completion(
        messages=[{"role": "user", "content": "Hi"}]
    )

    assert result.content == "hello"
    assert result.raw.get("dummy") is True

