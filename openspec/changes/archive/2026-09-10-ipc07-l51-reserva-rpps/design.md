# Design — L51 Reserva do RPPS apurada como L39

**Change:** `openspec/changes/ipc07-l51-reserva-rpps/` · **Proposal aprovada pelo PO em:** 2026-09-10

## Contexto

`L51` nasceu com `columns: {}` (B6). O motor devolve `{}` antes de aplicar filtros. O PO mandou
apurá-la como `L39`, com o mapeamento de contas já ancorado em `*id003`.

## Componentes afetados

| Componente | Papel |
|---|---|
| `knowledge/rules/bo/quadro_principal.yaml` | `L51` passa a `columns: *id003` |
| `app/domain/bo/matriz.py` | `_celulas` já apura linha com colunas; L51 deixa de cair no early-return |
| `app/infra/regras/vigencias.py` | `_completar_apresentacao` acrescenta as 6 colunas na semente antiga |
| testes / spec / `docs/source-analysis-ipc07.md` | cenário B6 de L51 atualizado |

## Fluxo da informação

```text
MSC → filtros L51 (ND 9.9 ∧ função 99 ∧ subfunção 997) → contas *id003 → 6 células
L50 = L48 + L49  (L51 não entra)
```

## Contratos / interfaces

Inalterado. `matriz["bo.quadro_principal.despesas.l51"]` deixa de ser `{}` e passa a ter as
chaves de despesa.

## Impacto

| Eixo | Impacto |
|---|---|
| Banco / migration | nenhum; jsonb da semente ganha colunas na leitura |
| Cache | `versao_regras` muda — cache BO invalida |
| Filas / worker | nenhum |
| APIs externas | nenhum |
| Regressão | L27–L50 bit a bit iguais; só L51 deixa de ser vazio |

## Decisões

### D1 — mesmo mapeamento da L39
**Escolhido:** `columns: *id003` · **Descartado:** copiar o bloco à mão · **Porquê:** uma âncora, um mapa.

### D2 — fora do XV
**Escolhido:** não referenciar L51 em L40/L50 · **Descartado:** somar no (X) ou no (XV) · **Porquê:** a ESTRUTURA continua depois do total; o PO pediu cálculo, não reclassificação.

### D3 — B6 restrita
**Escolhido:** revogar só a parte L51 · **Descartado:** reabrir L27–L30 · **Porquê:** escopo fechado.

## Arquivos criados / alterados

| Arquivo | Ação |
|---|---|
| `knowledge/rules/bo/quadro_principal.yaml` | alterar L51 |
| `docs/source-analysis-ipc07.md` | adendo B6 |
| `tests/test_base_ipc07.py` | alterar cenário L51 |
| `tests/bo/test_apuracao.py` | alterar apuração L51 |
| `app/domain/bo/matriz.py` | comentário |
| `scripts/validate_rules.py` | comentário |
| `openspec/specs/dca/*` | mesclar delta ao arquivar |

## Pendências conhecidas

- Aceite 1:1 contra `tt/dca` para L51 depende de ente que publique a linha; JP 2025 omite.
