# Proposal — Lint na base zero

**Status:** aprovada pelo PO em 2026-10-23
**Repositório:** `ps-dca`
**Capability:** nenhuma — **não há delta de spec**: zero mudança de comportamento
**Anexo DCA:** n/a

## Why

`AGENTS.md:99` manda `python -m ruff check .` sair **limpo**. Ele sai com 6 achados, e nenhum é
novo: vêm de antes das changes da DVP. Enquanto existirem, o gate VERIFY de toda change deixa de
ser binário — cada uma precisa comparar contra uma "linha de base" escrita à mão
(`bp-apuracao-f1` §4.2 já fazia isso em 2026-10-07, com 5 achados) e confiar em quem conferiu.
Achado novo some no meio dos antigos.

## What Changes

Os 6 achados, nenhum funcional:

| Arquivo | Achado |
|---|---|
| `app/infra/regras/vigencias.py:121` | `I001` imports fora de ordem |
| `app/infra/regras/vigencias.py:188` | `E501` 107 colunas |
| `tests/bo/test_template.py:206` | `I001` imports fora de ordem |
| `tests/pipeline/test_autorizacao_por_ug.py:314` | `E501` 101 colunas |
| `tests/pipeline/test_unidade_por_header.py:1` | `E501` 101 colunas |
| `tests/pipeline/test_unidade_por_header.py:5` | `F401` `HTTPException` importado e não usado |

Três saem com `ruff check --fix` (os dois `I001` e o `F401`); três são quebra de linha manual.

**Fora de escopo:** renomear, reorganizar módulo, mexer em lógica, mudar a configuração do ruff
(`pyproject.toml`). Se um achado exigisse mudar comportamento para sumir, ele ficaria e viraria
dívida declarada — nenhum dos 6 exige.

## Critérios de aceite

- [x] `python -m ruff check .` sai com **0 achados**.
- [x] `python -m pytest`: 916 passed, 3 deselected — o mesmo de antes.
- [x] Nenhuma linha de lógica alterada: o diff é import, quebra de linha e remoção de import morto.

## Aprovação do PO

- [x] PO aprovou em 2026-10-23, ao fim da trilha da DVP
