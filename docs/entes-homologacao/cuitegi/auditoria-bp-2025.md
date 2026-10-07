# Auditoria BP 2025 — Cuitegi/PB (`2505204`)

**Gerado em:** 2026-10-07 · **Change:** `bp-apuracao-f1`
**Apurado:** `python -m app.cli.bp 2505204 2025` (SICONFI, `MSCE`/encerramento), regras do IPC 04 ed. 2020-01
**Publicado:** `Balanço Patrimonial_2025_TCE-PB.pdf` (PublicSoft 2026.19.5.0, consolidado). Igual ao `I-AB`
do `tt/dca` nas âncoras.

A regra canônica não foi alterada por nenhuma divergência abaixo. Cada linha traz a hipótese e o lado
provável.

## Quadro Principal

| Linha | Coluna | Apurado | Publicado | Diferença | Hipótese · lado |
|---|---|---|---|---|---|
| `L1` | 2025 | 47.083.540,63 | 76.314.331,92 | −29.230.791,29 | exclusão intra `1.2.1.1.2` em `L10` (IPC 04 p. 8) · regra aplicada, ente não exclui |
| `L1` | 2024 | 39.466.565,14 | 63.600.595,67 | −24.134.030,53 | idem, mais `L4`/`L6` abaixo |
| `L4` | 2024 | 117.875,33 | 4.944.014,94 | −4.826.139,61 | na MSC a dívida ativa não tributária está em `112629900` (intra, excluída pelo IPC 04); o PDF a apresenta em `1.1.2.6.1` (consolidação) · MSC do ente |
| `L6` | 2025 | 0,00 | 0,00 | 0,00 | — |
| `L9` | 2025 | 20.651.902,91 | 49.882.694,20 | −29.230.791,29 | `1.2.1.1.2` intra · regra |
| `L16` | 2025 | 1.474.954,87 | 2.647.434,03 | −1.172.479,16 | `2.1.1.4.2` intra excluída de `L17` · regra |
| `L24` | 2025 | 90.080.964,24 | 119.311.755,53 | −29.230.791,29 | `2.2.1.4.2` intra excluída de `L25` · regra |
| `L24` | 2024 | 96.921.672,12 | 114.975.024,96 | −18.053.352,84 | idem. O PDF traz 82.981.174,41 na linha da conta, que está errada (evidência §3) |
| `L32` | 2025 | −42.467.656,79 | −45.644.857,64 | +3.177.200,85 | `2.3.7.1.2` intra excluída de `L39` · regra |
| `L34` | ambas | não apurada | 0,00 | — | `review_required` (P3-b); `2.3.2` = 0,00 medido |

**Equilíbrio `L1 − L15`:** −2.004.721,69 (2025) e −3.321.137,54 (2024). No ente, ativo intra (29.230.791,29)
≠ passivo intra (30.403.270,45), e ainda há PL intra. Pendente de decisão P8.

## Quadro dos Ativos e Passivos Financeiros e Permanentes

| Linha | Coluna | Apurado | Publicado | Diferença | Hipótese · lado |
|---|---|---|---|---|---|
| `L2` | 2025 / 2024 | 26.431.637,72 / 19.897.621,26 | iguais | 0,00 | — |
| `L3` | 2025 / 2024 | 49.882.694,20 / 43.702.974,41 | iguais | 0,00 | — |
| `L5` | 2025 | 2.718.406,66 | 3.105.939,59 | −387.532,93 | `6.3.1.7.1` fora do IPC 04 · decisão P7-a: regra mantida |
| `L5` | 2024 | 6.618.515,01 | 6.618.515,01 | 0,00 | — |
| `L6` | 2025 / 2024 | 119.311.755,53 / 114.975.024,96 | iguais | 0,00 | — |
| `L7` | 2025 | −45.715.830,27 | −46.103.363,20 | +387.532,93 | reflexo de `L5` |

## Contas de Compensação e Superávit/Déficit por fonte

Não apurados (P5-a). O ente publica as 10 linhas de compensação zeradas.
