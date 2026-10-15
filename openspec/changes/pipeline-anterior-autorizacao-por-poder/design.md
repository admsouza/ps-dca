# Design — Escolha do anterior só nas unidades do poder do usuário

**Change:** `openspec/changes/pipeline-anterior-autorizacao-por-poder/` · **Implementação autorizada pelo dev em 2026-10-15; aprovação do PO pendente**

## Fluxo

```text
reprocessar BF/BP com anterior_por_recorte
  → validar_escolhas (422, como hoje)
  → poderes = request.state.poderes (vazio → 403)
  → mapa {chave: poder_orgao}: po:<código> = código; ug:<id> = poderOrgao do cache de N, senão N−1, senão ""
  → recortes.visiveis(chaves, mapa, poderes): chave fora → 403 "sem acesso à unidade {chave}"
  → _exigir_n1 / enfileirar (nada é gravado antes do 403)
```

## Decisões

- Reusa `recortes.visiveis` (mesma regra da leitura e do resumo); sem regra nova.
- `consolidado` vê todas as chaves: comportamento idêntico ao atual (nem lê o cache).
- Unidade sem poder resolvido (`""`) só é visível para `consolidado` (fail closed).
- Função única `_exigir_poder_nas_unidades` em `app/routes/anexos.py`, chamada após o 422.
- `origem_exercicio_anterior` do consolidado (D1) fica fora.
