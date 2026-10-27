# Proposal — DFC servida pelo pipeline

**Status:** proposta — aprovada pelo PO em 2026-10-27 ("concluir o backend do DFC").
**Repositório:** `ps-dca`
**Capability:** `pipeline/plataforma` (existente)
**Anexo:** `DFC` — demonstrativo derivado, como `BO` e `BF`; não é anexo publicado no `tt/dca`

## Why

`dfc-apuracao-f1` entrega a apuração e o CLI. A rota continua respondendo **404** para a DFC:
`validar_anexo("DFC")` levanta `AnexoDesconhecido` porque o anexo não está no `REGISTRY`
(`app/services/pipeline/registry.py`), e o front não tem o que consumir. Esta change fecha o
backend — é o espelho exato de `dvp-no-pipeline`.

## What Changes

- `registry.py`: `Anexo("DFC", "app.services.dfc.quadro_principal:apurar", base_canonica="dfc")`,
  junto dos derivados (`BO`, `BF`, `BP`), antes dos anexos que o STN publica.
- Asserções que fixam a lista de anexos implementados: passam de 4 para 5.
- Golden `tests/pipeline/golden/rota_recorte_sem_ug.json`: `DFC` aparece no resumo.

**Fora de escopo:** recorte por unidade gestora e escolha da origem do exercício anterior
(`dfc-por-unidade-gestora`), no padrão de `dvp-por-unidade-gestora`. `ORDEM_POR_DOCUMENTO["IPC08"]`
já entrou em `dfc-apuracao-f1`, porque o CLI daquela change precisava.

## Entradas e saídas

| Interface | Hoje | Depois |
|---|---|---|
| `GET /dca/DFC` | 404 | 200 com as 84 linhas, do cache |
| `POST /dca/DFC/reprocessar` | 404 | 202 |
| `GET /dca/resumo` | sem DFC | `DFC` com `implementado: true` |
| `POST /batch-jobs` | 4 anexos | 5 anexos |

A rota e o cache já são genéricos por anexo; o que falta é o registro.

## Critérios de aceite

- [x] `GET /dca/DFC` devolve 200 com 84 linhas, e o JSON é igual ao de `python -m app.cli.dfc`.
- [x] `GET /dca/resumo` lista `DFC` como implementado.
- [x] `POST /batch-jobs` enfileira os cinco anexos.
- [x] Grafia não canônica (`dfc`, `DFC `) resolve para `DFC`.
- [x] O mapa de `DFC` vem do IPC 08, não do IPC 07 do BO.
- [x] BO, BF, BP e DVP bit a bit iguais.
- [x] `python -m pytest` verde; `python -m ruff check .` limpo.

## Casos de erro

| Situação | Comportamento esperado |
|---|---|
| Anexo fora do registry | 404, como hoje |
| DFC sem cache | resumo responde `sem_cache`, sem iniciar cálculo |
| Linha informada inválida no reprocessamento | recusa antes de enfileirar, como no BF |

## Aprovação do PO

- [x] PO aprovou em 2026-10-27 — "vamos concluir o backend do DFC para só depois começar o front"
