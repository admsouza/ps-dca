# Auditoria DFC 2025 — Cuitegi/PB: apurado × publicado

**Data:** 2026-10-27 · **Apuração:** `app/services/dfc/quadro_principal.py` sobre a MSC (MSCE,
abertura, classes 1–6) · **Publicado:** `gabarito-dfc-2025.md`

**Por que este ente importa:** o demonstrativo é **consolidado**, o mesmo recorte da MSC. É a
primeira comparação direta apurado × publicado da DFC — em Porto Alegre o PDF é da administração
direta e a diferença de recorte contamina tudo.

**Placar: 35 conferem, 32 divergem** (67 células da coluna do exercício atual).

## O que confere em centavos

Todo o bloco de **receitas derivadas e originárias**, linha a linha:

| Ln | Linha | Valor |
|---|---|---:|
| L3 | Receita Tributária | 1.962.087,50 |
| L4 | Receita de Contribuições | 5.514.405,94 |
| L5 | Receita Patrimonial | 12.278,74 |
| L6, L7, L8 | Agropecuária, Industrial, Serviços | 0,00 |
| **L9** | **Remuneração das Disponibilidades** | **2.846.486,38** |

Mais: `L19`–`L21`, `L23`, `L24`, `L28`–`L30`, `L31`, `L35` (caixa inicial 19.812.433,77), os
quatro do quadro de juros, `T.L4`, `T.L6` (8.865.268,95), `T.L9`–`T.L11`, `T.L14`, e cinco funções
(`L9` Previdência, `L13` Cultura, `L18` Gestão Ambiental, `L24` Comunicações, `L27` Desporto).

> **`L9` é a confirmação da change `dfc-naturezas-desdobramento`.** Antes da correção de pattern,
> a linha saía 0,00; agora sai 2.846.486,38, **idêntico ao publicado**, num ente de mesmo recorte.
> A correção que o PO mandou fazer está validada contra dado real.

## Divergências que são defeito da apuração

> Das quatro, **uma era defeito** (A1, corrigida). A2 e A4 foram reclassificadas como
> divergência de conceito, com decisão do PO em 2026-10-27 de **manter o IPC 08**. A3
> segue aberta, sem efeito no total.

### A1 — `L25` conta de novo o que `L23` já contou (1.791.501,94)

| Linha | Apurado | Publicado |
|---|---:|---:|
| L23 Aquisição de ativo não circulante | 1.791.501,94 | 1.791.501,94 ✔ |
| L25 Outros desembolsos de investimentos | **1.791.501,94** | **0,00** |
| L22 Desembolsos | **3.583.003,88** | **1.791.501,94** |

`L23` filtra por **elemento** (`4.4.xx.51.xx`, `4.4.xx.52.xx`, `4.4.xx.61.xx`…). `L25` filtra
`4.4.xx.xx.xx` + `4.5.xx.xx.xx` e exclui por **modalidade** (`4.4.36`, `4.4.40`, `4.4.41`…) — a
lista de exclusões **não** cobre os elementos de `L23`. A despesa de Cuitegi é modalidade 90
(aplicação direta), que nenhuma exclusão alcança: entra nas duas linhas.

A transcrição está **fiel ao PDF** (conferido em `knowledge/sources/ipc08/extracted.md`, p. 10):
a dupla contagem está no IPC 08 lido ao pé da letra. O ente resolve publicando `L25` = 0,00.

**Decidido e corrigido em 2026-10-27** (change `dfc-l25-residual`): `L25` é residual — apurada
sobre os registros que não atendem aos filtros de `L23` nem de `L24`, por registro e nunca por
subtração de totais. Depois da correção, `L23`, `L25`, `L22` e `L17` conferem com o publicado.

> **A correção afasta `L34` temporariamente.** `L22` deixa de estar inflado em 1.791.501,94, logo
> o fluxo líquido sobe o mesmo valor e a distância até o `L34` publicado cresce de 2.028.380,25
> para 3.819.882,19. É o esperado ao corrigir um defeito por vez: só com A2 e A4 resolvidos o
> total fecha. O que vale como progresso é o número de **células** que conferem, não o total.

### A2 — Transferências intragovernamentais não são reconhecidas (7.648.660,37)

| Linha | Apurado | Publicado | Dif |
|---|---:|---:|---:|
| T.L2 da União | 35.679.207,25 | 32.030.316,34 | +3.648.890,91 |
| T.L3 de Estados e DF | 4.051.689,61 | 3.523.204,56 | +528.485,05 |
| **T.L5 Intragovernamentais** | **0,00** | **7.648.660,37** | −7.648.660,37 |
| T.L7 TOTAL RECEBIDAS | 48.596.165,81 | 52.067.450,22 | −3.471.284,41 |
| T.L13 Intra concedidas | 3.591.044,75 | 7.647.660,37 | −4.056.615,62 |

**Investigado em 2026-10-27 e reclassificado: não é defeito da apuração, é divergência de
conceito** (`openspec/changes/dfc-intragovernamentais/`).

O IPC 08 chama de intragovernamental a transferência **orçamentária** — modalidade 91 na despesa,
categorias 7 e 8 na receita. O SIAFIC do ente chama a transferência **financeira**,
extraorçamentária: os valores publicados são idênticos aos do BF do mesmo ente ("Transferências
Financeiras Recebidas (II)" 7.648.660,37 e "Concedidas (VII)" 7.647.660,37) e batem em centavos
com as contas `4.5.1.x` e `3.5.1.x` da MSC.

Pelo IPC, a apuração está certa: `T.L13` = 3.591.044,75 é a modalidade 91, e `T.L5` = 0,00 porque
a única receita de categoria 7 do ente é `7.2.1.5.02.11` — contribuição patronal para o RPPS, não
transferência; ela pertence a `L4`, que confere com o publicado.

Trocar as contas pelas de transferência financeira foi **implementado e revertido**: atinge os
valores publicados, mas quebra `P.L10 = T.L7` e `P.L15 = T.L15`, perde a modalidade 91 e não cabe
numa regra só (o filtro de natureza vale para a linha inteira).

**Decisão do PO em 2026-10-27: manter o IPC 08.** A apuração fica como está; a diferença com o
SIAFIC do ente é divergência registrada, não defeito a corrigir.

### A3 — `L32` × `L33`: a amortização cai em "outros" (16.398,17)

| Linha | Apurado | Publicado |
|---|---:|---:|
| L32 Amortização / Refinanciamento | 0,00 | 16.398,17 |
| L33 Outros desembolsos de financiamentos | 16.398,17 | 0,00 |
| L31 Desembolsos | 16.398,17 ✔ | 16.398,17 ✔ |

O total fecha; a classificação não. `L32` exige **função 28 + subfunção 841–844** (D4) e a despesa
de Cuitegi está fora dessas. Não invalida D4 — que foi medida em cinco entes e refutou a leitura
`not_in` —, mas mostra que o filtro de função **exclui** despesa legítima em ente que classifica
fora do padrão. Vale medir se `L32` deve filtrar por natureza apenas.

### A4 — `L13` e `L15`: o ente agrupa o que separamos (3.591.044,75)

Consequência direta de A2: o ente põe a modalidade 91 em "Pessoal e demais despesas" e reserva
"Transferências concedidas" para as financeiras.

`L13` apurado (38.846.090,60) **+** `L15` apurado (3.591.044,75) = **42.437.135,35** = `L13`
publicado, em centavos. O ente põe em "Pessoal e demais despesas" o que nós mandamos para
"Transferências concedidas", e publica em `L15` as intragovernamentais de A2.

O quadro por função repete o padrão: nossas 14 funções somam 38.846.090,60 contra 44.245.035,46
publicados, e a diferença de 5.398.944,86 é da mesma família.

## Divergências que são do ente, não nossas

| O que | Publicado | Observação |
|---|---|---|
| `L36` Caixa final | **0,00** | deveria ser 26.286.597,15 (`L34+L35`) — erro de emissão |
| Total por função | 44.245.035,46 | ≠ `L13` publicado (42.437.135,35); dif 1.807.900,11 |
| `L10` × `T.L7` | 46.552.619,26 × 52.067.450,22 | o ente separa transferências de capital (1.337.455,00) e ainda sobram 4.177.375,96 |
| Quinto quadro | — | "Receitas Derivadas e Originárias" não existe no IPC 08 |
| `L27` | 1.337.455,00 | "Transferências de capital recebidas" em *financiamento*; o IPC 08 não tem essa linha |
| Reserva de Contingência | 0,00 | função 99, fora das 28 do IPC 08 |

## O resíduo de `L16`, agora com o valor do ente

O ente publica `L16` = **4.539.375,80**. Com esse valor informado, a apuração dá
`L34` = 8.502.543,63 contra 6.474.163,38 publicados — **dif 2.028.380,25**, que é a soma líquida
dos defeitos A1 a A4.

O resíduo que faria a apuração fechar era 6.567.756,05 (`docs/evidencia-dfc-apuracao-f1.md`).
A diferença entre ele e o `L16` real do ente é exatamente esse 2.028.380,25 — ou seja: **o
resíduo de `L16` é um termômetro dos defeitos da apuração**, e em Cuitegi ele agora tem um valor
publicado contra o qual se medir.

## Prioridade sugerida

1. ~~**A1**~~ — **corrigido** em 2026-10-27 (`dfc-l25-residual`). `L23`, `L25`, `L22` e `L17`
   passaram a conferir.
2. ~~**A2**~~ — **não é defeito**: divergência de conceito. PO decidiu manter o IPC (2026-10-27).
3. ~~**A4**~~ — a outra face de A2; fecha junto, pela mesma decisão.
4. **A3** — menor valor, só classificação, total já fecha.
