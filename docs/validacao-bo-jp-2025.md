# Validação da regra de saldo — João Pessoa, exercício 2025

**Medido em:** 2026-09-03 · **Ente:** `2507507` · **Competência:** 12/2025 · **Tipo de matriz:** `MSCC`
**Fonte dos saldos:** `tt/msc_orcamentaria`, `id_tv=ending_balance`, classes **5** e **6**
**Gabarito:** `tt/dca`, `an_exercicio=2025` — anexos `DCA-Anexo I-C` e `DCA-Anexo I-D`

Volume obtido: **4.600** registros de classe 5 e **4.320** de classe 6 (uma página ORDS cada).

## Regra testada

```
saldo(conta) = Σ C − Σ D   se a conta é credora no PCASP
             = Σ D − Σ C   se a conta é devedora no PCASP
```

A direção é resolvida **por conta folha de 9 dígitos** na coluna `NATUREZA DO SALDO` de
`docs/contas-stn/PCASP.md` (6.119 contas), pela conta do **registro** — nunca pela classe contábil
nem pelo prefixo declarado na regra.

## Resultado — despesa, contra `DCA-Anexo I-D`

| Coluna do gabarito | Contas | Calculado | Gabarito | Diferença |
|---|---|---|---|---|
| Despesas Pagas | `622130400` | 4.529.794.533,11 | 4.529.794.533,11 | **0,00** |
| Inscrição de RP Não Processados | `622130500` | 281.307.109,52 | 281.307.109,52 | **0,00** |
| Inscrição de RP Processados | `622130700` | 39.255.202,67 | 39.255.202,67 | **0,00** |
| Despesas Liquidadas | `622130400 + 622130700` | 4.569.049.735,78 | 4.569.049.735,78 | **0,00** |
| Despesas Empenhadas | `622130400 + 622130500 + 622130700` | 4.850.356.845,30 | 4.850.356.845,30 | **0,00** |

## Resultado — receita, contra `DCA-Anexo I-C`

| Coluna do gabarito | Conta | Natureza (PCASP) | Calculado | Gabarito | Diferença |
|---|---|---|---|---|---|
| Receitas Brutas Realizadas | `621200000` | Credora | 5.495.365.004,80 | 5.495.365.004,80 | **0,00** |
| Deduções — FUNDEB | `621310100` | **Devedora** | 332.643.194,90 | 332.643.194,90 | **0,00** |
| Outras Deduções da Receita | `621390000` | **Devedora** | 44.846.513,57 | 44.846.513,57 | **0,00** |

Espelho 1:1 em centavos nos 8 valores.

## Por que a heurística de classe não serve

As duas contas de dedução da receita são de **classe 6** e **devedoras**. A heurística
`_CLASSES_CREDORAS = {2, 6, 8}` do `regras-rgf-api` as calcularia como `C − D`, devolvendo
**−332.643.194,90** e **−44.846.513,57** — sinal invertido em relação ao gabarito do STN.

Com a direção lida da tabela, as duas saem positivas e batem. É a medição que sustenta a decisão D1
do design.

## C3 — exceções históricas (B1/B3): sem escrituração em 2025

**Nenhuma** das contas presentes na MSC de João Pessoa 12/2025 está ausente do `PCASP.md` atual.
A conta `5.3.1.3.0.00.00` de B1 e os oito padrões de B3 **não têm registro** nesta competência.

Consequência: declarar `natureza_saldo` nas regras dessas exceções é precaução contra exercícios
antigos, não requisito para apurar 2025. Nada fica sem direção neste caso real.

## C2 — contas bifront: 2 das 4 têm movimento, e nenhuma é necessária

| Conta | Título | ΣC | ΣD | `C − D` |
|---|---|---|---|---|
| `621100000` | Receita a Realizar | 2.120.858.176,58 | 1.666.390.673,65 | 454.467.502,93 |
| `522139900` | Valor Global da Dotação Adicional por Fonte | 860.124.415,93 | 131.087.932,03 | 729.036.483,90 |
| `621800000` | Correção — variação cambial | 0,00 | 0,00 | 0,00 |
| `622800000` | Correção — variação cambial | 0,00 | 0,00 | 0,00 |

As duas com movimento são **controles paralelos**, e as colunas fecham sem elas:

```
Dotação Atualizada = 522110100 (crédito inicial)      5.314.144.648,00
                   + 522120100 (suplementar)            828.005.403,02
                   + 522120201 (especiais abertos)      161.060.637,16
                   − 522130900 (cancelamento)           260.029.556,28
                   = 6.043.181.131,90

522310000 CRÉDITOS A DETALHAR  = 6.043.181.131,90   ✓
622310000 CRÉDITOS DETALHADOS  = 6.043.181.131,90   ✓
```

Nem `522139900` nem `621100000` entram nessa identidade. Somá-las duplicaria valor.

**Risco medido:** `522139900` é irmã de `522130100` (Superávit Financeiro, a conta que `L29`
declara). Uma regra que case o prefixo `5.2.2.1.3` por `startswith` a captura e **infla a coluna em
R$ 729.036.483,90**. O casamento precisa ser por conta folha declarada, ou excluir explicitamente o
subitem `99` (Outros).

## Colunas de previsão e dotação — contra `RREO-Anexo 01`

O gabarito dessas colunas não está na DCA (ver `docs/anexos-siconfi-inventario.md`); está no
`RREO-Anexo 01`, `nr_periodo=6`, que é o exercício fechado.

| Coluna publicada | Contas da MSC | Calculado | Gabarito | Diferença |
|---|---|---|---|---|
| `TotalDespesas` DOTAÇÃO INICIAL (d) | `522110100` | 5.314.144.648,00 | 5.314.144.648,00 | **0,00** |
| `TotalDespesas` DOTAÇÃO ATUALIZADA (e) | `522310000` | 6.043.181.131,90 | 6.043.181.131,90 | **0,00** |
| `TotalReceitas` PREVISÃO ATUALIZADA (a) | previsão inicial + `521210100` | 5.560.342.799,26 | 5.560.342.799,26 | **0,00** |

Total: **11 valores conferidos, zero diferença.**

## O resíduo de R$ 12.000.000,00 confirma B5 e B6

`TotalReceitas` PREVISÃO INICIAL publicada = 5.301.644.648,00. Pela MSC, `521110000` −
`521129900` = 5.313.644.648,00 — R$ 12.000.000,00 acima.

A diferença são três registros de `521110000` com natureza de receita `9.9.9.0.00.0.0` (*Recursos
Arrecadados em Exercícios Anteriores*). O STN não os soma no total das receitas: compõem a linha
própria de saldos de exercícios anteriores. O publicado confirma:

```
SaldoDeExerciciosAnteriores...  PREVISÃO INICIAL         12.000.000,00
                                PREVISÃO ATUALIZADA (a) 482.338.332,64
                                Até o Bimestre (c)      470.338.332,64
RecursosArrecadadosEm...        PREVISÃO INICIAL/ATUAL.  12.000.000,00
SuperavitFinanceiro             PREVISÃO ATUALIZADA (a) 470.338.332,64
```

- **B6 confirmado:** `L27` tem colunas de valor, e `12.000.000,00 + 470.338.332,64 =
  482.338.332,64` fecha `L27 = L28 + L29 + L30` na previsão atualizada.
- **B5 confirmado:** `SuperavitFinanceiro` = 470.338.332,64 = exatamente `522130100`, a conta que
  `L29` declara na linha. O override é o que o STN pratica.
- **`621100000` fica fora, medido:** ela vale 454.467.502,93 (`C − D`), e o `SALDO (a-c)` publicado
  é 442.467.502,93 — os mesmos R$ 12 mi de diferença. O saldo é coluna derivada (`a − c`), não a
  conta 6.2.1.1.

Uma natureza de receita que nenhuma linha do total classifica é **resíduo**, não erro — e precisa
ser medida e reportada, nunca somada ao total nem descartada em silêncio.

## Reprodução

```
GET tt/msc_orcamentaria?id_ente=2507507&an_referencia=2025&me_referencia=12
    &co_tipo_matriz=MSCC&classe_conta={5,6}&id_tv=ending_balance
GET tt/dca?an_exercicio=2025&id_ente=2507507&no_anexo=DCA-Anexo%20I-{C,D}
```

Os nomes de conta do `tt/dca` e da MSC vêm em latin-1; decodificar antes de comparar rótulos.
Valores conferidos em `Decimal`, nunca `float`.
