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

Todas as fases SPEC foram **aprovadas pelo PO em 2026-09-04**. As três estão liberadas para
PLAN/ARCH; nenhuma linha de código foi escrita.

| Change | Capability | Fase | Status |
|---|---|---|---|
| `plataforma-pipeline-dca` | `pipeline/plataforma` (nova) | **PLAN/ARCH** | SPEC aprovada em 2026-09-04. 22 requisitos / 63 cenários: ciclo requisição→cache→job→worker, camadas e regra de dependência, cache e lock únicos, `versao_regras` por hash canônico, mapeamento vigente em banco INSERT-only, reprocessamento forçado, procedência e diagnóstico. Infra: Postgres e Redis do hub, prefixo `dca_*`, `alembic_version_dca`, advisory lock `43812/1001`, fila `arq:queue:dca`. Implementada nas fases F2/F3 do BO. |
| `bo-quadro-principal-processamento` | `dca/balanco-orcamentario` (nova) | **PLAN/ARCH** | SPEC aprovada em 2026-09-04. 15 requisitos / 33 cenários. C1–C4 decididos; regra de saldo validada 1:1 em centavos contra JP 12/2025 (11 valores). Ordem F1 núcleo → F2 transporte → F3 pipeline. Depende das 51 regras de `ipc07-bo-regras-canonicas`. |
| `ipc07-bo-regras-canonicas` | `dca/base-canonica-regras` (nova) | **PLAN/ARCH** | SPEC aprovada em 2026-09-04. As 69 linhas do IPC 07 transcritíveis, 0 `review_required`. B1, B3, B5 decididos em 2026-08-27; B6, B2, B4 e dependências em 2026-09-03. |
| `knowledge-base-ipc` | `dca/base-canonica-regras` (nova) | SPEC — suspensa | Sucedida por changes separadas por IPC, começando por `ipc07-bo-regras-canonicas`. Não avançar nem arquivar até o PO confirmar o destino dos artefatos compartilhados. |

### Ordem de execução acordada

1. **F1 do BO** — núcleo puro (`domain/` + adapters + carregador YAML + service + CLI), verificável
   sem Postgres, Redis ou container. Aceite: os 11 valores de `docs/validacao-bo-jp-2025.md`.
2. **F2** — FastAPI e rota fina, conforme `plataforma-pipeline-dca`.
3. **F3** — job ARQ, cache, mapeamento em banco, registry, SSE, Discord.

## Changes arquivadas (recentes)

| Data | Change |
|---|---|
| — | — |

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
