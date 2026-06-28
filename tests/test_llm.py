"""Testes do provider de LLM e da montagem de prompt.

A SDK da Anthropic é **mockada** — nenhum token é gasto e nenhuma key é exigida.
"""

from __future__ import annotations

import pytest

from voxcoach.llm.claude import ClaudeProvider, _extract_text
from voxcoach.llm.prompts import SYSTEM_PROMPT, build_context
from voxcoach.models import Entity, Game, GameState, PlayerState, Team


# --------------------------------------------------------------------------- #
# build_context
# --------------------------------------------------------------------------- #


def _state() -> GameState:
    return GameState(
        game=Game.LOL,
        game_time=542.0,
        player=PlayerState(
            name="Me", champion="Ahri", level=9,
            health=1240.0, max_health=1680.0, gold=2456.0,
            kills=3, deaths=1, assists=5, items=["Luden's Companion"],
        ),
        teammates=[Entity(name="A", team=Team.ALLY, champion="Lee Sin")],
        enemies=[Entity(name="E", team=Team.ENEMY, champion="Zed")],
    )


def test_build_context_summarizes_state():
    ctx = build_context(_state(), hint="o jogador morreu; oriente o respawn")
    assert "Ahri nível 9" in ctx
    assert "KDA 3/1/5" in ctx
    assert "9min02s" in ctx           # 542s -> 9min02s
    assert "Zed" in ctx               # inimigo
    assert "Lee Sin" in ctx           # aliado
    assert "Luden's Companion" in ctx
    assert "oriente o respawn" in ctx


def test_build_context_without_hint_omits_situation():
    ctx = build_context(_state())
    assert "Situação:" not in ctx


def test_system_prompt_is_short_ptbr_and_clean():
    assert "português" in SYSTEM_PROMPT.lower()
    assert "frase curta" in SYSTEM_PROMPT.lower()
    # Deve proibir explicitamente linguagem ofensiva.
    assert "palavr" in SYSTEM_PROMPT.lower()  # palavrões/palavrão


# --------------------------------------------------------------------------- #
# ClaudeProvider (SDK mockada)
# --------------------------------------------------------------------------- #


class _Block:
    def __init__(self, text: str) -> None:
        self.text = text


class _Response:
    def __init__(self, blocks: list[_Block]) -> None:
        self.content = blocks


class _Messages:
    def __init__(self, response: _Response, recorder: dict) -> None:
        self._response = response
        self._recorder = recorder

    async def create(self, **kwargs):
        self._recorder.update(kwargs)
        return self._response


class _FakeClient:
    def __init__(self, response: _Response, recorder: dict) -> None:
        self.messages = _Messages(response, recorder)
        self.closed = False

    async def close(self) -> None:
        self.closed = True


def _provider(blocks: list[_Block]):
    recorder: dict = {}
    client = _FakeClient(_Response(blocks), recorder)
    return ClaudeProvider(model="m", client=client), recorder, client


async def test_generate_insight_returns_text_and_passes_params():
    provider, recorder, _ = _provider([_Block("  Recue e farme top.  ")])
    out = await provider.generate_insight("SYS", "CTX", max_tokens=50)

    assert out == "Recue e farme top."          # strip aplicado
    assert recorder["model"] == "m"
    assert recorder["max_tokens"] == 50
    assert recorder["system"] == "SYS"
    assert recorder["messages"] == [{"role": "user", "content": "CTX"}]


async def test_close_awaits_client_close():
    provider, _, client = _provider([_Block("x")])
    await provider.close()
    assert client.closed is True


def test_extract_text_joins_blocks_and_ignores_non_text():
    resp = _Response([_Block("Foco "), object(), _Block("no objetivo.")])
    assert _extract_text(resp) == "Foco no objetivo."
