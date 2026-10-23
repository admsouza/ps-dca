# pipeline/plataforma — Delta spec

## Purpose

Transportar a DVP pelo mesmo pipeline de BO, BF e BP — rota, cache, job, resumo e percurso —
sem que a plataforma aprenda regra contábil nenhuma.

## ADDED Requirements

### Requirement: Ordem de apresentação da DVP vem do documento

O serializador SHALL ordenar as linhas da DVP pelos quadros e grupos declarados para o documento
`IPC05`: quadro `QUADRO_PRINCIPAL` e grupos `VPA`, `VPD` e `RESULTADO`, nessa ordem. A ordem NÃO
DEVE depender de a numeração das linhas ser global e crescente.

Hoje as 19 linhas têm `ordem` de 1 a 19 sem repetição, e a saída sairia na ordem certa mesmo sem
declaração — por coincidência. Linha nova com `ordem` relativa ao grupo sairia fora de lugar, sem
erro e sem célula não apurada.

#### Scenario: VPA antes de VPD, resultado por último

- **WHEN** a DVP apurada é serializada
- **THEN** `L1` é a primeira linha e o grupo dela é `VPA`
- **AND** toda linha de `VPA` vem antes de toda linha de `VPD`
- **AND** `L19`, do grupo `RESULTADO`, é a última

#### Scenario: linha nova com ordem relativa ao grupo

- **GIVEN** uma linha de `VPD` com `ordem` 1, relativa ao grupo
- **WHEN** o demonstrativo é serializado
- **THEN** ela aparece dentro de `VPD`, e não antes de `L1`

### Requirement: `I-HI` é anexo implementado

O registry SHALL declarar o anexo `I-HI` com o serviço de apuração da DVP e a base canônica `dvp`.
O carregador de regras SHALL receber essa base — nunca a do BO.

Carregar o mapa do BO para a DVP não levanta exceção: devolve 51 linhas do IPC 07 e um
demonstrativo plausível e errado. Foi o defeito corrigido em `bf-no-pipeline` (2.6a).

#### Scenario: resumo deixa de reportar anexo sem serviço

- **WHEN** `GET /dca/resumo` é lido para um ente e exercício
- **THEN** a entrada de `I-HI` traz `implementado: true`

#### Scenario: percurso completo inclui a DVP

- **WHEN** o percurso completo é montado para um ente e exercício sem cache
- **THEN** os anexos a apurar são `BO`, `BF`, `BP` e `I-HI`
- **AND** a notificação lista os quatro

#### Scenario: grafia não canônica

- **WHEN** o anexo chega como `i-hi` ou `I_HI`
- **THEN** é canonizado para `I-HI`, sem criar entrada de cache separada

### Requirement: Uma serialização só

O JSON servido pela rota da DVP SHALL ser idêntico ao produzido pelo CLI da DVP para o mesmo ente,
exercício e fonte.

#### Scenario: rota e CLI não divergem

- **WHEN** o mesmo ente e exercício são apurados pela rota e por `python -m app.cli.dvp --json`
- **THEN** os dois JSON são iguais
