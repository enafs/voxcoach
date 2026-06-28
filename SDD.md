# SDD — Software Design Document

## Projeto: VoxCoach (voxcoach.gg)

> Coach de jogo em tempo real por voz. Lê APIs/dados locais oficiais do jogo e narra insights táticos no ouvido do jogador — **sem mod, sem injeção de código, sem risco de ban**.

---

## 1. Visão Geral

### 1.1 Problema
Jogadores querem melhorar durante a partida, mas não conseguem analisar estatísticas e tomar decisões táticas em tempo real sem parar o jogo. Ferramentas existentes muitas vezes usam injeção de memória ou leitura de tela invasiva, o que viola termos de serviço e arrisca banimento.

### 1.2 Solução
Um app desktop em background (system tray) que:
1. Lê **fontes de dados oficiais/legais** do jogo em tempo real (API local da Riot para LoL; GSI da Valve para CS2).
2. Processa o estado do jogo e envia o contexto relevante para um **LLM** (Claude/GPT, com API key do próprio usuário).
3. Narra os insights táticos por **voz (TTS)** no ouvido do jogador.

### 1.3 Princípios de Design
- **Sem risco de ban**: apenas fontes oficiais/permitidas. Nunca leitura de memória, injeção ou overlay invasivo.
- **Agnóstico de jogo (abstração leve)**: core genérico + adapters plugáveis por jogo. MVP entrega LoL; CS2 já previsto na arquitetura.
- **Plugável**: LLM, TTS e jogos são intercambiáveis via interfaces.
- **Usuário no controle**: API keys próprias, configuração local, custo mínimo.
- **Baixa latência**: decisões em tempo real exigem resposta rápida. Nem todo insight passa pelo LLM — alertas críticos e previsíveis saem de regras locais + frases cacheadas (latência ~0); o LLM fica para análise estratégica não-urgente (ver seção 3.2).

### 1.4 Escopo do MVP
- ✅ Adapter de LoL (Live Client Data API)
- ✅ Pipeline core: Watcher → Processor → LLM → TTS
- ✅ Interface system tray (start/stop/config)
- ✅ TTS local (`edge-tts`)
- ✅ LLM configurável (Claude/GPT)
- ⏳ Adapter de CS2 (previsto na arquitetura, não implementado no MVP)
- ❌ Valorant (inviável/arriscado — ver seção 4.4)
- ❌ GUI completa / overlay

---

## 2. Arquitetura

### 2.1 Visão de Alto Nível

```
┌─────────────────────────────────────────────────────────┐
│                      SYSTEM TRAY (UI)                     │
│              start / stop / config / status              │
└───────────────────────────┬─────────────────────────────┘
                            │ controla
                            ▼
┌─────────────────────────────────────────────────────────┐
│                       ORCHESTRATOR                        │
│        (loop principal, ciclo de vida da sessão)          │
└───┬───────────────┬───────────────┬───────────────┬──────┘
    │               │               │               │
    ▼               ▼               ▼               ▼
┌────────┐    ┌──────────┐    ┌──────────┐    ┌────────┐
│ GAME   │    │PROCESSOR │    │   LLM    │    │  TTS   │
│ADAPTER │───▶│ (estado, │───▶│ PROVIDER │───▶│PROVIDER│
│(plugin)│    │ eventos, │    │ (plugin) │    │(plugin)│
│        │    │ gatilhos)│    │          │    │        │
└────────┘    └──────────┘    └──────────┘    └────────┘
    │
    ├── LoLAdapter   (Live Client Data API — MVP)
    └── CS2Adapter   (Game State Integration — previsto)
```

### 2.2 Componentes

**Orchestrator** — Coração do app. Gerencia o ciclo de vida da sessão (detectar jogo ativo, iniciar polling, parar ao fim da partida). Conecta os módulos.

**Game Adapter (interface plugável)** — Responsável por obter o estado do jogo de uma fonte específica e traduzi-lo para um **modelo de dados normalizado** comum. Cada jogo implementa essa interface.

**Processor** — Recebe o estado normalizado, mantém histórico, detecta **eventos** (ex.: morreu, subiu de nível, objetivo disponível) e decide **se/quando/como** vale a pena falar. Classifica cada insight em uma **camada de processamento** (ver 3.2): fato determinístico (regra local, sem LLM) vs. recomendação analítica (LLM). Controla gatilhos/throttling para não falar demais.

**LLM Provider (interface plugável)** — Monta o prompt com o contexto do jogo e chama o provider configurado (Claude/GPT). Retorna o insight em texto **curto** (1–2 frases, `max_tokens` baixo) para minimizar latência de geração e de fala. MVP padrão: modelo rápido (ex.: Claude Haiku) para tempo real.

**TTS Provider (interface plugável)** — Converte o texto do insight em áudio. MVP usa `edge-tts` (grátis). A **reprodução** é responsabilidade separada de um `AudioPlayer` compartilhado (`sounddevice`), que suporta **interromper a fala atual** quando chega um alerta de prioridade maior.

### 2.3 Modelo de Dados Normalizado (conceito)

Todos os adapters traduzem para uma estrutura comum, ex.:

```python
@dataclass
class GameState:
    game: str               # "lol" | "cs2"
    game_time: float        # segundos de partida
    player: PlayerState     # vida, recursos, posição, kills/deaths/assists
    teammates: list[Entity]
    enemies: list[Entity]
    objectives: list[Objective]  # dragão, barão, bomb site, etc.
    events: list[GameEvent]      # eventos desde o último tick
    raw: dict                    # dados crus do adapter (fallback)
```

> O Processor e o LLM trabalham **apenas** com `GameState`, nunca com o formato cru do jogo. É isso que torna a arquitetura agnóstica.

---

## 3. Fluxo de Execução

1. Usuário clica **Start** no tray.
2. Orchestrator pergunta a cada adapter ativo: "há um jogo rodando?" (`is_game_active()`).
3. Adapter detecta partida (ex.: Live API responde em `127.0.0.1:2999`).
4. Loop de polling (ex.: a cada 1–2s):
   - Adapter busca dados → traduz para `GameState`.
   - Processor compara com o tick anterior → detecta eventos.
   - Processor avalia **gatilhos**: vale falar agora? (cooldown, prioridade, relevância).
   - Se sim → LLM monta prompt + responde insight → TTS narra.
5. Ao detectar fim de partida → Orchestrator encerra o loop, volta ao estado idle.

### 3.1 Controle de Gatilhos (anti-spam)
Regra essencial para não virar ruído. Exemplos de política:
- **Cooldown global**: no máximo 1 fala a cada N segundos.
- **Prioridade de evento**: morte iminente > objetivo disponível > dica genérica.
- **Silêncio em luta**: evitar falar no meio de um teamfight (atrapalha).
- **Relevância**: só aciona LLM se o estado mudou de forma significativa.

### 3.2 Estratégia de Latência (camadas de processamento)
O pipeline `Adapter → Processor → LLM → TTS` em série pode passar de 2–4s — tarde demais para um teamfight. Por isso **nem todo insight passa pelo LLM**. O critério de divisão **não é urgência, é a natureza do insight**: *isso exige análise/julgamento?*

- **Camada 1 — Fatos determinísticos (sem LLM, latência ~0):** o app apenas **constata** algo derivável direto do `GameState` por uma regra. Ex.: "ward inimiga vista", "jungler inimigo apareceu no top", "ult do oponente voltou", "barão em 30s". Saem de **regras locais** + **frases pré-definidas/cacheadas**, sem chamada de rede. Alertas críticos podem **interromper** a fala em andamento.
- **Camada 2 — Recomendações analíticas (com LLM, latência tolerável ~2–3s):** o app **aconselha** algo que exige raciocínio sobre o contexto. Ex.: "agora é hora de wardar, coloca no tribush", "troca a ward pela trinket azul, é melhor pro seu matchup". O atraso é aceitável porque não são reações de combate imediato.

> O **princípio** (fato vs. análise) vive aqui no SDD. O **catálogo** de quais eventos são Camada 1 vs. Camada 2 vive na implementação (adapter/processor de LoL), por ser específico de jogo e evolutivo.

Otimizações transversais:
- **Respostas curtas por design**: LLM limitado a 1–2 frases (`max_tokens` baixo) → gera mais rápido e fala mais rápido.
- **TTS streaming**: `edge-tts` entrega áudio em chunks; começar a tocar antes de sintetizar a frase inteira reduz a latência percebida.
- **Modelo rápido**: usar um modelo de baixa latência (ex.: Claude Haiku) no tempo real; reservar modelos maiores para resumos não-urgentes.
- **Cache de dicas comuns**: chave = situação normalizada, valor = áudio/texto já pronto.

---

## 4. Fontes de Dados por Jogo

### 4.1 LoL — ✅ MVP
- **Live Client Data API** (oficial): `https://127.0.0.1:2999/liveclientdata/allgamedata`
- Roda localmente durante a partida. Retorna dados ricos (placar, ouro, itens, eventos, runas).
- **Legal e seguro** — API oficial da Riot, sem injeção.
- Certificado self-signed (precisa ignorar verificação TLS para localhost).

### 4.2 CS2 — ⏳ Previsto
- **Game State Integration (GSI)** (oficial da Valve): cria um arquivo `.cfg` em `csgo/cfg/` e o jogo envia eventos via HTTP POST para um endpoint local que o app expõe.
- **Legal e suportado** pela Valve. Modelo *push* (em vez de *polling*).

### 4.3 TFT — Parcial / futuro
- Compartilha o cliente do LoL, mas a Live Client API cobre TFT de forma limitada. Viabilidade reduzida; avaliar caso a caso.

### 4.4 Valorant — ❌ Não recomendado
- A Riot **não** oferece API de jogo ao vivo para Valorant.
- Soluções de terceiros dependem de leitura de log/tela (área cinza) e o anti-cheat **Vanguard** (kernel-level) é agressivo.
- **Risco real de banimento.** Fica fora do escopo por decisão de design (princípio "sem risco de ban").

---

## 5. Stack Técnica

| Camada | Tecnologia | Justificativa |
|---|---|---|
| Linguagem | Python 3.11+ | Ecossistema, libs de LLM/áudio, produtividade |
| System tray | `pystray` + `Pillow` | Tray multiplataforma simples |
| HTTP client | `httpx` | Async, suporta polling e TLS custom |
| Servidor GSI (CS2) | `fastapi` + `uvicorn` | Recebe POST do CS2 (quando implementar) |
| LLM | `anthropic` / `openai` | Providers plugáveis, key do usuário |
| TTS | `edge-tts` | Grátis, vozes naturais pt-BR, baixa latência, streaming |
| Áudio | `sounddevice` + `soundfile` | Grátis, mantido, baixa latência, permite **interromper** a fala em andamento (essencial p/ alertas prioritários) |
| Concorrência | `threading` + `asyncio` | Tray em thread própria; engine (polling/LLM/TTS) num event loop async (ver 5.1) |
| Config | `pydantic-settings` + `.env`/`toml` | Config tipada e validada |
| Empacotamento | `PyInstaller` | Gerar `.exe` Windows-first |

### 5.1 Notas
- **Windows-first** (combina com seu ambiente), mas as libs escolhidas são multiplataforma.
- **Modelo de concorrência (híbrido)**: o tray (`pystray`) bloqueia a thread em que roda, então fica isolado em sua **própria thread**. O **Orchestrator** roda em outra thread com seu **próprio event loop `asyncio`**; todo o I/O da engine (polling `httpx`, chamada ao LLM, síntese TTS) é **async**. Resumo: *threads para separar tray ↔ engine; async dentro da engine*. Evita o emaranhado de N threads + locks.
- **Áudio 100% gratuito**: `sounddevice` + `soundfile` (sem custo, sem serviço externo). Atenção: `edge-tts` produz MP3 — validar decodificação via `soundfile` (libsndfile ≥ 1.1 decodifica MP3); fallback se necessário (ver Riscos).
- TTS abstraído atrás de interface → trocar para ElevenLabs depois é só novo provider.
- LLM key do usuário → custo fica com o usuário, alinhado ao modelo do OrderFi.

---

## 6. Estrutura de Pastas (proposta)

```
voxcoach/
├── pyproject.toml
├── README.md
├── .env.example
├── CLAUDE.md                  # anchor de sessão p/ Claude Code
├── DECISIONS.md               # decisões de arquitetura (ADR-like)
├── src/
│   └── voxcoach/
│       ├── __init__.py
│       ├── main.py            # entrypoint + tray
│       ├── orchestrator.py    # loop de sessão
│       ├── config.py          # pydantic-settings
│       ├── models.py          # GameState, dataclasses normalizadas
│       ├── adapters/
│       │   ├── base.py        # GameAdapter (interface)
│       │   ├── lol.py         # LoLAdapter (MVP)
│       │   └── cs2.py         # CS2Adapter (stub previsto)
│       ├── processor/
│       │   ├── processor.py   # detecção de eventos
│       │   └── triggers.py    # política de gatilhos / anti-spam
│       ├── llm/
│       │   ├── base.py        # LLMProvider (interface)
│       │   ├── claude.py
│       │   └── openai.py
│       └── tts/
│           ├── base.py        # TTSProvider (interface de síntese)
│           ├── player.py      # AudioPlayer (sounddevice) — reprodução + interrupção
│           ├── edge.py        # edge-tts (MVP)
│           └── elevenlabs.py  # futuro
└── tests/
    ├── test_adapters.py
    ├── test_processor.py
    └── fixtures/              # respostas mock da Live API
```

---

## 7. User Stories (MVP)

| # | Como... | Quero... | Para... |
|---|---|---|---|
| US01 | jogador | iniciar/parar o assistente pelo tray | controlar quando ele atua |
| US02 | jogador | configurar minha API key do LLM | usar meu próprio provedor sem custo de terceiros |
| US03 | jogador | que o app detecte automaticamente quando entro em partida de LoL | não ter que iniciar manualmente toda vez |
| US04 | jogador | receber dicas por voz baseadas no estado real do jogo | tomar decisões melhores em tempo real |
| US05 | jogador | que o app não fale demais / no momento errado | não ser distraído em momentos críticos |
| US06 | jogador | escolher a voz e o idioma do TTS | ter uma experiência confortável |
| US07 | jogador | que nenhuma técnica arrisque meu ban | jogar com segurança |
| US08 | dev (você) | adicionar um novo jogo implementando uma interface | expandir sem reescrever o core |

> Próximo passo (quando formos para o Claude Code): detalhar cada US com cenários **BDD** (Given/When/Then), igual ao padrão do OrderFi.

---

## 8. Decisões Registradas (resumo para o DECISIONS.md)

| ID | Decisão | Motivo |
|---|---|---|
| D01 | Python 3.11+ | Ecossistema LLM/áudio, produtividade |
| D02 | Arquitetura agnóstica c/ abstração leve | Suportar LoL + CS2 sem retrabalho |
| D03 | System tray como UI do MVP | Não atrapalha o jogo, simples de implementar |
| D04 | TTS local (`edge-tts`) | Custo zero, baixa latência, plugável |
| D05 | LLM com API key do usuário | Custo no usuário, privacidade |
| D06 | Apenas fontes oficiais/legais | Princípio inegociável: zero risco de ban |
| D07 | Valorant fora de escopo | Sem API oficial + Vanguard agressivo |
| D08 | LoL primeiro, CS2 previsto | Ambos têm API oficial; LoL é o mais rico |
| D09 | Camadas de processamento (fato vs. análise) | Fatos determinísticos via regra local + cache (latência ~0); LLM só p/ recomendação analítica que exige julgamento |
| D10 | Áudio com `sounddevice` + `soundfile` | Grátis, mantido, baixa latência, permite interromper fala (descarta `playsound`) |
| D11 | Concorrência híbrida (tray-thread + async-engine) | Tray bloqueia; engine I/O-bound → async. Menos bugs de concorrência |

---

## 9. Riscos e Mitigações

| Risco | Mitigação |
|---|---|
| LLM responder devagar (latência) | Pipeline de urgência (3.2): alertas críticos não passam pelo LLM. Respostas curtas + modelo rápido + TTS streaming |
| App "falar demais" | Política de gatilhos com cooldown e prioridade (seção 3.1) |
| Custo de API do LLM | Key do usuário + acionamento seletivo + cache de dicas comuns |
| Mudança na Live API da Riot | Adapter isolado; só um arquivo muda |
| Qualidade da voz local | Interface plugável → upgrade para ElevenLabs quando quiser |
| ~~`soundfile` não decodificar MP3 do `edge-tts`~~ | **Resolvido**: `soundfile` traz libsndfile 1.2.2 (wheel) com suporte a MP3; pipeline edge-tts→soundfile validado a 24 kHz |
| Bugs de concorrência (tray ↔ engine) | Fronteira clara: tray só envia comandos (start/stop) via fila thread-safe; engine isolada no seu event loop |

---

## 10. Próximos Passos

Abordagem combinada: **híbrido com peso no incremental** — ancorar a arquitetura com um scaffold mínimo, depois construir um *vertical slice* testável.

1. ✅ Validar este SDD (com decisões D09–D11 incorporadas).
2. **Scaffold mínimo** (não o completo): `pyproject.toml`, `CLAUDE.md`, `DECISIONS.md`, estrutura de pastas, **interfaces base** (`adapters/base.py`, `llm/base.py`, `tts/base.py`) e `models.py` (o `GameState` normalizado). Stubs vazios (`cs2.py`, `openai.py`, `elevenlabs.py`) ficam **adiados** para evitar código morto.
3. ✅ Detalhar US01–US08 em cenários **BDD** (Given/When/Then) — em `docs/stories/`.
4. **Vertical slice incremental**: `adapters/lol.py` com **fixtures** da Live API (testável fora de partida) → `processor` → `llm` → `tts/player`, ponta a ponta (US03 + US04). Depois tray (US01), depois polimento de gatilhos (US05).
