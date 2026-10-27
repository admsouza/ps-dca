# Proposal — Desdobramento da natureza de receita no IPC 08

**Status:** implementada em 2026-10-27, por decisão do PO na mesma data.
**Repositório:** `ps-dca`
**Capability:** `dca/demonstracao-fluxos-caixa`
**Base normativa:** IPC 08 ed. 2020-01 (cita o PCASP de 2019) × tabela de natureza de receita da
STN em `docs/contas-stn/natureza-receita.md`

## Why

`L9` (Remuneração das Disponibilidades) saía **0,00** em todos os entes medidos, contra
301.239.717,16 que Porto Alegre publica. A causa foi medida na apuração F1 e **não** é o `not_in`
das exclusões: é o `in`.

No IPC 08 o `00` ocupa a posição do desdobramento `DD2`, e o dígito seguinte é o `DD2` real:

| IPC 08 grafa | Tabela STN | MSC entrega | Pattern transcrito | Pattern correto |
|---|---|---|---|---|
| `1.3.21.00.1.x` | `1.3.2.1.01` Depósitos Bancários | `13210101` | `1321001x` ✗ | `132101` ✓ |
| `1.3.21.00.2.x` | `1.3.2.1.02` Depósitos Especiais | — | `1321002x` ✗ | `132102` ✓ |
| `1.3.21.00.3.x` | `1.3.2.1.03` Saldos Não-Desembolsados | — | `1321003x` ✗ | `132103` ✓ |
| `1.3.21.00.4.x` | `1.3.2.1.04` Recursos do RPPS | `13210401` | `1321004x` ✗ | `132104` ✓ |

O IPC lista exatamente quatro variantes e a STN tem exatamente esses quatro desdobramentos. A
transcrição preservou o literal certo (D8 manda isso) e normalizou o `00` como zero literal — que
não casa com nada.

## What Changes

- 8 patterns em `knowledge/rules/dfc/quadro_principal.yaml`: os quatro de `1.3.2.1` e os quatro de
  `7.3.2.1`, em `L9` (`in`) e `L5` (`not_in`). **Literais intactos.**
- `L5` passa a `status: review_required`, com `blocker` para a exclusão que continua sem casar.
- `scripts/validate_rules.py`: `IPC08` entra em `BLOQUEIO_DECLARADO`, como IPC06 e IPC04 — o
  bloqueio de `L5` é estado declarado pelo PO, não inconsistência.

**Fora de escopo, por decisão do PO:** os outros 9 literais do mesmo formato (`L10`, `L11`, e os
`2.9.30`/`8.9.30`). `L10` já está correto (`17`, `24`); em `L11` a tabela da STN tem
`2.9.4.**1**.01.0.1`, e nenhuma leitura simples casa com `2.9.40.00.1.1` — inferir sem medição
que a valide seria adivinhar.

## Efeito medido (2026-10-27)

| Linha | Antes | Depois | Delta |
|---|---:|---:|---:|
| `L5` Receita Patrimonial | 920.761.028,60 | 144.308.504,92 | −776.452.523,68 |
| `L9` Remuneração das Disponibilidades | 0,00 | 776.452.523,68 | +776.452.523,68 |
| `L2` Ingressos | 13.153.640.269,72 | 13.153.640.269,72 | **0,00** |

A receita estava sendo contada em `L5`, porque o `not_in` quebrado não a excluía. Corrigido, ela
vai para a linha certa e **o total não muda** — é reclassificação, não mudança de valor.

`L9` nos quatro entes: Porto Alegre 776.452.523,68 · Recife 262.093.146,63 · João Pessoa
250.966.175,03 · Cuitegi 2.846.486,38 — todas antes 0,00.

**O resíduo de `L16` não muda em nenhum ente**, inclusive o negativo de João Pessoa
(−657.093.004,03). A hipótese de que `L9` explicava aquele resíduo está **refutada por medição**.

## Critérios de aceite

- [x] `L9` apura nos quatro entes de homologação; `L5` cai o mesmo valor.
- [x] `L2`, `L1` e `L34` inalterados em centavos — é reclassificação.
- [x] Literais do PDF intactos; só o `pattern` muda.
- [x] `L5` com `review_required` e `blocker` explicando o que não casa.
- [x] BO, BF, BP e DVP bit a bit iguais.
- [x] `validate_rules` exit 0; `check_sources` 5 documentos; suíte verde; `ruff` limpo.

## Decisões do PO (2026-10-27)

- [x] Escopo: só os 8 de `1.3.2.1` / `7.3.2.1`. Os demais ficam como estão, registrados.
- [x] `7.3.21.00.31.x`: **não casar**. Tem dois dígitos onde as irmãs têm um, nenhum dos quatro
      entes tem registro que permita escolher entre `7321031` e `732103`, e o grupo `7.3.2.1` não
      consta da tabela da STN. Fica em `blocker`, não em palpite.
