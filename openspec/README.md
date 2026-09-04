# OpenSpec — ps-dca

Especificações versionadas no padrão [OpenSpec](https://openspec.pro/).
Processo autoritativo: [`../AGENTS.md`](../AGENTS.md).

## Estrutura

```text
openspec/
├── project.md               # contexto do projeto (ler primeiro)
├── AGENTS.md                # fluxo OpenSpec + tabela de changes ativas
├── config.yaml              # contexto + regras para agentes
├── templates/               # proposal.md · spec.md · design.md · tasks.md
├── specs/                   # fonte de verdade (comportamento acordado)
└── changes/
    ├── <change-ativa>/
    │   ├── proposal.md
    │   ├── design.md
    │   ├── tasks.md
    │   └── specs/<domínio>/<capability>/spec.md
    └── archive/AAAA-MM-DD-<slug>/
```

## Ciclo

| Fase | Artefato | Gate |
|---|---|---|
| SPEC | `proposal.md` + delta `specs/` | aprovação explícita do PO |
| PLAN/ARCH | `design.md` + `tasks.md` | decisões `D1..Dn` + arquivos listados |
| TEST | `tests/test_*.py` | teste falha pelo motivo esperado |
| IMPLEMENT | código mínimo | suíte verde, `tasks.md` marcado |
| REVIEW | `git diff` | escopo limpo |
| VERIFY | pytest + ruff + alembic + espelho 1:1 | resultado medido e reportado |

## Índice de specs (baseline)

| Domínio | Spec | Status |
|---|---|---|
| — | — | Nenhuma spec fechada ainda |

## Change ativa

| Change | Capability | Fase |
|---|---|---|
| — | — | — |
