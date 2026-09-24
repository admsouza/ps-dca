# Design — Anexo Manual alimenta (I) e totalizadoras

**Change:** `openspec/changes/bf-manual-anexo-alimenta-receita-i/` · **Proposal aprovada pelo PO em:** 2026-09-23

## Contexto

Manual hoje aplica só chaves do mapa. Front deriva `(I)` e faz preview de totais; após Apurar
totalizadoras fora de `(I)` ficam `None`.

## Fluxo

```text
partir mapa → saldos (f) anexo
  → de-para rótulo → bloco (I); TOTAL → L1; ignorar chaves (I) do body se anexo informou
  → compostas do principal em ordem topológica (calculation.references),
    somando parcelas não-nulas (D6)
  → montar coluna anterior; nao_apuradas só onde ainda None
  → conferência (f)×L1 anterior
```

## Decisões

### D1 — De-para por rótulo (+ TOTAL → L1)
Como na versão anterior.

### D2 — Ignorar chaves `(I)` no body se anexo informou
Se não houver nenhuma chave `A:…`, aceitar `L2`… no body (compat. testes / preenchimento só principal).

### D3 — `procedencia.valores_anteriores` = informado

### D4 — TOTAL anexo sem descendentes = soma dos `(f)` das folhas

### D5 — Conferência também no exercício anterior

### D6 — Compostas Manual somam parcelas disponíveis
**Escolhido:** `None` na referência não zera o total nem propaga indeterminação (diferente da
agregação MSC).  
**Porquê:** no Manual o usuário preenche parcial; o front já faz preview assim; após Apurar o
`TOTAL (VI)` deve refletir o que foi informado + derivado.

## Arquivos

| Arquivo | Ação |
|---|---|
| `app/services/bf/quadro_principal.py` | alterar |
| `tests/bf/test_apuracao.py` (ou novo) | cenários novos |
