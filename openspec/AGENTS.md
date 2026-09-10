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

A base canônica do IPC 07 e a F1 do Balanço Orçamentário estão **implementadas, verificadas e
arquivadas**, com as três pendências normativas (C5, C6, C7) encerradas por medição contra o
publicado do STN. **L51 Reserva do RPPS** passou a ser apurada como a L39 e o **template de
apresentação** passou a acompanhar o resultado, ambos em 2026-09-10.
Resta uma change ativa: a plataforma.

| Change | Capability | Fase | Status |
|---|---|---|---|
| `plataforma-pipeline-dca` | `pipeline/plataforma` (nova) | **PLAN/ARCH** | SPEC aprovada em 2026-09-04. 22 requisitos / 63 cenários: ciclo requisição→cache→job→worker, camadas e regra de dependência, cache e lock únicos, `versao_regras` por hash canônico, mapeamento vigente em banco INSERT-only, reprocessamento forçado, procedência e diagnóstico. Infra: Postgres e Redis do hub, prefixo `dca_*`, `alembic_version_dca`, advisory lock `43812/1001`, fila `arq:queue:dca`. Implementada nas fases F2/F3 do BO. |

### Ordem de execução acordada

0. ~~Base canônica do IPC 07~~ — **concluída em 2026-09-04**. As 51 regras do Quadro Principal que
   a F1 do BO consome já existem em `knowledge/rules/bo/quadro_principal.yaml`.
1. **F1 do BO** — núcleo puro (`domain/` + adapters + carregador YAML + service + CLI), verificável
   sem Postgres, Redis ou container. Aceite: os 11 valores de `docs/validacao-bo-jp-2025.md`.
2. **F2** — FastAPI e rota fina, conforme `plataforma-pipeline-dca`.
3. **F3** — job ARQ, cache, mapeamento em banco, registry, SSE, Discord.

## Changes arquivadas (recentes)

| Data | Change |
|---|---|
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
