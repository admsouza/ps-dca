# Evidência — atributo Financeiro/Permanente na MSC (BP, P4)

**Medido em:** 2026-10-07 · **Change:** `bp-apuracao-f1` (tarefa 0.4)
**Leitura:** SICONFI `tt/msc_patrimonial` e `tt/msc_orcamentaria`, `co_tipo_matriz=MSCE`,
`me_referencia=12`, `id_tv=ending_balance` — o par do BP em `app/infra/msc/fonte.py`.
**Domínio (confirmado pelo PO):** `financeiro_permanente` (SICONFI) / `financeiroPermanente`
(PublicSoft) — `1` = Financeiro, `2` = Permanente.

## 1. O SICONFI entrega o atributo

O campo `financeiro_permanente` vem em todo item. Distribuição por classe:

| Ente | Exercício | Classe 1 (F / P) | Classe 2 (F / P / sem) | Classe 6 |
|---|---|---|---|---|
| Cuitegi/PB `2505204` | 2025 | 115 / 19 | 82 / 13 / 20 | 1.272 sem atributo |
| Cuitegi/PB | 2024 | 110 / 38 | 123 / 40 / 14 | 2.698 sem atributo |
| João Pessoa/PB `2507507` | 2025 | 216 / 107 | 245 / 30 / 28 | 3.883 sem atributo |
| João Pessoa/PB | 2024 | 132 / 103 | 163 / 32 / 25 | 3.538 sem atributo |

Os registros da classe 2 **sem** atributo são exatamente o Patrimônio Líquido (`2.3`): somam
−45.644.857,64 (Cuitegi 2025) e −57.870.998,89 (2024), iguais ao `L32` publicado. O PL não entra
no quadro F/P, então essa ausência é esperada e **não** é resíduo. A classe 6 não tem atributo,
e o IPC 04 também não pede atributo para as contas dela.

## 2. Confronto com o BP publicado por Cuitegi (SIAFIC PublicSoft)

| Quadro F/P | 2025 apurado | 2025 publicado | 2024 apurado | 2024 publicado |
|---|---|---|---|---|
| `L2` Ativo Financeiro (classe 1, F) | 26.431.637,72 | 26.431.637,72 ✔ | 19.897.621,26 | 19.897.621,26 ✔ |
| `L3` Ativo Permanente (classe 1, P) | 49.882.694,20 | 49.882.694,20 ✔ | 43.702.974,41 | 43.702.974,41 ✔ |
| `L6` Passivo Permanente (classe 2, P) | 119.311.755,53 | 119.311.755,53 ✔ | 114.975.024,96 | 114.975.024,96 ✔ |
| `L5` Passivo Financeiro (regra do IPC 04) | 2.718.406,66 | 3.105.939,59 ✘ | 6.618.515,01 | 6.618.515,01 ✔ |

Composição de `L5`, conforme o IPC 04 p. 10: classe 2 com atributo F, mais `6.2.2.1.3.01`,
`6.2.2.1.3.05`, `6.3.1.1` e `6.3.1.5`:

| Parcela | Cuitegi 2025 | Cuitegi 2024 | JP 2025 | JP 2024 |
|---|---|---|---|---|
| Classe 2, F | 2.647.434,03 | 6.496.569,60 | 1.160.024.896,77 | 846.046.159,27 |
| `6.2.2.1.3.01` | 0,00 | 0,00 | 0,00 | 0,00 |
| `6.2.2.1.3.05` | 0,00 | 48.335,00 | 281.307.109,52 | 231.796.527,70 |
| `6.3.1.1` | 70.972,63 | 73.610,41 | 110.429.285,23 | 67.299.876,72 |
| `6.3.1.5` | 0,00 | 0,00 | 0,00 | 0,00 |
| **`L5`** | **2.718.406,66** | **6.618.515,01** | **1.551.761.291,52** | **1.145.142.563,69** |

### Divergência de `L5` em Cuitegi 2025: −387.532,93

A diferença é **exatamente** o saldo de `6.3.1.7.1.00.00` (`631710000`, "RP NÃO PROCESSADOS A
LIQUIDAR - INSCRIÇÃO NO EXERCÍCIO" no PCASP), 387.532,93. O IPC 04 (ed. 2020-01, que cita o PCASP
2019) não lista essa conta. Em 2025, Cuitegi registrou a inscrição em `6.3.1.7.1`, e
`6.2.2.1.3.05` ficou zerada. JP 2025 continua usando `6.2.2.1.3.05` (281.307.109,52, igual ao
`L25` do BF).

**Somar `6.3.1.7.1` à regra não resolve sozinho.** Em Cuitegi 2024, `6.2.2.1.3.05` e `6.3.1.7.1`
têm **os dois** 48.335,00. Com as duas contas, o 2024, que hoje confere, ficaria 48.335,00 acima do
publicado. Decisão do PO (P7 da proposal). Até lá, a regra canônica não muda e a divergência vai ao
relatório de auditoria.

## 3. Inconsistência do PDF de Cuitegi resolvida pela MSC

O PDF traz `2.2.0.0.0.00.00` = 82.981.174,41 e "Total do Passivo Não Circulante" = 114.975.024,96
na coluna 2024. A MSC de 2024 dá 114.975.024,96 para a classe 2 com atributo P. Esse é o único
valor que fecha `L1 = L15` (63.600.595,67). A linha de conta do PDF é que está errada.

## 4. `L34` — conta `2.3.2` (P3)

Saldo de `2.3.2` na MSCE de encerramento: **0,00** em Cuitegi e JP, 2024 e 2025. Manter `L34` como
`review_required` não tira valor de nenhum dos dois entes.

## 5. PublicSoft (`financeiroPermanente`), Cuitegi

`base-demonstrativos`, competência 13, `idTv=ending_balance`. A medição usou credencial fornecida
pelo PO e TLS sem verificação, pois o certificado do host `prd3` não confere com o nome, o mesmo
caso de `PUBLICSOFT_SSL_VERIFY=false`.

| Exercício | Classe 1 (F / P) | Classe 2 (F / P / sem) | Classe 6 |
|---|---|---|---|
| 2025 | 115 / 19 → 26.431.637,72 / 49.882.694,20 | 82 / 13 / 20 → 2.647.434,03 / 119.311.755,53 / −45.644.857,64 | 1.272 sem atributo, saldo −2.058.295,85 |
| 2024 | **409**: "Execute a auditoria da matriz antes de consultar a base de demonstrativos." | 409 | 409 |

2025 é **idêntico ao SICONFI** em contagem de registros, distribuição F/P e saldo, centavo a centavo.
O campo vem como string (`"1"`/`"2"`), e o PL vem sem atributo, como no SICONFI. 2024 está
bloqueado pela auditoria da matriz do ente. Esse 409 já é tratado pelo adapter como sem dados, e o
BP herda isso: coluna anterior `None` + `sem_dados_exercicio_anterior`.

O adapter (`anReferencia`/`meReferencia`) e a forma `exercicio`/`mesMsc` devolvem os mesmos 134
registros da classe 1 em 2025.

## 6. Decisão P7 (PO, 2026-10-07)

Opção (a): `L5` fica com as 4 contas do IPC 04. A diferença de 387.532,93 de Cuitegi 2025
(`6.3.1.7.1`) vai ao relatório de auditoria do ente, e a regra canônica não muda.
