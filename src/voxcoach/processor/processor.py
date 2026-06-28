"""Detecção de eventos e produção de insights (SDD §3, D09).

O Processor é *stateful*: guarda o tick anterior e quantos eventos já viu, para
detectar o que **mudou**. Ele traduz mudanças do ``GameState`` em ``Insight``s,
cada um classificado em uma **camada de processamento**:

- ``Layer.FACT`` (Camada 1): fato determinístico, frase pronta, **sem LLM**.
- ``Layer.ANALYSIS`` (Camada 2): exige julgamento → preenchido pelo LLM depois.

Este módulo é o "catálogo" específico de jogo previsto em D09: que mudança vira
que insight. A política de *quando* falar fica em ``triggers.py``.

Nota sobre eventos: a Live API do LoL devolve a lista de eventos **cumulativa**
desde o início da partida. Por isso comparamos pela contagem já vista, não pelo
conteúdo de um único tick.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum

from voxcoach.models import EventType, GameEvent, GameState, Team

LOW_HEALTH_RATIO = 0.30


class Layer(IntEnum):
    FACT = 1       # Camada 1 — determinístico, sem LLM
    ANALYSIS = 2   # Camada 2 — requer LLM


class Priority(IntEnum):
    LOW = 10
    MEDIUM = 20
    HIGH = 30
    CRITICAL = 40


@dataclass
class Insight:
    """Algo que *pode* ser falado. A decisão final é da TriggerPolicy."""

    kind: str                      # identificador estável (p/ dedupe), ex.: "level_up"
    layer: Layer
    priority: Priority
    text: str | None = None        # FACT: frase pronta; ANALYSIS: None (LLM preenche)
    interrupt: bool = False        # pode cortar a fala atual (alertas críticos)
    context: str | None = None     # ANALYSIS: dica de contexto p/ o prompt do LLM


class Processor:
    def __init__(self) -> None:
        self._prev: GameState | None = None
        self._seen_events = 0

    def reset(self) -> None:
        """Zera o estado (ex.: ao trocar de partida)."""
        self._prev = None
        self._seen_events = 0

    def process(self, state: GameState) -> list[Insight]:
        """Compara com o tick anterior e devolve os insights candidatos."""
        insights: list[Insight] = []

        # Nova partida (lista de eventos encolheu) → recomeça a contagem.
        if len(state.events) < self._seen_events:
            self._seen_events = 0

        new_events = state.events[self._seen_events :]
        self._seen_events = len(state.events)
        for ev in new_events:
            insights.extend(self._from_event(ev, state))

        if self._prev is not None:
            insights.extend(self._from_diff(self._prev, state))

        self._prev = state
        return insights

    # --- detectores por evento (Camada 1 + gatilhos de Camada 2) ---

    def _from_event(self, ev: GameEvent, state: GameState) -> list[Insight]:
        out: list[Insight] = []

        # Cada gatilho produz UM insight; o processor decide a camada (D09).
        if ev.type is EventType.PLAYER_DEATH:
            # Dizer "você morreu" é óbvio (ruído); o valor está no conselho → ANALYSIS.
            out.append(
                Insight(
                    "post_death_advice",
                    Layer.ANALYSIS,
                    Priority.HIGH,
                    context="o jogador morreu; oriente o uso do tempo de respawn e o "
                    "reposicionamento ao voltar",
                )
            )

        elif ev.type is EventType.PLAYER_KILL:
            out.append(Insight("player_kill", Layer.FACT, Priority.LOW, "Abate confirmado."))

        elif ev.type is EventType.OBJECTIVE_TAKEN:
            if _side_of(ev.actor, state) is Team.ENEMY:
                out.append(
                    Insight("objective_lost", Layer.FACT, Priority.HIGH,
                            "Os inimigos pegaram um objetivo.")
                )
            else:
                out.append(
                    Insight("objective_taken", Layer.FACT, Priority.MEDIUM,
                            "Seu time pegou um objetivo.")
                )

        return out

    # --- detectores por diferença de estado ---

    def _from_diff(self, prev: GameState, state: GameState) -> list[Insight]:
        out: list[Insight] = []
        p_now, p_prev = state.player, prev.player

        if p_now.level > p_prev.level:
            out.append(
                Insight("level_up", Layer.FACT, Priority.LOW, f"Nível {p_now.level}.")
            )

        if _crossed_below(p_prev, p_now, LOW_HEALTH_RATIO) and p_now.alive:
            out.append(
                Insight(
                    "low_health",
                    Layer.FACT,
                    Priority.HIGH,
                    "Vida baixa, recue.",
                    interrupt=True,
                )
            )

        return out


# --------------------------------------------------------------------------- #
# Helpers puros
# --------------------------------------------------------------------------- #


def _health_ratio(player) -> float | None:
    if player.max_health <= 0:
        return None
    return player.health / player.max_health


def _crossed_below(prev, now, ratio: float) -> bool:
    """True se a vida cruzou de >= ratio para < ratio entre os ticks."""
    before, after = _health_ratio(prev), _health_ratio(now)
    if before is None or after is None:
        return False
    return before >= ratio > after


def _side_of(name: str | None, state: GameState) -> Team | None:
    if not name:
        return None
    if name == state.player.name or any(e.name == name for e in state.teammates):
        return Team.ALLY
    if any(e.name == name for e in state.enemies):
        return Team.ENEMY
    return None
