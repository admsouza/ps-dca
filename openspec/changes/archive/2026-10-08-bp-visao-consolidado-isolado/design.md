# Design — BP emitido isolado ou consolidado

**Change:** `openspec/changes/bp-visao-consolidado-isolado/` · **Proposal aprovada pelo PO em:** 2026-10-08

## Fluxo

```text
GET /dca/BP?visao=…  ──► cache (ente, exercício, BP) ──► resultado.visoes[visao]  (200, sem job)
reprocessar/percurso ──► job ──► apurar BP: lê a fonte 1× ──► matriz isolado + matriz consolidado ──► cache
```

## Decisões

### D1 — Exclusão é filtro marcado com a visão
As 20 listas `not_in conta_contabil` removidas em `bp-espelho-iab` (recuperáveis de `eb7ae06^`) voltam às
regras com `visao: consolidado`. Filtro sem `visao` continua valendo sempre (nenhum hoje no BP). O schema
`knowledge/schemas/rule.json` ganha o campo opcional `visao` (`consolidado`), aceito só em regras do IPC 04.
**Descartado:** um segundo YAML só com o consolidado — duplicaria 40 regras e o `versao_regras`.

### D2 — O serviço apura as duas visões sobre os mesmos registros
`app/services/bp/quadro_principal.apurar` lê os registros uma vez (MSC atual, MSC anterior ou `I-AB`
publicado) e chama `_apurar_exercicio` duas vezes: com o mapa sem os filtros `visao: consolidado`
(isolado) e com o mapa inteiro (consolidado). `Resultado` ganha `visoes: dict[str, VisaoBP]` com `matriz` e
`equilibrio`; `Resultado.matriz` e `diagnostico.equilibrio` continuam sendo os do isolado, então CLI,
testes e consumidores atuais não mudam.
**Descartado:** visão como parâmetro do pedido (um job por visão) — trocar a visão reprocessaria e
sobrescreveria o cache da outra, o que o PO não quer.

### D3 — Cache sem migration
O resultado já é JSON no registro `(ente, exercicio, anexo)`. `serializar` grava `visoes.consolidado`
(`matriz` + `equilibrio`). O `versao_regras` do BP muda com D1, então todo BP em cache passa a
`desatualizado` na leitura, sem reprocessar (regra vigente).

### D4 — A visão é escolha de leitura
`GET /dca/BP` aceita `visao` (padrão `isolado`). A rota troca `matriz` e `diagnostico.equilibrio` pelos da
visão pedida e ecoa `visao`. Cache sem `visoes.consolidado` com `visao=consolidado` → `409`
(de-para falha ruidosa: nunca servir isolado rotulado de consolidado). `visao` em outro anexo → `422`.
`reprocessar`, `POST /batch-jobs` e `GET /dca/{anexo}/regra` não mudam.

### D5 — Só o Quadro Principal varia
F/P, Compensação e Superávit não têm coluna de exclusões no IPC 04; ficam idênticos nas duas visões,
inclusive F/P `L1`, que pode diferir de `L1` principal no consolidado (registrado na auditoria).

## Arquivos

| Arquivo | Mudança |
|---|---|
| `knowledge/schemas/rule.json` | `filters[].visao` opcional |
| `knowledge/rules/bp/quadro_principal.yaml` | 20 filtros intra com `visao: consolidado`; `L34` com `2.3.2.1.2.00.00` |
| `knowledge/policies/ipc04.yaml` | `exclusao_intra_so_no_consolidado` passa a executada na visão consolidada |
| `knowledge/indexes/rules_index.json` | regenerar |
| `app/domain/bo/modelo.py`, `app/infra/regras/carregador.py`, `app/infra/regras/vigencias.py` | `Filtro.visao`, ida e volta pelo banco |
| `app/services/bp/quadro_principal.py` | D2 |
| `app/services/pipeline/resultado.py` | serializar `visoes` |
| `app/routes/anexos.py` | parâmetro `visao` no `GET` (D4) |
| `tests/bp/test_visao.py`, `tests/pipeline/test_bp_visao.py`, `tests/test_regras_bp.py` | cenários do delta |
| `docs/entes-homologacao/cuitegi/auditoria-bp-2025.md` | coluna consolidado medida |

## Regressão

Visão `isolado` sai bit a bit igual ao BP de hoje. BO e BF intactos.
