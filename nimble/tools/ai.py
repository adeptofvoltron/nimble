from __future__ import annotations

import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from nimble.manifest.parser import AiConfig


class AiTool:
    def __init__(self, config: AiConfig | None) -> None:
        self._config = config

    def ask(self, text: str, system_prompt: str | None = None) -> str:
        if self._config is None:
            raise RuntimeError("AI not configured: add an 'ai' block to config.yaml")
        api_key = os.environ.get(self._config.api_key_env)
        if not api_key:
            raise RuntimeError(
                f"AI API key not set: env var {self._config.api_key_env!r}"
                " is empty or unset"
            )
        if self._config.provider == "anthropic":
            return self._ask_anthropic(text, system_prompt, api_key)
        if self._config.provider == "openai":
            return self._ask_openai(text, system_prompt, api_key)
        raise RuntimeError(
            f"Unsupported AI provider: {self._config.provider!r}."
            " Supported: anthropic, openai"
        )

    def _ask_anthropic(self, text: str, system_prompt: str | None, api_key: str) -> str:
        try:
            import anthropic
        except ImportError:
            raise RuntimeError(
                "anthropic package not installed; add 'anthropic' to your"
                " skill's manifest.yaml dependencies"
            )
        from anthropic.types import MessageParam, TextBlock

        client = anthropic.Anthropic(api_key=api_key)
        messages: list[MessageParam] = [{"role": "user", "content": text}]
        model: str = self._config.model  # type: ignore[union-attr]
        if system_prompt is not None:
            response = client.messages.create(
                model=model, max_tokens=1024, messages=messages, system=system_prompt
            )
        else:
            response = client.messages.create(
                model=model, max_tokens=1024, messages=messages
            )
        for block in response.content:
            if isinstance(block, TextBlock):
                return block.text
        raise RuntimeError("Anthropic response contained no text block")

    def _ask_openai(self, text: str, system_prompt: str | None, api_key: str) -> str:
        try:
            import openai
        except ImportError:
            raise RuntimeError(
                "openai package not installed; add 'openai' to your"
                " skill's manifest.yaml dependencies"
            )
        from openai.types.chat import ChatCompletionMessageParam

        client = openai.OpenAI(api_key=api_key)
        messages: list[ChatCompletionMessageParam] = []
        if system_prompt is not None:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": text})
        response = client.chat.completions.create(
            model=self._config.model,  # type: ignore[union-attr]
            messages=messages,
        )
        return str(response.choices[0].message.content)
