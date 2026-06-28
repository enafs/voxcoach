# US08 — Adicionar um novo jogo via interface

> **Como** dev, **quero** adicionar um novo jogo implementando uma interface,
> **para** expandir sem reescrever o core.

Relaciona: D02 (arquitetura agnóstica), `adapters/base.py` (`GameAdapter`), `models.py`.

```gherkin
Feature: Extensibilidade por adapters de jogo

  Scenario: Implementar GameAdapter habilita um novo jogo
    Given um novo jogo com fonte de dados oficial
    When o dev implementa a interface GameAdapter (is_game_active, fetch_state)
    And registra o adapter no orchestrator
    Then o app passa a suportar o novo jogo sem mudanças no Processor/LLM/TTS

  Scenario: O core não muda ao adicionar um jogo
    Given o pipeline Processor -> LLM -> TTS já existe
    When um novo adapter é adicionado
    Then nenhum desses módulos precisa ser alterado
    And o adapter é a única peça específica do jogo

  Scenario: O adapter traduz para GameState (não vaza formato cru)
    Given o novo adapter obtém dados crus da sua fonte
    When ele retorna o estado via fetch_state
    Then o resultado é um GameState normalizado
    And o formato cru fica restrito ao adapter (no máximo em GameState.raw)

  Scenario: Eventos específicos mapeados para o modelo genérico
    Given a fonte do jogo emite eventos próprios
    When o adapter os traduz
    Then cada evento vira um GameEvent com um EventType genérico
    And o que não tiver mapeamento usa EventType.OTHER preservando o dado cru
```
