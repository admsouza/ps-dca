# Design — BP consolidado inclui todas as contas

**Change:** `openspec/changes/bp-consolidado-sem-exclusao/` · **Proposal aprovada pelo PO em:** 2026-10-08

## Contexto

`apurar` lê a fonte uma vez e calcula duas matrizes. A principal tira os filtros `visao: consolidado`.
A segunda usa o mapa inteiro e exclui as intra-OFSS. O PO mandou o processamento incluir todas as contas.

## Componentes afetados

| Componente | Papel na change |
|---|---|
| `app/services/bp/quadro_principal.py` | as duas visões saem do mapa sem os filtros de exclusão |
| `GET /dca/BP` | sem mudança de contrato; os valores das duas visões passam a coincidir |

## Fluxo da informação

```text
MSC/I-AB → apurar (mapa sem filtros visao=consolidado) → matriz
         → visoes.consolidado aponta para a mesma matriz
         → cache → GET ?visao=
```

## Contratos / interfaces

`Resultado.matriz` e `Resultado.visoes["consolidado"].matriz` têm os mesmos valores.
`diagnostico.equilibrio` e `visoes["consolidado"].equilibrio` também.
`visao` no `GET` continua `isolado` | `consolidado`, padrão `isolado`.

## Impacto

| Eixo | Impacto |
|---|---|
| Banco / migration | nenhum |
| Cache | registro antigo com consolidado excluído segue até reprocessar |
| Filas / worker | nenhum |
| APIs externas | nenhuma |
| Regressão | isolado bit a bit igual; consolidado passa a ser igual ao isolado |

## Decisões

### D1 — não executar a exclusão
**Escolhido:** apurar as duas visões no mapa sem os filtros `visao: consolidado`.
**Descartado:** apagar os filtros do YAML.
**Porquê:** a lista do IPC 04 e o roundtrip da vigência continuam; o cálculo é que deixa de excluir.

### D2 — uma matriz
**Escolhido:** a visão consolidado reutiliza a matriz já apurada.
**Descartado:** segunda apuração do mesmo mapa.
**Porquê:** o resultado é o mesmo e a fonte continua lida uma vez.

## Arquivos criados / alterados

| Arquivo | Ação |
|---|---|
| `app/services/bp/quadro_principal.py` | alterar |
| `tests/bp/test_visao.py` | alterar |
| `tests/bp/test_espelho_iab.py` | alterar |
| `tests/pipeline/test_bp_visao.py` | alterar |

## Pendências conhecidas

- Cache anterior a esta change só perde a exclusão depois de reprocessar o BP.
