"""Reprodução de áudio com interrupção (D10).

Usa ``sounddevice`` para tocar e ``soundfile`` para decodificar o MP3 do
edge-tts. Cada nova fala **interrompe** a anterior (``stop`` antes de ``play``),
o que dá suporte a alertas prioritários sem esperar a fala atual terminar.

``sounddevice`` é I/O de hardware → importado de forma tardia e injetável, para
que os testes rodem sem placa de som. ``decode_audio`` é puro e testável.
"""

from __future__ import annotations

import io
from typing import Any

from voxcoach.tts.base import AudioChunk


def decode_audio(audio: AudioChunk) -> tuple[Any, int]:
    """Decodifica os bytes do ``AudioChunk`` em (amostras float32, samplerate).

    O formato é autodetectado pela libsndfile (MP3, WAV, ...), então o campo
    ``audio.format`` é informativo apenas.
    """
    import soundfile as sf  # import tardio

    data, samplerate = sf.read(io.BytesIO(audio.data), dtype="float32")
    return data, samplerate


class AudioPlayer:
    def __init__(self, *, sd: Any | None = None, decode=decode_audio) -> None:
        self._sd = sd
        self._decode = decode

    def _device(self) -> Any:
        if self._sd is None:
            import sounddevice  # import tardio (hardware)

            self._sd = sounddevice
        return self._sd

    def play(self, audio: AudioChunk) -> None:
        """Toca o áudio, interrompendo qualquer fala em andamento (não bloqueia)."""
        data, samplerate = self._decode(audio)
        sd = self._device()
        sd.stop()                 # interrompe a fala anterior (prioridade)
        sd.play(data, samplerate)

    def stop(self) -> None:
        """Interrompe a fala atual imediatamente."""
        self._device().stop()

    def wait(self) -> None:
        """Bloqueia até a fala atual terminar (útil em scripts/CLI)."""
        self._device().wait()
