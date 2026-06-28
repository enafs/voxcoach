"""Fábricas que montam componentes reais a partir da config (D05).

Compartilhado entre o CLI (modo live) e o app de tray.
"""

from __future__ import annotations

from voxcoach.llm.base import LLMProvider


def build_llm(settings) -> LLMProvider | None:
    """Cria o provider de LLM conforme a config; ``None`` se não houver key."""
    from voxcoach.config import LLMBackend

    if settings.llm_backend is LLMBackend.CLAUDE and settings.anthropic_api_key:
        from voxcoach.llm.claude import ClaudeProvider

        return ClaudeProvider(api_key=settings.anthropic_api_key, model=settings.llm_model)
    return None
