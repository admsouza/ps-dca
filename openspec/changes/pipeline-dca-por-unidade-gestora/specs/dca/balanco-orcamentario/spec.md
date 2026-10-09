# dca/balanco-orcamentario — Delta spec

## MODIFIED Requirements

### Requirement: Fontes MSC intercambiáveis atrás do mesmo contrato

Os adapters SICONFI e PublicSoft SHALL entregar registros com o mesmo conjunto de campos em
snake_case — `conta_contabil`, `natureza_conta`, `valor`, `natureza_receita`, `natureza_despesa`,
`fonte_recursos`, `poder_orgao`, `complemento_fonte` e `id_unidade_gestora`. O SICONFI não tem UG:
nele `id_unidade_gestora` é vazio. O núcleo de apuração NÃO DEVE conter referência a HTTP, a nome de
endpoint ou a formato de resposta de qualquer fonte.

#### Scenario: mesma matriz por fontes diferentes
- **GIVEN** o mesmo ente, ano e mês disponíveis nas duas fontes com os mesmos saldos
- **WHEN** o quadro é apurado com cada uma
- **THEN** as duas matrizes consolidadas são iguais célula a célula

#### Scenario: gate de auditoria da PublicSoft reprovado
- **GIVEN** que a base de demonstrativos responde `409` (auditoria não liberada)
- **WHEN** os saldos são solicitados à PublicSoft
- **THEN** o adapter devolve conjunto vazio de registros, sem levantar erro de transporte
- **AND** a apuração reporta ausência de dados, não zeros

#### Scenario: normalização de camelCase
- **GIVEN** uma resposta da PublicSoft com `codConta`, `naturezaConta`, `naturezaReceita`,
  `poderOrgao`, `idUnidadeGestora` e `nomeUnidadeGestora`, em `data[]` ou `items[]`
- **WHEN** o adapter normaliza
- **THEN** os campos chegam ao núcleo como `conta_contabil`, `natureza_conta`, `natureza_receita`,
  `poder_orgao` e `id_unidade_gestora`, e o nome da UG fica disponível para a lista da resposta

#### Scenario: base por UG indisponível para o ente
- **GIVEN** a base por UG responde `422` (MSC do ente importada por CSV)
- **WHEN** o job lê a fonte
- **THEN** o job apura o consolidado pela base de demonstrativos oficial, como hoje
- **AND** o recorte do resultado é por `poder_orgao` (`tipo_recorte` = `PO`)
