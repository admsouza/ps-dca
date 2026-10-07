# Design — Visualizar um anexo apurado nunca reprocessa

**Change:** `openspec/changes/pipeline-visualizar-sem-reprocessar/` · **Proposal aprovada pelo PO em:** 2026-10-07

## Contexto

`cache.ler_ou_enfileirar` usa a mesma função (`servivel`) para três perguntas distintas: "tem o que
mostrar?", "está atual?" e "precisa apurar?". A leitura, o reprocessamento e o percurso passam
todos por ela. Separar "tem o que mostrar" de "está atual" resolve a leitura sem mexer nos outros
dois caminhos.

## Componentes afetados

| Componente | Papel na change |
|---|---|
| `app/services/pipeline/cache.py` | `motivos_desatualizado(registro, versao_api, versao_regras)`; leitura serve `ok` sempre; `servivel` vira "ok e sem motivos" |
| `app/routes/anexos.py` | percurso: `versao_de` com a identidade do pedido (fonte padrão) |
| `worker.py` | percurso: pedido com a fonte padrão; apurador do percurso lê essa fonte |

## Fluxo da informação

```text
GET  → registro ok com resultado? ─sim→ 200 + resultado + desatualizado/motivos (nunca job)
                                 └não→ (ausente | erro | processando) caminho atual
POST reprocessar → forcar → job (inalterado)
POST batch-jobs  → montar_percurso: servivel() == ok e sem motivos → em_cache; senão a_apurar
```

## Contratos / interfaces

```python
# app/services/pipeline/cache.py
def motivos_desatualizado(registro, versao_api: str, versao_regras: str) -> list[str]:
    """[] | ["versao_api", "versao_regras", "pedido"] — `versao_regras` já traz o sufixo do pedido."""

def servivel(registro, versao_api, versao_regras) -> bool:     # ok, com resultado, sem motivos
```

`versao_regras` gravado é `"<hash das regras>|<identidade do pedido>"` (`versao_do_pedido`). A parte
antes do `|` decide `versao_regras`; a parte depois decide `pedido`.

Corpo do `200`: o `resultado` gravado, mais `desatualizado` e `motivos_desatualizado` no topo, como
os demais campos (`linhas`, `matriz`, `procedencia`, `diagnostico`).

## Impacto

| Eixo | Impacto |
|---|---|
| Banco / migration | nenhum |
| Cache | nada muda no que é gravado, exceto a fonte no pedido do percurso |
| Filas / worker | menos jobs: leitura nunca enfileira com resultado `ok` |
| APIs externas | menos leitura da MSC |
| Regressão | `reprocessar`, percurso, `already_queued`, órfão e erro inalterados |

## Decisões

### D1 — Desatualizado é servido, não é miss
**Escolhido:** `200` com o resultado gravado + motivos · **Descartado:** reapurar na leitura (hoje e
RREO/RGF) · **Porquê:** decisão do PO. Ver não pode trocar o número nem gastar MSC e worker.

### D2 — Motivos separados por origem
**Escolhido:** `versao_api`, `versao_regras`, `pedido` · **Porquê:** "o código mudou", "a regra
mudou" e "você pediu outra fonte" levam a ações diferentes do usuário. Um booleano só esconderia
qual delas.

### D3 — Percurso grava a fonte padrão
**Escolhido:** pedido do percurso = `{"fonte": DATA_SOURCE}` na rota e no worker, com o apurador
lendo essa fonte · **Descartado:** o `GET` ignorar a fonte na identidade · **Porquê:** SICONFI e
PublicSoft dão números diferentes, e a fonte precisa continuar na identidade. A escolha da fonte no
percurso é de `pipeline-fonte-por-pedido`.

## Arquivos criados / alterados

| Arquivo | Ação |
|---|---|
| `app/services/pipeline/cache.py` | alterar |
| `app/routes/anexos.py` | alterar (`versao_de` do percurso) |
| `worker.py` | alterar (pedido e apurador do percurso) |
| `tests/pipeline/test_visualizar_sem_reprocessar.py` | criar |
| testes vigentes de invalidação por versão | alterar (miss → desatualizado servido) |
