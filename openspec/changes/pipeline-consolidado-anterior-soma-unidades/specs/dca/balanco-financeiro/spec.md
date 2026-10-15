# dca/balanco-financeiro — Delta spec

## MODIFIED Requirements

### Requirement: Coluna do exercício anterior com origem escolhida por quem apura

A origem da coluna do exercício anterior do BF SHALL ser escolhida separadamente para cada unidade
`ug:` ou `po:` pela capability `pipeline/anterior-por-recorte`: resultado processado de N−1, MSC de
N−1 ou valores manuais da própria unidade. O consolidado SHALL ser a soma dessas colunas resolvidas e
NÃO DEVE ter origem ou mapa manual próprios.

O mapa manual de uma unidade SHALL ser gravado na procedência do recorte correspondente. Pedido
seguinte sem escolha explícita para a unidade SHALL reaplicar a escolha gravada ou usar o padrão da
capability. Linha manual não informada permanece não apurada; a coluna atual não aceita preenchimento
manual.

#### Scenario: manual de uma UG participa do consolidado

- **GIVEN** uma UG do BF com coluna anterior manual válida e as demais com suas origens resolvidas
- **WHEN** o BF é apurado
- **THEN** o consolidado soma o manual dessa UG com as colunas das demais unidades
- **AND** não existe mapa manual próprio do consolidado

#### Scenario: mapa manual no topo é recusado

- **WHEN** o BF recebe `origem_exercicio_anterior=manual` ou `valores_anteriores` no topo do pedido
- **THEN** o pedido é recusado antes do job
- **AND** o cliente deve informar o manual dentro de `anterior_por_recorte` para cada unidade afetada

#### Scenario: G8 atual não muda

- **GIVEN** `valores_sem_mapeamento` válidos para o exercício atual
- **WHEN** o BF é reprocessado após esta change
- **THEN** a coluna atual e sua procedência permanecem bit a bit iguais ao comportamento anterior
- **AND** esses valores não são tratados como origem da coluna anterior
