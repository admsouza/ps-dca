# Análise das fontes normativas — IPC 04 a 08

**Fase:** 1 (descoberta) · **Data:** 2026-08-27
**Escopo:** os 5 PDFs em `docs/referencia/ipc/`. Nenhuma regra foi criada nesta fase — apenas
levantamento estrutural para dimensionar o modelo canônico.

Ferramenta usada: **PyMuPDF 1.28** (`page.get_text()`), em venv temporária fora do repo.
Justificativa em [Extração](#7-extração).

---

## 1. Inventário dos documentos

| Código | Arquivo | Demonstrativo | Págs. | Edição (metadado do PDF) | SHA-256 (16 primeiros) |
|---|---|---|---|---|---|
| IPC04 | `IPC04 - BP atualizacao - 20200117.pdf` | Balanço Patrimonial (BP) | 18 | 2020-01-20 | `9967ed1e6e266c62` |
| IPC05 | `IPC05 - DVP atualizacao - 20200117.pdf` | Demonstração das Variações Patrimoniais (DVP) | 16 | 2020-01-20 | `7440efcc96bbdb80` |
| IPC06 | `IPC06 - Balanço Financeiro_2024- 2.pdf` | Balanço Financeiro (BF) | 19 | 2024-06-28 | `e663ffe5ee0376fd` |
| IPC07 | `IPC07 - BO atualizacoes - 20200117.pdf` | Balanço Orçamentário (BO) | 17 | 2020-01-20 | `51b9eeddcfb523ae` |
| IPC08 | `IPC08 - DFC atualizacoes final - 20200116.pdf` | Demonstração dos Fluxos de Caixa (DFC) | 21 | 2020-01-20 | `fb04f03c2015ec61` |

**Duas edições distintas convivem:** IPC04/05/07/08 são de **janeiro/2020** e declaram
basear-se no **PCASP 2019**; o IPC06 é de **junho/2024** e traz estrutura já reorganizada por
vinculação de recursos (Educação, Saúde, RPPS...). Consequência direta: o modelo canônico
**precisa** de versionamento por documento desde o primeiro dia (§6.3).

## 2. Anatomia comum dos 5 documentos

Todos seguem o mesmo esqueleto:

```text
PREFÁCIO · OBJETIVO · ALCANCE          -> texto institucional, sem regra executável
ASPECTOS GERAIS                        -> texto institucional
INSTRUÇÕES PARA PREENCHIMENTO          -> regras gerais em itens numerados (valem para o demonstrativo inteiro)
REGRAS DE PREENCHIMENTO                -> matrizes linha x coluna -> contas PCASP (o núcleo executável)
ESTRUTURA DO <demonstrativo>           -> layout de publicação (rótulos, ordem, colunas visuais)
```

Isso dá **três** naturezas de conteúdo, que o modelo precisa distinguir:

| Natureza | Onde | Tratamento canônico |
|---|---|---|
| Regra de composição de linha | seção "REGRAS DE PREENCHIMENTO" | vira regra YAML executável |
| Regra geral / pressuposto | itens numerados de "INSTRUÇÕES" | vira **policy** referenciada por várias regras (ex.: exclusão de intra) |
| Layout de publicação | seção "ESTRUTURA" | vira metadado de apresentação (ordem, rótulo), não critério |

> O IPC06 não tem "REGRAS DE PREENCHIMENTO" no sumário: as matrizes estão dentro de "INSTRUÇÕES
> PARA PREENCHIMENTO" (o título aparece no corpo, na p. 10, mas não no sumário). A
> rastreabilidade tem de ser por **página**, nunca por posição no sumário.

## 3. Quadros e linhas por documento (contagem medida)

Contagem obtida por varredura dos rótulos `L<n>` nas seções de regra — sem lacunas em nenhum
quadro (todo `L1..Lmax` está presente).

| Doc | Quadro | Linhas | Págs. da regra |
|---|---|---|---|
| IPC04 | Quadro Principal | 40 (`L1..L40`) | 8–10 |
| IPC04 | Ativos e Passivos Financeiros e Permanentes | 7 (`L1..L7`) | 11 |
| IPC04 | Contas de Compensação | 10 (`L1..L10`) | 12 |
| IPC04 | Superávit / Déficit Financeiro | **paramétrico** (1 linha por fonte + Total) | 13 |
| IPC05 | Quadro Principal | 19 (`L1..L19`) | 8–9 |
| IPC05 | Quadros Anexos (Notas I..XVI) | 16 notas, **não normativas** | 11–16 |
| IPC06 | Quadro Principal (Ingressos + Dispêndios) | 66 (`L1..L66`) | 10–13 |
| IPC06 | Quadro Anexo (receita por vinculação) | 14 (`L1..L14`) | 14–15 |
| IPC07 | Quadro Principal | 51 (`L1..L51`) | 8–11 |
| IPC07 | Execução de RP Não Processados | 9 (`L1..L9`) | 12 |
| IPC07 | Execução de RP Processados | 9 (`L1..L9`) | 13 |
| IPC08 | Quadro Principal | 36 (`L1..L36`) | 7–11 |
| IPC08 | Transferências Recebidas e Concedidas | 15 (`L1..L15`) | 12–14 |
| IPC08 | Desembolsos de Pessoal e Demais Despesas por Função | 29 (`L1..L29`) | 15 |
| IPC08 | Juros e Encargos da Dívida | 4 (`L1..L4`) | 16 |

**Total de linhas com regra explícita: 309**, em **15 quadros** de 5 demonstrativos.
Estimativa de regras YAML: **309 regras de linha** + 1 regra paramétrica (BP superávit/déficit
por fonte). Não há multiplicação por coluna: uma regra de linha carrega todas as suas colunas
(§5).

Os 16 "Quadros Anexos" do IPC05 **não geram regra**: o item 21 do próprio IPC05 diz que são
"sugestões" e que "não é objetivo esgotar as possibilidades de detalhamento". Transformá-los em
regra executável seria inventar norma.

## 4. Tipos de regra encontrados

Catálogo fechado a partir da leitura dos 5 documentos. Cada tipo é uma exigência concreta sobre
o modelo canônico.

### 4.1 Soma de contas PCASP por prefixo
Presente em todos. Ex.: IPC04 `L3 Caixa e Equivalentes de Caixa = 1.1.1.0.0.00.00`.
O código é sempre um **prefixo mascarado** (`0` à direita = "qualquer"), não um código exato.

### 4.2 Exclusão de contas
Coluna "Exclusões" em IPC04, IPC05, IPC07, IPC08. Ex.: IPC04 `L4` soma
`1.1.2.0.0.00.00; 1.1.3.0.0.00.00` e exclui 9 contas intra (5º nível = 2).

### 4.3 Agregação de outras linhas (dependência)
Ex.: IPC07 `L1 = (L2+L3+L4+L5+L6+L7+L8+L9)`; IPC06 `L33 = (L1+L15+L21+L24+L29)`.
Quase sempre soma; **subtração em quatro casos**: IPC04 `L7 Saldo Patrimonial = (L1 - L4)`,
IPC05 `L19 = (L1 - L9)`, IPC08 `L1 = (L2 - L12)`, `L17 = (L18 - L22)` (e `L26 = (L27 - L31)`).

### 4.4 Filtro por natureza de receita
IPC07 (`1100.00.00; 7100.00.00`) e IPC08 (`1.1.xx.xx.xx`, `7.1.xx.xx.xx`).
**Duas grafias para o mesmo conceito** — precisa normalização com máscara, não string literal.

### 4.5 Filtro por natureza de despesa
IPC07 principal (`ND: 3.1.00.00.00`), IPC07 RP (`ND: 3.1.00.00`), IPC08 (`3.1.71.xx.xx`) —
**três comprimentos distintos** de código ND no mesmo corpus.

### 4.6 Filtro por função / subfunção
IPC07: `ND: 46.xx.76, Função: 28.841, 28.842, 28.843, 28.844` (função e subfunção **concatenadas**).
IPC08: `Função: 28` + `Subfunção: 841, 842, 843 e 844` (**separadas**).
IPC08 quadro "por Função": `Função 01`..`Função 29`.

### 4.7 Filtro por atributo da conta (F/P)
Exclusivo do IPC04, Quadro dos Ativos e Passivos Financeiros e Permanentes:
`L2 = Somatório das contas escrituráveis de ativo com o atributo (F), excluídas as contas intra`.
Não é filtro por código — é filtro por **metadado do plano de contas**.

### 4.8 Filtro por fonte / destinação de recurso
IPC04 Quadro do Superávit/Déficit: `8.2.1.1.1.00.00 (saldo por fonte/destinação de recurso)`.
IPC06: `<nas fontes aplicáveis>` em 24 das 66 linhas do Quadro Principal, e em todas as 14 do
Quadro Anexo (ver §6.1 P4).

### 4.9 Filtro por movimento (natureza do saldo)
IPC06 `L27` (`<movimento credor>`) e `L60` (`<movimento devedor>`) sobre as **mesmas** contas
`2.1.8.8.0.00.00 + 2.2.8.8.0.00.00`. O que distingue ingresso de dispêndio é o lado do
lançamento, não a conta.

### 4.10 Momento do saldo (inicial / final)
IPC06 `L30..L32` (saldo inicial) e `L63..L65` (saldo final); IPC08 `L35` (saldo inicial),
`L36` (saldo final). O modelo precisa de um seletor de momento além do de conta.

### 4.11 Restrição de saldo remanescente
IPC04 Quadro das Contas de Compensação: `8.1.1.1.0.00.00 (somente saldo a executar)` em 8 linhas.
O IPC04 item 13 declara que **o PCASP não padroniza** o desdobramento que permitiria separar
executado de a executar — cabe ao ente detalhar em 6º/7º nível.
Logo a regra existe, mas **não é computável sem convenção do ente** (§6.1 P2).

### 4.12 Condicional de sinal
IPC07 `L25 Déficit = (L48 - L24)`, "Somente quando o resultado for deficitário";
`L49 Superávit = (L24 - L48)`, "Somente quando o resultado for superavitário".
O cálculo precisa suportar guarda condicional, não só expressão aritmética.

### 4.13 Soma algébrica de contas com sinal explícito
IPC06 `L2 = 6.2.1.2.0.00.00 - 6.2.1.3.0.00.00` (receita bruta menos dedução).
IPC08 `L3 = (+) 6.2.1.2.0.00.00 (-) 6.2.1.3.0.00.00`.
IPC07 RPNP inscritos: `5.3.1.2.0.00.00 + 5.3.1.3.0.00.00 + 5.3.1.6.0.00.00 (-) 6.3.1.6.0.00.00`.
A lista de contas de uma coluna é **assinada**, não um conjunto.

### 4.14 Regra geral aplicável a todo o demonstrativo (policy)
IPC04 item 9 / IPC05 item 16: "o ente deverá deduzir as contas de nível intraorçamentário
(5º nível = 2) **eventualmente criadas**" — ou seja, a lista de exclusões nas matrizes é
**exemplificativa**, e a regra real é estrutural (5º nível = 2).
IPC06 item 38: linhas de execução orçamentária devem excluir transferências financeiras
intraorçamentárias acompanhadas de execução.
IPC04 item 8 / IPC05 item 15: as exclusões de intra valem para o **consolidado do ente**; no
levantamento de órgão ou unidade isolada **não** se exclui.
Policies são de primeira classe; não podem ser diluídas nas 309 regras.

## 5. Estrutura matricial: como a coluna entra no modelo

O IPC07 item 23 define a mecânica de forma inequívoca:

> "As regras de preenchimento são apresentadas em estrutura matricial. O preenchimento de cada
> célula do quadro conjuga os critérios contábeis informados nas colunas com os critérios
> informados em cada linha. Nas colunas são apresentadas as contas contábeis das quais os dados
> são extraídos, enquanto as linhas delimitam tais dados."

Isto é: **coluna = de onde vem o valor (contas); linha = filtro sobre o valor (naturezas,
função, exclusões)**. Célula = interseção.

Quadros por número de colunas de valor:

| Quadro | Colunas de valor |
|---|---|
| IPC04 — todos | 1 (valor do exercício; "exercício anterior" é reexecução com outro período) |
| IPC05 — principal | 1 |
| IPC06 — principal | 1 |
| IPC06 — anexo | 3 por exercício (receita `a`, deduções `b`, saldo `c = a - b`) |
| IPC07 — principal, receitas | 4 (`a` previsão inicial, `b` previsão atualizada, `c` realizada, `d = c - b`) |
| IPC07 — principal, despesas | 6 (`e` dotação inicial, `f` atualizada, `g` empenhada, `h` liquidada, `i` paga, `j = f - g`) |
| IPC07 — RP não processados | 6 (`a`,`b` inscritos, `c` liquidados, `d` pagos, `e` cancelados, `f = a+b-d-e`) |
| IPC07 — RP processados | 5 (`a`,`b` inscritos, `c` pagos, `d` cancelados, `f = a+b-c-d`) |
| IPC08 — todos | 1 |

Decisão que isso força: **uma regra por linha, contendo o mapa de colunas** — não uma regra por
célula. 309 regras, não ~900. Os filtros de linha valem para todas as colunas da linha; as
contas variam por coluna.

Exemplo (IPC07 p. 8, `L2`): filtro de linha `natureza_receita in (1100.00.00, 7100.00.00)`;
colunas `a` -> `5.2.1.1.0.00.00`; `b` -> `5.2.1.1.0.00.00 + 5.2.1.2.0.00.00`;
`c` -> `6.2.1.2.0.00.00 + 6.2.1.3.0.00.00`; `d` -> `c - b`.

## 6. Pendências e ambiguidades

### 6.1 Bloqueiam a regra (`status: review_required`)

| # | Doc / local | Problema |
|---|---|---|
| P1 | IPC05 p. 8, cabeçalho `Exclusões¹` | Existe marcador de nota de rodapé **1**, mas o texto da nota **não existe no PDF** (verificado bloco a bloco nas pp. 8–9). Metade das exclusões está entre parênteses (`(4.2.1.1.2.00.00)`) e metade não (`4.3.3.1.2.00.00`) — sem a nota, a diferença é indeterminada. Não inferir. |
| P2 | IPC04 p. 12, itens 12–13 | `(somente saldo a executar)` em 8 linhas, com o próprio IPC declarando que o PCASP não padroniza esse desdobramento. Não computável sem convenção de 6º/7º nível do ente. |
| P3 | IPC04 p. 11, `L2`/`L3` | "contas escrituráveis de ativo com o atributo (F)/(P)". Depende da tabela de atributos do PCASP, que **não está neste repositório**. |
| P4 | IPC06, 24 linhas do Quadro Principal + 14 do Quadro Anexo | `<nas fontes aplicáveis>` — o IPC04 item 15 afirma que a classificação por fonte/destinação **não é padronizada** e cabe a cada ente. Mapeamento fonte -> linha é parâmetro do ente, não da norma. |
| P5 | IPC06 `L22`,`L23`,`L55`,`L56` | `<conta de controle>` — conta não informada. O item 36 confirma que criar essas contas é opcional. |
| P6 | IPC06 `L28`,`L61` | `<contas sob demanda>` — aberto por definição ("situações não previstas no mapeamento desta IPC", item 29). |
| P7 | IPC04 Quadro do Superávit/Déficit | Linhas não enumeradas (`<Código da fonte>` repetido). Regra é paramétrica na fonte; a cardinalidade vem do ente. |

### 6.2 Divergências de grafia a normalizar (não são ambiguidade de norma)

| # | Problema | Ocorrências |
|---|---|---|
| N1 | Natureza de receita em duas grafias: `1100.00.00` (IPC07) vs `1.1.xx.xx.xx` (IPC08) | todos os quadros de receita |
| N2 | ND em três comprimentos: `3.1.00.00.00`, `3.1.00.00`, `3.1.71.xx.xx` | todos os quadros de despesa |
| N3 | Função/subfunção concatenada (`28.841`, IPC07) vs separada (`Função: 28` + `Subfunção: 841`, IPC08) | IPC07 `L38`,`L39`,`L43`,`L44`,`L46`,`L47`,`L51`; IPC08 `L14`,`L32`, quadro d |
| N4 | ND com e sem sufixo de máscara: `4.6.90.71.xx` (IPC08 `L32`) vs `4.6.90.71` (IPC08 `L33`) | IPC08 `L33`; quadro b (`4.5.32.66`, `45.80.66`) |
| N5 | Erros de digitação no PDF: `45.80.66` (falta 1º ponto), `4.4..22.xx.xx` (ponto duplo), `1.1.3.8.2.000.00` (grupo de 3 dígitos), `1.1.1.0.0.00.0` (falta 1 dígito), `7.3.21.00.31.x` | IPC08 `L15`/`L9`; IPC04 `L4`; IPC06 `L30`; IPC08 `L5` |
| N6 | Rótulo com hífen espúrio da revisão do PDF: `L-40`, `Despesas Correntes (-VIII)`, `(L31 + L35 + L39 + -)` | IPC07 p. 10 |
| N7 | IPC07 `L40` diz `SUBTOTAL DAS DESPESAS (XI) = (VII + IX + X)`, mas `L31` é `(-VIII)` e a fórmula de linhas é `(L31 + L35 + L39)`. O numeral `VII` é inconsistente com o `VIII` de `L31` | IPC07 p. 10 |

N5, N6 e N7 são **erros de digitação do próprio PDF**. Regra do projeto: PDF prevalece — logo
essas regras nascem `review_required`, com o texto literal preservado em `evidence`, e a
correção só entra com decisão registrada. Não corrigir silenciosamente.

### 6.3 Vigência

O IPC06 é de 2024 e os outros quatro de 2020; os de 2020 declaram referência ao **PCASP 2019**.
Nenhum documento declara `valid_until`. Consequência: `valid_from` = data de edição do documento,
`valid_until` = `null`, e a resolução por exercício é responsabilidade do repositório de regras —
nunca inferida dentro da regra.

## 7. Extração

**Escolha: PyMuPDF** (`page.get_text()`), sem detecção de tabela.

Motivo medido: os 5 PDFs têm camada de texto completa (1.4k–3k caracteres por página de regra,
zero páginas vazias, nenhuma necessidade de OCR). O `find_tables()` do PyMuPDF **degradou** o
resultado nestes arquivos — devolveu matrizes de até 26 colunas com ~90% de células vazias
(cabeçalho e rodapé detectados como tabela), enquanto a leitura linear preservou a ordem
`Ln -> rótulo -> critério -> exclusões` de forma legível e consistente.

Não foi introduzida dependência paga (LlamaParse, Docling): não há justificativa — o texto nativo
é suficiente, e a estrutura matricial se reconstrói pelo cabeçalho de colunas + posição do rótulo
`Ln`, que já vêm corretos.

**Ressalva:** a extração linear **não** recupera a associação célula -> coluna quando uma linha
tem listas longas de naturezas quebradas em várias linhas físicas. Nesses casos a transcrição
para YAML exige leitura visual da página, e a regra nasce `status: extracted` +
`review.required: true`. São **14 linhas** nessa condição: IPC08 principal `L13`,`L15`,`L23`,
`L24`,`L25`,`L32`; IPC08 quadro b `L10`,`L11`,`L12`,`L14`; IPC08 quadro c `L1`; IPC08 quadro d
`L1`,`L2`,`L3`.

## 8. Exigências que o modelo canônico tem de atender

Consolidado desta análise — cada item tem origem rastreável acima:

1. Regra por **linha**, com mapa de **colunas** (§5).
2. Conta como **prefixo mascarado**, não código exato (§4.1).
3. Lista de contas **assinada** por coluna (§4.13).
4. Exclusões separadas das inclusões (§4.2).
5. Filtros genéricos por campo: `natureza_receita`, `natureza_despesa`, `funcao`, `subfuncao`,
   `fonte_recurso`, `financeiro_permanente`, `movimento` (§4.4–4.9; ver §11.2 — o atributo F/P vem
   do registro, não da conta).
6. Seletor de **momento do saldo** (inicial / final / movimento do período) (§4.10).
7. Cálculo por **referência a outras regras**, com soma e subtração (§4.3).
8. **Guarda condicional** no cálculo (§4.12).
9. **Policies** de documento, referenciáveis por várias regras (§4.14).
10. Placeholder explícito e não computável (`<nas fontes aplicáveis>`, `<conta de controle>`),
    que impede a regra de ser marcada `validated` (§6.1).
11. Versionamento por edição de documento, com `valid_from` e `valid_until: null` (§6.3).
12. `evidence` com o texto literal da página para as pendências (§11.5) e os 7 casos de grafia (§6.2).
13. Metadado de apresentação (rótulo, ordem, indentação) separado do critério (§2).

## 9. O que esta fase NÃO decidiu

- Ligação IPC -> **anexo DCA** (`I-AB`, `I-C`, ..., `I-HI`). Nenhum dos 5 PDFs menciona a DCA ou
  o layout SICONFI. Essa ponte é decisão de spec com o PO, não extração.
- Vigência aplicável por exercício de referência da DCA.
- Tratamento das 7 pendências de §6.1. **Atualizado pelo adendo:** 2 resolvidas, 1 estreitada;
  restam 5 (§11.5).

---

# Adendo — Tabelas de referência da STN e resolução das pendências

**Data:** 2026-08-27 · **Origem:** decisões do PO + descoberta de `docs/contas-stn/`

A Fase 1 cobriu apenas `docs/referencia/ipc/`. O repositório também traz as **tabelas oficiais da
STN** em `docs/contas-stn/`, que não entraram na análise original e que resolvem parte das
pendências de §6.1 e das divergências de §6.2.

## 10. Tabelas de referência disponíveis no repositório

| Arquivo | Conteúdo | Registros medidos | Resolve |
|---|---|---|---|
| `PCASP.md` | plano de contas completo, com `NATUREZA DO SALDO`, `STATUS`, `NÍVEL DETALHADO`, **`INDICADOR DO SUPERÁVIT FINANCEIRO`** e `Informação Complementar` | 6.119 contas | P3, N5, parte de P2 |
| `natureza-receita.md` | naturezas de receita, código `C.O.E.D1.DD2.D3.T` | 4.506 naturezas | N1 |
| `natureza_despesa.md` | naturezas de despesa, `C-G-M-E-SE` + nível | 174 NDs | N2 |
| `funcao-subfuncao.md` | função x subfunção com nomenclatura | 119 pares | N3 |
| `fonte-recursos.md` | fontes de recursos: código, nomenclatura, especificação | 98 fontes + 2 prefixos de exercício | P4, P7 |
| `complemento-fonte.md` | complementos de fonte (marcadores MDE, ASPS, RPPS, ...) | 51 complementos | — |
| `poder-orgao.md` | códigos de poder / órgão | 92 códigos | — |

### 10.1 O que o `PCASP.md` entrega

Domínios medidos nas colunas relevantes:

- `STATUS` = `Ativa` em **todas** as 6.119 linhas.
- `NÍVEL DETALHADO` = `Último` em **todas** as 6.119 linhas.
  Logo **a tabela já é o conjunto das contas escrituráveis** — isso define, sem inferência, o
  termo "contas escrituráveis" que o IPC04 p. 11 usa e não explica.
- `NATUREZA DO SALDO` em `Devedora` (2.968) · `Credora` (3.085) · `Credora/Devedora` (66).
- `INDICADOR DO SUPERÁVIT FINANCEIRO` em `Financeiro` (167) · `Permanente` (1.293) ·
  `Financeiro/Permanente` (924) · `-` (3.735).

Cruzamento indicador x classe:

| Classe | `Financeiro` | `Permanente` | `Financeiro/Permanente` | `-` |
|---|---|---|---|---|
| 1 — Ativo | 30 | 1.141 | 255 | 0 |
| 2 — Passivo | 137 | 152 | 669 | 181 |
| 3 a 8 | 0 | 0 | 0 | 3.554 |

O atributo F/P **só existe para as classes 1 e 2** — exatamente o escopo do Quadro dos Ativos e
Passivos Financeiros e Permanentes do IPC04. Nas classes 3 a 8 o indicador é sempre `-`.

Consequência crítica: **924 contas de ativo/passivo são `Financeiro/Permanente`**, ou seja,
ambíguas no nível da conta. Nessas contas o atributo **não é propriedade da conta** — é
propriedade do **registro**. É isso que a decisão do PO sobre P3 formaliza (§11.2).

## 11. Resolução das pendências (decisões do PO, 2026-08-27)

### 11.1 P1 — exclusões do IPC05 sem nota de rodapé: RESOLVIDO

**Decisão:** parênteses e não-parênteses são **equivalentes**. Toda entrada da coluna "Exclusões"
do IPC05 é exclusão, esteja ou não entre parênteses.

Efeito: as regras da DVP deixam de nascer `review_required` por causa de P1. O `literal` em
`evidence` continua registrando a grafia original, e a decisão fica citada na regra — registra-se
que a distinção foi declarada irrelevante **por decisão**, não que ela não existia no documento.

### 11.2 P3 — atributo Financeiro / Permanente: RESOLVIDO

**Decisão:** o atributo vem do **registro do fato**, não da conta:

| Fonte de dados | Chave no registro | Valores |
|---|---|---|
| SICONFI | `financeiro_permanente` | `1` = Financeiro (F) · `2` = Permanente (P) |
| PublicSoft | `financeiroPermanente` | `1` = Financeiro (F) · `2` = Permanente (P) |

O `PCASP.md` passa a ser o **domínio de validação** desse campo, não a sua origem:

| `INDICADOR DO SUPERÁVIT FINANCEIRO` da conta | valores aceitáveis no registro |
|---|---|
| `Financeiro` | `1` |
| `Permanente` | `2` |
| `Financeiro/Permanente` | `1` ou `2` |
| `-` | nenhum — conta fora do quadro F/P |

Efeito: IPC04 quadro 2 `L2`/`L3` passam a ser computáveis. `L2 Ativo Financeiro` = contas de
classe 1 com registro `= 1`, excluídas as intra; `L3 Ativo Permanente` = o mesmo com `= 2`. Idem
`L5`/`L6` para o passivo, somadas às contas de execução que o IPC04 lista nominalmente
(`6.2.2.1.3.01.00`, `6.2.2.1.3.05.00`, `6.3.1.1.0.00.00`, `6.3.1.5.0.00.00`).

### 11.3 P4 / P7 — fonte / destinação de recurso: RESOLVIDO com 2 ressalvas

**Decisão:** usar `docs/contas-stn/fonte-recursos.md` como mapeamento código x nomenclatura.

As faixas da tabela da STN batem com as linhas do IPC06 por **igualdade de nomenclatura** — é
junção por nome literal, não inferência:

| Linha do IPC06 (ingresso / dispêndio) | Fontes | Base da correspondência |
|---|---|---|
| `L2` / `L35` Recursos Não Vinculados | 500, 501, 502, 503 | nomes literais "não Vinculados" |
| `L4` / `L37` Educação | 540–599 | faixa nomeia FUNDEB, FNDE, Salário-Educação ou "Educação"; 599 = "Outros Recursos Vinculados à Educação" |
| `L5` / `L38` Saúde | 600–659 | faixa nomeia SUS ou "Saúde"; 659 = "Outros Recursos Vinculados à Saúde" |
| `L6` / `L39` Assistência Social | 660–669 | FNAS e fundos de assistência social; 669 = "Outros Recursos Vinculados à Assistência Social" |
| `L8` / `L41` Demais Vinculações Decorrentes de Transferências | 700–749 | faixa inteira é transferência; 747–749 = "Outras vinculações de transferências" |
| `L9` / `L42` Demais Vinculações Legais | 750–799 | 799 = "Outras Vinculações Legais", nome idêntico ao rótulo da linha |
| `L12` / `L45` RPPS Fundo em Capitalização | 800 | nome idêntico ao rótulo da linha |
| `L13` / `L46` RPPS Fundo em Repartição | 801 | nome idêntico ao rótulo da linha |
| `L14` / `L47` RPPS Taxa de Administração | 802 | nome idêntico ao rótulo da linha |

**Ressalva R1 — `L7`/`L40` "Previdência Social (Exceto ao RPPS)":** a fonte 803 (SPSM) está
confirmada pela nota de rodapé 2 do IPC06, que cita o SPSM nominalmente. A 804 "Demais Recursos
Previdenciários" é previdenciária e não é RPPS (800–802 esgotam o RPPS), o que sustenta incluí-la
— mas nenhum dos dois documentos afirma isso. Fica `review_required`.

**Ressalva R2 — `L10`/`L43` "Outras Vinculações":** sobram 860–869, 880, 898, 899. Mas 860–869 são
nomeadas **"Recursos Extraorçamentários"**, e o IPC06 `L27`/`L60` usa filtro próprio
`<fontes extraorçamentárias>` para Depósitos Restituíveis. Alocar 860–869 em `L10` colidiria com
`L27`/`L60` e contaria o mesmo recurso duas vezes. Fica `review_required`.

Os prefixos 1500 (exercício corrente) e 2500 (exercícios anteriores) são **dimensão ortogonal** à
vinculação, não fontes de vinculação. Não entram nas faixas acima.

### 11.4 Ligação IPC para anexo DCA: outra change (confirmado)

Permanece fora de escopo.

### 11.5 Pendências que continuam abertas

| # | Situação |
|---|---|
| P2 | `(somente saldo a executar)` — IPC04 contas de compensação, 8 linhas. O `PCASP.md` confirma a lacuna: as contas 8.1.1.x e 8.1.2.x existem, mas nenhuma coluna segrega executado de a executar. Continua dependendo de convenção de 6º/7º nível do ente. |
| P5 | `<conta de controle>` — IPC06 `L22`,`L23`,`L55`,`L56`. Conta opcional por decisão do ente (IPC06 item 36). |
| P6 | `<contas sob demanda>` — IPC06 `L28`,`L61`. Aberto por definição (IPC06 item 29). |
| R1 | fonte 804 em `L7`/`L40` do IPC06 (§11.3). |
| R2 | fontes 860–869 em `L10`/`L43` versus `<fontes extraorçamentárias>` de `L27`/`L60` (§11.3). |
| N5 | erros de digitação do PDF. Agora **verificáveis**: cada `literal` pode ser conferido contra `PCASP.md`, `natureza-receita.md`, `natureza_despesa.md` e `funcao-subfuncao.md`. O que não existir na tabela oficial é erro do PDF e vira `review_required` com o candidato correto **anotado, não aplicado**. |
| N6 / N7 | rótulo `L-40` e numeral romano inconsistente no IPC07 p. 10. Sem efeito no cálculo; ficam em `evidence`. |

Contagem de pendências: de **7** para **5** (P2, P5, P6, R1, R2) — e R1/R2 são muito mais
estreitas que o P4 original, que atingia 38 linhas do IPC06.
