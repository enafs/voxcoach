# DECISIONS — Registro de Decisões de Arquitetura (ADR)

Decisões de design do VoxCoach. Cada linha resume o **quê** e o **porquê**.
Detalhes completos no `SDD.md`. Quando uma decisão for revertida, marcar como
*Superada por Dxx* em vez de apagar.

| ID | Decisão | Motivo | Status |
|---|---|---|---|
| D01 | Python 3.11+ (usamos 3.12) | Ecossistema LLM/áudio, produtividade | Vigente |
| D02 | Arquitetura agnóstica c/ abstração leve (core + adapters) | Suportar LoL + CS2 sem retrabalho | Vigente |
| D03 | System tray como UI do MVP | Não atrapalha o jogo, simples de implementar | Vigente |
| D04 | TTS local (`edge-tts`) | Custo zero, baixa latência, plugável | Vigente |
| D05 | LLM com API key do usuário | Custo no usuário, privacidade | Vigente |
| D06 | Apenas fontes oficiais/legais | Princípio inegociável: zero risco de ban | Vigente |
| D07 | Valorant fora de escopo | Sem API oficial + Vanguard (kernel) agressivo | Vigente |
| D08 | LoL primeiro, CS2 previsto | Ambos têm API oficial; LoL é o mais rico | Vigente |
| D09 | Camadas de processamento (fato vs. análise) | Fatos determinísticos via regra local + cache (latência ~0); LLM só p/ recomendação analítica que exige julgamento | Vigente |
| D10 | Áudio com `sounddevice` + `soundfile` | Grátis, mantido, baixa latência, permite **interromper** a fala (descarta `playsound`) | Vigente |
| D11 | Concorrência híbrida (tray-thread + async-engine) | Tray bloqueia a thread; engine é I/O-bound → `asyncio`. Menos bugs de concorrência | Vigente |

## Notas de implementação ligadas às decisões

- **D09** — O *princípio* (fato determinístico vs. recomendação analítica) está
  na SDD 3.2. O *catálogo* de quais eventos de LoL caem em cada camada vive no
  adapter/processor (específico de jogo, evolutivo). Critério do LLM: *"isso
  exige análise/julgamento?"* — não *"isso é urgente?"*.
- **D10** — `edge-tts` emite MP3. **Risco resolvido (validado)**: a `soundfile`
  do PyPI traz `libsndfile 1.2.2` embutida no wheel (versão controlada por nós,
  não pelo SO), e MP3 está nos formatos suportados. Teste ponta a ponta OK:
  edge-tts → MP3 (21 KB) → `soundfile.read` → 84.672 amostras a 24 kHz. Fallback
  `miniaudio` **não é necessário**.
- **D11** — Fronteira: o tray só envia comandos (start/stop) à engine via fila
  thread-safe; a engine roda isolada no seu event loop `asyncio`.
