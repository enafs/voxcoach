"""Testes do Orchestrator (pipeline costurado), com dublês para adapter/LLM."""

from __future__ import annotations

import itertools

from voxcoach.llm.base import LLMProvider
from voxcoach.models import (
    EventType,
    Game,
    GameEvent,
    GameState,
    PlayerState,
)
from voxcoach.orchestrator import Orchestrator, Speaker, is_combat
from voxcoach.processor import Insight, Layer, Priority, Processor, TriggerPolicy


# --------------------------------------------------------------------------- #
# Dublês
# --------------------------------------------------------------------------- #


class RecordingSpeaker(Speaker):
    def __init__(self):
        self.spoken: list[tuple[str, bool]] = []

    async def speak(self, text: str, *, interrupt: bool = False) -> None:
        self.spoken.append((text, interrupt))


class StubLLM(LLMProvider):
    def __init__(self, reply="ANALISE"):
        self.reply = reply
        self.calls: list[tuple[str, str, int]] = []

    async def generate_insight(self, system_prompt, context, *, max_tokens=120):
        self.calls.append((system_prompt, context, max_tokens))
        return self.reply


class FakeAdapter:
    game = "lol"

    def __init__(self, active=True, states=None):
        self.active = active
        self._states = list(states or [])

    async def is_game_active(self) -> bool:
        return self.active

    async def fetch_state(self):
        return self._states.pop(0) if self._states else None

    async def close(self) -> None:
        pass


def make_state(*, level=5, health=1000.0, events=None) -> GameState:
    return GameState(
        game=Game.LOL,
        game_time=100.0,
        player=PlayerState(
            name="Me", champion="Ahri", level=level,
            health=health, max_health=1000.0,
        ),
        events=events or [],
    )


def _clock():
    return itertools.count(start=0, step=10).__next__


# --------------------------------------------------------------------------- #
# is_combat
# --------------------------------------------------------------------------- #


def test_is_combat_detects_combat_kinds():
    assert is_combat([Insight("low_health", Layer.FACT, Priority.HIGH, "x")]) is True
    assert is_combat([Insight("player_kill", Layer.FACT, Priority.LOW, "x")]) is False


# --------------------------------------------------------------------------- #
# tick
# --------------------------------------------------------------------------- #


async def _orch(speaker, llm=None, policy=None):
    return Orchestrator(
        adapter=FakeAdapter(),
        processor=Processor(),
        policy=policy or TriggerPolicy(cooldown_seconds=0.0),
        speaker=speaker,
        llm=llm,
        clock=_clock(),
    )


async def test_fact_insight_spoken_with_ready_text():
    speaker = RecordingSpeaker()
    orch = await _orch(speaker)
    # Subir de nível entre dois ticks gera um FACT com texto pronto.
    await orch.tick(make_state(level=5))
    await orch.tick(make_state(level=6))
    assert ("Nível 6.", False) in speaker.spoken


async def test_analysis_insight_calls_llm_and_speaks_reply():
    speaker = RecordingSpeaker()
    llm = StubLLM(reply="Recue e farme.")
    orch = await _orch(speaker, llm=llm)

    death = GameEvent(type=EventType.PLAYER_DEATH, game_time=120.0, actor="E", target="Me")
    await orch.tick(make_state(events=[death]))

    assert llm.calls, "o LLM deveria ter sido chamado para a Camada 2"
    assert any(text == "Recue e farme." for text, _ in speaker.spoken)


async def test_analysis_skipped_without_llm():
    speaker = RecordingSpeaker()
    orch = await _orch(speaker, llm=None)
    # Morte gera só ANALYSIS; sem LLM, nada é falado.
    death_only = [GameEvent(type=EventType.PLAYER_DEATH, game_time=1.0, target="Me")]
    spoken = await orch.tick(make_state(events=death_only))
    assert spoken is None
    assert speaker.spoken == []


async def test_combat_suppresses_non_critical():
    speaker = RecordingSpeaker()
    orch = await _orch(speaker)
    # Tick 1 estabelece vida alta; tick 2 cruza p/ vida baixa (combate) e sobe nível.
    await orch.tick(make_state(level=5, health=900.0))
    await orch.tick(make_state(level=6, health=150.0))
    spoken_texts = [t for t, _ in speaker.spoken]
    # low_health (HIGH) fala e marca combate; level_up (LOW) é suprimido.
    assert "Vida baixa, recue." in spoken_texts
    assert "Nível 6." not in spoken_texts


# --------------------------------------------------------------------------- #
# run (ciclo de vida)
# --------------------------------------------------------------------------- #


async def test_run_processes_then_stops():
    speaker = RecordingSpeaker()
    states = [make_state(level=5), make_state(level=6)]
    orch = Orchestrator(
        adapter=FakeAdapter(active=True, states=states),
        processor=Processor(),
        policy=TriggerPolicy(cooldown_seconds=0.0),
        speaker=speaker,
        clock=_clock(),
        poll_interval=0.0,
    )

    # Para o loop assim que algo for falado.
    original = speaker.speak

    async def speak_and_stop(text, *, interrupt=False):
        await original(text, interrupt=interrupt)
        orch.stop()

    speaker.speak = speak_and_stop  # type: ignore[method-assign]
    await orch.run()
    assert ("Nível 6.", False) in speaker.spoken
