# pipeline/unidade-gestora — Delta spec

Delta sobre a capability como fica depois de `pipeline-dca-por-unidade-gestora` e
`bf-por-unidade-gestora`.

## MODIFIED Requirements

### Requirement: Coluna anterior do BP por recorte vem da MSC do exercício anterior

Fora do `consolidado`, a coluna do exercício anterior do BP e do BF de cada **unidade** SHALL vir da
origem resolvida para ela pela capability `pipeline/anterior-por-recorte`: `processado`, `msce` ou
`manual`. A coluna anterior de cada **grupo de poder** SHALL ser a soma das unidades dele.

Fora do consolidado, NÃO DEVEM ser usados:
- a DCA publicada (`publicado_siconfi`);
- o anterior manual do consolidado (`valores_anteriores` de topo).

`diagnostico.conferencia_publicado` SHALL existir só no `consolidado`.

#### Scenario: consolidado pelo publicado, UG processada
- **GIVEN** BP de 2025 processado com `origem_exercicio_anterior=publicado_siconfi` e o BP de 2024 com recortes em cache
- **WHEN** o recorte `ug:1` é lido
- **THEN** a coluna anterior é a coluna atual de `ug:1` em 2024, sem `conferencia_publicado`

#### Scenario: sem N−1 processado
- **GIVEN** o BP de 2025 sem cache de 2024 com recortes
- **WHEN** o recorte `ug:1` é lido
- **THEN** a coluna anterior é a da MSCE de 2024 da UG 1, como antes desta change
