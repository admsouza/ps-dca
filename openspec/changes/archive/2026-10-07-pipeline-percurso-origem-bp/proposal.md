# Proposal — Percurso completo respeita a origem da coluna anterior do BP

**Status:** arquivada (2026-10-07)
**Repositório:** `ps-dca`
**Capability:** `pipeline/processamento-completo` (existente)
**Anexo DCA:** BP (Balanço Patrimonial)
**Front:** `front-declaracoes`, change `dca-percurso-origem-bp`

## Why

`bp-anterior-publicado-siconfi` deu ao BP duas origens para a coluna do exercício anterior
(`publicado_siconfi`, padrão, e `msce_exercicio_anterior`). A leitura e o reprocessamento do BP
recebem a origem escolhida, mas o percurso (`POST /batch-jobs`) não: ele apura o BP **sempre** pelo
padrão.

Quem escolhe MSC na engrenagem do BP e aciona “Reprocessar” no dialog recebe o BP pelo publicado. A
página, que pede MSC, mostra esse resultado marcado `desatualizado` (motivo `pedido`) até o BP ser
reprocessado sozinho. O percurso, que existe para não precisar disso, deixa o BP na origem errada.

Há dois pontos que forçam o padrão:

1. a rota `POST /batch-jobs` não aceita `origem_exercicio_anterior`;
2. no worker, `pedido_de` mescla `completo.pedido_do_percurso(...)` **por cima** do pedido, e esse
   pedido sempre traz a origem padrão do BP. Mesmo com a origem no payload, ela seria trocada.

## What Changes

- `POST /batch-jobs` aceita `origem_exercicio_anterior` (`publicado_siconfi` |
  `msce_exercicio_anterior`), que vale **só para o BP**; omitido → `publicado_siconfi`. Inválido → `422`.
- A origem vai no payload do job do percurso, e `pedido_do_percurso` passa a recebê-la: rota
  (decisão de cache em `montar_percurso`) e worker (apuração e gravação) usam a **mesma** identidade.
- BO e BF inalterados.

**Fora de escopo:** origem do BF no percurso (o percurso do BF já usa MSC, e o modo Manual não entra
no percurso).

## Entradas e saídas

| Interface | Entrada | Saída |
|---|---|---|
| `POST /batch-jobs` | `anReferencia`, `id_ente`, `forcar`, `origem_exercicio_anterior` (opcional) | inalterada (`202` com o percurso) |
| Job do percurso | `origem_bp` no payload | BP gravado com `procedencia.origem_exercicio_anterior` = a pedida |

## Exemplo concreto

Cuitegi/PB (`2505204`), 2025. O usuário salvou MSC na engrenagem do BP e aciona Reprocessar no dialog:

| | Hoje | Depois |
|---|---|---|
| Pedido | `POST /batch-jobs?…&forcar=true` | `…&forcar=true&origem_exercicio_anterior=msce_exercicio_anterior` |
| BP gravado | `origem_exercicio_anterior: publicado_siconfi` | `msce_exercicio_anterior` |
| `GET /dca/BP?…&origem_exercicio_anterior=msce_exercicio_anterior` | `200`, `desatualizado: true`, `["pedido"]` | `200`, `desatualizado: false` |

## Critérios de aceite

- [ ] Percurso com `msce_exercicio_anterior` grava o BP pela MSC, e o `GET` seguinte com a mesma
      origem responde `desatualizado: false`.
- [ ] Percurso sem a origem grava o BP pelo publicado (inalterado).
- [ ] Percurso sem `forcar`, com o BP em cache pela outra origem: o BP entra como `a_apurar`.
- [ ] BO e BF: identidade e resultado inalterados.
- [ ] `python -m pytest` e `python -m ruff check .` sem falha nova.

## Casos de erro

| Situação | Comportamento |
|---|---|
| Origem inválida | `422`, nenhum job enfileirado |
| `manual` | `422` (não existe no BP) |

## Aprovação do PO

- [x] PO pediu em 2026-10-07
- [x] PO aprovou a proposal em 2026-10-07
