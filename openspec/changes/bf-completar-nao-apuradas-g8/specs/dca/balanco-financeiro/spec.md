# dca/balanco-financeiro — Delta spec

## MODIFIED Requirements

### Requirement: Linha sem conta declarada no IPC 06 não é apurada

Seis linhas do quadro principal — `L22`, `L23`, `L28`, `L55`, `L56`, `L61` — não têm conta
declarada na base canônica. Por padrão elas SHALL sair **não apuradas** (`None`), com motivo no
diagnóstico, e NÃO DEVEM sair como zero.

Quem apura MAY completar a coluna **`exercicio_atual`** dessas seis linhas informando
`valores_sem_mapeamento` no corpo de `POST /dca/BF/reprocessar`. Esse override NÃO É o modo Manual
do exercício anterior e NÃO DEVE exigir `origem_exercicio_anterior: manual`.

Após o merge, a apuração SHALL reaplicar as compostas da coluna atual (para o total refletir a
parcela) e SHALL remover as células completadas de `diagnostico.nao_apuradas`. O mapa informado
SHALL ser gravado em `procedencia.valores_sem_mapeamento`. Pedido seguinte do mesmo ente e exercício
**sem** a chave no body SHALL reaplicar o mapa salvo. Corpo com `valores_sem_mapeamento: {}` SHALL
limpar o override.

Código fora da whitelist G8 ou decimal inválido SHALL ser recusado com `422` sem substituir o mapa
já salvo. `valores_sem_mapeamento` na query SHALL responder `400`.

A coluna do exercício atual, **fora** dessas seis linhas, NÃO DEVE aceitar preenchimento manual.

#### Scenario: linha sem conta sai não apurada

- **GIVEN** nenhum `valores_sem_mapeamento` salvo
- **WHEN** `L22` é apurada
- **THEN** a célula `exercicio_atual` é `None`
- **AND** o diagnóstico nomeia a linha e o motivo

#### Scenario: completar G8 no exercício atual

- **GIVEN** Recife (`2611606`), exercício 2025, corpo com `valores_sem_mapeamento.L22` = `1234567.89`
- **WHEN** o job de reprocessar termina
- **THEN** `exercicio_atual` de `L22` é `1234567.89`
- **AND** `procedencia.valores_sem_mapeamento` contém `L22`
- **AND** o diagnóstico NÃO lista `l22.exercicio_atual` como não apurada
- **AND** `origem_exercicio_anterior` permanece a que já estava (MSC ou manual), sem ser forçada a `manual`

#### Scenario: GET seguinte reaplica o mapa G8

- **GIVEN** a procedência do BF de Recife/2025 já contém `L22` = `1234567.89` em `valores_sem_mapeamento`
- **WHEN** um `GET /dca/BF` roda sem o mapa no body
- **THEN** `exercicio_atual` de `L22` continua `1234567.89`

#### Scenario: código fora de G8 é recusado

- **GIVEN** corpo com `valores_sem_mapeamento.L17` = `1.00`
- **WHEN** a request é validada
- **THEN** a API responde `422`
- **AND** o mapa G8 já salvo NÃO é substituído

#### Scenario: o total soma a parcela G8 informada

- **GIVEN** `L21` = `L22` + `L23` e `L22` informada em `valores_sem_mapeamento`
- **WHEN** a matriz é apurada
- **THEN** `L21.exercicio_atual` reflete a composta com a parcela de `L22`

## ADDED Requirements

### Requirement: `valores_sem_mapeamento` só no corpo

`valores_sem_mapeamento` SHALL viajar só no corpo JSON de `POST /dca/BF/reprocessar`. Na query
SHALL ser recusado com `400`.

#### Scenario: mapa G8 na query é recusado

- **WHEN** `valores_sem_mapeamento` aparece na query
- **THEN** a API responde `400`
