# User Stories (BDD)

Critérios de aceite das user stories do MVP (SDD §7), um arquivo por story, com
cenários **Given/When/Then** em Gherkin.

Estes arquivos são **documentação legível agora** e **convertíveis depois** para
`.feature` executável (ex.: `pytest-bdd`) sem retrabalho. Não confundir com
`DECISIONS.md` (decisões de arquitetura) — aqui é *comportamento esperado*.

| Story | Tema |
|---|---|
| [US01](US01-tray-start-stop.md) | Iniciar/parar pelo system tray |
| [US02](US02-config-api-key.md) | Configurar API key do LLM |
| [US03](US03-deteccao-automatica-partida.md) | Detecção automática de partida (LoL) |
| [US04](US04-dicas-por-voz.md) | Dicas por voz baseadas no estado real |
| [US05](US05-anti-spam.md) | Não falar demais / no momento errado |
| [US06](US06-voz-e-idioma.md) | Escolher voz e idioma do TTS |
| [US07](US07-sem-risco-de-ban.md) | Nenhuma técnica que arrisque ban |
| [US08](US08-novo-jogo-via-interface.md) | Adicionar novo jogo via interface |
