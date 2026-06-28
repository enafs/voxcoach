"""Testes do Processor e da TriggerPolicy.

Usa GameStates mínimos construídos à mão (agnóstico de jogo), não a fixture de
LoL — o processor trabalha só com o modelo normalizado.
"""

from __future__ import annotations

from voxcoach.models import (
    Entity,
    EventType,
    Game,
    GameEvent,
    GameState,
    PlayerState,
    Team,
)
from voxcoach.processor import Insight, Layer, Priority, Processor, TriggerPolicy


def make_state(
    *,
    game_time: float = 100.0,
    level: int = 5,
    health: float = 1000.0,
    max_health: float = 1000.0,
    alive: bool = True,
    events: list[GameEvent] | None = None,
    enemies: list[Entity] | None = None,
) -> GameState:
    return GameState(
        game=Game.LOL,
        game_time=game_time,
        player=PlayerState(
            name="Me", champion="Ahri", level=level,
            health=health, max_health=max_health, alive=alive,
        ),
        teammates=[],
        enemies=enemies or [],
        events=events or [],
    )


# --------------------------------------------------------------------------- #
# Processor — detecção de eventos novos
# --------------------------------------------------------------------------- #


def test_new_events_emitted_once():
    proc = Processor()
    kill = GameEvent(type=EventType.PLAYER_KILL, game_time=100.0, actor="Me", target="X")

    first = proc.process(make_state(events=[kill]))
    assert any(i.kind == "player_kill" for i in first)

    # Mesmo evento no próximo tick (lista cumulativa) não reaparece.
    second = proc.process(make_state(events=[kill]))
    assert not any(i.kind == "player_kill" for i in second)


def test_death_emits_analysis_only():
    proc = Processor()
    death = GameEvent(type=EventType.PLAYER_DEATH, game_time=120.0, actor="Enemy", target="Me")
    insights = proc.process(make_state(events=[death]))

    # Morte é momento de coaching, não de constatar o óbvio → só ANALYSIS.
    assert not any(i.kind == "player_death" for i in insights)
    analysis = next(i for i in insights if i.kind == "post_death_advice")
    assert analysis.layer is Layer.ANALYSIS
    assert analysis.text is None and analysis.context
    assert analysis.priority is Priority.HIGH


def test_objective_side_detection():
    proc = Processor()
    enemies = [Entity(name="EnemyJg", team=Team.ENEMY, champion="Kha'Zix")]
    drake = GameEvent(type=EventType.OBJECTIVE_TAKEN, game_time=400.0, actor="EnemyJg")
    insights = proc.process(make_state(events=[drake], enemies=enemies))

    lost = next(i for i in insights if i.kind == "objective_lost")
    assert lost.priority is Priority.HIGH


# --------------------------------------------------------------------------- #
# Processor — diferença de estado
# --------------------------------------------------------------------------- #


def test_level_up_detected():
    proc = Processor()
    proc.process(make_state(level=5))
    insights = proc.process(make_state(level=6))
    level = next(i for i in insights if i.kind == "level_up")
    assert level.text == "Nível 6."


def test_low_health_crossing_is_critical_and_interrupts():
    proc = Processor()
    proc.process(make_state(health=900.0, max_health=1000.0))   # 90%
    insights = proc.process(make_state(health=200.0, max_health=1000.0))  # 20%
    low = next(i for i in insights if i.kind == "low_health")
    assert low.priority is Priority.HIGH and low.interrupt is True


def test_low_health_not_retriggered_while_still_low():
    proc = Processor()
    proc.process(make_state(health=900.0, max_health=1000.0))
    proc.process(make_state(health=200.0, max_health=1000.0))   # cruza
    insights = proc.process(make_state(health=150.0, max_health=1000.0))  # segue baixo
    assert not any(i.kind == "low_health" for i in insights)


def test_reset_on_new_match():
    proc = Processor()
    kill = GameEvent(type=EventType.PLAYER_KILL, game_time=100.0, actor="Me", target="X")
    proc.process(make_state(events=[kill, kill]))
    # Lista de eventos encolhe → nova partida; evento volta a ser "novo".
    insights = proc.process(make_state(events=[kill]))
    assert any(i.kind == "player_kill" for i in insights)


# --------------------------------------------------------------------------- #
# TriggerPolicy
# --------------------------------------------------------------------------- #


def low(kind="a"):
    return Insight(kind, Layer.FACT, Priority.LOW, "x")


def critical(kind="crit"):
    return Insight(kind, Layer.FACT, Priority.HIGH, "y", interrupt=True)


def test_picks_highest_priority():
    policy = TriggerPolicy()
    chosen = policy.select([low("a"), critical("b")], now=0.0)
    assert chosen.kind == "b"


def test_cooldown_suppresses_second_low():
    policy = TriggerPolicy(cooldown_seconds=8.0)
    assert policy.select([low("a")], now=0.0) is not None
    assert policy.select([low("b")], now=3.0) is None      # dentro do cooldown
    assert policy.select([low("c")], now=9.0) is not None   # cooldown passou


def test_critical_bypasses_cooldown():
    policy = TriggerPolicy(cooldown_seconds=8.0)
    policy.select([low("a")], now=0.0)
    chosen = policy.select([critical("c")], now=1.0)        # logo após uma fala
    assert chosen is not None and chosen.kind == "c"


def test_combat_suppresses_non_critical():
    policy = TriggerPolicy()
    assert policy.select([low("a")], now=0.0, in_combat=True) is None
    assert policy.select([critical("c")], now=0.0, in_combat=True) is not None


def test_dedupe_same_kind():
    policy = TriggerPolicy(cooldown_seconds=0.0, dedupe_seconds=20.0)
    assert policy.select([low("same")], now=0.0) is not None
    assert policy.select([low("same")], now=5.0) is None      # mesmo kind, dedupe
    assert policy.select([low("same")], now=21.0) is not None  # dedupe expirou
