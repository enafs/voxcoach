"""CLI do VoxCoach.

Modos:
- ``--replay <allgamedata.json>``: roda o pipeline sobre uma fixture, **sem jogo
  e sem API key** (usa um LLM simulado). Demonstra o fluxo ponta a ponta.
- (padrão): modo *live* — adapter real de LoL, saída em **texto no console**.
  A fala por voz (TTS) será ligada junto com o tray.

Saída atual: ``ConsoleSpeaker`` (texto). Trocar para voz é só usar outro Speaker.
"""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from voxcoach.adapters.lol import LoLAdapter, normalize_all_game_data
from voxcoach.llm.base import LLMProvider
from voxcoach.orchestrator import Orchestrator, Speaker
from voxcoach.processor import Processor, TriggerPolicy

# `config` (pydantic-settings) só é necessário no modo live — importado lá dentro.


class ConsoleSpeaker(Speaker):
    """Imprime o insight no console (sem áudio). Marca alertas críticos."""

    async def speak(self, text: str, *, interrupt: bool = False) -> None:
        marker = "[ALERTA] " if interrupt else "[dica]   "
        print(f"{marker}{text}", flush=True)


class _StubLLM(LLMProvider):
    """LLM simulado p/ o modo replay: sem rede, sem custo."""

    async def generate_insight(self, system_prompt, context, *, max_tokens=120):
        situacao = next(
            (ln[len("Situação: ") :] for ln in context.splitlines()
             if ln.startswith("Situação: ")),
            "recomendação tática",
        )
        return f"(análise simulada) considere: {situacao}"


def _build_llm(settings):
    """Cria o provider real conforme a config; None se não houver key."""
    from voxcoach.config import LLMBackend

    if settings.llm_backend is LLMBackend.CLAUDE and settings.anthropic_api_key:
        from voxcoach.llm.claude import ClaudeProvider

        return ClaudeProvider(api_key=settings.anthropic_api_key, model=settings.llm_model)
    return None


async def _run_replay(path: Path, ticks: int) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    state = normalize_all_game_data(data)
    if state is None:
        print("Não foi possível identificar o jogador local na fixture.")
        return

    orch = Orchestrator(
        adapter=None,            # não usado no replay (chamamos tick direto)
        processor=Processor(),
        policy=TriggerPolicy(cooldown_seconds=0.0),  # demo: não engole insights
        speaker=ConsoleSpeaker(),
        llm=_StubLLM(),
        clock=_step_clock(),
    )

    print(f"== replay: {path.name} ({ticks} tick(s)) ==")
    for i in range(ticks):
        spoken = await orch.tick(state)
        if spoken is None:
            print(f"(tick {i + 1}: nada a falar)")


async def _run_live() -> None:
    from voxcoach.config import load_settings

    settings = load_settings()
    adapter = LoLAdapter()
    orch = Orchestrator(
        adapter=adapter,
        processor=Processor(),
        policy=TriggerPolicy(cooldown_seconds=settings.speak_cooldown_seconds),
        speaker=ConsoleSpeaker(),
        llm=_build_llm(settings),
        max_tokens=settings.llm_max_tokens,
        poll_interval=settings.poll_interval_seconds,
    )
    print("VoxCoach (modo live, saída em texto). Ctrl+C para sair.")
    try:
        await orch.run()
    except KeyboardInterrupt:
        orch.stop()
    finally:
        await adapter.close()


def _step_clock():
    """Relógio incremental p/ o replay (cada chamada avança 1 'segundo')."""
    t = {"v": 0.0}

    def clock() -> float:
        t["v"] += 1.0
        return t["v"]

    return clock


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="voxcoach", description="Coach de jogo por voz.")
    parser.add_argument(
        "--replay", metavar="ARQUIVO",
        help="roda o pipeline sobre uma fixture de allgamedata (sem jogo/sem key)",
    )
    parser.add_argument(
        "--ticks", type=int, default=2,
        help="quantos ticks simular no replay (padrão: 2)",
    )
    args = parser.parse_args(argv)

    if args.replay:
        asyncio.run(_run_replay(Path(args.replay), args.ticks))
    else:
        asyncio.run(_run_live())


if __name__ == "__main__":
    main()
