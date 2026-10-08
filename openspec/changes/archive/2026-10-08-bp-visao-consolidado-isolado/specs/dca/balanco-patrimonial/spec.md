# dca/balanco-patrimonial — Delta spec

## MODIFIED Requirements

### Requirement: O BP espelha o DCA-Anexo I-AB declarado

Na visão **isolado** (padrão), o Balanço Patrimonial SHALL reproduzir em centavos o `DCA-Anexo I-AB` que o
ente declara ao SICONFI: as linhas do Quadro Principal NÃO DEVEM excluir as contas intra-OFSS. A `L5` do
quadro F/P segue a composição do `I-AB` nas duas visões.

## ADDED Requirements

### Requirement: Visão consolidada pelas exclusões do IPC 04

As exclusões da coluna **Exclusões** do Quadro Principal do IPC 04 SHALL ser regras executáveis aplicadas
**somente** na visão `consolidado` (IPC 04 item 8). A exclusão da `L34` SHALL ser `2.3.2.1.2.00.00`
(o `2.3.2.0.2.00.00` do PDF não existe no PCASP). Os quadros F/P, Compensação e Superávit NÃO DEVEM
variar com a visão. O equilíbrio `L1 − L15` SHALL ser publicado por visão; diferença é achado, nunca ajuste.

#### Scenario: conta intra sai só no consolidado

- **GIVEN** `121120100` (intra, 90,00) e `121110101` (consolidação, 10,00)
- **WHEN** o BP é apurado
- **THEN** `L10` é 100,00 na visão `isolado` e 10,00 na visão `consolidado`

#### Scenario: L34 exclui a 2.3.2.1.2 no consolidado

- **GIVEN** `232110000` = 7,00 e `232120000` = 3,00
- **WHEN** o BP é apurado
- **THEN** `L34` é 10,00 no `isolado` e 7,00 no `consolidado`

#### Scenario: quadro F/P igual nas duas visões

- **GIVEN** `111110100` F = 26.431.637,72 e `121120100` P = 29.230.791,29
- **WHEN** o BP é apurado
- **THEN** F/P `L2` e `L3` são iguais nas duas visões

#### Scenario: equilíbrio por visão

- **GIVEN** intra só no ativo (`121120100` = 100,00) e passivo sem intra
- **WHEN** o BP é apurado
- **THEN** `equilibrio` é 0,00 no `isolado` e −100,00 no `consolidado`, sem ajuste

### Requirement: Uma apuração, duas visões servidas

Um processamento do BP SHALL produzir as duas visões a partir de uma única leitura da fonte e gravá-las no
mesmo registro de cache. `GET /dca/BP` SHALL aceitar `visao` (`isolado` | `consolidado`, padrão `isolado`)
e servir a visão pedida sem enfileirar job. `reprocessar` e o percurso NÃO recebem `visao`.

#### Scenario: trocar a visão não processa

- **GIVEN** BP de Cuitegi 2025 em cache `ok`
- **WHEN** o front lê `visao=isolado` e depois `visao=consolidado`
- **THEN** as duas respostas são `200` do mesmo registro, sem job, com `visao` ecoada no corpo

#### Scenario: fonte lida uma vez

- **WHEN** o BP é apurado com origem `msce_exercicio_anterior`
- **THEN** a fonte é consultada uma vez por ano e classe, não uma vez por visão

#### Scenario: visão inválida

- **WHEN** `GET /dca/BP?visao=orgao`
- **THEN** `422` "visao inválida"

#### Scenario: visão em outro anexo

- **WHEN** `GET /dca/BF?visao=consolidado`
- **THEN** `422`

#### Scenario: cache sem a visão consolidada

- **GIVEN** BP em cache gravado antes desta change
- **WHEN** `GET /dca/BP?visao=consolidado`
- **THEN** `409` pedindo reprocessar o BP; `visao=isolado` continua `200`
