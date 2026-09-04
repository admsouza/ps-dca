# Onde cada informação está publicada no SICONFI

**Medido em:** 2026-09-03 · **Ente de referência:** João Pessoa `2507507`, exercício 2025
**Endpoints:** `tt/dca` e `tt/rreo` do datalake do Tesouro

Levantamento empírico: cada anexo foi consultado e as colunas efetivamente devolvidas foram
tabuladas. Não é leitura de documentação — é o que a API entrega.

## Os 7 anexos da DCA

Consulta sem `no_anexo` devolve **2.002** registros para o ente/exercício, e a soma dos 7 anexos
fecha exatamente 2.002. **Não existe oitavo anexo**: `I-J` e `II` devolvem zero.

| Anexo | Demonstrativo | Registros | Colunas devolvidas | `cod_conta` |
|---|---|---|---|---|
| **I-AB** | Balanço Patrimonial | 140 | `31/12/2025` (data única) | `P1.*`, `P2.*`, `AtivoFinanceiro`, `AtivoPermanente` |
| **I-C** | Receitas Orçamentárias | 192 | Receitas Brutas Realizadas · Deduções — FUNDEB · Outras Deduções da Receita | `RO*`, `RI*` (natureza de receita) |
| **I-D** | Despesas Orçamentárias por natureza | 327 | Empenhadas · Liquidadas · Pagas · Inscrição RP Processados · Inscrição RP Não Processados | `DO*`, `DI*` (natureza de despesa) |
| **I-E** | Despesas por função/subfunção | 406 | as mesmas 5 de I-D | `TotalDespesas` + função |
| **I-F** | Restos a Pagar por natureza | 290 | 9 colunas de RP (inscritos no exercício anterior e em anteriores, liquidados, pagos, cancelados — processados e não processados) | `DO*`, `DI*` |
| **I-G** | Restos a Pagar por função | 443 | as mesmas 9 de I-F | `TotalDespesas` + função |
| **I-HI** | Demonstração das Variações Patrimoniais | 204 | `31/12/2025` (data única) | `P3.*`, `P4.*` |

## O achado: o Balanço Orçamentário não é um anexo da DCA

**Nenhum** dos 7 anexos publica previsão da receita, dotação inicial, dotação atualizada ou saldo
de execução. A DCA entrega **posição** (I-AB, I-HI) e **execução realizada** (I-C, I-D, I-E, I-F,
I-G) — nunca o confronto previsto × executado, que é a substância do Balanço Orçamentário.

O BO do IPC 07 é publicado como **`RREO-Anexo 01`**, e as colunas batem uma a uma com a matriz do
IPC:

| Coluna do `RREO-Anexo 01` | Corresponde no IPC 07 |
|---|---|
| PREVISÃO INICIAL | previsão inicial (a) |
| PREVISÃO ATUALIZADA (a) | previsão atualizada (b) |
| Até o Bimestre (c) | receitas realizadas (c) |
| SALDO (a-c) | saldo (d) |
| DOTAÇÃO INICIAL (d) · DOTAÇÃO ATUALIZADA (e) | dotação inicial · atualizada |
| EMPENHADAS (f) · SALDO (g)=(e-f) | empenhadas · saldo |
| LIQUIDADAS (h) · SALDO (i)=(e-h) | liquidadas · saldo |
| PAGAS (j) · INSCRITAS EM RP NÃO PROCESSADOS (k) | pagas · inscritas em RP |

`nr_periodo=6` (6º bimestre) é o exercício fechado, logo o gabarito anual do BO.

**Consequência de escopo, para o PO decidir:** o `ps-dca` calcula a DCA, e o BO não é um anexo da
DCA. A regra canônica do IPC 07 continua válida como conhecimento, mas o demonstrativo que ela
descreve tem gabarito no RREO. Ver a pendência registrada em
`openspec/changes/bo-quadro-principal-processamento/`.

## Gabarito das colunas de previsão e dotação

Conferido contra a MSC de JP 12/2025 (`ending_balance`, `MSCC`):

| `RREO-Anexo 01` | Valor publicado | Conta na MSC | Confere |
|---|---|---|---|
| `TotalDespesas` DOTAÇÃO INICIAL (d) | 5.314.144.648,00 | `522110100` Crédito Inicial | **exato** |
| `TotalDespesas` DOTAÇÃO ATUALIZADA (e) | 6.043.181.131,90 | `522310000` = `622310000` | **exato** |
| `TotalReceitas` PREVISÃO ATUALIZADA (a) | 5.560.342.799,26 | previsão inicial + `521210100` reestimativa | **exato** |

## O resíduo de R$ 12.000.000,00 — e a confirmação de B6

`TotalReceitas` PREVISÃO INICIAL publicada é 5.301.644.648,00. A MSC traz
`521110000` (previsão bruta) 5.646.540.648,00 menos `521129900` (deduções) 332.896.000,00 =
5.313.644.648,00 — **R$ 12.000.000,00 acima** do publicado.

A diferença não é erro. São três registros de `521110000` com natureza de receita `9.9.9.0.00.0.0`
— *Recursos Arrecadados em Exercícios Anteriores*, a natureza que existe para equilíbrio formal do
orçamento. O STN não os soma no total das receitas: eles compõem a linha própria de **saldos de
exercícios anteriores**, e o publicado confirma:

| `cod_conta` do RREO | Coluna | Valor |
|---|---|---|
| `SaldoDeExerciciosAnterioresUtilizadosParaCreditosAdicionais` | PREVISÃO INICIAL | 12.000.000,00 |
| — | PREVISÃO ATUALIZADA (a) | 482.338.332,64 |
| — | Até o Bimestre (c) | 470.338.332,64 |
| `RecursosArrecadadosEmExerciciosAnteriores` | PREVISÃO INICIAL / ATUALIZADA | 12.000.000,00 |
| `SuperavitFinanceiro` | PREVISÃO ATUALIZADA (a) / Até o Bimestre (c) | 470.338.332,64 |

Isso confirma, com dado publicado, duas decisões da change `ipc07-bo-regras-canonicas`:

- **B6** — `L27` (Saldos de Exercícios Anteriores) **tem** colunas de valor, e suas filhas também.
  `12.000.000,00 + 470.338.332,64 = 482.338.332,64` fecha `L27 = L28 + L29 + L30` na previsão
  atualizada. A decisão do PO de 2026-09-03 está correta contra o publicado.
- **B5** — `SuperavitFinanceiro` = **470.338.332,64** = exatamente a conta `522130100` da MSC, que
  é a conta declarada na linha `L29`. O override de conta em `L29`/`L30` é o que o STN pratica.

Ressalva medida: para essa linha o ente publicou 3 das 4 colunas de receita — `SALDO (a-c)` não
veio. Ausência de coluna no publicado é do ente, não da regra.

## Reprodução

```
GET tt/dca?an_exercicio=2025&id_ente=2507507                       # 2.002 regs, os 7 anexos
GET tt/dca?an_exercicio=2025&id_ente=2507507&no_anexo=DCA-Anexo I-D
GET tt/rreo?an_exercicio=2025&nr_periodo=6&co_tipo_demonstrativo=RREO
    &no_anexo=RREO-Anexo 01&id_ente=2507507                        # 451 regs
```

Rótulos e nomes de conta vêm em latin-1 nos dois endpoints.
