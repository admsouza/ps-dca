# pipeline/unidade-gestora — Delta spec

## ADDED Requirements

### Requirement: Recortes da DVP apurados no mesmo job

O job da DVP SHALL apurar, além do consolidado, um resultado por grupo de poder e um por unidade —
`ug:<id>` quando a fonte informa a unidade gestora, `po:<código>` quando não informa. Cada recorte
SHALL ser o mesmo serviço de apuração sobre os registros filtrados da unidade, sem nova leitura da
fonte. A soma das 16 linhas-base das unidades SHALL ser igual à do consolidado, em centavos.

#### Scenario: unidades somam o consolidado

- **GIVEN** um ente cuja MSC traz mais de uma unidade gestora no exercício
- **WHEN** a DVP é apurada
- **THEN** cada `ug:` tem resultado próprio
- **AND** a soma de cada linha-base das unidades é igual à do consolidado, em centavos

#### Scenario: uma leitura da fonte para todos os recortes

- **WHEN** o job apura consolidado, grupos e unidades
- **THEN** a MSC do exercício é lida uma vez, como já vale para BO, BP e BF

### Requirement: Leitura de um recorte da DVP sem reprocessar

`GET /dca/I-HI?recorte=` SHALL servir o recorte do cache, sem enfileirar job, com as mesmas chaves
de BO, BP e BF: `consolidado`, `poder:<nome>`, `ug:<id>` e `po:<código>`. Recorte inexistente ou
malformado SHALL responder 422, sem job. A visibilidade por poder do usuário SHALL ser a mesma já
aplicada aos outros anexos.

#### Scenario: leitura de recorte não enfileira

- **WHEN** `GET /dca/I-HI?recorte=ug:3` é pedido com o cache já gravado
- **THEN** a resposta é 200 com o resultado daquela unidade
- **AND** nenhum job é enfileirado

#### Scenario: recorte malformado

- **WHEN** `GET /dca/I-HI?recorte=ug` é pedido
- **THEN** a resposta é 422, sem job

#### Scenario: unidade fora do poder do usuário

- **GIVEN** um usuário do Legislativo
- **WHEN** ele pede um recorte do Executivo na DVP
- **THEN** a recusa é a mesma que vale para BO, BP e BF

#### Scenario: percurso completo apura a DVP por unidade

- **WHEN** o percurso completo roda para um ente com escolhas gravadas por unidade na DVP
- **THEN** a DVP é apurada com recortes, reaplicando a escolha gravada de cada unidade
- **AND** o percurso não aceita `anterior_por_recorte` no corpo, que ele não tem

#### Scenario: resumo publica os recortes da DVP

- **WHEN** `GET /dca/resumo` é lido para um ente com a DVP apurada por unidade
- **THEN** a entrada de `I-HI` traz `recortes`
