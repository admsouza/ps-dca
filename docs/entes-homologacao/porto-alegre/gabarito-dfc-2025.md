# Gabarito DFC 2025 — Porto Alegre/RS (4314902), administração direta

**Fonte:** Prefeitura Municipal de Porto Alegre — *Demonstração dos Fluxos de Caixa*, exercício 2025,
**administração direta** (`docs/entes-homologacao/porto-alegre/DFC 2025.pdf`, pp. 12–13 da publicação).

**Extração:** o PDF é **imagem pura** (2 páginas, uma imagem por página, sem camada de texto) —
transcrição visual, conferida pelas **43 identidades** do próprio demonstrativo, todas fechando em
centavos nas duas colunas (`scripts` de conferência fora do repo; ver §Conferência).

**Uso:** **homologação** da apuração da DFC (change `ipc08-dfc-regras-canonicas` e a change de
apuração seguinte). O mapeamento linha → conta é o do **IPC 08, ed. 2020-01**
(`knowledge/rules/dfc/`) sobre a **MSC** do ente; este demonstrativo é do **ente**, serve para
conferir o resultado e **não** é fonte de regra.

> **Ressalva — recorte não consolidado.** Igual ao BF do mesmo ente: este é o demonstrativo da
> **administração direta**, não do consolidado. Homologar contra a apuração do mesmo recorte.

---

## Quadro Principal (p. 12)

`Ln` é a linha do IPC 08 (`knowledge/rules/dfc/quadro_principal.yaml`). Rótulo é o do ente.

| Ln | Rótulo publicado | Exercício 2025 | Exercício 2024 |
|---|---|---|---|
| L2 | **Ingressos** | 20.339.004.451,07 | 33.314.315.334,76 |
| L3 | Receita Tributária | 3.740.394.788,89 | 3.656.551.505,40 |
| L4 | Receita de Contribuições | 91.299.480,93 | 77.212.738,67 |
| L5 | Receita Patrimonial | 140.455.542,25 | 20.531.122,70 |
| L6 | Receita Agropecuária | - | - |
| L7 | Receita Industrial | - | - |
| L8 | Receita de Serviços | 7.399.169,27 | 9.356.821,61 |
| L9 | Remuneração das Disponibilidades | 301.239.717,16 | 207.780.300,74 |
| L11 | Outras Receitas Derivadas e Originárias | 11.878.057.845,81 | 25.471.997.779,87 |
| L10 | Transferências Recebidas | 4.180.157.906,76 | 3.870.885.065,77 |
| L12 | **Desembolsos** | 19.894.596.631,09 | 32.983.040.362,59 |
| L13 | Pessoal e Demais Despesas | 4.505.711.396,10 | 4.048.115.598,61 |
| L14 | Juros e Encargos da Dívida | 115.201.049,07 | 75.099.447,68 |
| L15 | Transferências Concedidas | 2.818.573.069,81 | 2.463.930.537,79 |
| L16 | Outros Desembolsos Operacionais | 12.455.111.116,11 | 26.395.894.778,51 |
| L1 | **Fluxo de Caixa Líquido das Atividades Operacionais (I)** | 444.407.819,98 | 331.274.972,17 |
| L18 | **Ingressos** (investimento) | 5.916.388,98 | 4.808.264,63 |
| L19 | Alienação de Bens | 5.916.388,98 | 4.808.264,63 |
| L20 | Amortização de Empréstimos e Financiamentos Concedidos | (vazio) | - |
| L21 | Outros Ingressos de Investimentos | (vazio) | - |
| L22 | **Desembolsos** (investimento) | 174.741.973,94 | 226.247.510,77 |
| L23 | Aquisição de Ativo Não Circulante | 155.518.785,29 | 196.842.811,23 |
| L24 | Concessão de Empréstimos e Financiamentos | (vazio) | - |
| L25 | Outros Desembolsos de Investimentos | 19.223.188,65 | 29.404.699,54 |
| L17 | **Fluxo de Caixa Líquido das Atividades de Investimento (II)** | (168.825.584,96) | (221.439.246,14) |
| L27 | **Ingressos** (financiamento) | 138.365.831,64 | 119.957.231,53 |
| L28 | Operações de Crédito | 138.365.831,64 | 119.957.231,53 |
| L29 | Integralização do Capital Social de Empresas Dependentes | (vazio) | - |
| L30 | Outros Ingressos de Financiamento | (vazio) | - |
| L31 | **Desembolsos** (financiamento) | 152.587.815,65 | 138.949.871,35 |
| L32 | Amortização / Refinanciamento da dívida | 4.242.326,51 | 10.399.261,81 |
| L33 | Outros Desembolsos de Financiamentos | 148.345.489,14 | 128.550.609,54 |
| L26 | **Fluxo de Caixa Líquido das Atividades de Financiamento (III)** | (14.221.984,01) | (18.992.639,82) |
| L34 | **GERAÇÃO LÍQUIDA DE CAIXA E EQUIVALENTE DE CAIXA (I+II+III)** | 261.360.251,01 | 90.843.086,21 |
| L35 | Caixa e Equivalentes de Caixa inicial | 1.492.410.149,01 | 1.401.567.062,80 |
| L36 | Caixa e Equivalentes de Caixa final | 1.753.770.400,02 | 1.492.410.149,01 |

**36 linhas publicadas = 36 linhas do IPC 08.** Diferenças de forma, não de estrutura:

1. **Ordem invertida L10/L11** — o ente publica *Outras Receitas Derivadas e Originárias* antes de
   *Transferências Recebidas*. O IPC 08 traz L10 Transferências recebidas e L11 Outras
   Receitas/Ingressos Operacionais. A amarração `L10 = Total das Transferências Recebidas` confirma a
   correspondência.
2. **Rótulo de L3** — o ente escreve *Receita Tributária*; o IPC 08, *Impostos, Taxas e Contribuições
   de Melhoria*.

## Quadro de Transferências Recebidas e Concedidas (p. 12)

| Ln | Rótulo publicado | Exercício 2025 | Exercício 2024 |
|---|---|---|---|
| L1 | Intergovernamentais | 3.526.742.691,42 | 3.263.062.992,24 |
| L2 | da União | 2.196.080.565,08 | 2.098.212.232,82 |
| L3 | de Estados e Distrito Federal | 1.330.662.126,34 | 1.164.850.759,42 |
| L4 | de Municípios | - | - |
| L5 | Intragovernamentais | - | - |
| L6 | Outras Transferências Recebidas | 653.415.215,34 | 607.822.073,53 |
| L7 | **Total das Transferências Recebidas** | 4.180.157.906,76 | 3.870.885.065,77 |
| L8 | Intergovernamentais | 9.738.895,83 | 2.901.192,92 |
| L9 | à União | 8.069.597,75 | 1.700.310,33 |
| L10 | a Estados e Distrito Federal | 1.669.298,08 | 1.200.882,59 |
| L11 | a Municípios | - | - |
| L12 | *a Consórcios Públicos* | **não publicada** | **não publicada** |
| L13 | Intragovernamentais | 1.431.057.555,99 | 1.330.457.163,87 |
| L14 | Outras Transferências Concedidas | 1.377.776.617,99 | 1.130.572.181,00 |
| L15 | **Total das Transferências Concedidas** | 2.818.573.069,81 | 2.463.930.537,79 |

**14 das 15 linhas.** O ente **omite L12 (a Consórcios Públicos)** — linha não comparável, não
divergência. `L8 = L9+L10+L11` fecha sem ela.

## Quadro de Desembolsos de Pessoal e Demais Despesas por Função (p. 13)

| Ln | Função | Exercício 2025 | Exercício 2024 |
|---|---|---|---|
| L1 | Legislativa | 157.235.217,27 | 161.365.108,99 |
| L2 | Judiciária | 67.585.319,35 | 64.321.281,40 |
| L3 | Essencial à Justiça | - | - |
| L4 | Administração | 597.570.808,98 | 546.408.002,25 |
| L5 | Defesa Nacional | - | - |
| L6 | Segurança Pública | 61.205.993,22 | 61.777.531,48 |
| L7 | Relações Exteriores | - | - |
| L8 | Assistência Social | 26.784.723,46 | 17.120.522,05 |
| L9 | Previdência Social | 28.721.874,22 | 24.779.406,25 |
| L10 | Saúde | 2.116.786.065,37 | 1.860.715.499,16 |
| L11 | Trabalho | 421.800,53 | 303.347,23 |
| L12 | Educação | 813.382.394,86 | 705.291.182,13 |
| L13 | Cultura | 39.570.712,38 | 43.908.454,03 |
| L14 | Direitos da Cidadania | 3.027.407,32 | 11.043.284,17 |
| L15 | Urbanismo | 170.703.227,22 | 208.334.107,16 |
| L16 | Habitação | - | 183.051,33 |
| L17 | Saneamento | - | - |
| L18 | Gestão Ambiental | 29.657.428,29 | 37.593.862,56 |
| L19 | Ciência e Tecnologia | - | - |
| L20 | Agricultura | 1.975.783,57 | 3.298.324,87 |
| L21 | Organização Agrária | - | - |
| L22 | Indústria | - | - |
| L23 | Comércio e Serviços | 6.753.104,78 | 5.937.722,87 |
| L24 | Comunicações | - | - |
| L25 | Energia | - | - |
| L26 | Transporte | 186.469.943,50 | 165.674.105,86 |
| L27 | Desporto e Lazer | 4.692.668,63 | 4.346.409,03 |
| L28 | Encargos Especiais | 193.166.923,15 | 125.714.395,79 |
| L29 | **Total dos Desembolsos de Pessoal e Demais Despesas por Função** | 4.505.711.396,10 | 4.048.115.598,61 |

**29 de 29.** Ordem das funções 01–28 idêntica à do IPC 08.

## Quadro de Juros e Encargos da Dívida (p. 13)

| Ln | Rótulo publicado | Exercício 2025 | Exercício 2024 |
|---|---|---|---|
| L1 | Juros e Correção Monetária da Dívida Interna | 74.425.391,92 | 38.856.863,56 |
| L2 | Juros e Correção Monetária da Dívida Externa | 40.775.657,15 | 36.242.584,12 |
| L3 | Outros Encargos da Dívida | - | - |
| L4 | **Total dos Juros e Encargos da Dívida** | 115.201.049,07 | 75.099.447,68 |

**4 de 4.** O ente rotula **as duas colunas** como *Exercício Atual* — erro de publicação; a segunda
reproduz o exercício anterior (confere com L14 do Quadro Principal, coluna 2024).

---

## Conferência

43 identidades do próprio demonstrativo, **todas fechando em centavos nas duas colunas**:

| Identidade | 2025 | 2024 |
|---|---|---|
| `L2 = L3+…+L11` | ✔ | ✔ |
| `L12 = L13+…+L16` | ✔ | ✔ |
| `L1 = L2 − L12` | ✔ | ✔ |
| `L18 = L19+L20+L21` | ✔ | ✔ |
| `L22 = L23+L24+L25` | ✔ | ✔ |
| `L17 = L18 − L22` | ✔ | ✔ |
| `L27 = L28+L29+L30` | ✔ | ✔ |
| `L31 = L32+L33` | ✔ | ✔ |
| `L26 = L27 − L31` | ✔ | ✔ |
| `L34 = L1+L17+L26` | ✔ | ✔ |
| `L36 = L34+L35` | ✔ | ✔ |
| `T.L1 = T.L2+L3+L4` | ✔ | ✔ |
| `T.L7 = T.L1+L5+L6` | ✔ | ✔ |
| `T.L8 = T.L9+L10+L11` | ✔ | ✔ |
| `T.L15 = T.L8+L13+L14` | ✔ | ✔ |
| `J.L4 = J.L1+L2+L3` | ✔ | ✔ |
| `F.L29 = F.L1+…+L28` | ✔ | ✔ |
| `P.L10 = T.L7` (transferências recebidas) | ✔ | ✔ |
| `P.L15 = T.L15` (transferências concedidas) | ✔ | ✔ |
| `P.L14 = J.L4` (juros e encargos) | ✔ | ✔ |
| `P.L13 = F.L29` (pessoal e demais despesas) | ✔ | ✔ |
| `L35(2025) = L36(2024)` (continuidade do caixa) | ✔ | — |

As quatro amarrações entre quadros (`P.L10/P.L13/P.L14/P.L15`) confirmam que os quadros auxiliares
do IPC 08 são **detalhamento** das linhas do principal, e não quadros independentes — a apuração
pode derivar `P.L13`, `P.L14`, `P.L15` e `P.L10` dos auxiliares, ou conferi-los contra eles.

## O que este gabarito diz sobre as regras canônicas

1. **Estrutura confirmada em 84 linhas.** 36 + 15 + 29 + 4 do IPC 08 contra 36 + 14 + 29 + 4
   publicados; a única ausência (`T.L12`, Consórcios Públicos) é omissão do ente.
2. **L16 concentra 62,6% dos desembolsos operacionais** (12.455.111.116,11 de 19.894.596.631,09) e
   **L11, 58,4% dos ingressos** (11.878.057.845,81 de 20.339.004.451,07). São justamente as duas
   linhas que a change deixou frágeis: L16 **sem `columns`** (`review_required`, item 17) e L11 com
   contas mas `review_required` (naturezas `2.9.40.00.1.1` e `2.9.90.00.1.1` ausentes da tabela STN).
   Com L16 vazia, `L12` apurado sai 7.439.485.514,98 em vez de 19.894.596.631,09 — e o erro
   propaga para `L1`, `L34` e `L36`, quebrando a policy `ipc08.soma_fluxos_igual_variacao_caixa`.
3. **Ingressos operacionais (20,3 bi) ≫ receita orçamentária do BF do mesmo ente (8,7 bi).** A DFC
   publicada inclui movimento extraorçamentário; mapear L11/L16 só por natureza de receita/despesa
   orçamentária não reproduz o demonstrativo.
