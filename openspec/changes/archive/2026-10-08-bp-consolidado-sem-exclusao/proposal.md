# Proposal — BP consolidado inclui todas as contas

**Status:** arquivada (2026-10-08)
**Repositório:** `ps-dca`
**Capability:** `dca/balanco-patrimonial` (existente)
**Anexo DCA:** `DCA-Anexo I-AB`
**Base normativa:** IPC 04 (`docs/referencia/ipc/IPC04 - BP atualizacao - 20200117.pdf`), item 8
**Revê:** `bp-visao-consolidado-isolado` (2026-10-08) — a visão `consolidado` deixa de executar as exclusões intra-OFSS

## Why

O processamento padrão precisa reproduzir o balanço declarado, com todas as contas. Em Cuité de Gi
(`2505204`) 2025 a aba `DCA-Anexo I-AB` fecha em 76.314.331,92 dos dois lados. A visão `consolidado`
tira as intra-OFSS e abre −2.004.721,69 (ativo 47.083.540,63, passivo e PL 49.088.262,32). O PO
decidiu em 2026-10-08: o processamento inclui tudo; não pode excluir.

## What Changes

- A apuração do BP deixa de aplicar os filtros `visao: consolidado`. `isolado` e `consolidado` saem
  iguais, com as contas intra-OFSS dentro das linhas.
- Os filtros permanecem nas regras (lista do IPC 04 e roundtrip da vigência). Não entram no cálculo.
- `GET /dca/BP?visao=` continua escolhendo a visão sem job. As duas matrizes passam a ter os mesmos valores.

**Fora de escopo:** BO, BF e demais anexos; apagar os filtros do YAML; quadros F/P, Compensação e Superávit.

## Entradas e saídas

| Interface | Entrada | Saída |
|---|---|---|
| `GET /dca/BP` | `visao=isolado` ou `visao=consolidado` (padrão `isolado`) | `matriz` e `diagnostico.equilibrio` com todas as contas; as duas visões com os mesmos valores |

## Exemplo concreto

| Ente | Exercício | Anexo | Célula | Valor esperado |
|---|---|---|---|---|
| 2505204 — Cuitegi/PB | 2025 | I-AB | `L1` e `L15`, visão `consolidado` | 76.314.331,92; equilíbrio 0,00 |

## Critérios de aceite

- [x] Cuitegi 2025, `visao=consolidado`: `L1` = `L15` = 76.314.331,92 e equilíbrio 0,00, iguais ao isolado e à planilha.
- [x] Conta intra sintética entra nas duas visões (`L10` 100,00; `L34` 10,00).
- [x] `python -m pytest` 606 passed. `ruff check` limpo nos arquivos desta change.

## Casos de erro

| Situação | Comportamento esperado |
|---|---|
| `visao` fora de `isolado\|consolidado` | `422` "visao inválida" |
| `visao` em anexo que não é BP | `422` |
| cache do BP sem a chave `visoes.consolidado` | `409` pedindo reprocessar |

## Restrições e riscos

- Cache gravado antes desta change ainda serve o consolidado antigo (com exclusão) até reprocessar o BP.
- A coluna Exclusões do IPC 04 deixa de ser executada. A lista continua declarada na regra.

## Aprovação do PO

- [x] PO aprovou em 2026-10-08 — processamento inclui tudo; não pode excluir.
