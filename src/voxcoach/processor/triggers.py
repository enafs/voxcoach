"""Política de gatilhos / anti-spam (SDD §3.1).

Recebe os insights candidatos de um tick e decide **qual (se algum)** falar
agora, aplicando:

- **Prioridade**: escolhe o insight mais importante do tick.
- **Cooldown global**: no máximo uma fala comum a cada N segundos.
- **Bypass crítico**: insights de prioridade alta ignoram o cooldown e podem
  interromper a fala atual (ex.: "vida baixa, recue").
- **Silêncio em luta**: em combate, suprime falas não-críticas.
- **Dedupe/relevância**: não repete o mesmo tipo de insight em sequência.

O relógio é **injetado** (parâmetro ``now``) para manter a lógica determinística
e testável sem depender do tempo real.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from voxcoach.processor.processor import Insight, Priority


@dataclass
class TriggerPolicy:
    cooldown_seconds: float = 8.0
    dedupe_seconds: float = 20.0
    #: em combate, só fala insights com prioridade >= este limite
    combat_min_priority: Priority = Priority.HIGH
    #: prioridade a partir da qual o cooldown global é ignorado
    bypass_cooldown_priority: Priority = Priority.HIGH

    _last_spoken_at: float = field(default=float("-inf"), init=False)
    _recent_kinds: dict[str, float] = field(default_factory=dict, init=False)

    def select(
        self, insights: list[Insight], now: float, *, in_combat: bool = False
    ) -> Insight | None:
        """Escolhe no máximo um insight para falar agora, ou ``None``."""
        # Maior prioridade primeiro; FACT antes de ANALYSIS no empate (latência menor).
        for ins in sorted(insights, key=lambda i: (i.priority, -i.layer), reverse=True):
            if self._allowed(ins, now, in_combat):
                self._commit(ins, now)
                return ins
        return None

    def _allowed(self, ins: Insight, now: float, in_combat: bool) -> bool:
        critical = ins.priority >= self.bypass_cooldown_priority

        if in_combat and ins.priority < self.combat_min_priority:
            return False

        last_same = self._recent_kinds.get(ins.kind)
        if last_same is not None and (now - last_same) < self.dedupe_seconds:
            return False

        if critical:
            return True
        return (now - self._last_spoken_at) >= self.cooldown_seconds

    def _commit(self, ins: Insight, now: float) -> None:
        self._last_spoken_at = now
        self._recent_kinds[ins.kind] = now
