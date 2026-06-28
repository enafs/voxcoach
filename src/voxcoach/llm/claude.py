"""Provider de LLM via Anthropic Claude (D05).

Wrapper fino sobre a SDK ``anthropic`` (Messages API). A SDK é importada de forma
**tardia** (dentro do ``__init__``) para que:
- o módulo importe sem a dependência instalada (testes injetam um cliente falso);
- a dependência pesada só seja tocada quando o provider é realmente criado.

Modelo padrão: rápido (Haiku) para baixa latência no tempo real (SDD 3.2).
"""

from __future__ import annotations

import inspect
from typing import Any

from voxcoach.llm.base import LLMProvider

DEFAULT_MODEL = "claude-haiku-4-5-20251001"


class ClaudeProvider(LLMProvider):
    def __init__(
        self,
        api_key: str | None = None,
        model: str = DEFAULT_MODEL,
        *,
        client: Any | None = None,
    ) -> None:
        self._model = model
        if client is None:
            from anthropic import AsyncAnthropic  # import tardio (ver docstring)

            client = AsyncAnthropic(api_key=api_key)
        self._client = client

    async def generate_insight(
        self,
        system_prompt: str,
        context: str,
        *,
        max_tokens: int = 120,
    ) -> str:
        resp = await self._client.messages.create(
            model=self._model,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": context}],
        )
        return _extract_text(resp).strip()

    async def close(self) -> None:
        close = getattr(self._client, "close", None)
        if close is None:
            return
        result = close()
        if inspect.isawaitable(result):
            await result


def _extract_text(resp: Any) -> str:
    """Concatena os blocos de texto da resposta da Messages API."""
    parts: list[str] = []
    for block in getattr(resp, "content", []) or []:
        text = getattr(block, "text", None)
        if text:
            parts.append(text)
    return "".join(parts)
