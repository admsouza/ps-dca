# dca/balanco-patrimonial — Delta spec

## MODIFIED Requirements

### Requirement: O BP espelha o DCA-Anexo I-AB declarado

O Balanço Patrimonial SHALL reproduzir em centavos o `DCA-Anexo I-AB` que o ente declara ao SICONFI
(decisão do PO, 2026-10-07; aceite do projeto: espelho 1:1 contra `tt/dca`). Para isso:

- nas visões **isolado** (padrão) e **consolidado**, as linhas do Quadro Principal NÃO DEVEM excluir
  as contas intra-OFSS (5º nível = 2); o resultado é o declarado. Revoga a execução das exclusões
  da visão `consolidado` (`bp-visao-consolidado-isolado`, PO 2026-10-08; `bp-consolidado-sem-exclusao`,
  PO 2026-10-08).
- `L5` Passivo Financeiro SHALL ser `2.1` Financeiro + `2.2` Financeiro + `6.3.1.1` + `6.3.1.5` +
  `6.3.1.7.1`, a composição que o `I-AB` detalha. NÃO DEVE incluir `6.2.2.1.3.01` nem
  `6.2.2.1.3.05`. Revoga a decisão P7-a.

Vale para as duas colunas e para as duas origens da coluna do exercício anterior.

#### Scenario: Cuitegi 2025 igual ao I-AB declarado

- **GIVEN** a MSC de encerramento de Cuitegi (`2505204`), 2025
- **WHEN** o BP é apurado
- **THEN** `L1` e `L15` valem 76.314.331,92 nas visões `isolado` e `consolidado`, e `L32` vale −45.644.857,64
- **AND** `diagnostico.equilibrio` é 0,00 no exercício atual nas duas visões

#### Scenario: conta intra entra na linha

- **GIVEN** registros de `121120400` (intra, 90,00) e `121110400` (consolidação, 10,00)
- **WHEN** `L10` é apurada
- **THEN** `L10` é 100,00

#### Scenario: passivo financeiro pela composição do I-AB

- **GIVEN** `2.1` Financeiro = 2.647.434,03, `6.3.1.1` = 70.972,63, `6.3.1.7.1` = 387.532,93 e
  `6.2.2.1.3.05` = 0,00
- **WHEN** o quadro F/P é apurado
- **THEN** `L5` é 3.105.939,59

#### Scenario: inscrição em duas contas não é contada duas vezes

- **GIVEN** `6.2.2.1.3.05` = 48.335,00 e `6.3.1.7.1` = 48.335,00 (Cuitegi 2024)
- **WHEN** `L5` é apurada
- **THEN** só `6.3.1.7.1` entra, e `L5` é 6.618.515,01 com `2.1` F = 6.496.569,60 e `6.3.1.1` = 73.610,41

### Requirement: Visão consolidada pelas exclusões do IPC 04

A visão `consolidado` SHALL incluir as mesmas contas da visão `isolado`. Os filtros `visao: consolidado`
do Quadro Principal (coluna Exclusões do IPC 04, `L34` com `2.3.2.1.2.00.00`) permanecem declarados na
regra e NÃO DEVEM ser aplicados na apuração (PO 2026-10-08). Os quadros F/P, Compensação e Superávit
NÃO DEVEM variar com a visão. O equilíbrio `L1 − L15` SHALL ser o mesmo nas duas visões.

#### Scenario: conta intra entra nas duas visões

- **GIVEN** `121120100` (intra, 90,00) e `121110101` (consolidação, 10,00)
- **WHEN** o BP é apurado
- **THEN** `L10` é 100,00 na visão `isolado` e 100,00 na visão `consolidado`

#### Scenario: L34 inclui a 2.3.2.1.2 nas duas visões

- **GIVEN** `232110000` = 7,00 e `232120000` = 3,00
- **WHEN** o BP é apurado
- **THEN** `L34` é 10,00 no `isolado` e 10,00 no `consolidado`

#### Scenario: quadro F/P igual nas duas visões

- **GIVEN** `111110100` F = 26.431.637,72 e `121120100` P = 29.230.791,29
- **WHEN** o BP é apurado
- **THEN** F/P `L2` e `L3` são iguais nas duas visões

#### Scenario: equilíbrio igual nas duas visões

- **GIVEN** intra só no ativo (`121120100` = 100,00) e passivo sem intra
- **WHEN** o BP é apurado
- **THEN** `equilibrio` é 0,00 no `isolado` e 0,00 no `consolidado`
