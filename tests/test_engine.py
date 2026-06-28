"""Testes da Engine (thread + event loop), com um orchestrator falso."""

from __future__ import annotations

import asyncio
import threading
import time

from voxcoach.engine import Engine


class FakeOrchestrator:
    def __init__(self):
        self.started = threading.Event()
        self.closed = threading.Event()
        self._running = False

    async def run(self):
        self._running = True
        self.started.set()
        while self._running:
            await asyncio.sleep(0.005)

    def stop(self):
        self._running = False

    async def aclose(self):
        self.closed.set()


def _wait_until(cond, timeout=2.0) -> bool:
    end = time.time() + timeout
    while time.time() < end:
        if cond():
            return True
        time.sleep(0.01)
    return False


def test_start_runs_and_shutdown_closes():
    orch = FakeOrchestrator()
    engine = Engine(orch)
    try:
        engine.start()
        assert orch.started.wait(2.0)
        assert engine.running
    finally:
        engine.shutdown()
    assert orch.closed.is_set()
    assert not engine.running


def test_start_is_idempotent_while_running():
    orch = FakeOrchestrator()
    engine = Engine(orch)
    try:
        engine.start()
        assert orch.started.wait(2.0)
        future = engine._run_future
        engine.start()  # já rodando -> não troca a execução
        assert engine._run_future is future
    finally:
        engine.shutdown()


def test_stop_then_restart():
    orch = FakeOrchestrator()
    engine = Engine(orch)
    try:
        engine.start()
        assert orch.started.wait(2.0)

        engine.stop()
        assert _wait_until(lambda: not engine.running)

        orch.started.clear()
        engine.start()
        assert orch.started.wait(2.0)   # rodou de novo
        assert engine.running
    finally:
        engine.shutdown()
