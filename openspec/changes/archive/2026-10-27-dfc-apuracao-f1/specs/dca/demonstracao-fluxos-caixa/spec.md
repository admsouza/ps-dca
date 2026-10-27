# dca/demonstracao-fluxos-caixa — Delta spec

## Purpose

Apurar as 84 linhas da DFC a partir da MSC, no mesmo motor e no mesmo contrato de BO, BF, BP e
DVP, com as linhas sem conta declarada abertas para digitação do contador. O transporte HTTP e o
recorte por unidade gestora ficam para changes posteriores.

## ADDED Requirements

### Requirement: Apuração das 84 linhas pela MSC
A apuração SHALL ler a MSC pelo par já declarado em `dca/fonte-msc` — matriz de encerramento,
saldo de abertura, classes 1 a 6 — e produzir as 84 linhas em `exercicio_atual` e
`exercicio_anterior`. O saldo de cada célula SHALL ser tomado na direção da coluna. NÃO DEVE haver
alteração em `app/domain/` nem em `knowledge/rules/dfc/`.

#### Scenario: as 84 linhas apuram
- **GIVEN** a MSC de um ente com registros nas classes 1 a 6
- **WHEN** a DFC é apurada
- **THEN** nenhuma das 84 linhas fica não apurada por "referências sem coluna em comum"

#### Scenario: fonte sem registros não vira zero
- **GIVEN** uma fonte que não devolve registro nenhum
- **WHEN** a DFC é apurada
- **THEN** a coluna sai não apurada (`None`) e o diagnóstico marca `sem_dados`

### Requirement: Linha sem conta é informada, não contamina o total
`L16`, `L21` e `L30` NÃO DEVEM ter conta apurada: SHALL aceitar valor digitado pelo contador, no
mesmo mecanismo do Balanço Financeiro, e SHALL valer `0,00` na agregadora quando não informadas.
Código fora de `{L16, L21, L30}` e valor não decimal SHALL ser recusado antes de apurar. A
agregadora que as referencia NÃO DEVE ficar não apurada por causa delas.

#### Scenario: L16 não informada não derruba L12
- **WHEN** a DFC é apurada sem valor informado para `L16`
- **THEN** `L16` vale `0,00` na soma de `L12`, `L12` apura, e `L16` consta como informável no
  diagnóstico

#### Scenario: L16 informada entra no total
- **WHEN** o contador informa `L16`
- **THEN** o valor aparece em `L16` e soma em `L12`

#### Scenario: código fora da whitelist é recusado
- **WHEN** chega um valor informado para `L15`
- **THEN** a apuração é recusada antes de ler a MSC

### Requirement: Caixa inicial vem do exercício anterior
`L35` SHALL ser o saldo de `1.1.1.0.0.00.00` na MSC de **N−1**, e `L36` SHALL resultar de
`L34 + L35`. NÃO DEVE ser lido da MSC de N, que traz a posição final do exercício.

#### Scenario: L35 e L36 são as duas pontas do caixa
- **GIVEN** um ente cujo `1.1.1` vale `A` na MSC de N−1 e `B` na MSC de N
- **WHEN** a DFC é apurada para N
- **THEN** `L35` é `A` e `L36` é `B`

#### Scenario: sem MSC do exercício anterior
- **WHEN** não há MSC em N−1
- **THEN** `L35` sai não apurada, no mesmo contrato de BP, BF e DVP

### Requirement: A geração líquida fecha a variação do caixa
`L34` apurado SHALL ser igual à variação de `1.1.1.0.0.00.00` entre as MSC de N−1 e N, para o
mesmo conjunto de unidades. Esta é a conferência de aceite da apuração e NÃO DEVE depender do
demonstrativo publicado pelo ente, cujo recorte pode ser outro.

#### Scenario: identidade de caixa em Porto Alegre 2025
- **GIVEN** `1.1.1` valendo 2.785.855.199,20 na MSC de 2024 e 2.854.802.415,12 na de 2025
- **WHEN** a DFC de 2025 é apurada
- **THEN** `L34` é 68.947.215,92

#### Scenario: identidades do demonstrativo fecham sobre o apurado
- **WHEN** a DFC é apurada
- **THEN** `L2 = L3+…+L11`, `L12 = L13+…+L16`, `L1 = L2−L12`, `L34 = L1+L17+L26` e
  `L36 = L34+L35` fecham nas duas colunas

#### Scenario: os quadros auxiliares amarram no principal
- **WHEN** a DFC é apurada
- **THEN** `P.L10 = T.L7`, `P.L13 = F.L29`, `P.L14 = J.L4` e `P.L15 = T.L15`

### Requirement: A DFC é verificável sem rota
SHALL existir `python -m app.cli.dfc <ibge> <exercicio>`, imprimindo os quatro quadros com a
procedência e o diagnóstico, e `--json` com o mesmo conteúdo. NÃO DEVE exigir banco, fila nem
container.

#### Scenario: CLI imprime os quatro quadros
- **WHEN** `python -m app.cli.dfc 4314902 2025` roda contra a MSC
- **THEN** a saída traz as 84 linhas nos quatro quadros, a procedência com documento `IPC08` e o
  número de células não apuradas
