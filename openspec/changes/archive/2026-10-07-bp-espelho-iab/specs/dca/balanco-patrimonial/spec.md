# dca/balanco-patrimonial — Delta spec

## ADDED Requirements

### Requirement: O BP espelha o DCA-Anexo I-AB declarado

O Balanço Patrimonial SHALL reproduzir em centavos o `DCA-Anexo I-AB` que o ente declara ao SICONFI
(decisão do PO, 2026-10-07; aceite do projeto: espelho 1:1 contra `tt/dca`). Para isso:

- as linhas do Quadro Principal NÃO DEVEM excluir as contas intra-OFSS (5º nível = 2); o resultado é o
  consolidado declarado. Revoga a decisão P8-a.
- `L5` Passivo Financeiro SHALL ser `2.1` Financeiro + `2.2` Financeiro + `6.3.1.1` + `6.3.1.5` +
  `6.3.1.7.1`, a composição que o `I-AB` detalha. NÃO DEVE incluir `6.2.2.1.3.01` nem
  `6.2.2.1.3.05`. Revoga a decisão P7-a.

Vale para as duas colunas e para as duas origens da coluna do exercício anterior.

#### Scenario: Cuitegi 2025 igual ao I-AB declarado

- **GIVEN** a MSC de encerramento de Cuitegi (`2505204`), 2025
- **WHEN** o BP é apurado
- **THEN** `L1` e `L15` valem 76.314.331,92, `L32` vale −45.644.857,64
- **AND** `diagnostico.equilibrio` é 0,00 no exercício atual

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
