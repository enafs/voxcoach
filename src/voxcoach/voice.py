"""VoiceSpeaker — saída por voz, ligando TTS (síntese) + AudioPlayer (reprodução).

Implementa o ``Speaker`` do orchestrator usando os componentes de ``tts/``.
Cada fala nova **interrompe** a anterior (via ``AudioPlayer.play``), o que dá o
comportamento de "último insight ganha" — alertas prioritários cortam a fala
em andamento sem esperar (SDD 3.2).
"""

from __future__ import annotations

from voxcoach.orchestrator import Speaker
from voxcoach.tts.base import TTSProvider
from voxcoach.tts.player import AudioPlayer


class VoiceSpeaker(Speaker):
    def __init__(self, provider: TTSProvider, player: AudioPlayer) -> None:
        self._provider = provider
        self._player = player

    async def speak(self, text: str, *, interrupt: bool = False) -> None:
        audio = await self._provider.synthesize(text)
        # play() já faz stop antes de tocar → a fala anterior é interrompida.
        self._player.play(audio)
