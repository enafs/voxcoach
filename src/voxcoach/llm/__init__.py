"""Providers de LLM plugáveis (Claude no MVP; OpenAI previsto)."""

from voxcoach.llm.claude import ClaudeProvider
from voxcoach.llm.prompts import SYSTEM_PROMPT, build_context

__all__ = ["ClaudeProvider", "SYSTEM_PROMPT", "build_context"]
