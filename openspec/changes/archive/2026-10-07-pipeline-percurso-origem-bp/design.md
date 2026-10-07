# Design — Percurso completo respeita a origem da coluna anterior do BP

**Change:** `openspec/changes/pipeline-percurso-origem-bp/` · **Proposal aprovada pelo PO em:** 2026-10-07

## Componentes afetados

| Componente | Mudança |
|---|---|
| `app/routes/anexos.py` (`processar_percurso`) | query `origem_exercicio_anterior` validada por `ORIGENS_BP`; `versao_de` e enfileiramento com ela |
| `app/services/pipeline/completo.py` | `pedido_do_percurso(registro, fonte, anexo, origem_bp=None)` repassa a origem ao ramo BP de `parametros_efetivos` |
| `worker.py` (`apurar_completo`) | recebe `origem_bp` e o passa a `pedido_do_percurso`; o pedido do percurso deixa de sobrescrever a origem com o padrão |

## Contrato

```python
def pedido_do_percurso(registro, fonte: str, anexo: str = "",
                       origem_bp: str | None = None) -> dict:
    pedido = {"fonte": fonte, **({"origem_anterior": origem_bp} if origem_bp else {})}
    return parametros_efetivos(pedido, registro, anexo)
```

`parametros_efetivos` só olha `origem_anterior` no ramo do BP; no BF a chave não está presente, então
nada muda para ele.

## Decisões

### D1 — Parâmetro só do BP, com nome igual ao da rota individual
**Escolhido:** `origem_exercicio_anterior` em `/batch-jobs`, aplicado só ao BP · **Descartado:** um
parâmetro por anexo · **Porquê:** o BF não tem escolha no percurso, e o mesmo nome da rota individual
evita um vocabulário a mais no front.

### D2 — Uma função de identidade para rota e worker
**Porquê:** é o que já evita o "percurso grava uma identidade e a leitura confere outra"
(`pipeline-visualizar-sem-reprocessar`, D3). A origem entra pelo mesmo caminho.

## Impacto

Sem banco, sem migration. Payload do job do percurso ganha `origem_bp`. Regressão: BO e BF bit a bit.

## Arquivos

| Arquivo | Ação |
|---|---|
| `app/routes/anexos.py`, `app/services/pipeline/completo.py`, `worker.py` | alterar |
| `tests/pipeline/test_percurso_origem_bp.py` | criar |
