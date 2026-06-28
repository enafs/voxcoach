"""Interface plugável de provider de LLM (D05).

Usado **apenas** para a Camada 2 do pipeline (recomendações analíticas que
exigem julgamento — ver SDD 3.2). Fatos determinísticos não passam por aqui.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class LLMProvider(ABC):
    """Gera um insight curto de coaching a partir do contexto da partida."""

    @abstractmethod
    async def generate_insight(
        self,
        system_prompt: str,
        context: str,
        *,
        max_tokens: int = 120,
    ) -> str:
        """Retorna 1–2 frases de coaching.

        ``context`` é um resumo textual do ``GameState`` montado pelo Processor.
        A resposta é mantida curta de propósito: gera mais rápido e fala mais
        rápido (baixa latência — SDD 3.2).
        """

    async def close(self) -> None:
        return None
