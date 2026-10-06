# dca/fonte-msc — Delta spec

## MODIFIED Requirements

### Requirement: Gate de auditoria da PublicSoft
O DCA SHALL NÃO consultar `/matriz-saldo/auditorias`, que exige o JWT do usuário (com o
`token_ps` responde `401`). Quem verifica a auditoria é o `base-demonstrativos`, que responde `409`
para competência não auditada. O adapter SHALL tratar esse `409` como **sem dados**. Qualquer
outro erro HTTP SHALL falhar a apuração. A consulta SHALL enviar só os parâmetros do DTO:
`anReferencia`, `meReferencia`, `classeConta` e `idTv`.

**Temporário, aguardando o PO:** a auditoria do **exercício anterior** fica desligada. O `409`
do exercício anterior não bloqueia o BF do exercício atual.

#### Scenario: encerramento na PublicSoft com auditoria pendente
- **WHEN** a competência 13 responde `409`
- **THEN** a leitura devolve conjunto vazio, sem consultar `/auditorias`

#### Scenario: erro que não é 409
- **WHEN** `base-demonstrativos` responde `401`
- **THEN** a apuração falha

#### Scenario: query dentro do DTO
- **WHEN** qualquer matriz é lida
- **THEN** os parâmetros são exatamente `anReferencia`, `meReferencia`, `classeConta` e `idTv`
