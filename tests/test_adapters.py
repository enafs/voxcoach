"""Testes do adapter de LoL.

Dois grupos:
- Normalização **pura** (sem rede), usando a fixture de `allgamedata`.
- Comportamento do `LoLAdapter` com o HTTP mockado via `respx`.
"""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
import respx

from voxcoach.adapters.lol import (
    ALL_GAME_DATA,
    GAME_STATS,
    LIVE_API_BASE,
    LoLAdapter,
    normalize_all_game_data,
)
from voxcoach.models import EventType, Game, Team

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def allgamedata() -> dict:
    return json.loads((FIXTURES / "allgamedata.json").read_text(encoding="utf-8"))


# --------------------------------------------------------------------------- #
# Normalização pura
# --------------------------------------------------------------------------- #


def test_normalize_returns_gamestate(allgamedata):
    state = normalize_all_game_data(allgamedata)
    assert state is not None
    assert state.game is Game.LOL
    assert state.game_time == pytest.approx(542.3)


def test_player_identified_and_mapped(allgamedata):
    player = normalize_all_game_data(allgamedata).player
    assert player.name == "Faker"
    assert player.champion == "Ahri"
    assert player.level == 9
    assert (player.kills, player.deaths, player.assists) == (3, 1, 5)
    assert player.health == pytest.approx(1240.5)
    assert player.max_health == pytest.approx(1680.0)
    assert player.gold == pytest.approx(2456.7)
    assert player.alive is True
    assert "Luden's Companion" in player.items


def test_teams_split_correctly(allgamedata):
    state = normalize_all_game_data(allgamedata)
    # 10 jogadores no total; o "eu" não entra em nenhuma lista.
    assert len(state.teammates) == 4
    assert len(state.enemies) == 5
    assert all(e.team is Team.ALLY for e in state.teammates)
    assert all(e.team is Team.ENEMY for e in state.enemies)
    enemy_champs = {e.champion for e in state.enemies}
    assert {"Zed", "Kha'Zix", "Caitlyn", "Lux", "Darius"} == enemy_champs


def test_dead_entity_flagged(allgamedata):
    state = normalize_all_game_data(allgamedata)
    jinx = next(e for e in state.teammates if e.champion == "Jinx")
    assert jinx.alive is False


def test_events_mapped_relative_to_player(allgamedata):
    events = normalize_all_game_data(allgamedata).events
    kill = next(e for e in events if e.type is EventType.PLAYER_KILL)
    assert kill.actor == "Faker" and kill.target == "MidGap"

    death = next(e for e in events if e.type is EventType.PLAYER_DEATH)
    assert death.actor == "SpinToWin" and death.target == "Faker"

    assert any(e.type is EventType.OBJECTIVE_TAKEN for e in events)
    # Kill alheio (sem o jogador) não vira PLAYER_*; fica OTHER.
    others = [e for e in events if e.type is EventType.OTHER]
    assert any(e.data.get("EventName") == "ChampionKill" for e in others)


def test_returns_none_without_local_player(allgamedata):
    # Espectador: activePlayer não bate com ninguém em allPlayers.
    allgamedata["activePlayer"]["summonerName"] = "NoSuchPlayer"
    allgamedata["activePlayer"]["riotIdGameName"] = "NoSuchPlayer"
    assert normalize_all_game_data(allgamedata) is None


def test_raw_payload_preserved(allgamedata):
    state = normalize_all_game_data(allgamedata)
    assert state.raw is allgamedata  # fallback p/ dados não modelados


# --------------------------------------------------------------------------- #
# LoLAdapter (HTTP mockado)
# --------------------------------------------------------------------------- #


@respx.mock
async def test_is_game_active_true():
    respx.get(LIVE_API_BASE + GAME_STATS).mock(
        return_value=httpx.Response(200, json={"gameTime": 1.0})
    )
    adapter = LoLAdapter()
    try:
        assert await adapter.is_game_active() is True
    finally:
        await adapter.close()


@respx.mock
async def test_is_game_active_false_when_connection_refused():
    respx.get(LIVE_API_BASE + GAME_STATS).mock(
        side_effect=httpx.ConnectError("connection refused")
    )
    adapter = LoLAdapter()
    try:
        assert await adapter.is_game_active() is False
    finally:
        await adapter.close()


@respx.mock
async def test_fetch_state_returns_normalized(allgamedata):
    respx.get(LIVE_API_BASE + ALL_GAME_DATA).mock(
        return_value=httpx.Response(200, json=allgamedata)
    )
    adapter = LoLAdapter()
    try:
        state = await adapter.fetch_state()
    finally:
        await adapter.close()
    assert state is not None
    assert state.player.champion == "Ahri"
    assert len(state.enemies) == 5


@respx.mock
async def test_fetch_state_none_on_error():
    respx.get(LIVE_API_BASE + ALL_GAME_DATA).mock(
        side_effect=httpx.ConnectError("connection refused")
    )
    adapter = LoLAdapter()
    try:
        assert await adapter.fetch_state() is None
    finally:
        await adapter.close()
