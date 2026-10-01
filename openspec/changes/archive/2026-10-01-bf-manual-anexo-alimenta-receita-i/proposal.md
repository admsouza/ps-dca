# Proposal — Anexo Manual alimenta (I) e totalizadoras

**Status:** aprovada pelo PO · em implementação
**Repositório:** `ps-dca`
**Capability:** `dca/balanco-financeiro` (existente)
**Anexo DCA:** Balanço Financeiro (IPC 06)
**Base normativa:** IPC 06, ed. 2024-06 — quadro anexo detalha Receita Orçamentária `(I)`;
  totalizadoras e TOTAL (VI)/(XII) vêm de `calculation.references`
**Fonte da verdade externa:** n/a
**Change irmã (front):** `front-declaracoes` / `bf-manual-anexo-alimenta-receita-i` +
  `bf-manual-preview-totais` (preview só tela; esta change torna o valor **oficial** após Apurar)

**Dependência:** `bf-anterior-manual-persistido` — mapa no corpo / procedência.

## Why

No Manual, digitar anexo e `(I)` duas vezes diverge; totais de seção (`TOTAL (VI)`, etc.)
só existiam no preview do front e sumiam após Apurar. A regra oficial precisa morar no
`ps-dca`.

## What Changes

- Saldos `(f)` do anexo alimentam o bloco Receita Orçamentária `(I)` (de-para por rótulo;
  TOTAL anexo → `L1`).
- Após o mapa efetivo (folhas + `(I)`), totalizadoras do principal (incl. fora de `(I)`,
  ex. `L15`, `L33` TOTAL VI, `L66`) são preenchidas pelas `calculation.references` da
  base canônica (soma das parcelas disponíveis).
- Chaves do bloco `(I)` no body: ignoradas quando o anexo informa (D2).
- `procedencia.valores_anteriores` = mapa informado (sem expandir derivados).
- Conferência `(f)` × `L1` anterior no diagnóstico.

**Fora de escopo:** alimentar Despesa Orçamentária `(VII)` a partir de outro quadro;
  mudar MSC; migration.

## Entradas e saídas

| Interface | Entrada | Saída |
|---|---|---|
| `POST /dca/BF/reprocessar` | Manual + anexo (`A:…`) + folhas fora de `(I)` | `(I)` e totalizadoras/`TOTAL (VI)` com `exercicio_anterior` preenchidos |

## Exemplo concreto

| Ente | Exercício | Entrada | Esperado |
|---|---|---|---|
| Recife 2611606 | 2025 | `A:L1:receita=100`, `A:L1:deducoes=40` | `L2` anterior = 60; `L1` = total `(f)` do anexo |
| Recife 2611606 | 2025 | `L17=10` + anexo com `(I)=60` | `L15` = soma das transferências informadas; `L33` = soma das seções disponíveis |

## Critérios de aceite

- [ ] POST só com anexo preenche `(I)` sem chaves `L1`–`L14` do principal
- [ ] TOTAL anexo → `L1`; folhas fora de `(I)` só pelo mapa
- [ ] Com folhas/`(I)` efetivos, `L33` (e demais compostas) saem na matriz Manual
- [ ] MSC e Manual só-`L17` (sem anexo) sem regressão indevida
- [ ] pytest dos cenários do delta verdes

## Casos de erro

| Situação | Esperado |
|---|---|
| Código/decimal inválido | `422`; cache intacto |
| Sem anexo e sem chave | linha “não informado” |

## Aprovação do PO

- [x] PO aprovou em 2026-09-23 (escopo ampliado: totalizadoras na mesma change)
