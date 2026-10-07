# De-para e conferência do BP — linhas do IPC 04 × `DCA-Anexo I-AB` (`tt/dca`)

**Medido em:** 2026-10-07 · **Changes:** `bp-apuracao-f1` (tarefas 0.5 e 4.5) e `bp-espelho-iab`
**Apuração:** `python -m app.cli.bp <ente> 2025` (SICONFI, `MSCE`/encerramento, classes 1, 2 e 6)
**Publicado:** `tt/dca?an_exercicio=2025&no_anexo=DCA-Anexo I-AB&id_ente=<ente>`

O `I-AB` publica o BP **por conta**, com o `cod_conta` prefixado (`P1.1.0.0.0.00.00`), em coluna única
`31/12/2025`. O de-para abaixo existe só para conferir e nunca entra na apuração (design D4).
Desde `bp-espelho-iab` o BP **espelha** o `I-AB` declarado: sem exclusões intra-OFSS e com a `L5` pela
composição do `I-AB`; o aceite é 1:1 em centavos.

| `cod_conta` no `I-AB` | Linha do IPC 04 |
|---|---|
| `P1.0.0.0.0.00.00` | Principal `L1` ATIVO |
| `P1.1.0.0.0.00.00` | Principal `L2` Ativo Circulante |
| `P1.2.0.0.0.00.00` | Principal `L9` Ativo Não Circulante |
| `P2.1.0.0.0.00.00` | Principal `L16` Passivo Circulante |
| `P2.2.0.0.0.00.00` | Principal `L24` Passivo Não Circulante |
| `P2.3.0.0.0.00.00` | Principal `L32` Patrimônio Líquido |
| `AtivoFinanceiro` / `AtivoPermanente` | F/P `L2` / `L3` |
| `PassivoFinanceiro` / `PassivoPermanente` | F/P `L5` / `L6` |
| `SaldoPatrimonial` | F/P `L7` |

## João Pessoa/PB (`2507507`), 2025

| Âncora | Apurado | Publicado | Diferença |
|---|---|---|---|
| `L1` ATIVO | 6.665.421.468,62 | 6.665.421.468,62 | **0,00** |
| `L2` Ativo Circulante | 4.118.744.840,03 | 4.118.744.840,03 | **0,00** |
| `L9` Ativo Não Circulante | 2.546.676.628,59 | 2.546.676.628,59 | **0,00** |
| `L16` Passivo Circulante | 1.392.896.773,11 | 1.392.896.773,11 | **0,00** |
| `L24` Passivo Não Circulante | 1.456.585.687,09 | 1.456.585.687,09 | **0,00** |
| `L32` Patrimônio Líquido | 3.815.939.008,42 | 3.815.939.008,42 | **0,00** |
| F/P `L2` Ativo Financeiro | 3.263.070.247,57 | 3.263.070.247,57 | **0,00** |
| F/P `L3` Ativo Permanente | 3.402.351.221,05 | 3.402.351.221,05 | **0,00** |
| F/P `L5` Passivo Financeiro | 1.551.761.291,52 | 1.551.761.291,52 | **0,00** |
| F/P `L6` Passivo Permanente | 1.689.457.563,43 | 1.689.457.563,43 | **0,00** |
| F/P `L7` Saldo Patrimonial | 3.424.202.613,67 | 3.424.202.613,67 | **0,00** |

11/11 em centavos, `L1 − L15` = 0,00. Antes (IPC 04 com exclusões): `L1` 5.594.325.422,52, `L32`
−2.130.101.566,60 e `L1 − L15` = +5.946.040.575,02, tudo da parcela intra-OFSS que o `I-AB` não exclui.

## João Pessoa/PB (`2507507`), 2024 — coluna anterior do BP de 2025

Pelas duas origens (MSC de 2024 e `I-AB` publicado de 2024), contra o `I-AB` de 2024 do `tt/dca`:

| Âncora | `I-AB` 2024 | MSC | Publicado |
|---|---|---|---|
| `L1` ATIVO | 5.793.165.957,20 | 5.793.165.957,20 | 5.793.165.957,20 |
| `L2` Ativo Circulante | 2.811.263.956,80 | 2.811.263.956,80 | 2.811.263.956,80 |
| `L9` Ativo Não Circulante | 2.981.902.000,40 | 2.981.902.000,40 | 2.981.902.000,40 |
| `L16` Passivo Circulante | 1.076.261.867,78 | 1.076.261.867,78 | 1.076.261.867,78 |
| `L24` Passivo Não Circulante | 1.248.665.416,44 | 1.248.665.416,44 | 1.248.665.416,44 |
| `L32` Patrimônio Líquido | 3.468.238.672,98 | 3.468.238.672,98 | 3.468.238.672,98 |
| F/P `L2` Ativo Financeiro | 1.910.956.600,64 | 1.910.956.600,64 | 1.910.956.600,64 |
| F/P `L3` Ativo Permanente | 3.882.209.356,56 | 3.882.209.356,56 | 3.882.209.356,56 |
| F/P `L5` Passivo Financeiro | 1.145.142.563,69 | 1.145.142.563,69 | 1.145.142.563,69 |
| F/P `L6` Passivo Permanente | 1.478.881.124,95 | 1.478.881.124,95 | 1.478.881.124,95 |
| F/P `L7` Saldo Patrimonial | 3.169.142.268,56 | 3.169.142.268,56 | 3.169.142.268,56 |

11/11 nas duas origens, equilíbrio 0,00.

## Cuitegi/PB (`2505204`), 2025

| Âncora | Planilha (`I-AB`) | Apurado | Diferença |
|---|---|---|---|
| `L1` ATIVO | 76.314.331,92 | 76.314.331,92 | **0,00** |
| `L2` Ativo Circulante | 26.431.637,72 | 26.431.637,72 | **0,00** |
| `L9` Ativo Não Circulante | 49.882.694,20 | 49.882.694,20 | **0,00** |
| `L16` Passivo Circulante | 2.647.434,03 | 2.647.434,03 | **0,00** |
| `L24` Passivo Não Circulante | 119.311.755,53 | 119.311.755,53 | **0,00** |
| `L32` Patrimônio Líquido | −45.644.857,64 | −45.644.857,64 | **0,00** |
| F/P `L2`, `L3`, `L5`, `L6`, `L7` | 5 valores | iguais | **0,00** |

15 linhas do Quadro Principal e 5 do F/P iguais em centavos; `L1 − L15` = 0,00. Detalhe linha a linha em
`docs/entes-homologacao/cuitegi/auditoria-bp-2025.md`.

## Decisão do PO (P7-a e P8-a revogadas)

O IPC 04 manda excluir as contas intra-OFSS e lista `6.2.2.1.3.01`/`6.2.2.1.3.05` no Passivo Financeiro.
O PO decidiu em 2026-10-07 que o BP reproduz o `I-AB` declarado: sem as exclusões e com a `L5` pela
composição do `I-AB` (`2.1` F + `2.2` F + `6.3.1.1` + `6.3.1.5` + `6.3.1.7.1`). Change `bp-espelho-iab`.
