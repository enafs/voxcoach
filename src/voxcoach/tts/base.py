"""Interface plugável de síntese de voz (D04, D10).

Separação de responsabilidades proposital:
- **Síntese** (texto -> áudio) é do ``TTSProvider`` — específico do provedor
  (edge-tts no MVP; ElevenLabs no futuro).
- **Reprodução** (tocar / interromper) é do ``AudioPlayer`` (``tts/player.py``),
  compartilhado entre providers. É o player que permite **cortar a fala atual**
  quando chega um alerta de prioridade maior (SDD 2.2 / 3.2).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass


@dataclass
class AudioChunk:
    """Pedaço de áudio sintetizado. ``format`` ex.: "mp3", "wav"."""

    data: bytes
    format: str


class TTSProvider(ABC):
    """Converte texto em áudio. Não reproduz — isso é do ``AudioPlayer``."""

    @abstractmethod
    async def synthesize(self, text: str) -> AudioChunk:
        """Sintetiza o texto inteiro e retorna o áudio completo."""

    @abstractmethod
    def synthesize_stream(self, text: str) -> AsyncIterator[AudioChunk]:
        """Sintetiza em chunks, para começar a tocar antes do fim.

        Reduz a latência percebida (SDD 3.2). Implementado como async generator.
        """

    async def close(self) -> None:
        return None
