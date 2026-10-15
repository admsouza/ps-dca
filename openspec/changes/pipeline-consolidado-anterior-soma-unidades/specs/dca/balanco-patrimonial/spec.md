# dca/balanco-patrimonial — Delta spec

## MODIFIED Requirements

### Requirement: Origem da coluna do exercício anterior escolhida pelo usuário

A origem da coluna do exercício anterior do BP SHALL ser escolhida por unidade `ug:` ou `po:` pela
capability `pipeline/anterior-por-recorte`: resultado processado de N−1, MSC de N−1 ou valores
manuais da própria unidade. O consolidado SHALL ser a soma das colunas resolvidas das unidades e
NÃO DEVE aceitar `publicado_siconfi`, `msce_exercicio_anterior`, `processado_exercicio_anterior` ou
`manual` como origem própria.

As duas visões do BP e o quadro do Superávit/Déficit SHALL obedecer à mesma soma por unidade. A coluna
do exercício atual e o espelho vigente do DCA-Anexo I-AB NÃO DEVEM mudar.

#### Scenario: consolidado do BP usa somente as unidades

- **GIVEN** unidades do BP com origens anteriores resolvidas
- **WHEN** o BP é apurado
- **THEN** todas as folhas anteriores do consolidado são a soma das unidades com diferença `0,00`
- **AND** nenhuma DCA publicada ou MSC adicional é lida para o consolidado

#### Scenario: manual por unidade substitui manual consolidado

- **WHEN** uma unidade recebe valores manuais válidos em `anterior_por_recorte`
- **THEN** esses valores entram na soma do consolidado
- **AND** valores manuais no topo do pedido são recusados

#### Scenario: exercício atual permanece igual

- **WHEN** o mesmo BP é apurado antes e depois desta change com a mesma fonte atual
- **THEN** a coluna do exercício atual e os quadros atuais são bit a bit iguais

## REMOVED Requirements

### Requirement: Manual no consolidado do BP

**Motivo:** o consolidado passa a ser derivado das unidades e não pode ter valores próprios. ·
**Migração:** distribuir os valores manuais pelas unidades correspondentes em
`anterior_por_recorte`; dado sem unidade falha explicitamente.
