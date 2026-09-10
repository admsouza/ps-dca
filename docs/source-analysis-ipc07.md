# IPC 07 — Balanço Orçamentário: bloqueios e ambiguidades

**Documento:** `docs/referencia/ipc/IPC07 - BO atualizacoes - 20200117.pdf`
**Edição:** 2020-01 (PDF gerado em 2020-01-20) · **17 páginas** · SHA-256 `51b9eeddcfb523ae…`
**Data desta análise:** 2026-08-27
**Motivo:** o IPC07 é o primeiro a ser implementado. Este documento esgota os pontos bloqueantes
e as ambiguidades **desta peça**, separando o que já está resolvido do que precisa de decisão.

Complementa [`source-analysis.md`](source-analysis.md) (visão dos 5 IPCs). Onde houver
divergência, este documento prevalece para o IPC07 — ele foi produzido com reconstrução
geométrica da matriz, não com leitura linear.

---

## 1. Escopo medido

| Quadro | Págs. da regra | Linhas | Colunas de valor |
|---|---|---|---|
| Quadro Principal — receitas | 8–9 | 30 (`L1`–`L30`) | 4 |
| Quadro Principal — despesas | 10–11 | 21 (`L31`–`L51`) | 6 |
| Execução de RP Não Processados | 12 | 9 (`L1`–`L9`) | 6 |
| Execução de RP Processados | 13 | 9 (`L1`–`L9`) | 5 |

**69 regras de linha.** Estrutura de publicação nas pp. 14–17.

### 1.1 Matriz reconstruída por geometria

As páginas de regra são **paisagem rotacionada 90°**: no espaço do PDF, a linha da tabela é uma
banda em `x` e a coluna é uma banda em `y`. Extração linear de texto embaralha a associação
célula→coluna; a reconstrução por coordenadas resolve as 69 linhas sem ambiguidade.

Bandas de coluna do Quadro Principal (receitas, p. 8–9), em `y`:

| Banda `y` | Coluna |
|---|---|
| ~781 | Linha (`Ln`) |
| ~594–730 | RECEITAS ORÇAMENTÁRIAS (descrição) |
| ~480–560 | Critérios — **Natureza de Receita** (e as fórmulas de agregação) |
| ~370–440 | Critérios — **Exclusões** |
| ~300–320 | Contas — Previsão Inicial (a) |
| ~230–250 | Contas — Previsão Atualizada (b) |
| ~150–170 | Contas — Receitas Realizadas (c) |
| ~80–90 | SALDO (d) = (c − b) |

Despesas (p. 10), em `y`: ND/Função ~528–590 · **Exclusões ~450–500** · Dotação Inicial (e)
~392–412 · Dotação Atualizada (f) ~323–345 · Empenhadas (g) ~254–277 · Liquidadas (h) ~188–210 ·
Pagas (i) ~124–146 · Saldo (j) ~72–101.

**Consequências verificadas:**

- A coluna "Critérios (Informação Complementar)" carrega **duas coisas**: os filtros de linha
  (natureza / ND / função) **e** as fórmulas de agregação (`(L2 + L3 + …)`). Não são colunas
  separadas.
- `L38 Amortização da Dívida` tem **dois blocos de exclusão** na mesma célula (`ND: 46.xx.76` +
  funções, e `ND: 46.xx.77` + funções). Ambos estão na banda de Exclusões — confirmado.
- `L11 Operações de Crédito` tem **8 códigos de exclusão** em 4 pares, não 4.
- `L19`–`L23` põem o código na banda **Natureza**, não em Exclusões.
- `L25 Déficit`: a fórmula `(L48 - L24)` e a condição "Somente quando o resultado for deficitário"
  estão **na mesma célula** da banda Natureza.

## 2. Conferência dos códigos contra as tabelas oficiais da STN

Universo: `PCASP.md` (6.119 contas, todas folha/ativa) · `natureza-receita.md` (4.504 naturezas) ·
`natureza_despesa.md` (172 NDs) · `funcao-subfuncao.md` (117 pares).

Normalização usada: dígitos, `x` como coringa, zeros à direita descartados; casamento por prefixo.

| Domínio | Códigos distintos no IPC07 | Com correspondência | Sem correspondência |
|---|---|---|---|
| Contas contábeis / padrões de conta (PCASP) | 41 | **32 atuais** | **9 históricos** |
| Naturezas de receita | 27 | 14 | **13** |
| Naturezas de despesa | 15 | 2 | **13** |
| Função / subfunção | 7 | **7** | 0 |

Função e subfunção fecham 100%: `28.841`, `28.842`, `28.843`, `28.844`, `28.846`, `99.999`,
`99.997` — todos os 7 pares existem.

---

## 3. Bloqueantes — precisam de decisão

### B1 — `5.3.1.3.0.00.00` não existe no PCASP, e o quadro simétrico não tem o termo

**Onde:** p. 12, Quadro de RP Não Processados, coluna "Inscritos — Em Exercícios Anteriores (a)".

**Texto do PDF:** `5.3.1.2.0.00.00 + 5.3.1.3.0.00.00 + 5.3.1.6.0.00.00 (-) 6.3.1.6.0.00.00`

**Medido:** o grupo `5.3.1` do PCASP tem exatamente 4 contas — e nenhuma é `5.3.1.3`:

```
5.3.1.1.0.00.00  RP NÃO PROCESSADOS INSCRITOS
5.3.1.2.0.00.00  RP NÃO PROCESSADOS - EXERCÍCIOS ANTERIORES
5.3.1.6.0.00.00  RP NÃO PROCESSADOS RECEBIDOS POR TRANSFERÊNCIA
5.3.1.7.0.00.00  RP NÃO PROCESSADOS - INSCRIÇÃO NO EXERCÍCIO
```

**Agravante:** o quadro **simétrico** de RP Processados (p. 13) tem **três** termos na mesma
coluna, sem contrapartida de `5.3.2.3`:
`5.3.2.2.0.00.00 + 5.3.2.6.0.00.00 (-) 6.3.2.6.0.00.00`. O grupo `5.3.2` também tem 4 contas
(`5.3.2.1`, `5.3.2.2`, `5.3.2.6`, `5.3.2.7`) e nenhuma `5.3.2.3`.

**Duas leituras possíveis, nenhuma decidível pelo documento:**

1. `5.3.1.3` **existiu no PCASP 2019** (a edição que o IPC07 declara usar) e foi extinta depois. O
   `PCASP.md` do repositório é atual — traz contas de PROPAG / LC 212/2025.
2. O termo é **espúrio**, introduzido na revisão de 2020, e a fórmula correta tem 3 termos, igual
   à do quadro de RP Processados.

**Impacto:** a coluna (a) do quadro de RPNP — logo **as 9 linhas** desse quadro.

**Decisão necessária:** confirmar contra o PCASP 2019, ou aceitar a fórmula de 3 termos por
simetria (decisão registrada), ou manter as 9 linhas `review_required`.

**Decisão do PO (2026-08-27) — SUPERADA:** manter a leitura da família/prefixo `531` e preservar
`5.3.1.3.0.00.00` na fórmula do IPC07. A implementação SHALL conter comentário adjacente ao
tratamento informando que essa conta existia no contexto do PCASP 2019 e foi descontinuada em
edições posteriores. Não remover o termo por comparação com o PCASP atual.

**Decisão do PO (2026-09-04) — vigente:** `5.3.1.3.0.00.00` foi descontinuada e **o que ela
guardava está em `5.3.1.2.0.00.00`**, que já é o primeiro termo da mesma fórmula. O termo é
redundante e **sai da regra**: a coluna passa a declarar 3 contas,
`5.3.1.2 + 5.3.1.6 (-) 6.3.1.6` — simétrica à do quadro de RP Processados.

Por que não substituir `5313` por `5312`: a apuração soma por conta declarada e **não deduplica**
(`app/domain/bo/saldo.py`), então declarar `5.3.1.2` duas vezes dobraria o valor — R$ 67.299.876,72
a mais na coluna (a) em João Pessoa 2025.

Medições que sustentam (`docs/evidencia-c6-c7.md`):

- `5313` e `5323` em **zero** de ~185.000 registros de classe 5 (`MSCC`, `ending_balance`, 12/2025)
  em 9 entes grandes — SP, MG, RJ, BA, PR, RS, CE, PE e João Pessoa.
- O grupo `5.3.2` não tem `5.3.2.3`, e a fórmula de RP Processados sempre teve 3 termos.
- `5.3.1` e `5.3.2` são Devedora em 8 de 8; `6.3.1`/`6.3.2` Credora em 16 de 16.

Efeito medido na apuração: **nenhum**. Conta declarada sem escrituração já contribuía zero, e a
regressão contra JP 2025 saiu com 0 células divergentes em 69 linhas. O que muda é que a presença
de escrituração em `5.3.1.3` deixa de apagar a célula das 9 linhas do quadro.

Consequência: a pendência **C6 é encerrada sem alteração de schema** — `natureza_saldo` perdeu o
único caso de uso e foi removida do domínio, junto com `_direcao_da_conta`, que nunca era chamada.
Change: `ipc07-b1-remocao-termo-5313`.

---

### B2 — 13 naturezas de receita intraorçamentárias não existem na tabela do repositório

**Medido em `natureza-receita.md`:** categorias econômicas presentes —
`1` (4.269 códigos) · `2` (234) · `9` (1). **Categorias `7` e `8` têm zero códigos.**

Após a reclassificação de B3 como conta PCASP, o IPC07 ainda usa 13 naturezas intra das categorias
`7` e `8` que não são validáveis:

```
7100.00.00  7200.00.00  7300.00.00  7400.00.00  7500.00.00  7600.00.00  7700.00.00  7900.00.00
8100.00.00  8200.00.00  8300.00.00  8400.00.00  8900.00.00
```

**Impacto:** **13 linhas** do Quadro Principal citam natureza de categoria 7 ou 8 — `L2`–`L9` e
`L11`–`L15`. Os padrões `8111`, `8118`, `8121` e `8128` de B3 são contas PCASP, não naturezas.

**Observação importante:** isso **não** torna a regra ambígua. O IPC07 é explícito e o par
"principal + intra" é sistemático em todas as linhas. O que fica bloqueado é a **validação
automática** (D13 do design), não a transcrição da regra.

**Decisão necessária:** trazer o Ementário completo da receita (com as categorias 7 e 8) para
`docs/contas-stn/`, ou declarar exceção documentada de que categorias 7/8 não são validáveis com a
tabela atual.

---

### B3 — códigos de refinanciamento reclassificados como padrões de conta PCASP

**Onde:** p. 9, `L19` Mobiliária, `L20` Contratual (internas), `L22` Mobiliária, `L23` Contratual
(externas) — e as 8 exclusões de `L11`.

**O que o PDF traz** (as duas grafias são o **mesmo código** em dígitos — ver R6):

| Linha | Grafia em `L11` (exclusões) | Grafia em `L19`–`L23` | Dígitos |
|---|---|---|---|
| `L19` | `2111.00.20` | `2111.00.2.0` | `2111002` |
| `L20` | `2118.01.60` | `2118.01.6.0` | `2118016` |
| `L22` | `2121.00.20` | `2121.00.2.0` | `2121002` |
| `L23` | `2128.01.60` | `2128.01.6.0` | `2128016` |

**Medição original no domínio incorreto:** nenhum casava em `natureza-receita.md`. O que existe
nessa tabela é:

- `2.1.1.1.*` — 6 códigos: `01.0.1`, `01.0.3` (mercado interno, **exceto** refinanciamento),
  `02.0.1`, `02.0.3` (**Refinanciamento da Dívida Pública**), `03.0.1`, `03.0.3` (TDA).
- `2.1.2.1.*` — 4 códigos: `01.0.1`, `01.0.3`, `02.0.1`, `02.0.3` (**Refinanciamento**).
- `2.1.1.8` e `2.1.2.8` — **não existem**. Sob `2.1.1` os desdobramentos de 4º nível são
  `1` (mobiliária), `2` (contratual), `3` (empréstimos compulsórios), `9` (outras).

**Candidatos, com a base do nome — anotados, não aplicados:**

| Linha | Rótulo do IPC07 | Candidato | Nome na tabela oficial |
|---|---|---|---|
| `L19` | Mobiliária (interna) | `2.1.1.1.02` | "Títulos de Responsabilidade do Tesouro Nacional - **Refinanciamento da Dívida Pública**" |
| `L22` | Mobiliária (externa) | `2.1.2.1.02` | idem, mercado externo |
| `L20` | Contratual (interna) | `2.1.1.2.55` | "Operações de Crédito Internas para **Refinanciamento da Dívida Contratual**" |
| `L23` | Contratual (externa) | `2.1.2.2.55` | "Operações de Crédito Externas para **Refinanciamento da Dívida Contratual**" |

Para `L19`/`L22` o candidato é forte: o `2` de `2111.00.2.0` e o `02` de `2111.02.0.x` parecem a
**mesma informação em posição trocada** — DD2 = 02 = Refinanciamento. Para `L20`/`L23` o candidato
é apenas por nome: `2118`/`2128` não se assemelha a `2112.55`/`2122.55` em nenhuma leitura.

Vale a mesma hipótese de vigência de B1: o IPC07 declara PCASP 2019, e `2.1.1.8` pode ter existido
no ementário daquele exercício.

**Impacto:** 5 linhas — `L11`, `L19`, `L20`, `L22`, `L23`. Como `L18 = (L19+L20)`,
`L21 = (L22+L23)`, `L17 = (L18+L21)` e `L24 = (L16+L17)`, o erro propaga para `L24`, `L25`, `L26`
e, via `L25`, para o resultado do exercício.

**Decisão do PO (2026-08-27) — resolvido:** os oito padrões `2111`, `8111`, `2118`, `8118`,
`2121`, `8121`, `2128` e `8128` são **contas PCASP**, não naturezas de receita. As grafias das
exclusões de `L11` e dos critérios de `L19`–`L23` normalizam para os mesmos oito padrões PCASP.
Os candidatos de natureza de receita levantados acima ficam preservados apenas como histórico da
investigação e **não serão aplicados**. A ausência no PCASP atual é tratada como diferença de
vigência em relação ao PCASP 2019, sem `review_required`.

---

### B4 — `natureza_despesa.md` cobre apenas o grupo 3.1

**Medido:** 172 códigos, **todos** com `C.G = 3.1` (o único fora do padrão, `3.1.90.4600`, é erro
de grafia da própria tabela). Nenhum código dos grupos 3.2, 3.3, 4.4, 4.5, 4.6 ou 9.9.

O IPC07 usa 7 grupos de ND. **Seis não são validáveis:**

```
3.2.00.00.00  3.3.00.00.00  4.4.00.00.00  4.5.00.00.00  4.6.00.00.00  9.9.00.00.00
46.xx.76      46.xx.77
```

**Impacto:** 17 linhas — Quadro Principal `L33`, `L34`, `L36`, `L37`, `L38`, `L39`, `L51`; RPNP
`L3`, `L4`, `L6`, `L7`, `L8`; RPP `L3`, `L4`, `L6`, `L7`, `L8`. (`L32` e as duas linhas de
`ND: 3.1` dos quadros de RP são as únicas validáveis.)

**Ambiguidade adicional de grafia, dentro da mesma célula:** `L38` usa **duas convenções** para
ND ao mesmo tempo — `4.6.00.00.00` (C.G.M.E.SE, 5 grupos) no critério e `46.xx.76` (CG.M.E,
3 grupos) na exclusão. Mesmo domínio, mesma célula, notações diferentes.

**Decisão necessária:** trazer a tabela completa de natureza de despesa, ou declarar exceção
documentada.

---

### B5 — `L29` e `L30` põem **conta contábil** na coluna de natureza

**Onde:** p. 9.

```
L29  Superávit Financeiro          →  "Conta contábil: 5.2.2.1.3.01.00"
L30  Reabertura de Créditos Adicionais →  "Contas contábeis: 5.2.2.1.2.02.02; 5.2.2.1.2.03.02;
                                            5.2.2.1.2.02.03; 5.2.2.1.2.03.03"
```

Confirmado por geometria: esses valores estão na banda **Natureza de Receita** (`y` ≈ 500–536), a
mesma que em `L2` traz `1100.00.00`. As 5 contas existem no PCASP.

**O problema:** o IPC07 item 23 define que a coluna fornece as contas e a linha aplica o filtro.
Aqui a linha traz **conta**, e as contas da coluna são `5.2.1.1` / `5.2.1.2` / `6.2.1.2` /
`6.2.1.3`. A interseção é **vazia** — `5.2.2.x` não é `5.2.1.x`.

Logo a conta da linha só pode **substituir** a da coluna. Essa semântica de override **não está
declarada em nenhum lugar do documento**.

**Impacto:** 2 linhas (`L29`, `L30`). O mesmo padrão reaparece no IPC04 e no IPC06, então a
decisão é estrutural, não local.

**Decisão necessária:** aprovar a semântica "conta declarada na linha substitui a conta da coluna"
como decisão registrada, ou manter `review_required`.

**Decisão do PO (2026-08-27) — resolvido:** a conta declarada na linha substitui as contas da
coluna exclusivamente em `L29` e `L30`. O override não é uma regra geral do IPC07 e SHALL ser
rejeitado em qualquer outro `rule_id`.

---

### B6 — quais colunas `L27`–`L30` e `L51` realmente têm?

**Divergência entre as duas seções do próprio IPC07:**

| Linha | REGRAS (p. 9 / 11) | ESTRUTURA (p. 15) |
|---|---|---|
| `L27` | "Saldos de Exercícios Anteriores" | "Saldos de Exercícios Anteriores **(Utilizados Para Créditos Adicionais)**" — 4 colunas preenchidas |
| `L28`, `L29`, `L30` | critérios declarados | aparecem **sem** marcação de coluna |
| `L51` Reserva do RPPS | `ND 9.9.00.00.00`, `Função 99.997` | aparece **depois** de `TOTAL (XV)`, **sem** colunas |

`L27` é `(L28 + L29 + L30)`. Se `L28`–`L30` não têm coluna, `L27` não pode ter as 4 que a
ESTRUTURA mostra.

**Decisão do PO — 2026-09-03:** a seção REGRAS prevalece. `L27`–`L30` têm as **4** colunas de
receita, o que mantém `L27 = L28 + L29 + L30` coerente. `L51` **não tem** coluna de valor:
permanece como linha de filtro e rótulo (`ND 9.9.00.00.00`, Função `99.997`), fora do
`TOTAL (XV)`. Consequência: `columns` pode ser lista vazia, e nenhuma das 5 linhas fica
`review_required`.

**Decisão do PO — 2026-09-10 (restringe B6 só em `L51`):** apurar `L51` **como a `L39`**,
respeitando o mapeamento de despesa (`columns: *id003`). Filtros da REGRAS permanecem
(`ND 9.9.00.00.00`, função `99`, subfunção `997`). `L51` **continua fora** do `TOTAL (XV)`
(`L50 = L48 + L49`). `L27`–`L30` não mudam.

---

## 4. Ambiguidades resolvidas por evidência interna do próprio IPC07

Nenhuma destas precisa de decisão: o PDF se contradiz e uma das leituras é a coerente. Em todas,
o `literal` original fica em `evidence`.

### R1 — `L-40` → `L40`
p. 10. Hífen espúrio da revisão de 2020. É o **único** rótulo hifenizado das 69 linhas.

### R2 — `Despesas Correntes (-VIII)` → `(VIII)`
p. 10 grafa `(-VIII)`. **A ESTRUTURA, p. 15, grafa `Despesas Correntes (VIII)`.** Mesmo documento.

### R3 — `SUBTOTAL DAS DESPESAS (XI) = (VII + IX + X)` → `(VIII + IX + X)`
p. 10 grafa `VII`. **A ESTRUTURA, p. 15, grafa `SUBTOTAL DAS DESPESAS (XI) =(VIII + IX + X)`.**
`VII` é o TOTAL das **receitas** (`L26`, p. 14) — não poderia entrar num subtotal de despesa.

### R4 — `(L31 + L35 + L39 + -)` → `(L31 + L35 + L39)`
p. 10. O `+ -` final é artefato. Confirmado por R3: `XI = VIII + IX + X` são exatamente três
termos — `L31` (VIII), `L35` (IX), `L39` (X). `L51` não entra: a ESTRUTURA o coloca depois de
`TOTAL (XV)`.

### R5 — `L47`: `28.842, - 28.844 e 28.846` → `28.842, 28.844 e 28.846`
p. 11. Confirmado por dois caminhos: simetria com `L44` (`28.841 e 28.843`) e a exclusão de `L38`,
que remove de `46.xx.77` exatamente `{841, 842, 843, 844, 846}` — a união de `L44` e `L47`.

### R6 — grafia `2111.00.20` (L11) vs `2111.00.2.0` (L19): **mesmo código**
Em dígitos, ambas são `2111002`. Não há divergência entre as duas células; o código é o mesmo (e
ambas falham igual — ver B3).

### R7 — coerência das exclusões de `L38` com `L41`–`L47`
`L38` exclui `46.xx.76 → {841,842,843,844}` e `46.xx.77 → {841,842,843,844,846}`.
As linhas de refinanciamento capturam: `L43` `76/{841,843}`, `L46` `76/{842,844}`,
`L44` `77/{841,843}`, `L47` `77/{842,844,846}`. **União idêntica.** Sem lacuna, sem duplicidade.

### R8 — associação célula→coluna em todas as 69 linhas
Resolvida por geometria (§1.1). Não resta nenhuma célula indeterminada no IPC07.

### R9 — `L25` e `L49` cruzam os blocos de receita e despesa
`L25 Déficit = (L48 - L24)` está no bloco de receitas e referencia `L48` (despesas);
`L49 Superávit = (L24 - L48)` faz o inverso. Não é ambiguidade — mas exige que o modelo permita
referência **entre grupos** do mesmo quadro. Sem ciclo: `L24 = (L16+L17)` e `L48 = (L40+L41)` não
dependem de `L25` nem de `L49`.

### R10 — sobreposição de contas entre colunas do RPNP
p. 12: "Liquidados (c)" = `6.3.1.3 + 6.3.1.4`; "Pagos (d)" = `6.3.1.4`. A sobreposição é
intencional — pago é subconjunto de liquidado — e não afeta o saldo, que é
`f = (a + b − d − e)`, sem `c`.

### R11 — rótulo `L27` divergente entre as seções
"Saldos de Exercícios Anteriores" (p. 9) vs "… (Utilizados Para Créditos Adicionais)" (p. 15).
Rótulo de apresentação; não altera critério. Registrar os dois.

---

## 5. Consolidado

### 5.1 Bloqueios por natureza

| Tipo | Itens | Bloqueia a **regra**? | Bloqueia a **validação**? |
|---|---|---|---|
| Decisão registrada do PO | B1, B3, B5, B6 | não (resolvido) | não |
| Lacuna de tabela de domínio (exceção declarada pelo PO) | B2, B4 | não | não — reportada como exceção |
| Erro de digitação do PDF | R1–R5 | não (resolvido internamente) | não |

### 5.2 Linhas afetadas, das 69

| Cenário | `review_required` | Elegíveis a `validated` |
|---|---|---|
| Com todas as decisões do PO (B1, B3, B5, B6) | **0** | 69 |
| Se as lacunas de domínio (B2, B4) fossem tratadas como erro | **30** | 39 |

As decisões de B1, B3 e B5 retiraram 14 linhas do estado `review_required`; a de B6 retirou as
5 restantes (`L27`–`L30` e `L51`).

### 5.3 O que decidir, em ordem de impacto

Nada. B1, B3 e B5 foram decididos pelo PO em 2026-08-27; B6, B2 e B4 em 2026-09-03. B2 e B4
ficaram como **exceção declarada**: as tabelas de `docs/contas-stn/` não são completadas nesta
change, e o validador distingue exceção de erro.

### 5.4 Caminho que não depende de decisão

As **69 linhas** podem ser transcritas desde já, todas cobertas por decisão explícita do PO
(B1, B3, B5, B6) ou por evidência interna (R1–R11).

As lacunas B2 e B4 afetam **30 linhas distintas** apenas na validação de domínio; a regra em si já
está determinada. Como o PO decidiu tratá-las como exceção declarada, as 69 linhas ficam
elegíveis a `validated`.

O inventário passa a ter 41 contas/padrões PCASP: 32 conferidos na tabela atual e 9 exceções
históricas decididas pelo PO (B1: 1; B3: 8). Todos os 7 pares função/subfunção seguem conferidos.


---

## B6 restringida em 2026-09-04 — `L29` não tem previsão inicial

A decisão B6 de 2026-09-03 mandou `L27` a `L30` declararem as quatro colunas de receita. Medição em
25 entes (`docs/evidencia-c6-c7.md`): **zero** publicam `PREVISÃO INICIAL` para
`SuperavitFinanceiro` no `RREO-Anexo 01` — nem os que publicam todas as outras colunas.

Um superávit financeiro é apurado sobre o exercício **fechado**, logo não existe no orçamento
originário: entra como crédito adicional, na previsão atualizada.

**Restrição:** `L29` declara três colunas — `previsao_atualizada`, `receitas_realizadas` e `saldo`.
O restante de B6 segue valendo (`L27`, `L28` e `L30` com as quatro), e **B5** — a conta da linha em
`L29` — não é afetada. A decisão de 2026-09-03 fica registrada, não apagada.

Efeito medido em João Pessoa 2025: `L27.previsao_inicial` passou de 482.338.332,64 para
**12.000.000,00**, batendo em centavos com o STN.

## C5 fechada em 2026-09-04 — as linhas cruzadas, e a assimetria

`L25`, `L26`, `L49` e `L50` cruzam receita e despesa. O IPC 07 não diz em qual coluna são
apresentadas; o publicado do STN diz, e foi medido em JP (superavitário) e nos 12 estados
deficitários de 2025 (`docs/evidencia-c5-deficit-superavit.md`).

| Linha | Colunas | Fórmula por célula |
|---|---|---|
| `L25` Déficit | `receitas_realizadas` (1) | `L48.empenhadas − L24.receitas_realizadas` |
| `L26` TOTAL (VII) | previsão inicial, atualizada, realizadas (3) | `L24 + L25` |
| `L49` Superávit | `empenhadas`, `liquidadas`, `pagas` (3) | `L24.receitas_realizadas − L48.<coluna>` |
| `L50` TOTAL (XV) | 5 de despesa, sem `saldo_dotacao` | `L48 + L49` |

**Não são simétricas:** cada bloco recebe tantas células de ajuste quantas colunas de realização
tem — a receita tem uma, a despesa tem três.

Três achados que a medição obrigou, e que o documento não continha:

1. **A fórmula é cruzada em coluna.** `L49.empenhadas` lê `L24.receitas_realizadas`. A referência
   passou a poder nomear a coluna lida.
2. **Célula suprimida pela condição contribui zero, e se apresenta em branco.** Em ente
   deficitário o STN deixa `Superavit` em branco e **publica** `TotalDespesasComSuperavit` igual a
   `TotalDespesas` (SP e GO, exatos).
3. **A condição é decidida uma vez, por linha, não célula a célula.** São Paulo 2025 tem déficit
   contra a empenhada e superávit contra liquidadas e pagas — e o STN deixa `Superavit` em branco
   nas três. Decidir por célula publicaria duas células que o STN não publica. A regra declara em
   qual coluna a condição é avaliada (`calculation.condition.column`).

## Observação aberta — `L30` em Goiás, R$ 963.024,00

Medido no aceite de C5: em GO 2025 o nosso `L27.previsao_atualizada` dá 9.690.185.679,58 contra
9.689.222.655,58 do STN. A diferença é **exatamente** `L30` Reabertura de Créditos Adicionais
(963.024,00), linha que GO **não publica** no anexo, embora a MSC do ente tenha o valor. `L29` bate
em centavos nos três entes conferidos.

É da mesma família da ressalva da Paraíba, que não publicou `Deficit` tendo empenhada acima da
receita: o ente publica menos linhas do que a sua MSC sustenta. **Não é defeito de apuração e não
foi tratado nesta change** — fica registrado para o PO decidir se cabe conferência por ente.
