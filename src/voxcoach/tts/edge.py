"""Provider de TTS via edge-tts (MVP, D04).

Grátis, vozes naturais pt-BR, com streaming de áudio (MP3). Só **sintetiza**;
a reprodução é do ``AudioPlayer`` (``tts/player.py``).

A classe ``Communicate`` do edge-tts é injetável (``communicate_factory``) para
testar sem rede; por padrão, importa o edge-tts de forma tardia.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any, Callable

from voxcoach.tts.base import AudioChunk, TTSProvider

DEFAULT_VOICE = "pt-BR-AntonioNeural"
_AUDIO_FORMAT = "mp3"   # edge-tts entrega MP3


class EdgeTTSProvider(TTSProvider):
    def __init__(
        self,
        voice: str = DEFAULT_VOICE,
        rate: str = "+0%",
        *,
        communicate_factory: Callable[..., Any] | None = None,
    ) -> None:
        self._voice = voice
        self._rate = rate
        self._factory = communicate_factory

    def _make(self, text: str) -> Any:
        if self._factory is not None:
            return self._factory(text, self._voice, rate=self._rate)
        import edge_tts  # import tardio

        return edge_tts.Communicate(text, self._voice, rate=self._rate)

    async def synthesize_stream(self, text: str) -> AsyncIterator[AudioChunk]:
        comm = self._make(text)
        async for chunk in comm.stream():
            if chunk.get("type") == "audio" and chunk.get("data"):
                yield AudioChunk(data=chunk["data"], format=_AUDIO_FORMAT)

    async def synthesize(self, text: str) -> AudioChunk:
        parts = bytearray()
        async for chunk in self.synthesize_stream(text):
            parts.extend(chunk.data)
        return AudioChunk(data=bytes(parts), format=_AUDIO_FORMAT)
