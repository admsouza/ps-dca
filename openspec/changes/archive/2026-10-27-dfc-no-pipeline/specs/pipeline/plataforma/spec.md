# pipeline/plataforma — Delta spec

## Purpose

Servir a DFC pelas mesmas rotas de BO, BF, BP e DVP, sem caso especial: o que falta é o registro
do anexo, porque rota, cache e despacho já são genéricos.

## ADDED Requirements

### Requirement: A DFC é um anexo servido pelo pipeline
O `REGISTRY` SHALL declarar `DFC` com o serviço `app.services.dfc.quadro_principal:apurar` e
`base_canonica="dfc"`, entre os demonstrativos derivados e antes dos anexos que o STN publica.
`GET /dca/DFC` SHALL responder 200 a partir do cache e `POST /dca/DFC/reprocessar` SHALL
responder 202. O código `I-E` NÃO DEVE ser usado para a DFC.

#### Scenario: anexo implementado entra no registry
- **WHEN** o registry é consultado pelo anexo `DFC`
- **THEN** o serviço é `app.services.dfc.quadro_principal:apurar` e a base canônica é `dfc`

#### Scenario: o apurador vem do serviço declarado no registry
- **WHEN** o pipeline resolve o apurador de `DFC`
- **THEN** a função vem de `app.services.dfc.quadro_principal`

#### Scenario: o mapa do anexo vem da sua própria base canônica
- **GIVEN** que sem `base_canonica` o carregador devolveria as regras do BO, sem erro
- **WHEN** o mapa vigente de `DFC` é carregado
- **THEN** o documento é `IPC08` e há 84 linhas

#### Scenario: os quadros da DFC saem na ordem do IPC 08
- **WHEN** o template da DFC é montado
- **THEN** os quadros saem em bloco, na ordem Quadro Principal, Transferências, Pessoal por
  Função e Juros — nunca intercalados — e a primeira linha é `L1` do grupo `OPERACIONAIS`

#### Scenario: o percurso completo inclui a DFC
- **WHEN** o percurso de todos os anexos é montado
- **THEN** os anexos a apurar são `BO`, `BF`, `BP`, `DFC` e `I-HI`, nessa ordem
