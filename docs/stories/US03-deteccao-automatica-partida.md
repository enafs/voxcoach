# US03 — Detecção automática de partida (LoL)

> **Como** jogador, **quero** que o app detecte automaticamente quando entro em
> partida de LoL, **para** não ter que iniciar manualmente toda vez.

Relaciona: SDD §3 (fluxo), `GameAdapter.is_game_active()`, Live Client Data API.

```gherkin
Feature: Detecção automática de partida via Live Client Data API

  Background:
    Given o assistente foi iniciado e está em idle
    And o adapter de LoL aponta para https://127.0.0.1:2999

  Scenario: Entrar em partida de LoL
    Given não havia partida ativa
    When a Live API passa a responder em 127.0.0.1:2999
    Then o adapter reporta is_game_active = true
    And a sessão inicia o loop de polling

  Scenario: Live API indisponível (sem partida)
    Given não há partida em andamento
    When a Live API não responde
    Then o adapter reporta is_game_active = false
    And o app permanece em idle
    And tenta novamente no próximo ciclo

  Scenario: Falha transitória não encerra a sessão
    Given uma sessão ativa em andamento
    When a Live API falha em um único tick (erro momentâneo)
    Then o app não encerra a sessão imediatamente
    And reutiliza o último estado conhecido até o próximo tick

  Scenario: Fim de partida
    Given uma sessão ativa
    When a Live API para de responder de forma sustentada
    Then o app encerra o loop da sessão
    And volta ao estado idle aguardando a próxima partida

  Scenario: Certificado self-signed da Live API
    Given a Live API usa certificado self-signed em localhost
    When o adapter faz a requisição
    Then a verificação TLS é ignorada apenas para 127.0.0.1
    And a conexão é estabelecida com sucesso
```
