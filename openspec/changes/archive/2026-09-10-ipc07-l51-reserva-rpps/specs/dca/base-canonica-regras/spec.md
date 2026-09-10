# dca/base-canonica-regras — Delta spec (L51)

## MODIFIED Requirements

### Requirement: Decisões do PO são aplicadas com escopo fechado e auditável

As decisões do PO sobre B1, B3, B5 e B6 SHALL ser registradas na regra e aplicadas somente ao caso
decidido. A validação SHALL rejeitar a ampliação dessas exceções para outros `rule_id`, contas ou
domínios. A decisão NÃO DEVE apagar o literal do IPC07 nem alterar as tabelas de
`docs/contas-stn/`.

Decisão revogada por decisão posterior SHALL ter a revogação registrada, e a decisão anterior NÃO
DEVE ser apagada do histórico em `docs/source-analysis-ipc07.md`. A decisão **B1** de 2026-08-27 —
preservar `5.3.1.3.0.00.00` como exceção histórica do PCASP 2019 — foi **revogada em 2026-09-04**:
a conta foi descontinuada e seu conteúdo está em `5.3.1.2.0.00.00`, já declarada na mesma coluna.
Nenhuma regra invoca mais a exceção B1. A decisão **B3** segue valendo — seus padrões são usados
como `field: conta_contabil` em filtro, não como conta de coluna.

A decisão **B6** de 2026-09-03 — `L27` a `L30` com as quatro colunas de receita — foi
**restringida em 2026-09-04**: `L29` Superávit Financeiro NÃO declara `previsao_inicial`, porque
**zero de 25 entes** publicam `PREVISÃO INICIAL` para `SuperavitFinanceiro` no `RREO-Anexo 01`.

A parte de B6 que deixava `L51` sem coluna de valor foi **revogada em 2026-09-10**: o PO mandou
apurar `L51` como `L39`, com o mapeamento `*id003`. `L51` permanece fora do `TOTAL (XV)`.
`L27`–`L30` não mudam.

#### Scenario: L27, L28 e L30 têm as quatro colunas de receita, e L29 tem três

- **GIVEN** que a p. 15 mostra `L28`, `L29` e `L30` sem marcação de coluna, e o PO decidiu em
  2026-09-03 que a seção REGRAS prevalece
- **WHEN** `L27`, `L28`, `L29` e `L30` são lidas
- **THEN** `L27`, `L28` e `L30` declaram as 4 colunas de receita — `previsao_inicial`,
  `previsao_atualizada`, `receitas_realizadas` e `saldo`
- **AND** `L29` declara **três**: `previsao_atualizada`, `receitas_realizadas` e `saldo`
- **AND** cada uma registra `provenance.decision: B6` e não fica `review_required`

#### Scenario: L51 Reserva do RPPS usa o mapeamento de despesa da L39

- **GIVEN** o IPC 07 p. 11 `L51 Reserva do RPPS ND 9.9.00.00.00 Função 99.997` e a decisão do PO
  em 2026-09-10
- **WHEN** `bo.quadro_principal.despesas.l51` é lida
- **THEN** `columns` é o mesmo conjunto da `L39` (`dotacao_inicial`, `dotacao_atualizada`,
  `empenhadas`, `liquidadas`, `pagas`, `saldo_dotacao`) com as mesmas contas
- **AND** os filtros `natureza_despesa = 9.9.00.00.00`, `funcao = 99` e `subfuncao = 997` são
  preservados
- **AND** `L50` NÃO referencia `L51`
- **AND** a regra registra `provenance.decision: B6` e não fica `review_required`

#### Scenario: override de conta fora de L29 e L30 é rejeitado

- **WHEN** qualquer regra diferente de `bo.quadro_principal.receitas.l29` e
  `.l30` declara `line_account_override: true`
- **THEN** a validação reporta que o override não é permitido para o `rule_id` e termina com exit
  `1`

## REMOVED Requirements

Nenhum requisito inteiro. O cenário `L51 não tem coluna de valor` deixa de valer (substituído pelo
cenário acima).
