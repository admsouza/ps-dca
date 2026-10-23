# Design — DVP por unidade gestora

**Change:** `openspec/changes/dvp-por-unidade-gestora/` · **Proposal aprovada pelo PO em:** 2026-10-23

## Contexto

`com_recortes` (`app/services/pipeline/apuracao.py:223`) já apura consolidado, grupos de poder e
unidades para qualquer anexo listado em `RECORTAVEIS`, filtrando os registros por unidade
(`_Filtrada`) e observando as unidades do exercício (`_Observada`). O tratamento por unidade da
coluna anterior é decidido por introspecção: `por_unidade = "anterior" in _aceitos_por(apurar, …)`.

A DVP é o caso mais simples: não tem estorno (a parte cara do BF), não tem G8 e não tem publicado
por unidade.

## Componentes afetados

| Componente | Papel |
|---|---|
| `app/services/pipeline/apuracao.py` | `"I-HI"` em `RECORTAVEIS` |
| `app/services/pipeline/resumo.py` | `"I-HI"` em `COM_UNIDADES` |
| `app/services/dvp/quadro_principal.py` | `anterior` já era declarado; ganha `anterior_pronto`, `valores_anteriores` e `zero_sem_anterior` |
| `app/services/pipeline/anterior.py` | `validar_escolhas` aceita `I-HI` (`:163`) e `_validar_manual` despacha para a DVP (`:184`) |
| `app/services/dvp/informados.py` | criar, no formato de `app/services/bp/informados.py` |

## Fluxo da informação

```text
job → com_recortes → _Observada (unidades do exercício)
  → consolidado (MSCE) + um apurar por grupo de poder e por unidade (_Filtrada)
  → coluna anterior da unidade: escolha gravada | processado N−1 | MSCE | manual
  → consolidado e grupo: soma das colunas já resolvidas
  → cache por anexo, com os recortes no mesmo registro
```

## Contratos / interfaces

`apurar(ente, exercicio, fonte=…, mapa=…, anterior=…, valores_anteriores=…, anterior_pronto=…)`,
no mesmo vocabulário de `app/services/bp/quadro_principal.py`. Chaves de recorte: `consolidado`,
`poder:<nome>`, `ug:<id>`, `po:<código>`.

## Impacto

| Eixo | Impacto |
|---|---|
| Banco / migration | nenhum — os recortes vão no mesmo registro de cache |
| Cache | identidade do pedido passa a incluir as escolhas por unidade, como em BF e BP |
| Filas / worker | mesmo job; custo cresce com o número de unidades |
| APIs externas | nenhuma nova: a MSC já lida no job é reaproveitada |
| Regressão | consolidado da DVP bit a bit igual ao de `dvp-quadro-principal`; BO, BP e BF intactos |

## Decisões

### D1 — Sem estorno
**Escolhido:** a DVP não abate estorno em recorte nenhum. **Porquê:** o estorno de GRE/GDE é do BF
(`bf-estorno-receita-extra`); a DVP soma classes 3 e 4 da MSC e não tem linha de abatimento.

### D2 — Consolidado sem origem própria
**Escolhido:** a coluna anterior do consolidado é a soma das unidades resolvidas.
**Descartado:** `publicado_siconfi` como no BP. **Porquê:** o `I-HI` publicado é do ente inteiro;
não há `I-HI` por unidade para espelhar. Mesma regra de `pipeline-consolidado-anterior-soma-unidades`.

### D3 — Manual só nas linhas-base, pela estrutura
**Escolhido:** digitável é a linha sem `referencias`; chave `L<n>`, sem prefixo.
**Descartado:** lista de códigos escrita no validador; prefixo de quadro. **Porquê:** não é decisão
desta change, é o comportamento do manual **por unidade**, que é o do BP:
`app/services/bp/informados.py:58-59` recusa totalizadora pela estrutura do mapa
(`tests/bp/test_anterior_manual.py:104`) e a totalizadora sai da `calculation` (`:31`). Na DVP essas
linhas são exatamente L1, L9 e L19. O prefixo de chave só existe onde há mais de um quadro —
`P:`/`FP:`/`C:`/`S:` no BP, `A:` no quadro anexo do BF (`app/services/bf/informados.py:73`); o
quadro principal do BF, com um quadro só, usa `L2` direto. O manual do BF consolidado, que aceita
totalizadora (`bf/informados.py:85-90`), é anterior ao manual por unidade e não é o caso da DVP.

### D4 — Percurso por unidade sai de graça
**Escolhido:** nada a fazer para a DVP entrar no percurso completo por unidade.
**Porquê:** anexo em `RECORTAVEIS` é apurado com recortes em qualquer job (`apuracao.py:472`), e
`parametros_efetivos` (`app/services/pipeline/cache.py:128-151`) reaplica as escolhas gravadas por
unidade, sem lista de anexos. `pipeline-anterior-por-recorte` já declarou que no percurso cada
unidade usa a escolha gravada ou o padrão, porque o `/batch-jobs` não tem corpo.

## Arquivos criados / alterados

| Arquivo | Ação |
|---|---|
| `app/services/pipeline/apuracao.py` | alterar (`RECORTAVEIS`) |
| `app/services/pipeline/resumo.py` | alterar (`COM_UNIDADES`) |
| `app/services/dvp/quadro_principal.py` | alterar (coluna anterior por unidade e manual) |
| `app/services/pipeline/anterior.py` | alterar (`validar_escolhas`, `_validar_manual`) |
| `app/services/dvp/informados.py` | criar |
| `tests/recorte/test_dvp_por_unidade.py` | criar |
| `tests/pipeline/test_rota_dvp.py` | alterar (recorte deixa de ser 422) |

## Pendências conhecidas

- `tests/pipeline/test_rota_recorte.py` afirma hoje que `recorte` fora de BO/BP/BF é 422
  (`app/routes/anexos.py:179-180`). Esta change acrescenta a DVP à lista, e o teste muda junto —
  não é regressão.
- Os dois pontos da proposal que dependem do PO (manual e percurso por unidade).
