# pipeline/plataforma — Delta spec

## MODIFIED Requirements

### Requirement: Resumo agregado responde sempre

O resumo do estado de todos os anexos SHALL responder `200` mesmo quando nenhum tiver cache, SHALL
listar os anexos na ordem canônica e SHALL trazer, por anexo, apenas metadados — nunca o resultado.
Anexo ainda sem implementação SHALL aparecer como `sem_cache`; NÃO DEVE ser omitido. O resumo NÃO
DEVE iniciar cálculo.

As entradas de BF e BP SHALL trazer `recortes`: as unidades (`ug:`/`po:`) do resultado `ok`, com
`chave`, `tipo` e `rotulo`, filtradas pela mesma visibilidade por poder da leitura do anexo. Sem
resultado `ok`, `recortes` SHALL ser `[]`. Grupos de poder e consolidado NÃO DEVEM aparecer.

#### Scenario: bootstrap sem nenhum cache

- **WHEN** o resumo é solicitado para um ente sem nenhuma apuração
- **THEN** a resposta é `200` com todos os anexos em `sem_cache`
- **AND** BF e BP trazem `recortes = []`
- **AND** nenhum job é enfileirado

#### Scenario: metadados sem payload

- **WHEN** o resumo é solicitado com anexos já apurados
- **THEN** cada entrada traz status, data de cálculo, versões e duração
- **AND** nenhuma entrada traz o resultado do demonstrativo

#### Scenario: unidades do BF

- **GIVEN** Cuitegi (`2505204`) 2024 com BF `ok` por SIAFIC e quatro UGs
- **WHEN** o resumo de 2024 é solicitado por usuário que vê os dois poderes
- **THEN** a entrada do BF traz as 4 UGs em `recortes`, sem `consolidado` e sem `poder:*`

#### Scenario: visibilidade por poder

- **GIVEN** o mesmo cache e um usuário só do Executivo
- **WHEN** o resumo é solicitado
- **THEN** a Câmara não aparece em `recortes`
