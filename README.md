# ps-dca

Processamento da **DCA** (Declaração de Contas Anuais — SICONFI/STN): cálculo dos anexos,
cache por anexo e espelho conferível contra a API oficial `tt/dca`.

> **Estado: fase de spec.** Não há código nem arquitetura definida. Nada é implementado
> antes das specs fecharem com o PO.

## Por onde começar

| Objetivo | Arquivo |
|---|---|
| Processo de trabalho (agentes e humanos) | [`AGENTS.md`](AGENTS.md) |
| Contexto, escopo e stack alvo | [`openspec/project.md`](openspec/project.md) |
| Fluxo OpenSpec e changes ativas | [`openspec/AGENTS.md`](openspec/AGENTS.md) |
| Modelos de artefato | [`openspec/templates/`](openspec/templates/) |
| Referência normativa (IPCs) | [`docs/referencia/ipc/`](docs/referencia/ipc/) |

## Ciclo

```text
SPEC → PLAN/ARCH → TEST → IMPLEMENT → REVIEW → VERIFY
```

Projetos irmãos com o mesmo padrão: `regras-rreo-api` (RREO), `regras-rgf-api` (RGF).
Importação XBRL: `prd-audite` (fonte da verdade).
