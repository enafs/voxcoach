# US04 — Dicas por voz baseadas no estado real

> **Como** jogador, **quero** receber dicas por voz baseadas no estado real do
> jogo, **para** tomar decisões melhores em tempo real.

Relaciona: D09 (camadas de processamento), SDD 3.2, pipeline completo.

```gherkin
Feature: Insights táticos narrados por voz

  Background:
    Given uma sessão ativa de LoL com polling em andamento
    And o estado do jogo é normalizado em GameState a cada tick

  Scenario: Fato determinístico (Camada 1, sem LLM)
    Given o estado mostra que a ult de um inimigo voltou a ficar disponível
    When o Processor avalia o tick
    Then o insight é resolvido por regra local + frase cacheada
    And nenhuma chamada ao LLM é feita
    And o TTS narra o alerta com latência mínima

  Scenario: Recomendação analítica (Camada 2, com LLM)
    Given o estado sugere uma decisão que exige julgamento (ex.: onde wardar)
    When o Processor decide que vale acionar a Camada 2
    Then um resumo do GameState é enviado ao LLM
    And o LLM retorna 1–2 frases curtas de coaching
    And o TTS narra a recomendação

  Scenario: LLM indisponível ou lento (degradação graciosa)
    Given a Camada 2 foi acionada
    When o LLM excede o tempo limite ou falha
    Then a recomendação é descartada sem travar o pipeline
    And a Camada 1 (fatos determinísticos) continua operando

  Scenario: Insight reflete o estado real, não dado cru
    Given o adapter normalizou o estado em GameState
    Then o Processor e o LLM trabalham apenas com GameState
    And nenhum formato cru da Live API vaza para o prompt
```
