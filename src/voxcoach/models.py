"""Modelo de dados normalizado do VoxCoach.

Todo adapter de jogo traduz o formato cru da sua fonte (Live Client Data API,
GSI, ...) para estas estruturas. O Processor e o LLM trabalham **apenas** com
``GameState`` — nunca com o formato cru. É isso que torna a arquitetura
agnóstica de jogo (ver SDD 2.3 e D02).

Usamos ``dataclass`` (e não pydantic) de propósito: o estado é construído a
cada tick no loop quente; queremos zero overhead de validação aqui. A validação
fica na fronteira de configuração (``config.py``).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Game(str, Enum):
    LOL = "lol"
    CS2 = "cs2"


class Team(str, Enum):
    ALLY = "ally"
    ENEMY = "enemy"
    NEUTRAL = "neutral"


class EventType(str, Enum):
    """Eventos genéricos, agnósticos de jogo.

    Cada adapter mapeia seus eventos crus para um destes. ``OTHER`` cobre o que
    ainda não foi modelado (o dado cru fica em ``GameEvent.data``).
    """

    PLAYER_DEATH = "player_death"
    PLAYER_KILL = "player_kill"
    PLAYER_ASSIST = "player_assist"
    LEVEL_UP = "level_up"
    OBJECTIVE_SPAWNED = "objective_spawned"
    OBJECTIVE_TAKEN = "objective_taken"
    ITEM_PURCHASED = "item_purchased"
    OTHER = "other"


@dataclass
class Position:
    x: float
    y: float
    z: float | None = None


@dataclass
class PlayerState:
    """Estado do jogador local (o usuário do app)."""

    name: str
    champion: str | None = None       # campeão / herói / agente
    level: int = 1
    health: float = 0.0
    max_health: float = 0.0
    resource: float = 0.0             # mana / energia / etc.
    max_resource: float = 0.0
    gold: float = 0.0
    kills: int = 0
    deaths: int = 0
    assists: int = 0
    alive: bool = True
    position: Position | None = None
    items: list[str] = field(default_factory=list)


@dataclass
class Entity:
    """Outro participante da partida (aliado ou inimigo)."""

    name: str
    team: Team
    champion: str | None = None
    level: int | None = None
    alive: bool = True
    position: Position | None = None


@dataclass
class Objective:
    """Objetivo de mapa: dragão, barão, arauto, bomb site, etc."""

    name: str
    available: bool = False
    seconds_until: float | None = None   # tempo até spawnar / expirar
    controlled_by: Team | None = None


@dataclass
class GameEvent:
    """Um evento detectado desde o último tick."""

    type: EventType
    game_time: float
    actor: str | None = None
    target: str | None = None
    data: dict[str, Any] = field(default_factory=dict)


@dataclass
class GameState:
    """Estado normalizado da partida num instante. Contrato central do app."""

    game: Game
    game_time: float                                     # segundos de partida
    player: PlayerState
    teammates: list[Entity] = field(default_factory=list)
    enemies: list[Entity] = field(default_factory=list)
    objectives: list[Objective] = field(default_factory=list)
    events: list[GameEvent] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)    # dados crus (fallback)
