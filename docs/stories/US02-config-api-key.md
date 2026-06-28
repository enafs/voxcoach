# US02 — Configurar a API key do LLM

> **Como** jogador, **quero** configurar minha própria API key do LLM,
> **para** usar meu provedor sem custo de terceiros.

Relaciona: D05 (key do usuário), `config.py` (`VOXCOACH_*`).

```gherkin
Feature: Configuração do provedor de LLM

  Scenario: Configurar uma key válida (Claude)
    Given o jogador definiu VOXCOACH_LLM_BACKEND=claude
    And definiu VOXCOACH_ANTHROPIC_API_KEY com uma key válida
    When o assistente inicia
    Then o provider de LLM é carregado com sucesso
    And a engine fica pronta para gerar recomendações analíticas

  Scenario: Key ausente ao iniciar
    Given nenhum VOXCOACH_ANTHROPIC_API_KEY foi definido
    When o jogador tenta iniciar o assistente
    Then o app informa que a API key está faltando
    And não inicia a Camada 2 (LLM), mas a Camada 1 (fatos) pode operar

  Scenario: Key inválida (rejeitada pelo provedor)
    Given uma API key inválida foi configurada
    When a engine faz a primeira chamada ao LLM
    Then o erro é tratado sem derrubar o app
    And o jogador é avisado de que a key é inválida

  Scenario: Trocar de backend
    Given o jogador estava usando claude
    When define VOXCOACH_LLM_BACKEND=openai e a key correspondente
    And reinicia o assistente
    Then o provider OpenAI é usado nas próximas recomendações

  Scenario: A key nunca é versionada
    Given o jogador preencheu o arquivo .env
    Then o .env está no .gitignore e não é commitado
```
