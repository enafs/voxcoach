"""Captura um snapshot real do Live Client Data API do LoL.

Rode com uma partida ativa (Modo de Treino / Practice Tool serve). Salva o
payload de `allgamedata` para usar como fixture de teste.

Uso:
    python scripts/capture_fixture.py [arquivo_de_saida]

Padrão: tests/fixtures/allgamedata.real.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import httpx

URL = "https://127.0.0.1:2999/liveclientdata/allgamedata"


def main() -> int:
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("tests/fixtures/allgamedata.real.json")
    try:
        # verify=False: a Live API usa certificado self-signed em localhost.
        resp = httpx.get(URL, verify=False, timeout=3.0)
    except httpx.HTTPError as exc:
        print(f"[x] Nenhuma partida ativa ou API indisponivel em 127.0.0.1:2999\n    {exc}")
        print("    Dica: entre em uma partida (Modo de Treino serve) e rode de novo.")
        return 1

    if resp.status_code != 200:
        print(f"[x] Status inesperado: {resp.status_code}")
        return 1

    data = resp.json()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    n_players = len(data.get("allPlayers", []))
    n_events = len((data.get("events") or {}).get("Events", []))
    print(f"[ok] Salvo: {out}")
    print(f"     {n_players} jogadores, {n_events} eventos, {out.stat().st_size} bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
