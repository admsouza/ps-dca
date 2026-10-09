# Auditoria do recorte por unidade — Cuitegi/PB (2505204), 2025

**Gerado em:** 2026-10-09 · **Change:** `pipeline-dca-por-unidade-gestora`
**Fonte:** MSC do ente na API do SICONFI, matriz de encerramento. O SICONFI não informa UG, então o
recorte é por **poder/órgão (PO)**. BP com a origem padrão do anterior (`publicado_siconfi`) no
consolidado, e MSCE do ano anterior nos recortes.

> **Pendente:** o recorte por **UG** (PublicSoft, `/base-demonstrativos/unidades-gestoras`) depende do
> `token_ps` do ente, disponível só no worker de homologação. Medir lá e acrescentar a seção "Por UG".

## Consolidado

O BO e o BP apurados com recortes saem **bit a bit iguais** à apuração sem recortes (`matriz`,
`linhas`, `procedencia` e `diagnostico`, exceto `duracao_ms`).

## BP — Quadro Principal, exercício atual

| Recorte | Rótulo | `L1` ATIVO | `L15` PASSIVO E PL | Equilíbrio |
|---|---|---:|---:|---:|
| `po:10131` | Poder Executivo – Prefeitura Municipal | 30.379.465,58 | 30.379.465,58 | 0,00 |
| `po:10132` | Poder Executivo – RPPS Municipal | 45.810.517,17 | 45.810.517,17 | 0,00 |
| `po:20231` | Poder Legislativo - Câmara Municipal | 124.349,17 | 124.349,17 | 0,00 |
| `poder:executivo` | Poder Executivo | 76.189.982,75 | 76.189.982,75 | 0,00 |
| `poder:legislativo` | Poder Legislativo | 124.349,17 | 124.349,17 | 0,00 |
| `poder:executivo+legislativo` | Poderes Executivo e Legislativo | 76.314.331,92 | 76.314.331,92 | 0,00 |
| `consolidado` | Consolidado do ente | 76.314.331,92 | 76.314.331,92 | 0,00 |

Σ `L1` dos três POs = **76.314.331,92** = consolidado, com diferença 0,00. Não há registro sem PO
(nenhum recorte `po:` vazio), então os grupos Executivo e Legislativo cobrem o ente inteiro.

## BO — `L24` (total das receitas)

| Recorte | Previsão inicial | Previsão atualizada |
|---|---:|---:|
| `po:10131` Prefeitura | 43.121.434,00 | 43.121.434,00 |
| `po:10132` RPPS | 5.561.166,00 | 5.561.166,00 |
| `po:20231` Câmara | 0,00 | 0,00 |
| `poder:executivo` | 48.682.600,00 | 48.682.600,00 |

A Câmara não arrecada: a receita realizada do grupo Executivo é a do ente (50.723.704,91).

## Custo

| Anexo | Apuração com recortes (MSC já lida no job) | Tamanho do `resultado` |
|---|---:|---:|
| BO | 2,0 s | 182 KB |
| BP | 3,4 s (inclui a MSCE do ano anterior, lida só para os recortes) | 296 KB |

O tamanho ficou acima da estimativa do design (cerca de 120 KB), porque cada recorte guarda
`linhas` e `procedencia` completos. Com 20 UGs, a projeção é de ~1,5 MB por anexo no JSONB. Medir em
João Pessoa antes de decidir se vale guardar só `matriz` e `diagnostico` por recorte.
