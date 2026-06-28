# CLAUDE.md — Âncora de sessão do VoxCoach

Contexto persistente para o Claude Code. Leia isto e o `SDD.md` antes de mexer
no código. Fonte de verdade do design: **`SDD.md`**. Decisões: **`DECISIONS.md`**.

## O que é

**VoxCoach** (voxcoach.gg) — coach de jogo em tempo real **por voz**. App
desktop em background (system tray) que lê **fontes de dados oficiais/legais**
do jogo, processa o estado, consulta um LLM quando vale a pena, e narra insights
táticos por TTS no ouvido do jogador. **Sem mod, sem injeção, sem risco de ban**
(princípio inegociável — D06).

MVP entrega **League of Legends** (Live Client Data API). CS2 (GSI) está previsto
na arquitetura, não implementado.

## Arquitetura (resumo — detalhes na SDD §2)

Pipeline: `GameAdapter → Processor → LLM → TTS`, orquestrado por um loop async.

- **Adapter** (plugável): lê a fonte do jogo e normaliza para `GameState`. O
  resto do app **só** conhece `GameState`, nunca o formato cru — é o que torna a
  arquitetura agnóstica de jogo (D02).
- **Processor**: detecta eventos, aplica gatilhos/anti-spam e classifica o
  insight em **camada de processamento** (D09):
  - **Camada 1 — fato determinístico** (ex.: "ward vista", "ult voltou"):
    regra local + frase cacheada, **sem LLM**, latência ~0.
  - **Camada 2 — recomendação analítica** (ex.: "warda no tribush agora",
    "troca pra trinket azul"): **com LLM**, latência ~2–3s tolerável.
  - Critério do LLM: *"isso exige análise/julgamento?"* — não *"é urgente?"*.
- **LLM** (plugável): Claude (padrão) / OpenAI. Respostas **curtas** (1–2 frases).
- **TTS**: síntese via `edge-tts` (`TTSProvider`) + reprodução via `AudioPlayer`
  (`sounddevice`), que permite **interromper** a fala para um alerta prioritário.

**Concorrência (D11)**: tray (`pystray`) roda na própria thread (ela bloqueia);
a engine roda em outra thread com seu próprio event loop `asyncio`. Todo o I/O
da engine é async. Tray ↔ engine se comunicam por fila thread-safe.

## Estrutura

```
src/voxcoach/
├── __init__.py
├── __main__.py          # python -m voxcoach
├── cli.py               # CLI: --replay (dry-run) e modo live; ConsoleSpeaker
├── orchestrator.py      # loop de sessão + Speaker (abstração de saída)
├── config.py            # pydantic-settings (env VOXCOACH_*)
├── models.py            # GameState normalizado (dataclasses) — contrato central
├── adapters/{base,lol}.py       # GameAdapter + LoLAdapter (Live API)
├── processor/{processor,triggers}.py  # detecção de eventos + anti-spam
├── llm/{base,claude,prompts}.py        # LLMProvider + Claude + montagem de prompt
└── tts/{base,edge,player}.py           # TTSProvider + edge-tts + AudioPlayer
```

Ainda **não** existem (adiados de propósito p/ evitar código morto):
`main.py` (entrypoint + tray), `adapters/cs2.py`, `llm/openai.py`,
`tts/elevenlabs.py`.

## Setup e comandos

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows (PowerShell: .venv\Scripts\Activate.ps1)
pip install -e ".[dev]"          # instala o pacote em modo editável + ferramentas

pytest                           # testes (quando existirem)
ruff check src tests             # lint
```

Config: copie `.env.example` → `.env` e preencha sua API key (D05).

## Convenções

- Python 3.12, `from __future__ import annotations`, type hints em tudo.
- `GameState` é **dataclass** (loop quente, sem validação). Config é **pydantic**.
- Async em toda a engine (`httpx.AsyncClient`, etc.). Nada de I/O bloqueante no loop.
- Comentários e docstrings em **pt-BR** (padrão do projeto).
- Novo jogo/LLM/TTS = implementar a interface base correspondente. Não vazar
  formato cru para fora do adapter.

## Status atual

Fase: **vertical slice CONCLUÍDO** (SDD §10, passo 4). Pipeline ponta a ponta:
adapter → processor → triggers → llm → speaker, orquestrado em `orchestrator.py`
e exposto via `cli.py`. **41 testes passando**. Risco MP3×soundfile **resolvido**.

Rodar a demo (sem jogo, sem key):
`PYTHONPATH=src ./.venv/Scripts/python.exe -m voxcoach --replay tests/fixtures/allgamedata.json`

Saída atual é **texto no console** (`ConsoleSpeaker`). A fala por voz (TTS já
pronto em `tts/`) entra junto com o tray, via um `VoiceSpeaker`.

Limitações conhecidas (intencionais no MVP):
- Fala **um insight por tick**; se uma ANALYSIS de prioridade alta sai sem LLM
  configurado, aquele tick fica em silêncio (não cai para um FACT menor).
- Detecção de combate = só `low_health` (Live API não dá posições).

Próximo: **`main.py`** — entrypoint + **system tray** (US01, D03) e `VoiceSpeaker`
ligando o TTS real. Tray roda em thread própria; engine no event loop (D11).

Rodar testes: `./.venv/Scripts/python.exe -m pytest -q` (venv com httpx/pytest/
pytest-asyncio/respx; deps pesadas como sounddevice/pystray só no slice de áudio/tray).
