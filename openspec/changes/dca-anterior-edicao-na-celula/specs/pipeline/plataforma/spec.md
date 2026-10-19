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

A unidade com escolha gravada da coluna do exercício anterior SHALL trazer também
`anterior: {origem, manual}`, lido da procedência (`anterior_por_recorte`). Unidade sem escolha NÃO
DEVE trazer a chave: a origem é a automática do pipeline. O resumo NÃO DEVE devolver os valores
digitados — `manual` diz apenas que existem.

#### Scenario: escolha gravada da unidade no resumo

- **GIVEN** um BF `ok` com `ug:1` em manual com valores e `ug:2` em `msce_exercicio_anterior`
- **WHEN** o resumo é solicitado
- **THEN** `ug:1` traz `anterior = {"origem": "manual", "manual": true}`
- **AND** `ug:2` traz `anterior = {"origem": "msce_exercicio_anterior", "manual": false}`
- **AND** a unidade sem escolha não traz a chave `anterior`
