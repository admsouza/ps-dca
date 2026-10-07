# pipeline/processamento-completo — Delta spec

## ADDED Requirements

### Requirement: Percurso respeita a origem da coluna anterior do BP

`POST /batch-jobs` SHALL aceitar `origem_exercicio_anterior` (`publicado_siconfi` |
`msce_exercicio_anterior`), aplicado **só** ao Balanço Patrimonial; omitido, vale
`publicado_siconfi`. A decisão de cache do percurso (rota) e a apuração e gravação do BP (worker)
SHALL usar a mesma identidade de pedido, com essa origem. Origem inválida SHALL responder `422` sem
enfileirar job. BO e BF NÃO DEVEM mudar de identidade nem de resultado.

#### Scenario: percurso grava o BP pela origem pedida

- **GIVEN** `POST /batch-jobs` com `origem_exercicio_anterior=msce_exercicio_anterior`
- **WHEN** o percurso conclui
- **THEN** o BP gravado declara `origem_exercicio_anterior: msce_exercicio_anterior`
- **AND** a leitura do BP com a mesma origem responde `desatualizado: false`, sem enfileirar job

#### Scenario: percurso sem origem mantém o padrão

- **WHEN** `POST /batch-jobs` chega sem `origem_exercicio_anterior`
- **THEN** o BP é apurado pelo publicado, como antes

#### Scenario: cache do BP em outra origem entra a apurar

- **GIVEN** o BP em cache válido pela origem publicado
- **WHEN** o percurso sem `forcar` é pedido com `msce_exercicio_anterior`
- **THEN** o BP aparece no percurso como `a_apurar`
- **AND** BO e BF com cache válido continuam `em_cache`

#### Scenario: origem inválida no percurso

- **WHEN** `POST /batch-jobs` chega com `origem_exercicio_anterior=manual`
- **THEN** a resposta é `422`
- **AND** nenhum job é enfileirado
