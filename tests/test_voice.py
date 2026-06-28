"""Testes do VoiceSpeaker (TTS real mockado)."""

from __future__ import annotations

from voxcoach.tts.base import AudioChunk
from voxcoach.voice import VoiceSpeaker


class _FakeProvider:
    def __init__(self):
        self.texts: list[str] = []

    async def synthesize(self, text: str) -> AudioChunk:
        self.texts.append(text)
        return AudioChunk(data=b"AUDIO:" + text.encode(), format="mp3")

    async def synthesize_stream(self, text):  # não usado aqui
        yield AudioChunk(data=b"", format="mp3")

    async def close(self):
        pass


class _FakePlayer:
    def __init__(self):
        self.played: list[AudioChunk] = []
        self.stopped = 0

    def play(self, audio: AudioChunk) -> None:
        self.played.append(audio)

    def stop(self) -> None:
        self.stopped += 1

    def wait(self) -> None:
        pass


async def test_speak_synthesizes_then_plays():
    provider, player = _FakeProvider(), _FakePlayer()
    speaker = VoiceSpeaker(provider, player)

    await speaker.speak("recue", interrupt=True)

    assert provider.texts == ["recue"]
    assert len(player.played) == 1
    assert player.played[0].data == b"AUDIO:recue"


async def test_each_speak_plays_again():
    provider, player = _FakeProvider(), _FakePlayer()
    speaker = VoiceSpeaker(provider, player)

    await speaker.speak("um")
    await speaker.speak("dois")

    assert [c.data for c in player.played] == [b"AUDIO:um", b"AUDIO:dois"]
