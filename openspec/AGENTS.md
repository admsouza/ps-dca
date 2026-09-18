# OpenSpec — Instruções para agentes de IA

> Ver também [`AGENTS.md`](../AGENTS.md) na raiz (regras autoritativas): perguntar OpenSpec antes
> de especificar/implementar/refatorar; ao concluir a change, atualizar `tasks.md` e mover para
> `openspec/changes/archive/`.

## Fluxo de trabalho

1. Leia `openspec/project.md` para contexto do repositório.
2. Para trabalhar numa change ativa, leia **nesta ordem**:
   - `openspec/changes/<change>/proposal.md` — por quê e o quê
   - `openspec/changes/<change>/specs/**/spec.md` — requisitos (delta)
   - `openspec/changes/<change>/design.md` — como
   - `openspec/changes/<change>/tasks.md` — checklist (`- [ ]`)
3. A fonte de verdade do comportamento acordado está em `openspec/specs/`.
4. Durante uma change, edite apenas os deltas em `openspec/changes/<change>/specs/`.
5. Ao concluir e arquivar, os deltas são mesclados em `openspec/specs/`.

## Criar uma change

```bash
mkdir -p openspec/changes/<slug>/specs/<domínio>/<capability>
cp openspec/templates/proposal.md openspec/changes/<slug>/proposal.md
cp openspec/templates/spec.md     openspec/changes/<slug>/specs/<domínio>/<capability>/spec.md
cp openspec/templates/design.md   openspec/changes/<slug>/design.md
cp openspec/templates/tasks.md    openspec/changes/<slug>/tasks.md
```

Slug em kebab-case, prefixado pelo anexo quando aplicável: `dca-anexo-i-c-receitas`.

Domínios previstos: `dca/` (regra de anexo), `import/` (ingestão XBRL), `pipeline/`
(orquestração, cache, jobs), `auth/`, `front/` (consumo UI, implementado em outro repo).

## Regras de especificação

- Requisitos usam **SHALL/MUST**; cenários usam `#### Scenario:` (4 hashtags).
- Delta specs usam `## ADDED Requirements`, `## MODIFIED Requirements`, `## REMOVED Requirements`.
- Capability nova exige `## Purpose` no delta spec.
- Specs descrevem **comportamento observável** — não nomes de classes nem passos de implementação.
- Detalhes de implementação ficam em `design.md` e `tasks.md`.
- Toda spec de anexo cita a **base normativa** (MCASP/IPC/layout SICONFI) e ao menos um
  **exemplo real** (ente, exercício, valor esperado).

## Fases e gates

`SPEC → PLAN/ARCH → TEST → IMPLEMENT → REVIEW → VERIFY` — definição e gates de cada fase em
[`../AGENTS.md` §2](../AGENTS.md). A fase SPEC só fecha com **aprovação explícita do PO**.

## Change ativa

A base canônica do IPC 07, a F1 do Balanço Orçamentário e a plataforma (rota, cache, job, worker,
SSE) estão **implementadas, verificadas e arquivadas**.

Em **2026-09-18** o **Balanço Financeiro foi concluído no backend** e as quatro changes dele foram
arquivadas:

| Change arquivada | O que entregou |
|---|---|
| `2026-09-18-bf-apuracao-f1` | núcleo, serviço e CLI do quadro principal: 66 linhas × 2 colunas |
| `2026-09-18-bf-quadro-anexo` | as 14 linhas × 6 colunas do quadro anexo, com as derivadas |
| `2026-09-18-msc-competencia-de-encerramento` | competência 13 na PublicSoft, 12 no SICONFI |
| `2026-09-18-bf-no-pipeline` | `GET /dca/BF`: registry, cache multi-origem, serializador, chave |

A apuração foi medida contra a MSC do SICONFI em **5 entes de homologação**, com relatório de
auditoria por ente em `docs/entes-homologacao/<ente>/auditoria-bf-2025.md`: as 24 identidades do
IPC 06 fecham em todos, e **32 de 34** confrontos contra o RREO publicado pelo próprio ente batem em
centavos.

**Change ativa: apenas `plataforma-pipeline-dca`** (63 cenários, F2/F3 implementadas, spec ainda não
mesclada).

Pendências abertas que **não** bloqueiam o front:

- as 10 decisões de `docs/decisoes-bf-para-po-2026-09-18.md`, adotadas conforme a recomendação
  medida e sujeitas a confirmação na auditoria final;
- as divergências contra o BF publicado pelos entes, remetidas à etapa de auditoria;
- o critério de identificação da MSC de encerramento na periodicidade mensal
  (`docs/pendencias-periodicidade-mensal.md`).

## Changes arquivadas (recentes)

| Data | Change |
|---|---|
| 2026-09-14 | `msc-fonte-e-competencia` — **fonte MSC por demonstrativo e apuração mensal.** Decisão do PO: todos os demonstrativos sobre a matriz de **encerramento**, saldo de **abertura** no BO, BF, DVP e DFC, e de **encerramento** no BP. O par vira propriedade do demonstrativo, e a combinação errada deixa de ser exprimível. Competência passa a parâmetro (padrão 12), para entes que prestam contas mensalmente — nos meses 1–11 a leitura é a consolidada, porque a **`MSCE` só existe em dezembro** (medido). Regressão do BO: **337 células × 2 entes, zero divergências**. Retry com backoff nos adapters. Revoga a decisão C1. Capability nova `dca/fonte-msc` (12 cenários); BO passa a 46. Suíte **312 passed**. |
| 2026-09-14 | `ipc06-bf-regras-canonicas` — **base canônica do Balanço Financeiro (IPC 06, ed. 2024-06).** 80 regras em `knowledge/rules/bf/` (Quadro Principal 66 + Quadro Anexo 14), 5 policies e 3 enums novos: `fonte_recurso`, `saldo` (inicial/final) e `movimento` (credor/devedor). Campos e colunas passam a ser validados **por documento**. Fontes por subgrupo vindas do Anexo I da Portaria STN 710/2021 (`fontes-recursos-stn-2026.xlsx`, decisão F3). `review_required 6` — L22, L23, L28, L55, L56 e L61, sem mapeamento no IPC 06 (F1/F2). Suíte **287 passed**; parte `BO` do índice bit a bit igual. Spec: 27 requisitos / 83 cenários. Análise da fonte: `docs/source-analysis-ipc06.md`. |
| 2026-09-10 | `bo-template-no-resultado` — **template de apresentação no resultado.** `linhas` com `rule_id`, `codigo`, `rotulo`, `quadro`, `grupo`, `nivel`, `ordem` e `totalizadora`; `nivel`/`ordem` vindos da transcrição normativa, nunca derivados da composição; vigência antiga completada pela transcrição no carregamento. Aditiva: `matriz`, `procedencia` e `diagnostico` inalterados. 2 requisitos / 8 cenários mesclados na spec do BO (35 → 43). |
| 2026-09-10 | `ipc07-l51-reserva-rpps` — **L51 Reserva do RPPS apurada como L39.** Mesmo mapeamento `*id003`, filtros ND `9.9` + função `99` + subfunção `997`, fora do TOTAL (XV). Revoga a parte de B6 que deixava L51 sem coluna. |
| 2026-09-04 | `bo-quadro-principal-processamento` — **F1 do BO entregue e verificada.** Núcleo puro (`domain/` + adapters + carregador YAML + service + CLI), sem Postgres nem Redis. Aceite 1:1 em centavos contra JP 12/2025 e conferência linha a linha contra o `RREO-Anexo 01`. Spec em `openspec/specs/dca/balanco-orcamentario/spec.md` — 17 requisitos / 43 cenários. F2 e F3 são trabalho de `plataforma-pipeline-dca`. |
| 2026-09-04 | `ipc07-c5-c7-linhas-cruzadas` — **C5 e C7 fechadas.** `L25`, `L26`, `L49` e `L50` passam a ser apuradas, com colunas medidas no publicado do STN e referência que nomeia a coluna lida; `L29` perde `previsao_inicial` (B6 restringida). Motor: 3 casos distintos na parcela agregada e condição decidida por linha. **Suíte 153 passed / 0 failed** — verde pela primeira vez. Aceite: JP 13/13 em centavos, SP e GO conferidos. Evidência: `docs/evidencia-c5-deficit-superavit.md`. |
| 2026-09-04 | `ipc07-b1-remocao-termo-5313` — `5.3.1.3.0.00.00` removida da coluna (a) do quadro de RP Não Processados: descontinuada, com o conteúdo em `5.3.1.2`, já primeiro termo da fórmula. Revoga a decisão B1 de 2026-08-27. **Encerra a pendência C6 sem alteração de schema.** Regressão bit a bit: 0 células divergentes em 69 linhas. Removido de passagem o código morto de `natureza_saldo` e a função `_direcao_da_conta`, nunca chamada. Evidência: `docs/evidencia-c6-c7.md`. |
| 2026-09-04 | `ipc07-bo-regras-canonicas` — base canônica do IPC 07 entregue: 69 regras em `knowledge/rules/bo/`, 2 policies, schemas, validador e índice. 89 testes verdes; `review_required` 0. Spec em `openspec/specs/dca/base-canonica-regras/spec.md`. |
| 2026-09-04 | `knowledge-base-ipc` — sucedida por changes separadas por IPC; nunca implementada. Artefatos compartilhados (`knowledge/schemas/`, `knowledge/sources/`, `scripts/check_sources.py`) passaram para `ipc07-bo-regras-canonicas`. |

## Antes de codar (regras do projeto)

- **Não há código neste repositório e não haverá enquanto a spec não fechar com o PO.**
- Respeitar contrato de auth: JWT + `X-Unidade-Id`; rejeitar `x-authorization`.
- Importação XBRL: `C:\Projetos\prd-audite` manda (ver `../AGENTS.md` §4).
- Replicar o padrão de RREO/RGF antes de inventar abstração nova (YAGNI).
- Marcar tarefas concluídas em `tasks.md` no momento em que fecham (`- [x]`).

## Validação

A adotar na fase IMPLEMENT:

```bash
python -m pytest
python -m ruff check .
alembic upgrade head
```
