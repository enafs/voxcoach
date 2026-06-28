"""Montagem de prompts para o LLM (Camada 2).

Separado do provider para ser testável sem a SDK. ``build_context`` resume o
``GameState`` (mais a dica do insight) num texto compacto; o LLM nunca vê o
formato cru do jogo — só este resumo derivado do modelo normalizado.
"""

from __future__ import annotations

from voxcoach.models import GameState

SYSTEM_PROMPT = (
    "Você é um coach de League of Legends falando ao vivo no ouvido do jogador "
    "durante a partida. Responda em português do Brasil, em no máximo 1–2 frases "
    "curtas e diretas, como um treinador objetivo. Dê uma recomendação acionável, "
    "sem rodeios e sem repetir dados óbvios. Nunca invente informação que não "
    "esteja no contexto."
)


def build_context(state: GameState, hint: str | None = None) -> str:
    """Resumo textual do estado da partida para o prompt do LLM."""
    p = state.player
    minutes, seconds = divmod(int(state.game_time), 60)

    lines = [
        f"Tempo de jogo: {minutes}min{seconds:02d}s",
        (
            f"Você: {p.champion or '?'} nível {p.level}, "
            f"KDA {p.kills}/{p.deaths}/{p.assists}, "
            f"vida {int(p.health)}/{int(p.max_health)}, ouro {int(p.gold)}"
        ),
    ]
    if p.items:
        lines.append("Itens: " + ", ".join(p.items))
    if state.enemies:
        enemies = ", ".join(e.champion for e in state.enemies if e.champion)
        if enemies:
            lines.append(f"Inimigos: {enemies}")
    if state.teammates:
        allies = ", ".join(e.champion for e in state.teammates if e.champion)
        if allies:
            lines.append(f"Aliados: {allies}")
    if hint:
        lines.append(f"Situação: {hint}")

    return "\n".join(lines)
