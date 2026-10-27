# dca/demonstracao-fluxos-caixa — Delta spec

## Purpose

Impedir que o mesmo desembolso de investimento seja contado em duas linhas.

## ADDED Requirements

### Requirement: Outros desembolsos de investimentos é residual
`L25` SHALL ser apurada apenas sobre os registros que **não** atendem aos filtros de `L23` nem aos
de `L24`. A exclusão SHALL ser por registro, nunca por subtração de totais, e `L25` NÃO DEVE
resultar negativa por esse motivo. Os filtros declarados no YAML NÃO DEVEM mudar.

#### Scenario: aquisição de ativo não entra duas vezes
- **GIVEN** uma despesa paga de elemento 52 e modalidade 90, que atende aos filtros de `L23` e
  também aos de `L25`
- **WHEN** a DFC é apurada
- **THEN** o valor aparece só em `L23`, `L25` fica `0,00` e `L22` é igual a `L23`

#### Scenario: o que L23 exclui continua em L25
- **GIVEN** uma despesa que o `not_in` de `L23` recusa e que atende aos filtros de `L25`
- **WHEN** a DFC é apurada
- **THEN** ela entra em `L25` — a exclusão mútua tira de `L25` apenas o que de fato entrou em
  `L23` ou `L24`
