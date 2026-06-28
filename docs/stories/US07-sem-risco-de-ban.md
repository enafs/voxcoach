# US07 — Nenhuma técnica que arrisque ban

> **Como** jogador, **quero** que nenhuma técnica arrisque meu ban,
> **para** jogar com segurança.

Relaciona: D06 (fontes oficiais), D07 (Valorant fora), SDD §4. Princípio inegociável.

```gherkin
Feature: Coleta de dados apenas por meios oficiais e seguros

  Scenario: Usar apenas fonte oficial do jogo
    Given o adapter de LoL está ativo
    When ele obtém o estado da partida
    Then os dados vêm exclusivamente da Live Client Data API oficial (127.0.0.1:2999)

  Scenario: Nenhuma técnica invasiva é empregada
    Given o app está em execução durante uma partida
    Then ele não lê memória do processo do jogo
    And não injeta código no jogo
    And não usa overlay invasivo nem leitura de tela

  Scenario: Jogo sem API oficial não é suportado
    Given um jogo não expõe uma fonte de dados oficial/legal (ex.: Valorant)
    When se avalia o suporte a esse jogo
    Then o jogo fica fora de escopo por decisão de design
    And nenhum método de área cinza é implementado

  Scenario: CS2 via integração oficial suportada (quando implementado)
    Given o CS2 oferece Game State Integration oficial da Valve
    When o adapter de CS2 for implementado
    Then ele usará GSI (HTTP POST via .cfg), sem técnicas invasivas
```
