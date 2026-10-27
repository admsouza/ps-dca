# Evidência — Apuração da DFC (F1)

**Change:** `dfc-apuracao-f1` · **Medição:** 2026-10-27 · **Fonte:** API SICONFI (`tt/msc_*`),
MSCE competência 12, saldo de abertura, classes 1 a 6, exercício 2025.

## O que foi implementado

`app/services/dfc/quadro_principal.py` apura as 84 linhas pelo motor de BO/BF/BP/DVP. Três coisas
que a medição obrigou, todas registradas como decisão em `openspec/changes/dfc-apuracao-f1/`:

| | Antes | Depois |
|---|---|---|
| **D2** agregadoras | `L1`, `L12`, `L17`, `L18`, `L26`, `L27`, `L34` e `L36` saíam **não apuradas** ("referências sem coluna em comum", porque `L16`/`L21`/`L30` não têm `columns`) | totalizadas no serviço, em ordem topológica, com as informadas já postas |
| **D3** caixa inicial | `L35` = 2.854.802.415,12, que é o caixa **final** | `L35` = 2.785.855.199,20, o `1.1.1` da MSC de N−1 |
| **D10** item 17 | sem lugar para o valor do ente | `L16`, `L21`, `L30` aceitam valor digitado; ausentes valem `0,00` e não derrubam o total |

Porto Alegre/RS 2025 pelo CLI: **84 linhas, 0 células não apuradas**.

## A identidade de caixa fecha — e o resíduo é o diagnóstico

`L34` tem de ser a variação de `1.1.1` entre as duas MSC. Como `L16` é campo livre, sempre existe
um valor que fecha; **o que informa não é o fechamento, é o resíduo necessário**:

| Ente | `L34` sem os Outros | Variação do caixa | `L16` que fecha | % dos ingressos |
|---|---:|---:|---:|---:|
| Porto Alegre/RS | 1.045.831.543,34 | 68.947.215,92 | **976.884.327,42** | 7,43% |
| Recife/PE | 1.095.390.436,56 | 506.192.732,10 | **589.197.704,46** | 5,92% |
| Cuitegi/PB | 13.041.919,43 | 6.474.163,38 | **6.567.756,05** | 11,12% |
| João Pessoa/PB | 726.170.814,11 | 1.383.263.818,14 | **−657.093.004,03** | **−11,86%** |

Nos quatro entes, com `L16` = resíduo, `L34` e `L36` fecham em centavos contra a MSC — `L36` igual
ao `1.1.1` de N, `L35` igual ao de N−1.

> **Atualização de 2026-10-27** (change `dfc-l25-residual`): corrigida a dupla contagem entre
> `L23` e `L25`, o resíduo de João Pessoa encolheu de −657.093.004,03 para −217.997.300,88, e os
> demais subiram o valor de `L23` (Porto Alegre 1.372.542.206,88 · Recife 1.193.493.653,24 ·
> Cuitegi 8.359.257,99). Dois terços do caso negativo eram aquele defeito.

**João Pessoa é o alerta.** Um "outros desembolsos operacionais" **negativo** não existe: significa
que o caixa do ente cresceu 1,38 bi e a apuração só explica 726 mi, faltando ingresso que o mapa
não alcança. O fechamento aritmético esconde isso; o sinal do resíduo denuncia. Nos outros três o
resíduo é positivo e de magnitude plausível para a linha "Outros".

Por isso o aceite da apuração **não** é "fecha", e sim: `L34` e `L36` fecham contra a MSC **e** o
resíduo de `L16` é positivo e explicável. Em João Pessoa isso ainda não acontece.

## Suspeito número um: as naturezas de 5º nível do IPC 08

`L9` (Remuneração das Disponibilidades) sai **0,00** em Porto Alegre, contra 301.239.717,16 que o
ente publica. A causa foi medida e **não é o `not_in`** das exclusões — é o `in`:

| | Valor |
|---|---|
| Padrão transcrito do IPC 08 | `1.3.21.00.1.x` → `1321001x` |
| Natureza que a MSC entrega | `13210101`, `13210401`, `13210601` |
| Soma dessas naturezas em 6212/6213 (PoA) | 776.648.829,66 |

A receita **existe** e o padrão não a alcança: a partir do 6º dígito o layout do IPC 08 (que cita
o PCASP de 2019) não corresponde ao que a MSC usa hoje. Os registros nas contas de `L9` são 335, e
**nenhum** passa no filtro.

**Corrigido no mesmo dia** pela change `dfc-naturezas-desdobramento`: o `00` do IPC ocupa a
posição do desdobramento `DD2`, logo `1.3.21.00.1.x` é `1.3.2.1.01` e o pattern certo é `132101`.

**A hipótese de que isso explicava o resíduo negativo de João Pessoa está refutada.** Medido: a
correção move 776.452.523,68 de `L5` para `L9` em Porto Alegre e **não altera `L2`, `L1`, `L34`
nem o resíduo de nenhum dos quatro entes**. É reclassificação. A causa do resíduo negativo
continua aberta, e `L11` também foi descartada — seus patterns corrigidos não casam com nada na
MSC do ente.

## Conferência cruzada com o Balanço Financeiro

`L35` e `L36` da DFC têm de reproduzir `L29` e `L62` do BF do mesmo ente, porque os dois leem a
mesma MSC. Conferem em centavos
(`docs/entes-homologacao/porto-alegre/auditoria-bf-2025.md`, linhas 65 e 109):

| | DFC apurada | BF auditado |
|---|---:|---:|
| Caixa inicial de 2025 | 2.785.855.199,20 | 2.785.855.199,20 (`L29`) |
| Caixa final de 2025 | 2.854.802.415,12 | 2.854.802.415,12 (`L62`) |

## Regressão dos valores já medidos

`L14` = 115.727.775,84 e `L32` = 4.278.384,37, iguais aos de `docs/evidencia-dfc-d4-funcao-28.md`
— a apuração não mudou o que D4 mediu.

## Comparação com o publicado por Porto Alegre

Informativa, não é aceite: o PDF é da administração direta e a MSC é consolidada.

| Linha | Apurado (consolidado) | Publicado (adm. direta) |
|---|---:|---:|
| L3 Impostos, Taxas e Contribuições | 4.068.529.090,17 | 3.740.394.788,89 |
| L10 Transferências recebidas | 4.888.923.505,51 | 4.180.157.906,76 |
| L13 Pessoal e Demais Despesas | 7.944.639.904,23 | 4.505.711.396,10 |
| L14 Juros e encargos | 115.727.775,84 | 115.201.049,07 |
| L32 Amortização / Refinanciamento | 4.278.384,37 | 4.242.326,51 |

`L13` é o maior desvio (76% acima) e merece medição por unidade gestora na change de recorte.

## Reprodução

```
python -m app.cli.dfc 4314902 2025 --informado L16=976884327.42
python -m pytest -m vivo tests/dfc/test_conferencia_viva.py
```
