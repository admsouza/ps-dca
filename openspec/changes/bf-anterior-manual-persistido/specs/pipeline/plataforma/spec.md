# pipeline/plataforma — Delta spec

## ADDED Requirements

### Requirement: Mapa manual do BF não viaja na query e não depende do cliente repeti-lo

A gravação do mapa do exercício anterior SHALL ser um `POST` com o mapa no corpo JSON. `valores_anteriores` na query SHALL ser recusado com `400`, sem enfileirar job e sem alterar a linha de cache.

`GET /dca/BF`, `POST /dca/BF/reprocessar` sem corpo e `POST /batch-jobs` SHALL reaplicar o mapa já gravado na procedência quando a origem não vier explícita. NÃO DEVEM exigir que o cliente reenvie o mapa.

A autorização SHALL ser a mesma das demais rotas de anexo. O mapa NÃO DEVE aparecer em log.

#### Scenario: mapa no corpo é gravado

- **WHEN** `POST /dca/BF/reprocessar` traz `origem_exercicio_anterior=manual` e `valores_anteriores` no corpo, para um ente autorizado
- **THEN** a resposta é `202`
- **AND** ao fim do job a procedência guarda o mapa

#### Scenario: mapa na query é recusado

- **WHEN** `GET /dca/BF` ou `POST /dca/BF/reprocessar` traz `valores_anteriores` na query
- **THEN** a resposta é `400`
- **AND** nenhum job é enfileirado
- **AND** a linha de cache não muda

#### Scenario: percurso completo reaplica o mapa

- **GIVEN** o BF do ente com mapa manual na procedência
- **WHEN** `POST /batch-jobs` roda sem origem
- **THEN** o desfecho do `BF` conserva a coluna do exercício anterior do mapa salvo

#### Scenario: ente não autorizado

- **WHEN** o `POST` do mapa pede um ente fora da unidade do token
- **THEN** a resposta é `403`
- **AND** a linha de cache não muda
