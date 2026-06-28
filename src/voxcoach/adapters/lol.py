"""Adapter de League of Legends — Live Client Data API (MVP, D08).

Fonte oficial e local da Riot: ``https://127.0.0.1:2999/liveclientdata/...``.
Roda durante a partida, sem injeção nem leitura de memória (D06/US07).

A normalização (cru -> ``GameState``) é uma função **pura** (``normalize_all_game_data``)
para ser testável sem rede; o ``LoLAdapter`` cuida apenas do HTTP.

Limitações conhecidas da Live API (refletidas na normalização):
- Não expõe coordenadas (x, y) ao vivo — apenas a *role* (lane). ``position`` fica ``None``.
- Não expõe timers de objetivo (dragão/barão); ``objectives`` fica vazio por ora.
"""

from __future__ import annotations

from typing import Any

import httpx

from voxcoach.adapters.base import GameAdapter
from voxcoach.models import (
    Entity,
    EventType,
    Game,
    GameEvent,
    GameState,
    PlayerState,
    Team,
)

LIVE_API_BASE = "https://127.0.0.1:2999"
ALL_GAME_DATA = "/liveclientdata/allgamedata"
GAME_STATS = "/liveclientdata/gamestats"

# EventName cru da Live API -> evento de objetivo (independe do jogador).
_OBJECTIVE_EVENTS = {"DragonKill", "BaronKill", "HeraldKill", "TurretKilled", "InhibKilled"}


class LoLAdapter(GameAdapter):
    """Lê a Live Client Data API e normaliza para ``GameState``."""

    game = "lol"

    def __init__(
        self,
        base_url: str = LIVE_API_BASE,
        *,
        timeout: float = 2.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        # verify=False: a Live API usa certificado self-signed em localhost (SDD 4.1 / US07).
        self._client = client or httpx.AsyncClient(
            base_url=base_url, verify=False, timeout=timeout
        )

    async def is_game_active(self) -> bool:
        try:
            resp = await self._client.get(GAME_STATS)
        except httpx.HTTPError:
            return False
        return resp.status_code == 200

    async def fetch_state(self) -> GameState | None:
        try:
            resp = await self._client.get(ALL_GAME_DATA)
        except httpx.HTTPError:
            return None
        if resp.status_code != 200:
            return None
        return normalize_all_game_data(resp.json())

    async def close(self) -> None:
        await self._client.aclose()


# --------------------------------------------------------------------------- #
# Normalização pura (testável sem rede)
# --------------------------------------------------------------------------- #


def normalize_all_game_data(data: dict[str, Any]) -> GameState | None:
    """Traduz o payload de ``allgamedata`` para ``GameState``.

    Retorna ``None`` quando o jogador local não é identificável (ex.: modo
    espectador), pois sem o "eu" não há contexto de coaching.
    """
    active = data.get("activePlayer") or {}
    all_players = data.get("allPlayers") or []
    game_data = data.get("gameData") or {}

    active_name = _active_player_name(active)
    me = _find_player(all_players, active_name)
    if me is None:
        return None

    my_team = me.get("team")
    stats = active.get("championStats") or {}
    scores = me.get("scores") or {}

    player = PlayerState(
        name=active_name or me.get("summonerName", "unknown"),
        champion=me.get("championName"),
        level=int(active.get("level", me.get("level", 1))),
        health=float(stats.get("currentHealth", 0.0)),
        max_health=float(stats.get("maxHealth", 0.0)),
        resource=float(stats.get("resourceValue", 0.0)),
        max_resource=float(stats.get("resourceMax", 0.0)),
        gold=float(active.get("currentGold", 0.0)),
        kills=int(scores.get("kills", 0)),
        deaths=int(scores.get("deaths", 0)),
        assists=int(scores.get("assists", 0)),
        alive=not me.get("isDead", False),
        items=[it.get("displayName", "") for it in (me.get("items") or [])],
    )

    teammates: list[Entity] = []
    enemies: list[Entity] = []
    for p in all_players:
        if p is me:
            continue
        team = Team.ALLY if p.get("team") == my_team else Team.ENEMY
        entity = Entity(
            name=p.get("summonerName") or p.get("riotIdGameName") or "unknown",
            team=team,
            champion=p.get("championName"),
            level=p.get("level"),
            alive=not p.get("isDead", False),
        )
        (teammates if team is Team.ALLY else enemies).append(entity)

    events = _normalize_events(
        (data.get("events") or {}).get("Events", []), active_name
    )

    return GameState(
        game=Game.LOL,
        game_time=float(game_data.get("gameTime", 0.0)),
        player=player,
        teammates=teammates,
        enemies=enemies,
        objectives=[],  # Live API não expõe timers de objetivo (ver módulo docstring)
        events=events,
        raw=data,
    )


def _active_player_name(active: dict[str, Any]) -> str | None:
    """Nome do jogador local. Em patches recentes pode vir como Riot ID."""
    return active.get("summonerName") or active.get("riotIdGameName")


def _find_player(
    players: list[dict[str, Any]], name: str | None
) -> dict[str, Any] | None:
    if not name:
        return None
    for p in players:
        if p.get("summonerName") == name or p.get("riotIdGameName") == name:
            return p
    return None


def _normalize_events(
    raw_events: list[dict[str, Any]], active_name: str | None
) -> list[GameEvent]:
    out: list[GameEvent] = []
    for ev in raw_events:
        name = ev.get("EventName", "")
        actor = ev.get("KillerName")
        target = ev.get("VictimName")
        etype = EventType.OTHER

        if name == "ChampionKill":
            if target == active_name:
                etype = EventType.PLAYER_DEATH
            elif actor == active_name:
                etype = EventType.PLAYER_KILL
            elif active_name in (ev.get("Assisters") or []):
                etype = EventType.PLAYER_ASSIST
        elif name in _OBJECTIVE_EVENTS:
            etype = EventType.OBJECTIVE_TAKEN

        out.append(
            GameEvent(
                type=etype,
                game_time=float(ev.get("EventTime", 0.0)),
                actor=actor,
                target=target,
                data=ev,
            )
        )
    return out
