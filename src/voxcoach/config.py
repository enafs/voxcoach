"""Configuração tipada e validada do VoxCoach (D05).

Carregada de variáveis de ambiente e/ou de um arquivo ``.env`` (prefixo
``VOXCOACH_``). A chave de API é do **próprio usuário** — custo e privacidade
ficam com ele.
"""

from __future__ import annotations

from enum import Enum

from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMBackend(str, Enum):
    CLAUDE = "claude"
    OPENAI = "openai"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="VOXCOACH_",
        extra="ignore",
    )

    # --- LLM ---
    llm_backend: LLMBackend = LLMBackend.CLAUDE
    anthropic_api_key: str | None = None
    openai_api_key: str | None = None
    # Modelo rápido por padrão p/ tempo real (SDD 3.2 / D09).
    llm_model: str = "claude-haiku-4-5-20251001"
    llm_max_tokens: int = 120        # respostas curtas (1–2 frases)

    # --- TTS ---
    tts_voice: str = "pt-BR-AntonioNeural"
    tts_rate: str = "+0%"

    # --- Engine ---
    poll_interval_seconds: float = 1.5
    speak_cooldown_seconds: float = 8.0   # gatilho anti-spam (SDD 3.1)


def load_settings() -> Settings:
    """Ponto único de carregamento da config."""
    return Settings()
