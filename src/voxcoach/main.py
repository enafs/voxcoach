"""Entrypoint do VoxCoach com system tray (US01, D03).

Arquitetura de concorrência (D11): o tray (``pystray``) bloqueia a thread em que
roda, então fica na main thread; a engine roda em **outra thread** com seu event
loop (ver ``engine.py``). O tray só dispara comandos start/stop/quit.

``pystray`` e ``Pillow`` são importados de forma tardia — só quando o app é
lançado de fato (não no import do módulo).
"""

from __future__ import annotations

from voxcoach.adapters.lol import LoLAdapter
from voxcoach.engine import Engine
from voxcoach.factory import build_llm
from voxcoach.orchestrator import Orchestrator
from voxcoach.processor import Processor, TriggerPolicy
from voxcoach.tts.edge import EdgeTTSProvider
from voxcoach.tts.player import AudioPlayer
from voxcoach.voice import VoiceSpeaker


def build_engine() -> Engine:
    """Monta a engine real (adapter de LoL + LLM + voz) a partir da config."""
    from voxcoach.config import load_settings

    settings = load_settings()
    adapter = LoLAdapter()
    speaker = VoiceSpeaker(
        EdgeTTSProvider(voice=settings.tts_voice, rate=settings.tts_rate),
        AudioPlayer(),
    )
    orchestrator = Orchestrator(
        adapter=adapter,
        processor=Processor(),
        policy=TriggerPolicy(cooldown_seconds=settings.speak_cooldown_seconds),
        speaker=speaker,
        llm=build_llm(settings),
        max_tokens=settings.llm_max_tokens,
        poll_interval=settings.poll_interval_seconds,
    )
    return Engine(orchestrator)


def _make_icon_image():
    from PIL import Image, ImageDraw

    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse((8, 8, 56, 56), fill=(70, 150, 255, 255))   # disco azul
    draw.ellipse((26, 26, 38, 38), fill=(255, 255, 255, 255))  # ponto central
    return img


def main() -> None:
    import pystray

    engine = build_engine()

    def on_start(icon, item):
        engine.start()

    def on_stop(icon, item):
        engine.stop()

    def on_quit(icon, item):
        engine.shutdown()
        icon.stop()

    menu = pystray.Menu(
        pystray.MenuItem("Iniciar", on_start),
        pystray.MenuItem("Parar", on_stop),
        pystray.MenuItem("Sair", on_quit),
    )
    icon = pystray.Icon("voxcoach", _make_icon_image(), "VoxCoach", menu)
    icon.run()


if __name__ == "__main__":
    main()
