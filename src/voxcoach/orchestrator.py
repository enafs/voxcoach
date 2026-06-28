"""Orchestrator — o loop de sessão que costura o pipeline (SDD §2.2, §3).

Fluxo por tick:
    adapter.fetch_state() -> processor.process() -> triggers.select()
        -> FACT: usa a frase pronta
        -> ANALYSIS: chama o LLM (se houver) p/ gerar a recomendação
        -> speaker.speak(text)

A **saída** é abstraída por ``Speaker`` para trocar console ↔ voz (TTS) sem
tocar no core. O **relógio** é injetável (``clock``) para testes determinísticos.
"""

from __future__ import annotations

import asyncio
import time
from abc import ABC, abstractmethod
from typing import Callable

from voxcoach.adapters.base import GameAdapter
from voxcoach.llm.base import LLMProvider
from voxcoach.llm.prompts import SYSTEM_PROMPT, build_context
from voxcoach.models import GameState
from voxcoach.processor import Insight, Processor, TriggerPolicy

# Sinais de combate ativo (suprime falas não-críticas — SDD 3.1). Mínimo e honesto:
# a Live API não dá posições, então detecção de teamfight rica fica como trabalho
# futuro. "low_health" é o sinal de perigo imediato disponível hoje.
_COMBAT_KINDS = {"low_health"}


class Speaker(ABC):
    """Consome o texto final de um insight (console, voz, ...)."""

    @abstractmethod
    async def speak(self, text: str, *, interrupt: bool = False) -> None: ...


def is_combat(insights: list[Insight]) -> bool:
    return any(i.kind in _COMBAT_KINDS for i in insights)


class Orchestrator:
    def __init__(
        self,
        adapter: GameAdapter,
        processor: Processor,
        policy: TriggerPolicy,
        speaker: Speaker,
        *,
        llm: LLMProvider | None = None,
        max_tokens: int = 120,
        poll_interval: float = 1.5,
        idle_interval: float = 3.0,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._adapter = adapter
        self._processor = processor
        self._policy = policy
        self._speaker = speaker
        self._llm = llm
        self._max_tokens = max_tokens
        self._poll_interval = poll_interval
        self._idle_interval = idle_interval
        self._clock = clock
        self._running = False

    def stop(self) -> None:
        self._running = False

    async def run(self) -> None:
        """Loop principal: detecta partida, faz polling, encerra ao fim."""
        self._running = True
        in_session = False
        while self._running:
            active = await self._adapter.is_game_active()

            if active and not in_session:
                in_session = True
                self._processor.reset()
            elif not active and in_session:
                in_session = False

            if active:
                state = await self._adapter.fetch_state()
                if state is not None:
                    await self.tick(state)

            await asyncio.sleep(self._poll_interval if active else self._idle_interval)

    async def tick(self, state: GameState) -> str | None:
        """Processa um estado e narra no máximo um insight. Retorna o texto falado."""
        insights = self._processor.process(state)
        chosen = self._policy.select(
            insights, now=self._clock(), in_combat=is_combat(insights)
        )
        if chosen is None:
            return None
        return await self._handle(chosen, state)

    async def _handle(self, insight: Insight, state: GameState) -> str | None:
        text = insight.text
        if text is None:  # Camada 2 (ANALYSIS) — precisa do LLM
            if self._llm is None:
                return None  # sem LLM configurado: pula a recomendação analítica
            context = build_context(state, insight.context)
            text = await self._llm.generate_insight(
                SYSTEM_PROMPT, context, max_tokens=self._max_tokens
            )
        if not text:
            return None
        await self._speaker.speak(text, interrupt=insight.interrupt)
        return text
