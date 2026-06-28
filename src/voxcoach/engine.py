"""Engine — roda o Orchestrator num event loop em thread separada (D11).

O tray (``pystray``) bloqueia a thread em que roda, então a engine vive em
**outra thread** com seu **próprio event loop asyncio**. O tray apenas envia
comandos (``start`` / ``stop`` / ``shutdown``) de forma thread-safe; toda a
lógica de I/O assíncrono fica isolada aqui.

O ``Orchestrator`` é injetado (qualquer objeto com ``run()``/``stop()``/
``aclose()``), o que mantém a Engine testável sem o app real.
"""

from __future__ import annotations

import asyncio
import threading
from typing import Any


class Engine:
    def __init__(self, orchestrator: Any) -> None:
        self._orch = orchestrator
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(
            target=self._loop.run_forever, name="voxcoach-engine", daemon=True
        )
        self._thread.start()
        self._run_future: Any | None = None

    @property
    def running(self) -> bool:
        return self._run_future is not None and not self._run_future.done()

    def start(self) -> None:
        """Inicia (ou reinicia) o loop de sessão. Idempotente se já rodando."""
        if self.running:
            return
        self._run_future = asyncio.run_coroutine_threadsafe(self._orch.run(), self._loop)

    def stop(self) -> None:
        """Pede para a sessão encerrar (thread-safe). Não bloqueia."""
        self._loop.call_soon_threadsafe(self._orch.stop)

    def shutdown(self, timeout: float = 5.0) -> None:
        """Para a sessão, libera recursos e encerra o loop/thread."""
        try:
            self.stop()
            if self._run_future is not None:
                try:
                    self._run_future.result(timeout)
                except Exception:
                    pass
            fut = asyncio.run_coroutine_threadsafe(self._orch.aclose(), self._loop)
            try:
                fut.result(timeout)
            except Exception:
                pass
        finally:
            self._loop.call_soon_threadsafe(self._loop.stop)
            self._thread.join(timeout)
