# Evidência — Balanço Financeiro, João Pessoa 2025

**Medido em:** 2026-09-14 · **Ente:** `2507507` · **Competência:** 12/2025 · **Matriz:** `MSCC`
**Fontes:** `tt/dca` (anexos publicados) e `tt/msc_patrimonial` / `msc_orcamentaria` /
`msc_controle`, classes 1–8, `id_tv` `beginning_balance`, `ending_balance` e `period_change`,
exercícios 2025 e 2024.

Levantamento feito **antes** de escrever código, para decidir G1–G6 da change `bf-apuracao-f1`
com dado e não com suposição. A apuração abaixo foi feita por script de medição, fora de `app/`.

---

## 1. O `tt/dca` não publica o Balanço Financeiro

Consulta sem filtro de anexo devolve **2.002** registros para o ente/exercício, distribuídos nos
mesmos 7 anexos já inventariados em `docs/anexos-siconfi-inventario.md`:

| Anexo | Registros |
|---|---|
| DCA-Anexo I-AB (Balanço Patrimonial) | 140 |
| DCA-Anexo I-C (Receitas Orçamentárias) | 192 |
| DCA-Anexo I-D (Despesas por natureza) | 327 |
| DCA-Anexo I-E (Despesas por função) | 406 |
| DCA-Anexo I-F (RP por natureza) | 290 |
| DCA-Anexo I-G (RP por função) | 443 |
| DCA-Anexo I-HI (DVP) | 204 |

Busca por `cod_conta` que contenha `ingresso`, `dispendio`, `extraorc`, `transferenciafinanceira`
ou `financeir`: só `AtivoFinanceiro` e `PassivoFinanceiro`, ambos do Balanço Patrimonial.

**Consequência:** não existe gabarito 1:1 do BF no SICONFI, como havia para o BO no `RREO-Anexo 01`.
O aceite da F1 do BF não pode ser "célula a célula contra o publicado". Precisa ser:

1. **identidade interna** — `L33 TOTAL (VI)` = `L66 TOTAL (XII)`, e cada pai igual à soma das filhas;
2. **âncoras publicadas** — as linhas do BF que têm correspondente em I-C, I-D, I-F e I-AB;
3. **conciliação de caixa** — ingressos menos dispêndios explicando a variação de caixa do exercício.

## 2. Fonte de recursos (G1) — confirmado

`fonte_recursos` vem **sempre com 4 dígitos** na MSC deste ente, em todas as classes e tipos de
valor medidos (46 a 89 fontes distintas por consulta, `tamanhos {4: n}` em 100% dos casos). O
detalhamento do ente **não** vai nesse campo: existe uma coluna própria, `complemento_fonte`.

Exemplos lidos: `1500`, `1501`, `1540`, `1541`, `1543`, `1546`, `1550`, `1551`, `1552`, `1553`,
`1569`, `1571`.

Aplicando `codigo_principal(fonte) = digitos[1:4]` e casando por **igualdade** contra as faixas do
Anexo I (decisão F3):

| Identidade | Apurado | Soma das filhas | Diferença |
|---|---|---|---|
| `L1 = L2 + L3 + L11` | 5.117.875.296,33 | 5.117.875.296,33 | **0,00** |
| `L34 = L35 + L36 + L44` | 4.850.356.845,30 | 4.850.356.845,30 | **0,00** |

**Resíduo de fonte: nenhum.** Toda fonte escriturada em `6.2.1.2`, `6.2.1.3` e `6.2.2.1.3` cai em
um dos subgrupos declarados. O mapeamento F3 está correto contra dado real.

## 3. Tipos de valor (G2, G3) — confirmado

Os três `id_tv` respondem nas classes que o BF precisa:

| Classe | `beginning_balance` | `ending_balance` | `period_change` |
|---|---|---|---|
| 1 (ativo) | 331 regs | 323 regs | 342 regs |
| 2 (passivo) | 306 regs | 291 regs | 500+ regs |
| 6 (execução) | 500+ | 4.320 | 5.860 |

`natureza_conta` vem por registro (`C`/`D`), o que torna `movimento credor` × `devedor`
separável — desde que a leitura seja de `period_change`. Em `2.1.8.8`, no período:
**C = 127.592.727,15** e **D = 145.790.710,23**. No saldo acumulado os dois sentidos seriam um
número só (−18.197.983,08), e `L27`/`L60` sairiam indistinguíveis.

## 4. Volume e latência (G4) — não é problema

Download completo de 2025 **e** 2024, 8 classes × até 3 tipos de valor: **~45 segundos**, maior
resposta com 6.202 registros (classe 6, `period_change`, 2024). Duas instabilidades de conexão em
~40 chamadas — o adapter precisa de retry com backoff, que o do BO ainda não tem.

## 5. Achado novo: a direção do saldo no BF é **por conta**, não por coluna

No BO, a direção de uma coluna é a do grupo, e a conta redutora entra subtraindo por consequência
(`credora_prefixo`). Aplicar isso ao BF **inverte a dedução**: o par do IPC 06
`6.2.1.2.0.00.00 (+) 6.2.1.3.0.00.00 (−)` já traz o sinal na regra, e tomar as duas na direção do
grupo faz a dedução somar.

| Critério de direção | `L1 Receita Orçamentária` |
|---|---|
| direção da coluna (como no BO) | 5.872.854.713,27 |
| **direção por conta** | **5.117.875.296,33** |
| publicado (I-C: 5.495.365.004,80 − 377.489.708,47) | **5.117.875.296,33** |

A leitura por conta bate **em centavos** com o publicado. Isso é decisão nova — **G7** — e precisa
entrar na spec: o motor tem de escolher o critério de direção pela regra, não por convenção global.

## 6. Âncoras que já batem

| Linha do BF | Apurado | Publicado | Fonte | Diferença |
|---|---|---|---|---|
| `L1` Receita Orçamentária | 5.117.875.296,33 | 5.117.875.296,33 | I-C (bruta − deduções) | **0,00** |
| `L25` Inscrição de RP Não Processados | 281.307.109,52 | 281.307.109,52 | I-D | **0,00** |
| `L26` Inscrição de RP Processados | 39.255.202,67 | 39.255.202,67 | I-D | **0,00** |
| `L34` Despesa Orçamentária | 4.850.356.845,30 | 4.850.356.845,30 | I-D (empenhadas) | **0,00** |

`L15` (transferências recebidas) e `L48` (concedidas) saem **iguais**, 8.570.629.908,16 — o que se
espera de transferências internas ao ente, e que anula o par nos dois totais.

## 7. O que ainda não fecha

> **Retificado em 2026-09-14.** A primeira medição leu `L29`–`L32` do `beginning_balance` da
> competência 12, que é a abertura de **dezembro**, não do exercício. O saldo de abertura do
> exercício está em `(ano, mês 1, beginning)` ou `(ano-1, mês 12, ending)` — as duas vias dão
> **1.865.100.624,27**, contra 2.613.640.800,87 antes usados. Ver
> `docs/evidencia-matriz-mscc-vs-msce.md`. Os números abaixo já estão corrigidos.

Com a direção por conta, a abertura do exercício correta e as 6 linhas bloqueadas tratadas como
parcela inexistente (G5a):

```
L29 Saldo do Exercício Anterior   1.865.100.624,27
L33 TOTAL (VI)                   15.898.515.801,53
L66 TOTAL (XII)                  16.875.758.073,28
diferença                          −977.242.271,75     (dispêndios maiores)
```

Sem G5a, `L21`, `L24`, `L33`, `L54`, `L57` e `L66` sairiam **todas não apuradas** — o BF inteiro
ficaria em branco por causa de seis linhas. A opção (a) é o que torna o demonstrativo mensurável.

Peças identificadas para a diferença, todas dentro das linhas hoje bloqueadas:

| Peça | Valor | Onde entraria |
|---|---|---|
| `1.2.1.3.0.9.01` Títulos Públicos do Tesouro Nacional — movimento credor no período (redução do investimento) | 374.780.440,97 | `L22` Resgates de Investimentos (ingresso) |
| `L27`/`L60` sem o filtro de fontes extraorçamentárias | −13.802.518,58 no líquido | ver §8 |
| restante | ~616.000.000 | `L23`, `L28`, `L55`, `L56`, `L61` e a exclusão de intraorçamentárias (item 38) |

## 8. F1 e F2 do IPC 06: o ente não escritura conta de controle para isso

As classes 7 e 8 de João Pessoa têm 6 e 12 contas, e **nenhuma** é de movimentação financeira de
investimentos ou bloqueio de caixa:

```
721900000 OUTROS CONTROLES - DISPONIBILIDADES POR DESTINAÇÃO
721110000 RECURSOS ORDINÁRIOS
722900000 OUTROS CONTROLES - PROGRAMAÇÃO FINANCEIRA
799000000 DEMAIS CONTROLES
821900000 OUTROS CONTROLES - EXECUÇÃO DAS DISPONIBILIDADES
...
```

São controles de disponibilidade por destinação e de programação financeira — o conteúdo do
`ANEXO 5` do RREO, não das "Outras Movimentações Financeiras" do BF.

**Consequência:** manter F1/F2 como `review_required` está certo, mas a saída provável **não** é
"descobrir a conta de controle do ente" — é apurar `L22`/`L55` pela **variação patrimonial dos
investimentos** (`1.1.4` a curto prazo e `1.2.1.3` a longo prazo), que é dado que existe:
movimento credor → resgate (`L22`), movimento devedor → aplicação (`L55`). Em 2025 o ente tem
`1.1.4` zerada e `1.2.1.3` com 374.780.440,97 de movimento credor.

Isso é uma decisão normativa nova para o PO — chame-se **G8** — e é o que falta para o BF fechar.

## 9. Conciliação de caixa

```
caixa em 01/01/2025 (abertura do exercício)        1.865.100.624,27
caixa em 31/12/2025 (encerramento)                 3.248.364.442,41
variação no exercício                             +1.383.263.818,14
```

O BF fecha quando `ingressos − dispêndios` (fora as linhas de saldo) explicar exatamente esses
1.383.263.818,14. Hoje explicam 406.021.546,39 — a mesma diferença de 977.242.271,75 vista em §7.

## Reprodução

```
GET tt/dca?an_exercicio=2025&id_ente=2507507
GET tt/msc_patrimonial?id_ente=2507507&an_referencia=2025&me_referencia=12
    &co_tipo_matriz=MSCC&classe_conta=1&id_tv=beginning_balance&limit=5000
GET tt/msc_orcamentaria?...&classe_conta=6&id_tv=ending_balance&limit=5000
GET tt/msc_controle?...&classe_conta=7&id_tv=ending_balance&limit=5000
```

Paginação ORDS obrigatória (`hasMore`), blocos de 5.000. Rótulos em latin-1.
