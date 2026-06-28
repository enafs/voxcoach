"""Testes da camada de TTS.

- ``EdgeTTSProvider`` com a classe Communicate mockada (sem rede).
- ``AudioPlayer`` com sounddevice falso (sem hardware) + ordem de interrupção.
- ``decode_audio`` num round-trip real via soundfile (WAV em memória).
"""

from __future__ import annotations

import io

import numpy as np
import soundfile as sf

from voxcoach.tts.base import AudioChunk
from voxcoach.tts.edge import EdgeTTSProvider
from voxcoach.tts.player import AudioPlayer, decode_audio


# --------------------------------------------------------------------------- #
# EdgeTTSProvider (Communicate mockado)
# --------------------------------------------------------------------------- #


class _FakeCommunicate:
    def __init__(self, text, voice, rate=None):
        self.text, self.voice, self.rate = text, voice, rate

    async def stream(self):
        yield {"type": "WordBoundary", "offset": 0}   # deve ser ignorado
        yield {"type": "audio", "data": b"abc"}
        yield {"type": "audio", "data": b"def"}


async def test_stream_yields_only_audio_chunks():
    provider = EdgeTTSProvider(communicate_factory=_FakeCommunicate)
    chunks = [c async for c in provider.synthesize_stream("oi")]
    assert [c.data for c in chunks] == [b"abc", b"def"]
    assert all(c.format == "mp3" for c in chunks)


async def test_synthesize_aggregates_bytes():
    provider = EdgeTTSProvider(communicate_factory=_FakeCommunicate)
    audio = await provider.synthesize("oi")
    assert audio.data == b"abcdef"
    assert audio.format == "mp3"


async def test_factory_receives_voice_and_rate():
    captured = {}

    def factory(text, voice, rate=None):
        captured.update(text=text, voice=voice, rate=rate)
        return _FakeCommunicate(text, voice, rate)

    provider = EdgeTTSProvider(voice="pt-BR-AntonioNeural", rate="+10%",
                               communicate_factory=factory)
    await provider.synthesize("dica")
    assert captured == {"text": "dica", "voice": "pt-BR-AntonioNeural", "rate": "+10%"}


# --------------------------------------------------------------------------- #
# AudioPlayer (sounddevice falso)
# --------------------------------------------------------------------------- #


class _FakeSD:
    def __init__(self):
        self.calls: list[tuple] = []

    def play(self, data, samplerate):
        self.calls.append(("play", len(data), samplerate))

    def stop(self):
        self.calls.append(("stop",))

    def wait(self):
        self.calls.append(("wait",))


def test_play_interrupts_then_plays():
    sd = _FakeSD()
    player = AudioPlayer(sd=sd, decode=lambda audio: (np.zeros(10, dtype="float32"), 24000))
    player.play(AudioChunk(data=b"x", format="mp3"))
    # stop ANTES de play garante a interrupção da fala anterior.
    assert sd.calls == [("stop",), ("play", 10, 24000)]


def test_stop_calls_device_stop():
    sd = _FakeSD()
    player = AudioPlayer(sd=sd)
    player.stop()
    assert sd.calls == [("stop",)]


# --------------------------------------------------------------------------- #
# decode_audio (round-trip real via soundfile)
# --------------------------------------------------------------------------- #


def test_decode_audio_roundtrip():
    samplerate = 24000
    signal = np.linspace(-0.5, 0.5, 1200, dtype="float32")
    buf = io.BytesIO()
    sf.write(buf, signal, samplerate, format="WAV")
    audio = AudioChunk(data=buf.getvalue(), format="wav")

    data, sr = decode_audio(audio)
    assert sr == samplerate
    assert len(data) == len(signal)
