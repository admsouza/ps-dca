# pipeline/processamento-completo — Delta spec

## MODIFIED Requirements

### Requirement: Percurso deriva a coluna anterior do consolidado

`POST /batch-jobs` SHALL processar BF e BP sem origem própria do consolidado. Para cada unidade, o
percurso SHALL reaplicar a escolha gravada ou o padrão de `pipeline/anterior-por-recorte`; depois,
SHALL formar o consolidado pela soma das unidades.

O campo legado `origem_exercicio_anterior` NÃO DEVE ser aceito para BF ou BP e SHALL responder `422`
antes de criar o percurso. A identidade do pedido não deve mais variar por origem do consolidado.

#### Scenario: percurso soma as escolhas gravadas

- **GIVEN** unidades com escolhas anteriores gravadas em origens diferentes
- **WHEN** `POST /batch-jobs` é executado sem origem consolidada
- **THEN** BF e BP reaplicam as escolhas de cada unidade
- **AND** cada consolidado declara `soma_das_unidades`

#### Scenario: percurso recusa origem consolidada

- **WHEN** `POST /batch-jobs` recebe `origem_exercicio_anterior`
- **THEN** responde `422`
- **AND** nenhum job de anexo é enfileirado

#### Scenario: falha de atribuição não publica parcial

- **GIVEN** uma contribuição anterior sem recorte no BF ou no BP
- **WHEN** o percurso alcança o anexo
- **THEN** esse anexo termina em `erro`, sem cache `ok` parcial
- **AND** o percurso mantém o tratamento de falha por anexo já vigente

## REMOVED Requirements

### Requirement: Percurso respeita a origem da coluna anterior do BP

**Motivo:** o BP consolidado deixa de receber origem própria. · **Migração:** o percurso reaplica as
escolhas por unidade e deriva o consolidado da soma.
