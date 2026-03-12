from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import google.generativeai as genai

from src.config import load_config


@dataclass
class GeminiConfig:
    api_key: str
    model: str = "gemini-2.5-flash"
    temperature: float = 0.2
    max_output_tokens: int = 2048


class GeminiClient:
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_output_tokens: Optional[int] = None,
    ) -> None:
        app_cfg = load_config()
        # Reuse Groq temperature/max_tokens defaults unless overridden; Gemini API key is separate
        gemini_key = api_key or (  # explicit arg wins
            # Prefer dedicated GEMINI_API_KEY if present
            (load_config and __import__("os").environ.get("GEMINI_API_KEY", ""))
        )
        if not gemini_key:
            raise ValueError("GEMINI_API_KEY is not set")

        self.api_key = gemini_key
        self.model_name = model or GeminiConfig.model
        self.temperature = (
            temperature if temperature is not None else GeminiConfig.temperature
        )
        self.max_output_tokens = (
            max_output_tokens
            if max_output_tokens is not None
            else GeminiConfig.max_output_tokens
        )

        genai.configure(api_key=self.api_key)
        self._model = genai.GenerativeModel(self.model_name)

    def generate_content(
        self,
        system_instruction: str,
        user_prompt: str,
        request_json: bool = False,
    ) -> str:
        """Generate text from Gemini. If request_json is True, asks for application/json."""
        prompt_parts: List[str] = []
        if system_instruction:
            prompt_parts.append(system_instruction.strip())
        prompt_parts.append(user_prompt.strip())
        full_prompt = "\n\n".join(prompt_parts)

        gen_config: Dict[str, Any] = {
            "temperature": self.temperature,
            "max_output_tokens": self.max_output_tokens,
        }
        if request_json:
            gen_config["response_mime_type"] = "application/json"

        response = self._model.generate_content(full_prompt, generation_config=gen_config)
        text = response.text or ""
        return text.strip()

    def generate_json(
        self,
        system_instruction: str,
        user_prompt: str,
    ) -> str:
        """Convenience: generate content (no JSON mode) for line-based parsing."""
        return self.generate_content(system_instruction, user_prompt, request_json=False)

