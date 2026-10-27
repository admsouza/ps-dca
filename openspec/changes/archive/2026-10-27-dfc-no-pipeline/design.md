# Design — DFC servida pelo pipeline

**Change:** `openspec/changes/dfc-no-pipeline/` · **Proposal:** aprovada pelo PO em 2026-10-27

## Contexto

`dfc-apuracao-f1` entregou `app/services/dfc/` e o CLI. A rota já é genérica por anexo
(`anexos.py:583`), o cache também, e o despacho resolve o serviço pelo registry
(`apuracao.py`). O que falta é uma linha de registro — e as asserções que fixam a lista de
anexos implementados.

## Decisões

### D1 — `DFC` entre os derivados, não entre os `I-*`
**Escolhido:** o anexo entra logo depois do `BP`, antes de `I-AB`. **Descartado:** usar `I-E`.
**Porquê:** `I-E` é despesa por função, outro demonstrativo
(`docs/anexos-siconfi-inventario.md`). A DFC é derivada da MSC e **não** é publicada pelo
`tt/dca`, exatamente como `BO` e `BF` — a ordem do registry é a de apresentação, e ela agrupa os
derivados.

### D2 — Golden alterado cirurgicamente
**Escolhido:** reescrever no golden apenas as 12 entradas `*|resumo`, mantendo formatação.
**Descartado:** regerar o arquivo inteiro. **Porquê:** regerar produziu 17 mil linhas de diff por
formatação, escondendo a mudança real. Conferido antes de gravar: as únicas diferenças são as 12
entradas de resumo ganhando `DFC`, e nenhuma entrada `*|leitura` mudou.

## Arquivos alterados

| Arquivo | Ação |
|---|---|
| `app/services/pipeline/registry.py` | `ANEXO_DFC` e a entrada no `REGISTRY` |
| `tests/pipeline/test_dfc_no_pipeline.py` | criar |
| `tests/pipeline/test_rota_dfc.py` | criar |
| `tests/pipeline/test_pipeline_completo.py` | 4 anexos → 5 |
| `tests/pipeline/test_dvp_no_pipeline.py` | lista do percurso |
| `tests/pipeline/test_notificacao_discord.py` | lista do percurso |
| `tests/pipeline/golden/rota_recorte_sem_ug.json` | 12 entradas de resumo |
| `app/routes/`, `app/services/pipeline/cache.py` | **nenhum** — já genéricos |

## Impacto

| Eixo | Impacto |
|---|---|
| Banco / migration | nenhum |
| Cache | a DFC passa a ter entrada própria; nada invalidado |
| Front | `GET /dca/DFC` deixa de responder 404 |
| Regressão | BO, BF, BP e DVP bit a bit iguais |
