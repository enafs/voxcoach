"""Interface plugável de adapter de jogo (D02, D08).

Cada jogo (LoL no MVP; CS2 previsto) implementa ``GameAdapter``. O Orchestrator
e o Processor só conhecem ``GameState`` — nunca o formato cru da fonte. Trocar
de jogo, ou absorver uma mudança na API da Riot, é mexer em um arquivo só.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from voxcoach.models import GameState


class GameAdapter(ABC):
    """Obtém o estado de um jogo específico e o normaliza para ``GameState``."""

    #: identificador curto do jogo, ex.: "lol", "cs2"
    game: str

    @abstractmethod
    async def is_game_active(self) -> bool:
        """``True`` se há uma partida deste jogo rodando agora.

        Ex.: para LoL, a Live Client Data API responde em 127.0.0.1:2999.
        """

    @abstractmethod
    async def fetch_state(self) -> GameState | None:
        """Busca e normaliza o estado atual.

        Retorna ``None`` quando o estado está indisponível neste tick (ex.: a
        partida acabou de encerrar, ou a fonte falhou momentaneamente).
        """

    async def close(self) -> None:
        """Libera recursos (ex.: cliente HTTP). Override quando necessário."""
        return None
