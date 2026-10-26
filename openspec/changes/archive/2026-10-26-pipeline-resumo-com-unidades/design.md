# Design — Resumo da DCA com as unidades de BF e BP

## Componentes

- `app/services/pipeline/resumo.py`: `resumir` ganha `poderes` e acrescenta `recortes` às entradas de BF/BP.
- `app/routes/anexos.py`: `GET /dca/resumo` passa `request.state.poderes`; `EntradaResumo` ganha `recortes`.
- `app/domain/recorte.py`: reutilizado (`visiveis`, `GRUPOS`, `tipo`), sem alteração.

## Fluxo

`GET /dca/resumo` -> `unidade_autorizada` (grava `request.state.poderes`) -> `resumir(poderes=...)` ->
uma leitura do cache -> para BF/BP com status `ok`, lê `resultado["recortes"]`, descarta grupos e
consolidado, filtra por `recortes.visiveis` e devolve `{chave, tipo, rotulo}`. Nenhum job é enfileirado.

## Contrato

`GET /dca/resumo`: entradas `BF`/`BP` ganham `recortes: [{"chave": "ug:12", "tipo": "ug", "rotulo": "..."}]`.
Demais anexos não trazem a chave. Sem resultado `ok`, sem `recortes` gravados ou sem poderes: `[]`.

Banco, cache, filas e APIs externas: sem impacto.

## Decisões

- **D1** Só BF e BP recebem a chave `recortes`; `response_model_exclude_unset=True` evita `null` nos
  demais. Descartado: `recortes: []` em todos os anexos (mudaria o payload dos outros seis).
- **D2** Visibilidade via `recortes.visiveis` com os `poderOrgao` gravados, igual a `_no_recorte`.
  Descartado: extrair helper compartilhado com `_no_recorte` (refatoração fora do escopo; são 3 linhas).
- **D3** `poderes` com default `()` em `resumir`: fail closed. Descartado: parâmetro obrigatório
  (quebraria chamadores existentes sem ganho).
- **D4** Rótulo é o gravado no recorte. Descartado: recalcular a partir de `NOMES_PO`.

## Arquivos

- alterados: `app/services/pipeline/resumo.py`, `app/routes/anexos.py`,
  `tests/pipeline/test_transporte.py`, `tests/pipeline/test_rota_recorte.py`,
  `openspec/changes/pipeline-resumo-com-unidades/proposal.md`
- criados: `design.md`, `tasks.md` desta change
