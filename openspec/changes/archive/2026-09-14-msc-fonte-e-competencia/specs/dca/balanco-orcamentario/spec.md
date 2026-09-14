# dca/balanco-orcamentario — Delta spec

Ajusta a origem dos saldos do BO à decisão do PO de 2026-09-14. **Nenhum valor apurado muda** —
medido em Cuitegi/PB e João Pessoa/PB, 337 células cada, zero divergências.

## MODIFIED Requirements

### Requirement: Leitura da MSC na matriz de encerramento, saldo de abertura, classes 5 e 6

A apuração SHALL consultar, na competência **12**, a matriz de **encerramento** (`MSCE`) pelo saldo
de **abertura**, classes **5** e **6**, na matriz orçamentária — o par declarado para o `BO` em
`dca/fonte-msc`. Nas competências **1 a 11**, SHALL consultar `MSCC` pelo saldo de **encerramento**,
porque a matriz de encerramento não existe nesses meses. A variação do período NÃO DEVE ser consultada. A `MSCE` lida pelo saldo de
**encerramento** NÃO DEVE ser usada: nela as contas já foram encerradas, e 47 das 337 células do BO
saem erradas, com a diferença absorvida pela linha de Superávit — um total que continua fechando
com linhas erradas.

A leitura anterior (`MSCC` pelo saldo de encerramento) produz **exatamente** os mesmos valores:
medido em Cuitegi/PB `2505204` e em João Pessoa/PB `2507507`, exercício 2025, 337 células cada, com
os mesmos volumes de registro por classe. A troca é de origem, não de resultado.

#### Scenario: duas consultas por apuração

- **WHEN** o quadro principal de um ente é apurado
- **THEN** são feitas exatamente duas leituras de saldos, classe `5` e classe `6`, mesma
  competência e mesmo par (matriz, tipo de saldo)
- **AND** ambas usam a matriz orçamentária

#### Scenario: a troca de origem não muda valor nenhum

- **GIVEN** o BO de Cuitegi/PB e o de João Pessoa/PB, exercício 2025
- **WHEN** cada um é apurado sobre `MSCC`/encerramento e sobre `MSCE`/abertura
- **THEN** as 337 células saem idênticas em centavos, nos dois entes
- **AND** os 11 valores de `docs/validacao-bo-jp-2025.md` seguem batendo com o publicado

#### Scenario: a matriz de encerramento lida pelo encerramento é recusada

- **WHEN** o par do `BO` é resolvido, em qualquer competência de 1 a 12
- **THEN** nunca resulta `MSCE` com saldo de encerramento
- **AND** esse par existe apenas para o Balanço Patrimonial

#### Scenario: paginação completa da fonte SICONFI

- **GIVEN** um ente cujo retorno excede 5.000 registros numa classe
- **WHEN** os saldos são lidos
- **THEN** o adapter segue `hasMore`/`offset` até o fim
- **AND** o total de registros entregue ao apurador é o total da fonte, não a primeira página

#### Scenario: apuração mensal de um ente que presta contas por mês

- **GIVEN** Cuitegi/PB `2505204`, exercício 2025
- **WHEN** o BO é apurado para as competências 3, 6, 9 e 12
- **THEN** as receitas realizadas saem 10.942.851,04, 22.477.392,39, 34.047.498,07 e 50.723.704,91
- **AND** as três primeiras vêm de `MSCC`/encerramento e a última de `MSCE`/abertura
- **AND** a procedência de cada uma declara a competência e o par usado

#### Scenario: volume do caso real

- **WHEN** JP `2507507` 12/2025 é lido
- **THEN** chegam `4.600` registros de classe 5 e `4.320` de classe 6
- **AND** os mesmos volumes são obtidos nos dois pares (matriz, tipo de saldo)
