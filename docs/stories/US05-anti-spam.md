# US05 — Não falar demais / no momento errado

> **Como** jogador, **quero** que o app não fale demais nem no momento errado,
> **para** não ser distraído em momentos críticos.

Relaciona: SDD 3.1 (controle de gatilhos), `processor/triggers.py` (futuro).

```gherkin
Feature: Política de gatilhos (anti-spam)

  Background:
    Given uma sessão ativa com narração habilitada

  Scenario: Cooldown global entre falas
    Given o app acabou de narrar um insight
    When outro insight de mesma prioridade surge dentro do cooldown
    Then o app não narra novamente até o cooldown expirar

  Scenario: Prioridade — alerta crítico interrompe fala
    Given o app está narrando uma dica de baixa prioridade
    When um alerta de prioridade alta é gerado (ex.: morte iminente)
    Then a fala atual é interrompida
    And o alerta de alta prioridade é narrado imediatamente

  Scenario: Silêncio durante teamfight
    Given o estado indica um teamfight em andamento
    When surge uma dica não-crítica
    Then o app suprime a fala para não atrapalhar
    And reavalia quando a luta terminar

  Scenario: Sem mudança significativa não aciona o LLM
    Given o estado do tick atual é essencialmente igual ao anterior
    When o Processor avalia os gatilhos
    Then a Camada 2 (LLM) não é acionada
    And nenhuma fala é gerada

  Scenario: Relevância — só fala quando agrega
    Given vários eventos menores ocorreram no tick
    When o Processor pondera prioridade e relevância
    Then apenas o insight mais relevante é narrado
```
