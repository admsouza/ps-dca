# Evidência — apuração do BF sobre a MSC, medida em 2026-09-18

Mede o Balanço Financeiro **pelas regras do IPC 06** (`knowledge/rules/bf/quadro_principal.yaml`,
66 linhas do quadro principal) sobre a **MSC publicada na API do SICONFI**, com a direção do saldo
vinda do **PCASP da STN** (`docs/contas-stn/PCASP.md`), e confronta linha a linha com o BF publicado
pelos SIAFIC dos entes de homologação (`docs/depara-bf-siafic-ipc06.md`).

**Nenhuma regra canônica foi alterada.** O que muda quando o número não fecha é a hipótese, não o
IPC 06.

## Método

Reaproveita o que o Balanço Orçamentário já resolveu — carregador de regras, adapter MSC com
paginação e retry, direção do saldo por conta do PCASP, motor de matriz, resíduos. Sobre isso, a
medição cobriu os três gaps conhecidos do BF:

| Gap | Como foi coberto na medição |
|---|---|
| G1 `fonte_recurso` | campo religado a `fonte_recursos`; valor da MSC reduzido aos 3 dígitos do IPC (o 1º é o exercício da vinculação) |
| G7 direção do saldo | variante `saldo_da_celula` que usa a direção **de cada conta**, não a da coluna |
| tipo de saldo | cada linha apurada em 7 combinações: MSCE e MSCC × abertura, encerramento e período × exercício e exercício anterior |

Script de medição em `scratchpad/medir_bf*.py` (fora de `app/`, fase 0 — nenhuma linha de código de
produção foi escrita).

## Placar por ente (exercício 2025, coluna do exercício atual)

| Ente | Batem em centavos | Divergem | Não apuráveis | Equilíbrio do apurado (`L33 − L66`) |
|---|---|---|---|---|
| Recife/PE | **42 / 66** | 18 | 6 | 18.025.391,58 (0,08% de 22,3 bi) |
| João Pessoa/PB | **40 / 66** | 20 | 6 | −972.846.807,25 |
| Porto Alegre/RS | 17 / 65 | 43 | 5 | 356.960.596,03 |

Das 18 divergências de Recife, 12 são **propagação**: `L1`, `L3`, `L24`, `L29`, `L33`, `L34`, `L36`,
`L54`, `L57`, `L62`, `L66` e `L21` só divergem porque uma linha filha diverge. As causas-raiz são 6.

## Pendências resolvidas por medição

### G1 — casamento da fonte de recursos: **confirmado**

Descartar o 1º dígito e comparar os 3 seguintes por igualdade faz as 22 linhas por fonte fecharem.
Em Recife, `L2`, `L4`–`L8`, `L10`–`L14`, `L35`, `L37`–`L41`, `L43`–`L47` batem em centavos.

### G7 — direção do saldo **por conta**: confirmado

Com a direção por conta, receita e despesa por fonte fecham. A regra do IPC 06 já traz o sinal do
par redutor (`6.2.1.2 (+)` / `6.2.1.3 (−)`), então a direção da coluna deixa de ser necessária.

### G2 — saldo do exercício anterior: **resolvido, e diferente do que se supunha**

`L29`–`L32` não são um tipo de saldo diferente: são **o exercício anterior**. Medido em Recife:

| | valor | origem |
|---|---|---|
| `L30 + L31` (caixa) | 802.570.332,31 | MSCE/abertura de **2024**, conta `1.1.1` |
| `L32` (depósitos) | 717.721,98 | conta `1.1.3.5.1` |
| `L29` publicado | **803.288.054,29** | soma exata das duas |

E ficou provado que **MSCE/abertura do exercício é a posição final**, não a de 1º de janeiro: em
Recife ela devolve 1.308.763.064,41, que é exatamente `L63 + L64` publicados (saldo **para** o
exercício seguinte). A mesma regra, lida em exercícios diferentes, produz `L29` e `L62`.

### N1 — o tipo de saldo **não é único para o demonstrativo**

`L25`/`L26` (inscrição de restos a pagar) **não existem no saldo de abertura**: as contas `5.3.1.7` e
`5.3.2.7` só ganham saldo no **encerramento**, que é quando a inscrição acontece. Lá valem
74.205.408,29 e 106.062.740,96 — idênticos ao publicado por Recife.

Isso refina a decisão G9 (MSCE/abertura para o BF): a matriz é a mesma, mas o **tipo de saldo é por
linha**. Três origens cobrem o demonstrativo inteiro:

| Origem | Linhas |
|---|---|
| MSCE/abertura do exercício | todas as de fluxo e o saldo final (`L62`–`L65`) |
| MSCE/encerramento do exercício | `L25`, `L26` |
| MSCE/abertura do exercício anterior | `L29`–`L32` |

### G8 — hipótese refutada; G3 — limitação da fonte

**Seis linhas não têm conta no IPC 06** (`L22`, `L23`, `L28`, `L55`, `L56`, `L61`) e Recife publica
valor material em quatro delas. A busca reversa procurou esses valores em **7 combinações** de
matriz e tipo de saldo, em todos os prefixos de conta de 3 a 9 dígitos, como saldo, como total de
créditos e como total de débitos:

| Linha | Publicado por Recife | Encontrado na MSC |
|---|---|---|
| `L22` Resgates de Investimentos | 370.110.128,29 | **não** |
| `L55` Transferências para Investimentos | 690.544.116,24 | **não** |
| `L28` Outros Recebimentos Extraorçamentários | 1.629.640.087,52 | **não** |
| `L61` Outros Pagamentos Extraorçamentários | 1.640.655.129,62 | **não** |
| `L27` Depósitos Restituíveis (ingresso) | 1.773.240.873,95 | **não** (apurado: 97.411.954,85) |
| `L60` Depósitos Restituíveis (dispêndio) | 1.649.296.604,40 | **não** (apurado: 97.411.954,85) |

O método foi validado por **controle**: a mesma busca acha `L16` (10.938.332.536,31 → conta
`3.5.1.1.2.02.00`) e `L25` (74.205.408,29 → conta `5.3.1.7`). Não achar, aqui, é resultado.

A hipótese **(a) do G8** — apurar `L22`/`L55` pela variação patrimonial de `1.1.4` e `1.2.1.3` —
**não se sustenta em Recife**: `1.1.4` varia +710.419.938,88 no exercício e `1.1.2.1` varia
−57.745.528,96; nenhuma combinação chega aos 370.110.128,29 / 690.544.116,24 publicados. A conta
`1.2.1.3` sequer tem movimento no ente.

Quanto a `L27`/`L60` (G3), o movimento **bruto** de depósitos não existe na API: o saldo de
`2.1.8.8` vai de 132.890.609,07 (2024) a 176.421.602,57 (2025), variação +43.530.993,50; o
`period_change` da MSCC dá líquido −6.107.254,33; e o publicado implica +123.944.269,55. Três
números, nenhum igual: o que o ente chama de depósitos restituíveis não é `2.1.8.8 + 2.2.8.8`.

### N2 — `L32`/`L65` têm conta, e a regra não a declara

O valor publicado (717.721,98 nas duas) é exatamente o saldo da conta **`1.1.3.5.1`**, presente em
todas as combinações. A regra `L30` já exclui `1.1.3` do caixa; falta `L32` declará-la — pendência
de base canônica contra o IPC 06, a confirmar no texto normativo antes de qualquer alteração.

### N3 — divergência de `L9`/`L42` é do ente, não da regra

450.202.814,72 de receita e 260.723.445,80 de despesa vêm de **2 registros na conta sintética
`6.2.1.2.0.00.00` sem fonte de recursos na MSC**. O ente os classificou em "Demais Vinculações
Legais". Confirma o critério de aceite: fonte não classificada é **resíduo no diagnóstico**, nunca
zero silencioso nem redistribuição por conta própria.

### N4 — Porto Alegre não é comparável enquanto o recorte for outro

17 de 65 linhas batem, e o padrão das divergências explica: a MSC é **consolidada** e o PDF é da
**administração direta**. `L11`–`L14` e `L44`–`L47` (RPPS) saem apuradas em 2,27 bi e 1,96 bi contra
zero publicado, e `L15`/`L48` vão a 30,9 bi contra 7,5 bi. Porto Alegre só homologa se a apuração
for restrita ao mesmo recorte.

### N5 — a granularidade de João Pessoa não é comparável linha a linha, mas o bloco fecha

JP detalha 4 vinculações próprias que o IPC 06 agrega. Comparando **bloco contra bloco**:

| Bloco | Apurado | Publicado | Diferença |
|---|---|---|---|
| Ingressos `L8 + L9 + L10` | 580.159.482,56 | 580.159.482,56 | **0,00** |
| Dispêndios `L41 + L42 + L43` | 529.816.473,72 | 529.816.473,72 | **0,00** |

Ou seja: a apuração está certa e o de-para é que não tem como ser 1:1 nessas linhas.

### N6 — item 38 (intraorçamentárias): interpretação natural **refutada**

A policy `ipc06.exclusao_de_intraorcamentarias` declara o conceito e **não diz quais códigos**
caracterizam a transferência intra acompanhada de execução. A interpretação natural — excluir da
receita as naturezas das categorias **7 e 8** e da despesa as de modalidade de aplicação **91** — foi
aplicada e medida:

| Ente | `L1` sem item 38 | `L1` com item 38 | `L1` publicado | Efeito |
|---|---|---|---|---|
| Belo Horizonte | **20.523.952.374,89** | 19.261.638.788,12 | 20.523.952.374,89 | **afasta** (batia em centavos) |
| João Pessoa | **5.117.875.296,33** | 4.988.347.452,09 | 5.117.875.296,33 | **afasta** (batia em centavos) |
| Recife | 9.939.848.008,46 | 9.471.717.975,89 | 10.390.050.823,18 | afasta |
| Porto Alegre | 12.326.099.796,32 | 10.608.481.111,25 | 8.699.250.917,21 | aproxima (mas o recorte é outro — N4) |
| Cuitegi | 89.752.313,29 | 89.752.313,29 | 50.723.704,91 | neutro: **não há intra no ente** |

`L34` se comporta igual. Volume medido da parcela intra: Recife 4,1% da receita, Porto Alegre 12,9%,
Belo Horizonte 5,7%, João Pessoa 2,2%, Cuitegi 0%.

**Conclusão:** aplicar assim quebra duas linhas que batiam em centavos em dois entes. O item 38 não
se refere a esse conjunto de códigos — ou a MSC dos entes já vem sem a duplicidade que ele evita. A
apuração **não aplica** o item 38 até que o escopo seja definido no normativo, e declara isso no
relatório de cada ente. Isso também **desmente a hipótese** de que o item 38 explicaria a divergência
de Cuitegi: lá não há um centavo de intraorçamentária.

### N7 — conferência cruzada com o RREO: a apuração confere; a publicação é que varia

O RREO Anexo 01 que **o próprio ente** publica no SICONFI é uma terceira fonte, independente do PDF
do BF. Confrontando as três em 2026-09-18:

| Ente | Linha | Apurado (IPC 06 × MSC) | RREO do ente | BF publicado | Leitura |
|---|---|---|---|---|---|
| Cuitegi | `L1` | 89.752.313,29 | **89.752.313,29** | 50.723.704,91 | apuração = RREO; **o BF diverge** |
| Cuitegi | `L34` | 89.779.672,93 | **89.779.672,93** | 44.557.533,10 | apuração = RREO; **o BF diverge** |
| Cuitegi | `L25` | 18.673,00 | **18.673,00** | 387.532,93 | apuração = RREO; **o BF diverge** |
| Porto Alegre | `L1` | 12.326.099.796,32 | **12.326.099.796,32** | 8.699.250.917,21 | apuração = RREO; o BF é da administração direta |
| Porto Alegre | `L34` | 12.061.040.035,33 | **12.061.040.035,33** | 7.943.814.238,89 | idem |
| Porto Alegre | `L25` | 682.738.236,07 | **682.738.236,07** | 564.763.534,49 | idem |
| João Pessoa | `L1`, `L34`, `L25` | — | igual | igual | as três fontes concordam |
| Belo Horizonte | `L1`, `L34`, `L25` | — | igual | igual | as três fontes concordam |
| Recife | `L25` | 74.205.408,29 | **74.205.408,29** | 74.205.408,29 | as três concordam |
| Recife | `L1` | 9.939.848.008,46 | 10.390.050.823,18 | 10.390.050.823,18 | **a apuração é que diverge** — ver abaixo |

Com o **RREO Anexo 07** (Restos a Pagar) a conferência cruzada dobrou: além de `L1`, `L34` e `L25`,
ele cobre `L58` e `L59` (pagamentos de RP no exercício) e as inscrições do exercício anterior em
`L25` e `L26`. Total: **34 confrontos nos 5 entes, 32 batendo em centavos com o RREO**, dos quais
**13** em que é o **BF publicado** que diverge das outras duas fontes e apenas **2** em que a
apuração diverge (`L1` e `L34` de Recife, causa conhecida: registro sem fonte).

**13 de 15 confrontos do Anexo 01 batem em centavos com o RREO do próprio ente.** Isso resolve a divergência de
Cuitegi, que estava sem causa: a apuração está certa e o **BF publicado pelo ente é que não confere
com o RREO que ele mesmo declarou**. É exatamente o cenário que a diretriz do PO previu — o
demonstrativo pode sofrer alteração na publicação.

**A exceção é Recife, e a causa é de composição.** A receita apurada **direto das contas**
(`6.2.1.2 (+)` / `6.2.1.3 (−)`) dá **10.390.050.823,18** — igual ao RREO e ao BF. Mas o IPC 06 compõe
`L1` como `L2 + L3 + L11`, todas filtradas por fonte de recursos, e os 2 registros da conta sintética
`6.2.1.2.0.00.00` **não têm fonte na MSC** (450.202.814,72). O mesmo vale para `L34` (260.723.445,80).
A regra está sendo aplicada com fidelidade; o que falta é declarar o resíduo — e decidir se o total
apurado direto entra como conferência.

## Decisões que a medição sustenta

| # | Recomendação com base no medido |
|---|---|
| **G1** | (a) descartar o 1º dígito, casar 3 por igualdade — **confirmado** |
| **G2** | `L29`–`L32` lidas do **exercício anterior**, mesma matriz e tipo de saldo — **confirmado** |
| **G7** | (a) direção **por conta** no BF — **confirmado** |
| **G9** | manter MSCE, com **tipo de saldo por linha** (abertura, encerramento em `L25`/`L26`, ano−1 em `L29`–`L32`) |
| **G5** | (a) linha sem mapeamento contribui como **parcela inexistente**; sem isso, 6 linhas derrubam `L21`, `L24`, `L33`, `L54`, `L57` e `L66` |
| **G8** | (b) **manter `review_required`** e declarar as 6 linhas como não apuráveis pela MSC — a hipótese (a) foi medida e refutada |

## O que continua aberto

- As 6 linhas sem conta no IPC 06 ficam não apuráveis enquanto a MSC não expuser movimento bruto.
  Em Recife elas respondem por 4,13 bi dos 4,13 bi que faltam em `L33`.
- O desequilíbrio residual de João Pessoa (−972.846.807,25) ainda não tem causa isolada; em Recife
  o mesmo resíduo é de 18.025.391,58.
- `L18`/`L51` em JP: o ente publica 311.639.747,97 de aportes ao RPPS que a MSC classifica dentro de
  `L16`/`L49`. Divergência de classificação do ente, a confirmar.
- Coluna do exercício anterior: **medida** — está nos relatórios de auditoria de cada ente. Quadro
  Anexo: não medido.
- Causa da divergência de Cuitegi: **não isolada**. Não é o item 38 (intra = 0) e não é fonte de
  recursos (as fontes do ente são padrão). A receita apurada é 89.752.313,29 contra 50.723.704,91
  publicados; 92,3 mi dos 97,7 mi brutos são transferências correntes e de capital, o que é normal
  num município desse porte e não confirma dupla contagem por si só.
