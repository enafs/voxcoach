# US01 — Iniciar/parar o assistente pelo tray

> **Como** jogador, **quero** iniciar/parar o assistente pelo system tray,
> **para** controlar quando ele atua.

Relaciona: D03 (tray como UI), D11 (tray-thread ↔ async-engine via fila).

```gherkin
Feature: Controle do assistente pelo system tray

  Background:
    Given o VoxCoach está rodando em background com ícone no system tray

  Scenario: Iniciar o assistente
    Given o assistente está parado (idle)
    When o jogador clica em "Start" no menu do tray
    Then a engine começa a procurar por uma partida ativa
    And o ícone/menu do tray passa a indicar estado "ativo"

  Scenario: Parar o assistente durante uma sessão ativa
    Given o assistente está ativo e narrando insights
    When o jogador clica em "Stop" no menu do tray
    Then a engine encerra o polling e qualquer fala em andamento é interrompida
    And o tray volta a indicar estado "idle"

  Scenario: Status refletido no tray
    Given o assistente está idle
    When uma partida é detectada e a sessão inicia
    Then o tray reflete a transição idle -> ativo sem ação do jogador

  Scenario: Sair do aplicativo
    Given o VoxCoach está rodando
    When o jogador clica em "Sair" no menu do tray
    Then a engine é encerrada de forma limpa (recursos liberados)
    And o processo termina

  Scenario: Comando do tray não bloqueia a engine
    Given o assistente está ativo
    When o jogador aciona "Stop" no tray
    Then o comando é enviado à engine por uma fila thread-safe
    And a thread do tray permanece responsiva
```
