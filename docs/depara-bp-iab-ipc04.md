# De-para e conferência do BP — linhas do IPC 04 × `DCA-Anexo I-AB` (`tt/dca`)

**Medido em:** 2026-10-07 · **Change:** `bp-apuracao-f1` (tarefas 0.5 e 4.5)
**Apuração:** `python -m app.cli.bp <ente> 2025` (SICONFI, `MSCE`/encerramento, classes 1, 2 e 6)
**Publicado:** `tt/dca?an_exercicio=2025&no_anexo=DCA-Anexo I-AB&id_ente=<ente>`

O `I-AB` publica o BP **por conta**, com o `cod_conta` prefixado (`P1.1.0.0.0.00.00`), em coluna única
`31/12/2025`. O de-para abaixo existe só para conferir e nunca entra na apuração (design D4).

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

| Âncora | Apurado | Publicado | Diferença | Intra-OFSS (5º nível = 2) na MSC |
|---|---|---|---|---|
| `L1` ATIVO | 5.594.325.422,52 | 6.665.421.468,62 | −1.071.096.046,10 | 1.071.096.046,10 |
| `L2` Ativo Circulante | 3.047.648.793,93 | 4.118.744.840,03 | −1.071.096.046,10 | 1.071.096.046,10 |
| `L9` Ativo Não Circulante | 2.546.676.628,59 | 2.546.676.628,59 | **0,00** | 0,00 |
| `L16` Passivo Circulante | 321.800.727,01 | 1.392.896.773,11 | −1.071.096.046,10 | — |
| `L24` Passivo Não Circulante | 1.456.585.687,09 | 1.456.585.687,09 | **0,00** | — |
| `L32` Patrimônio Líquido | −2.130.101.566,60 | 3.815.939.008,42 | −5.946.040.575,02 | 5.946.040.575,02 |
| F/P `L2` Ativo Financeiro | 3.263.070.247,57 | 3.263.070.247,57 | **0,00** | |
| F/P `L3` Ativo Permanente | 3.402.351.221,05 | 3.402.351.221,05 | **0,00** | |
| F/P `L5` Passivo Financeiro | 1.551.761.291,52 | 1.551.761.291,52 | **0,00** | |
| F/P `L6` Passivo Permanente | 1.689.457.563,43 | 1.689.457.563,43 | **0,00** | |
| F/P `L7` Saldo Patrimonial | 3.424.202.613,67 | 3.424.202.613,67 | **0,00** | |

**O quadro F/P bate 5/5 em centavos**, `L5` inclusive (P7-a confirmado em JP). No Quadro Principal,
**toda** diferença é a parcela intra-OFSS que o IPC 04 exclui conta a conta (`1.1.1.1.2` em `L3`;
`2.1.x.x.2` em `L17`/`L23`; `2.3.7.1.2`/`2.3.7.2.2` em `L39`). O `I-AB` é a declaração do ente, **sem**
as exclusões do consolidado.

`L1 − L15` apurado: **+5.946.040.575,02**. Ativo e passivo intra são recíprocos (1.071.096.046,10 dos
dois lados) e se anulam. O que sobra é o **superávit acumulado intra** de `2.3.7.x.2`, que o IPC 04
manda excluir de `L39` e que não tem contrapartida no ativo nem no passivo.

## Cuitegi/PB (`2505204`), 2025

| Âncora | Apurado | Publicado (`I-AB` = PDF do SIAFIC) | Diferença | Intra na MSC |
|---|---|---|---|---|
| `L1` ATIVO | 47.083.540,63 | 76.314.331,92 | −29.230.791,29 | 29.230.791,29 (`1.2.1.1.2`) |
| `L2` Ativo Circulante | 26.431.637,72 | 26.431.637,72 | **0,00** | 0,00 |
| `L9` Ativo Não Circulante | 20.651.902,91 | 49.882.694,20 | −29.230.791,29 | 29.230.791,29 |
| `L16` Passivo Circulante | 1.474.954,87 | 2.647.434,03 | −1.172.479,16 | `2.1.1.4.2` |
| `L24` Passivo Não Circulante | 90.080.964,24 | 119.311.755,53 | −29.230.791,29 | `2.2.1.4.2` |
| `L32` Patrimônio Líquido | −42.467.656,79 | −45.644.857,64 | +3.177.200,85 | `2.3.7.1.2` = −3.177.200,85 |
| F/P `L2`, `L3`, `L6` | iguais | iguais | **0,00** | |
| F/P `L5` | 2.718.406,66 | 3.105.939,59 | −387.532,93 | `6.3.1.7.1` (P7-a) |
| F/P `L7` | −45.715.830,27 | −46.103.363,20 | +387.532,93 | idem |

`L1 − L15` apurado: **−2.004.721,69** (2024: −3.321.137,54). Aqui o intra **não** é recíproco: o ativo
intra é 29.230.791,29 e o passivo intra é 30.403.270,45, mais o PL intra de −3.177.200,85.

## Achado para o PO (P8)

As exclusões intra-OFSS do IPC 04 estão sendo aplicadas como a norma manda. Elas quebram o
equilíbrio `L1 = L15` sempre que o intra do ente não fecha em zero: no PL (JP) ou entre ativo e
passivo (Cuitegi). O `I-AB` publicado não aplica as exclusões e fecha. Decisão em
`openspec/changes/bp-apuracao-f1/proposal.md` § P8.
