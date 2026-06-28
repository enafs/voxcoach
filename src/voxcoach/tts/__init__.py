"""TTS: síntese de voz (providers) + reprodução com interrupção (player)."""

from voxcoach.tts.base import AudioChunk, TTSProvider
from voxcoach.tts.edge import EdgeTTSProvider
from voxcoach.tts.player import AudioPlayer, decode_audio

__all__ = ["AudioChunk", "TTSProvider", "EdgeTTSProvider", "AudioPlayer", "decode_audio"]
