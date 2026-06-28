# US06 — Escolher voz e idioma do TTS

> **Como** jogador, **quero** escolher a voz e o idioma do TTS,
> **para** ter uma experiência confortável.

Relaciona: D04 (edge-tts), `config.py` (`VOXCOACH_TTS_*`), `TTSProvider`.

```gherkin
Feature: Seleção de voz e idioma do TTS

  Scenario: Usar a voz pt-BR padrão
    Given nenhuma voz foi configurada
    When o assistente narra um insight
    Then a voz pt-BR padrão (pt-BR-AntonioNeural) é usada

  Scenario: Escolher outra voz
    Given o jogador definiu VOXCOACH_TTS_VOICE para outra voz suportada
    When o assistente narra o próximo insight
    Then a fala usa a voz escolhida

  Scenario: Ajustar a velocidade da fala
    Given o jogador definiu VOXCOACH_TTS_RATE (ex.: "+10%")
    When o assistente narra um insight
    Then a fala respeita a velocidade configurada

  Scenario: Voz inválida (fallback seguro)
    Given uma voz inexistente foi configurada
    When o TTS tenta sintetizar
    Then o erro é tratado sem derrubar o app
    And o jogador é avisado para corrigir a configuração
```
