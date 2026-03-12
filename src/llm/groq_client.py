import logging
import time
from typing import Any, Dict, List, Optional

from dataclasses import dataclass

from src.config import load_config

try:
    from groq import Groq  # type: ignore
except ImportError:  # pragma: no cover
    Groq = None  # type: ignore


logger = logging.getLogger(__name__)


@dataclass
class ChatCompletionResult:
    content: str
    raw: Dict[str, Any]


class GroqClient:
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        max_retries: int = 3,
        backoff_seconds: float = 1.0,
    ) -> None:
        cfg = load_config().groq
        self.api_key = api_key or cfg.api_key
        if not self.api_key:
            raise ValueError("GROQ_API_KEY is not set")

        if Groq is None:
            raise ImportError("groq package is not installed")

        self.model = model or cfg.model
        self.max_tokens = max_tokens or cfg.max_tokens
        self.temperature = temperature if temperature is not None else cfg.temperature
        self.max_retries = max_retries
        self.backoff_seconds = backoff_seconds
        self._client = Groq(api_key=self.api_key)

    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        response_format: Optional[Dict[str, Any]] = None,
    ) -> ChatCompletionResult:
        """Call Groq chat completion with basic retries."""
        attempt = 0
        last_error: Optional[Exception] = None

        while attempt <= self.max_retries:
            try:
                params: Dict[str, Any] = {
                    "model": model or self.model,
                    "messages": messages,
                    "max_tokens": max_tokens or self.max_tokens,
                    "temperature": (
                        self.temperature if temperature is None else temperature
                    ),
                }
                if response_format is not None:
                    params["response_format"] = response_format

                response = self._client.chat.completions.create(**params)
                content = response.choices[0].message.content or ""
                return ChatCompletionResult(content=content, raw=response.to_dict())
            except Exception as exc:  # pragma: no cover
                last_error = exc
                attempt += 1
                if attempt > self.max_retries:
                    logger.error("Groq chat_completion failed after retries", exc_info=exc)
                    raise
                sleep_for = self.backoff_seconds * attempt
                logger.warning(
                    "Groq chat_completion failed on attempt %s, retrying in %s seconds",
                    attempt,
                    sleep_for,
                )
                time.sleep(sleep_for)

        assert last_error is not None
        raise last_error

