# Design — Exercício anterior somente Processado ou Manual

**Change:** `openspec/changes/dca-anterior-processado-manual/` · **Proposal aprovada pelo PO em:** 2026-10-21

## Contexto

`pipeline/anterior.py` resolve hoje `sem escolha = Processado se existir, senão MSCE`. A mudança
remove esse fallback sem alterar a MSC usada para apurar o exercício atual nem a primeira passada
interna que descobre os recortes.

## Componentes afetados

| Componente | Papel na change |
|---|---|
| `app/services/pipeline/anterior.py` | aceitar somente Processado/Manual e exigir N−1 no padrão |
| `app/routes/anexos.py` | devolver `409` antes de enfileirar quando o padrão não pode ser atendido |
| `app/services/pipeline/cache.py` | normalizar escolhas legadas de MSCE |
| `tests/recorte` e `tests/pipeline` | cobrir padrão, manual, legado e erros HTTP |

## Fluxo da informação

```text
pedido → escolha efetiva por unidade → exigir Processado N−1 ou validar Manual → job → soma dos recortes
```

## Contratos / interfaces

`anterior_por_recorte` aceita `processado_exercicio_anterior`, `manual` e `padrao`. `padrao`
remove a escolha gravada e volta a Processado. MSCE deixa de ser entrada pública.

## Impacto

| Eixo | Impacto |
|---|---|
| Banco / migration | nenhum |
| Cache | procedência antiga com MSCE é normalizada; identidade continua por escolhas explícitas |
| Filas / worker | nenhum job novo; a ausência de N−1 falha antes da fila quando detectável |
| APIs externas | nenhuma |
| Regressão | exercício atual, regras e manual permanecem iguais |

## Decisões

### D1 — Ausência de Processado
**Escolhido:** `409` com Processar N−1 ou Manual · **Descartado:** fallback MSCE · **Porquê:** um
fallback invisível contradiz as duas origens acordadas.

### D2 — MSCE interna
**Escolhido:** manter somente onde a apuração interna precisa observar a fonte atual ·
**Descartado:** apagar o suporte dos serviços BF/BP · **Porquê:** isso ampliaria o diff e quebraria
testes/CLI sem necessidade; a origem deixa de ser pública, não a leitura da MSC.

### D3 — Legado
**Escolhido:** normalizar escolha gravada de MSCE para ausência de escolha · **Descartado:** migração
de banco · **Porquê:** a procedência já é JSON e a normalização no limite evita migration.

## Arquivos criados / alterados

| Arquivo | Ação |
|---|---|
| `app/services/pipeline/anterior.py` | alterar |
| `app/routes/anexos.py` | alterar |
| `app/services/pipeline/cache.py` | alterar, se a normalização não couber no resolver |
| `tests/recorte/test_anterior_por_recorte.py` | alterar |
| `tests/pipeline/test_rota_anterior_por_recorte.py` | alterar |
| specs vigentes de pipeline, BF e BP | atualizar no arquivamento |

## Pendências conhecidas

- Nenhuma decisão contábil; somente comportamento da origem.
