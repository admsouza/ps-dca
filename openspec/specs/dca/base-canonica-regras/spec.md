# dca/base-canonica-regras

> Comportamento acordado e em vigor. Consolidado da change `ipc07-bo-regras-canonicas`,
> aprovada pelo PO em 2026-09-04 e arquivada em `openspec/changes/archive/`.
> Alterações entram por nova change, nunca por edição direta deste arquivo.

## Purpose

Garantir que cada uma das 69 linhas de regra do Balanço Orçamentário definidas no IPC 07 exista
como regra canônica versionada e rastreável até a página do documento, e que ambiguidade
documental seja declarada em vez de interpretada. A base canônica é a única fonte executável das
regras do BO; o código é implementação dela.

Esta é a primeira entrega da capability. As changes de IPC04, IPC05, IPC06 e IPC08 estendem os
enums e acrescentam requisitos — não substituem os daqui.

## Requirements

### Requirement: Rastreabilidade obrigatória até a origem documental

Toda regra canônica SHALL declarar `source` com `document`, `document_version`, `page`, `section`,
`table` e `row`. A validação SHALL rejeitar regra sem esses campos.
`source.page` SHALL estar entre 1 e o número de páginas declarado em
`knowledge/sources/ipc07/metadata.yaml`. A validação NÃO DEVE aceitar `source.page` ausente, nulo,
zero ou fora do intervalo.

#### Scenario: regra com origem completa é aceita

- **GIVEN** uma regra com `source.document: IPC07`, `document_version: "2020-01"`, `page: 8`,
  `section: "REGRAS DE PREENCHIMENTO DO BALANÇO ORÇAMENTÁRIO"`, `table: "Quadro Principal"`,
  `row: "L2"`
- **WHEN** a validação é executada
- **THEN** a regra é contada como válida

#### Scenario: regra sem source é rejeitada

- **WHEN** um arquivo de regra não possui o bloco `source`
- **THEN** a validação reporta o `rule_id` e o caminho `arquivo:linha`, e termina com exit `1`,
  sem gerar índice

#### Scenario: página fora do documento é rejeitada

- **GIVEN** que o IPC07 tem 17 páginas registradas em `knowledge/sources/ipc07/metadata.yaml`
- **WHEN** uma regra declara `source.page: 40`
- **THEN** a validação reporta página inválida e termina com exit `1`

### Requirement: Identificador legível e estável

Toda regra SHALL ter `rule_id` no formato `bo.<quadro>.<grupo?>.<linha>`, em minúsculas, com
segmentos separados por ponto, único em toda a base. O `rule_id` NÃO DEVE depender do caminho do
arquivo nem conter UUID. O segmento `<grupo>` SHALL estar presente no Quadro Principal, para
distinguir o bloco de receitas do de despesas.

#### Scenario: identificador de linha de receita

- **WHEN** a regra da linha `L2` do Quadro Principal é lida
- **THEN** seu `rule_id` é `bo.quadro_principal.receitas.l2`

#### Scenario: linhas homônimas em quadros diferentes

- **GIVEN** que o quadro de RP Não Processados e o de RP Processados **ambos** têm linhas
  `L1`–`L9`
- **WHEN** a base é lida
- **THEN** os identificadores são `bo.rp_nao_processados.l1` e `bo.rp_processados.l1`, distintos
- **AND** o número de `rule_id` distintos é igual ao número de regras carregadas

#### Scenario: identificador duplicado é rejeitado

- **GIVEN** duas regras com `rule_id: bo.quadro_principal.receitas.l2` em arquivos diferentes
- **WHEN** a validação é executada
- **THEN** o erro nomeia o `rule_id` e **os dois** caminhos de arquivo, e o exit é `1`

### Requirement: Regra por linha, com o mapa de colunas do quadro

Uma regra canônica SHALL representar **uma linha** de um quadro e SHALL declarar em `columns` as
colunas de valor daquele quadro. Os filtros declarados em `filters` SHALL valer para todas as
colunas da regra. Cada coluna SHALL declarar suas contas com sinal explícito (`+` ou `-`).
NÃO DEVE existir uma regra por célula.

O número de colunas de valor por quadro SHALL ser: Quadro Principal — receitas **4**; Quadro
Principal — despesas **6**; RP Não Processados **6**; RP Processados **5**.

A coluna NÃO DEVE declarar conta ausente do PCASP vigente para o exercício, nem a mesma conta duas
vezes: a apuração soma por conta declarada, sem deduplicar, e a repetição dobraria o valor. Quando
um termo do literal do IPC07 é descontinuado do PCASP e seu conteúdo passa a estar em outra conta
**já declarada na mesma coluna**, o termo SHALL ser removido da regra, e o literal original SHALL
permanecer legível na nota de proveniência.

#### Scenario: linha de receita com quatro colunas

- **GIVEN** o IPC07 p. 8, Quadro Principal, linha `L2`
- **WHEN** a regra `bo.quadro_principal.receitas.l2` é lida
- **THEN** ela declara `filters` com `natureza_receita in ("1100.00.00", "7100.00.00")`
- **AND** declara as colunas `previsao_inicial`, `previsao_atualizada`, `receitas_realizadas`,
  `saldo`
- **AND** `previsao_atualizada` inclui `5.2.1.1.0.00.00` e `5.2.1.2.0.00.00`, ambas com sinal `+`
- **AND** `saldo` é calculada como `receitas_realizadas - previsao_atualizada`

#### Scenario: linha de despesa com seis colunas

- **GIVEN** o IPC07 p. 10, Quadro Principal, linha `L32 Pessoal e Encargos Sociais`
- **WHEN** a regra é lida
- **THEN** ela filtra `natureza_despesa in ("3.1.00.00.00")`
- **AND** declara as colunas `dotacao_inicial`, `dotacao_atualizada`, `empenhadas`, `liquidadas`,
  `pagas`, `saldo_dotacao`
- **AND** `empenhadas` inclui as 7 contas de `6.2.2.1.3.01.00` a `6.2.2.1.3.07.00`
- **AND** `saldo_dotacao` é calculada como `dotacao_atualizada - empenhadas`

#### Scenario: coluna com contas de sinal negativo

- **GIVEN** o IPC07 p. 12, quadro de RP Não Processados, coluna
  "Inscritos — Em Exercícios Anteriores (a)", cujo literal é
  `5.3.1.2.0.00.00 + 5.3.1.3.0.00.00 + 5.3.1.6.0.00.00 (-) 6.3.1.6.0.00.00`
- **WHEN** a regra de qualquer linha de filtro desse quadro é lida
- **THEN** a coluna declara **exatamente 3** contas: `5.3.1.2` e `5.3.1.6` com sinal `+`, e
  `6.3.1.6` com sinal `-`
- **AND** `5.3.1.3` NÃO é declarada, por estar descontinuada e ter o conteúdo em `5.3.1.2`
- **AND** o literal de 4 termos permanece legível na nota de proveniência da regra

#### Scenario: quadro sem coluna de exclusões

- **GIVEN** que os quadros de RP Não Processados e de RP Processados não têm coluna "Exclusões"
- **WHEN** as 18 regras desses quadros são lidas
- **THEN** nenhuma declara exclusão de conta ou de filtro

### Requirement: Filtros com campos e operadores de conjunto fechado

Um filtro SHALL declarar `field`, `operator` e `values`. Para o IPC07, `field` SHALL pertencer a
`{ conta_contabil, natureza_receita, natureza_despesa, funcao, subfuncao }` e `operator` a
`{ in, not_in }`. A validação SHALL rejeitar `field` ou `operator` fora desses conjuntos.

Cada valor SHALL declarar `literal` com a grafia exata do PDF. Quando a normalização em dígitos for
determinável, o valor SHALL declarar também `pattern`; quando não for, `pattern` SHALL ser `null` e
a regra SHALL ficar `review_required`.

#### Scenario: exclusão por padrões de conta PCASP

- **GIVEN** o IPC07 p. 9, `L11 Operações de Crédito`, cuja coluna Exclusões traz 8 códigos em 4
  pares
- **WHEN** a regra é lida
- **THEN** ela declara `natureza_receita in ("2100.00.00", "8100.00.00")`
- **AND** declara `conta_contabil not_in` com os **8** padrões PCASP de exclusão, não 4
- **AND** não procura esses 8 padrões em `natureza-receita.md`

#### Scenario: função e subfunção como filtros separados

- **GIVEN** o IPC07 p. 10, `L38`, cuja exclusão grafa `Função: 28.841, 28.842, 28.843, 28.844`
- **WHEN** a regra é lida
- **THEN** a exclusão é expressa como dois filtros, `funcao in ("28")` e
  `subfuncao in ("841", "842", "843", "844")`
- **AND** o `literal` de cada valor preserva a grafia concatenada `28.841` do documento

#### Scenario: operador inválido é rejeitado

- **WHEN** uma regra declara `operator: starts_with`
- **THEN** a validação reporta operador inválido e termina com exit `1`

#### Scenario: campo de filtro inválido é rejeitado

- **WHEN** uma regra do BO declara `field: fonte_recurso`
- **THEN** a validação reporta campo não suportado para o IPC07 e termina com exit `1`

### Requirement: Duas exclusões independentes na mesma célula

Quando a célula de exclusão combinar mais de um par natureza + classificação funcional, a regra
SHALL declarar cada combinação como um **grupo de exclusão próprio**. A regra NÃO DEVE achatar os
grupos numa lista única, porque o produto cartesiano das listas achatadas exclui mais do que o
documento manda.

#### Scenario: exclusões de L38

- **GIVEN** o IPC07 p. 10, `L38 Amortização da Dívida`, cuja célula de exclusão traz
  `ND: 46.xx.76, Função: 28.841, 28.842, 28.843, 28.844` **e**
  `ND: 46.xx.77, Função: 28.841, 28.842, 28.843, 28.844 e 28.846`
- **WHEN** a regra é lida
- **THEN** ela declara **dois** grupos de exclusão
- **AND** o primeiro combina `natureza_despesa 46.xx.76` com as subfunções `841, 842, 843, 844`
- **AND** o segundo combina `natureza_despesa 46.xx.77` com as subfunções `841, 842, 843, 844, 846`
- **AND** a união desses grupos é idêntica ao que as linhas `L43`, `L44`, `L46` e `L47` capturam

### Requirement: Cálculo por referência a outras regras, inclusive entre grupos

Linha composta por outras linhas SHALL declarar o cálculo em `calculation.references`, apontando
para `rule_id` existentes, com o sinal de cada componente. A regra composta NÃO DEVE duplicar os
filtros nem as contas das regras referenciadas. Referência entre grupos do mesmo quadro SHALL ser
permitida. A validação SHALL rejeitar referência a `rule_id` inexistente e SHALL rejeitar ciclo.

Uma referência PODE nomear a **coluna** lida na linha referenciada, quando a coluna que está sendo
calculada tem outro nome. Sem esse campo, a coluna lida é a mesma que está sendo calculada. Com
ele, a linha cruzada entre receita e despesa se torna calculável: os dois blocos não têm coluna em
comum, e a interseção vazia é o que mantinha `L25`, `L26`, `L49` e `L50` sem apurar.

Linha cujas referências não compartilham coluna SHALL declarar explicitamente suas colunas. A
validação SHALL rejeitar referência que nomeie coluna ausente na linha referenciada.

Ao agregar uma coluna, a apuração SHALL distinguir **três** situações na parcela:

| Situação na linha referenciada | Contribuição | Efeito no total |
|---|---|---|
| **não declara** a coluna | nenhuma — a parcela não existe | o total é a soma das demais parcelas |
| declara e a célula foi **suprimida pela condição** | **zero** | o total tem valor |
| declara e a célula está **não apurada** | indeterminada | o total sai `None`, com aviso |

Colapsar as duas primeiras em `None` é o que faria `L27.previsao_inicial` sair não apurada quando
`L29` não tem a coluna, e `L26`/`L50` saírem em branco quando a linha de ajuste não se aplica — os
dois contra o publicado do STN.

#### Scenario: soma de linhas

- **GIVEN** o IPC07 p. 8, `L1 Receitas Correntes (I) = (L2 + L3 + L4 + L5 + L6 + L7 + L8 + L9)`
- **WHEN** a regra `bo.quadro_principal.receitas.l1` é lida
- **THEN** ela declara 8 referências, todas com sinal `+`
- **AND** NÃO declara conta contábil nem filtro de natureza próprios

#### Scenario: referência do bloco de receitas para o de despesas

- **GIVEN** o IPC07 p. 9, `L25 Déficit (VI) = (L48 - L24)`, onde `L48` pertence ao bloco de
  despesas
- **WHEN** a regra `bo.quadro_principal.receitas.l25` é lida
- **THEN** ela referencia `bo.quadro_principal.despesas.l48` com sinal `+`, nomeando a coluna
  `empenhadas`, e `bo.quadro_principal.receitas.l24` com sinal `-`, na coluna calculada
- **AND** declara **uma** coluna própria: `receitas_realizadas`
- **AND** a validação aceita a referência entre grupos
- **AND** NÃO detecta ciclo, porque `L24 = (L16 + L17)` e `L48 = (L40 + L41)` não dependem de `L25`

#### Scenario: referência inexistente é rejeitada

- **WHEN** uma regra referencia `bo.quadro_principal.receitas.l99`, que não existe
- **THEN** o erro nomeia o `rule_id` órfão, a regra de origem e o `arquivo:linha`, e o exit é `1`

#### Scenario: referência nomeia coluna ausente é rejeitada

- **GIVEN** uma regra cuja referência nomeia a coluna `pagas` de `bo.quadro_principal.receitas.l24`,
  que só tem colunas de receita
- **WHEN** a validação é executada
- **THEN** o erro nomeia a regra de origem, a linha referenciada, a coluna pedida e as colunas
  disponíveis, e o exit é `1`
- **AND** nenhuma célula é apurada com zero no lugar da coluna ausente

#### Scenario: ciclo de dependência é rejeitado

- **GIVEN** `A` referencia `B` e `B` referencia `A`
- **WHEN** a validação é executada
- **THEN** o erro imprime o caminho completo do ciclo e termina com exit `1`

### Requirement: Guarda condicional no cálculo

Quando o documento condicionar a linha ao sinal do resultado, a regra SHALL declarar a condição em
`calculation.condition`, legível por máquina. A regra NÃO DEVE registrar a condição apenas como
texto descritivo.

As colunas em que a linha condicional é apresentada SHALL ser as medidas no publicado do STN, e
**não são simétricas** entre déficit e superávit: cada bloco recebe tantas células de ajuste
quantas colunas de realização ele tem — a receita tem uma, a despesa tem três.

#### Scenario: déficit orçamentário

- **GIVEN** o IPC07 p. 9, `L25 Déficit (VI) = (L48 - L24)`, "Somente quando o resultado for
  deficitário"
- **WHEN** a regra é lida
- **THEN** o cálculo declara `L48` com sinal `+`, na coluna `empenhadas`, e `L24` com sinal `-`
- **AND** declara **uma** coluna: `receitas_realizadas` — medido em 11 dos 12 estados deficitários
  de 2025, exato em centavos contra `Deficit` do `RREO-Anexo 01`
- **AND** declara que o valor só é apresentado quando o resultado dessa subtração for positivo
- **AND** `evidence.text` contém a frase literal do documento

#### Scenario: superávit orçamentário

- **GIVEN** o IPC07 p. 11, `L49 Superávit (XIV) = (L24 - L48)`, "Somente quando o resultado for
  superavitário"
- **WHEN** a regra é lida
- **THEN** o cálculo declara `L24` com sinal `+`, na coluna `receitas_realizadas`, e `L48` com
  sinal `-`, na coluna calculada
- **AND** declara **três** colunas: `empenhadas`, `liquidadas` e `pagas` — medido em João Pessoa
  2025, exato em centavos nas três contra `Superavit` do `RREO-Anexo 01`
- **AND** a condição é declarada de forma simétrica à de `L25`, mas o **conjunto de colunas não é**
- **AND** as duas regras coexistem sem que uma anule a outra

#### Scenario: total que agrega linha condicional declara as colunas do publicado

- **GIVEN** `L26 TOTAL (VII) = (L24 + L25)` e `L50 TOTAL (XV) = (L48 + L49)`
- **WHEN** as duas regras são lidas
- **THEN** `L26` declara `previsao_inicial`, `previsao_atualizada` e `receitas_realizadas`, e
  **não** declara `saldo`
- **AND** `L50` declara `dotacao_inicial`, `dotacao_atualizada`, `empenhadas`, `liquidadas` e
  `pagas`, e **não** declara `saldo_dotacao`
- **AND** nenhuma das duas declara conta contábil própria

### Requirement: Ambiguidade interna do documento resolvida por evidência da própria peça

Quando as seções "REGRAS DE PREENCHIMENTO" e "ESTRUTURA DO BALANÇO ORÇAMENTÁRIO" do IPC07
divergirem, e uma das leituras for a única coerente, a regra SHALL adotar essa leitura, SHALL
preservar o literal divergente em `evidence.text` e SHALL registrar em `provenance` a página que
sustenta a leitura adotada. A regra NÃO DEVE ficar `review_required` por esse motivo, e NÃO DEVE
apagar o literal.

#### Scenario: rótulo com hífen espúrio

- **GIVEN** que a p. 10 grafa `L-40`, único rótulo hifenizado das 69 linhas
- **WHEN** a regra é lida
- **THEN** seu `rule_id` termina em `.l40`
- **AND** `source.row` e `evidence.text` preservam `L-40`

#### Scenario: numeral romano inconsistente no subtotal das despesas

- **GIVEN** que a p. 10 grafa `SUBTOTAL DAS DESPESAS (XI) = (VII + IX + X)`, e que `VII` é o TOTAL
  das **receitas** (`L26`, p. 14)
- **AND** que a p. 15 grafa `SUBTOTAL DAS DESPESAS (XI) =(VIII + IX + X)`
- **WHEN** a regra `bo.quadro_principal.despesas.l40` é lida
- **THEN** ela referencia `L31`, `L35` e `L39`, todas com sinal `+`
- **AND** `evidence.text` preserva `(VII + IX + X)` e `(L31 + L35 + L39 + -)`
- **AND** `provenance` registra a p. 15 como base da leitura adotada
- **AND** a regra NÃO tem um quarto componente

#### Scenario: sinal espúrio no rótulo de Despesas Correntes

- **GIVEN** que a p. 10 grafa `Despesas Correntes (-VIII)` e a p. 15 grafa
  `Despesas Correntes (VIII)`
- **WHEN** a regra `bo.quadro_principal.despesas.l31` é lida
- **THEN** a descrição adotada não traz o sinal negativo
- **AND** o literal da p. 10 fica em `evidence.text`

#### Scenario: sinal espúrio em lista de subfunções

- **GIVEN** que a p. 11 grafa, em `L47`, `Função: 28.842, - 28.844 e 28.846`
- **WHEN** a regra é lida
- **THEN** o filtro declara as subfunções `842`, `844` e `846`
- **AND** a leitura é sustentada pela simetria com `L44` e pela exclusão de `L38`, cuja união de
  subfunções para `46.xx.77` é exatamente `{841, 842, 843, 844, 846}`

#### Scenario: duas grafias do mesmo código

- **GIVEN** que a p. 9 grafa `2111.00.20` nas exclusões de `L11` e `2111.00.2.0` no critério de
  `L19`
- **WHEN** as duas regras são lidas
- **THEN** ambas normalizam para os mesmos dígitos
- **AND** a base NÃO registra isso como divergência entre as células

### Requirement: Decisões do PO são aplicadas com escopo fechado e auditável

As decisões do PO sobre B1, B3, B5 e B6 SHALL ser registradas na regra e aplicadas somente ao caso
decidido. A validação SHALL rejeitar a ampliação dessas exceções para outros `rule_id`, contas ou
domínios. A decisão NÃO DEVE apagar o literal do IPC07 nem alterar as tabelas de
`docs/contas-stn/`.

Decisão revogada por decisão posterior SHALL ter a revogação registrada, e a decisão anterior NÃO
DEVE ser apagada do histórico em `docs/source-analysis-ipc07.md`. A decisão **B1** de 2026-08-27 —
preservar `5.3.1.3.0.00.00` como exceção histórica do PCASP 2019 — foi **revogada em 2026-09-04**:
a conta foi descontinuada e seu conteúdo está em `5.3.1.2.0.00.00`, já declarada na mesma coluna.
Nenhuma regra invoca mais a exceção B1. A decisão **B3** segue valendo — seus padrões são usados
como `field: conta_contabil` em filtro, não como conta de coluna.

A decisão **B6** de 2026-09-03 — `L27` a `L30` com as quatro colunas de receita — foi
**restringida em 2026-09-04**: `L29` Superávit Financeiro NÃO declara `previsao_inicial`, porque
**zero de 25 entes** publicam `PREVISÃO INICIAL` para `SuperavitFinanceiro` no `RREO-Anexo 01`. O
restante de B6 segue valendo, e a decisão **B5** — a conta da linha em `L29` — não é afetada.

#### Scenario: refinanciamento usa padrões de conta PCASP

- **GIVEN** os pares `2111/8111`, `2118/8118`, `2121/8121` e `2128/8128` das exclusões de `L11` e
  dos critérios de `L19`, `L20`, `L22` e `L23`
- **WHEN** essas cinco regras são lidas
- **THEN** os oito códigos são declarados como `field: conta_contabil`
- **AND** as grafias de `L11` e `L19`–`L23` normalizam para os mesmos oito padrões PCASP
- **AND** nenhum candidato de `natureza-receita.md` é aplicado
- **AND** a ausência desses padrões no PCASP atual é registrada como exceção histórica do PCASP
  2019 decidida pelo PO, sem `review_required` por B3

#### Scenario: a fórmula fica simétrica à do quadro de RP Processados

- **GIVEN** que o quadro de RP Processados declara `5.3.2.2 + 5.3.2.6 (-) 6.3.2.6` na coluna
  homóloga, e que o grupo `5.3.2` não tem `5.3.2.3`
- **WHEN** as colunas "Inscritos — Em Exercícios Anteriores (a)" dos dois quadros são comparadas
- **THEN** ambas declaram 3 contas, nas mesmas posições de família
- **AND** nenhuma regra de `rp_nao_processados` declara `decision: B1`, nem fica `review_required`

#### Scenario: conta da linha substitui contas das colunas em L29 e L30

- **GIVEN** que `L29` declara `5.2.2.1.3.01.00` e `L30` declara quatro contas `5.2.2.1.2.*`
- **WHEN** qualquer coluna dessas duas regras é avaliada
- **THEN** as contas declaradas na linha substituem as contas padrão da coluna
- **AND** a regra registra `line_account_override: true`
- **AND** `L29` e `L30` não ficam `review_required` por B5

#### Scenario: L27, L28 e L30 têm as quatro colunas de receita, e L29 tem três

- **GIVEN** que a p. 15 mostra `L28`, `L29` e `L30` sem marcação de coluna, e o PO decidiu em
  2026-09-03 que a seção REGRAS prevalece
- **WHEN** `L27`, `L28`, `L29` e `L30` são lidas
- **THEN** `L27`, `L28` e `L30` declaram as 4 colunas de receita — `previsao_inicial`,
  `previsao_atualizada`, `receitas_realizadas` e `saldo`
- **AND** `L29` declara **três**: `previsao_atualizada`, `receitas_realizadas` e `saldo` — um
  superávit financeiro é apurado sobre o exercício fechado e não existe em previsão inicial
- **AND** `L27` mantém `calculation` como `L28 + L29 + L30` em cada coluna, e em
  `previsao_inicial` a parcela de `L29` **não existe** — o total é `L28 + L30` = 12.000.000,00 em
  João Pessoa 2025, e não sai `None`
- **AND** cada uma registra `provenance.decision: B6` e o literal divergente da p. 15 em
  `evidence.text`
- **AND** nenhuma delas fica `review_required`

#### Scenario: L51 não tem coluna de valor

- **GIVEN** que a ESTRUTURA coloca `L51` — Reserva do RPPS — depois de `TOTAL (XV)` sem coluna, e o
  PO decidiu em 2026-09-03 que `L51` não tem coluna de valor
- **WHEN** `bo.quadro_principal.despesas.l51` é lida
- **THEN** `columns` é lista vazia
- **AND** os filtros `natureza_despesa = 9.9.00.00.00` e `funcao_subfuncao = 99.997` são
  preservados
- **AND** a regra registra `provenance.decision: B6` e não fica `review_required`
- **AND** a validação NÃO reporta erro por ausência de coluna

#### Scenario: override de conta fora de L29 e L30 é rejeitado

- **WHEN** qualquer regra diferente de `bo.quadro_principal.receitas.l29` e
  `bo.quadro_principal.receitas.l30` declara `line_account_override: true`
- **THEN** a validação reporta que o override não é permitido para o `rule_id` e termina com exit
  `1`

### Requirement: Bloqueio documental é declarado, nunca interpretado

Quando o documento e as decisões registradas do PO não permitirem determinar a regra com
segurança, a regra SHALL ter
`status: review_required` e `review.reason` nomeando o bloqueio e citando o item ou a página. A
regra NÃO DEVE escolher uma interpretação. Quando houver candidato provável, ele SHALL ser
registrado em `review.candidate` e NÃO DEVE ser aplicado em `filters` nem em `columns`.

#### Scenario: nenhum bloqueio documental permanece no IPC07

- **GIVEN** que B1, B3, B5 e B6 têm decisão registrada do PO
- **WHEN** a base do BO é validada
- **THEN** nenhuma regra declara `review.blocker`
- **AND** qualquer regra que nasça `review_required` por bloqueio documental é reportada como
  inconsistência, com exit `1`

#### Scenario: regra sob revisão marcada como validada

- **WHEN** uma regra declara `status: validated` junto com `review.required: true`
- **THEN** a validação reporta inconsistência e termina com exit `1`

### Requirement: Códigos conferidos contra as tabelas oficiais da STN

Todo código citado — conta contábil, natureza de receita, natureza de despesa, função e subfunção —
SHALL ser conferido contra as tabelas de `docs/contas-stn/`. Código ausente da tabela SHALL levar a
regra a `review_required`, exceto nas decisões históricas B1/B3 e nas lacunas de domínio B2/B4.
A validação NÃO DEVE substituir o código. As tabelas NÃO DEVEM ser alteradas.

Quando a tabela de domínio for comprovadamente **incompleta** para uma faixa de códigos, a
validação SHALL reportar esses códigos como **exceção declarada**, distinta de erro, e a regra NÃO
DEVE ficar `review_required` só por isso.

#### Scenario: código válido

- **WHEN** uma regra cita a conta `6.2.1.2.0.00.00`, presente no PCASP
- **THEN** a validação aceita o código

#### Scenario: naturezas intraorçamentárias ausentes da tabela

- **GIVEN** que `natureza-receita.md` tem códigos apenas nas categorias econômicas `1`, `2` e `9`,
  e **zero** nas categorias `7` e `8`
- **WHEN** a validação confere os 13 códigos intra que o IPC07 cita nas 13 linhas afetadas
- **THEN** ela os reporta como exceção declarada por lacuna de domínio
- **AND** essas 13 regras NÃO ficam `review_required` por esse motivo
- **AND** o relatório final distingue "exceção declarada" de "código inexistente"

#### Scenario: naturezas de despesa fora do grupo 3.1

- **GIVEN** que `natureza_despesa.md` contém 172 códigos, todos do grupo `3.1`
- **WHEN** a validação confere os 13 códigos de ND que o IPC07 cita fora desse grupo
- **THEN** ela os reporta como exceção declarada por lacuna de domínio

#### Scenario: tabela da STN alterada

- **GIVEN** que o SHA-256 de uma tabela de `docs/contas-stn/` registrado em
  `knowledge/sources/stn/metadata.yaml` não confere com o arquivo
- **WHEN** a verificação de fontes é executada
- **THEN** ela reporta a tabela, o hash esperado e o obtido, e termina com exit `1`

### Requirement: Integridade e imutabilidade do documento de origem

`knowledge/sources/ipc07/metadata.yaml` SHALL registrar nome do arquivo, número de páginas, edição
e SHA-256 do PDF. O PDF NÃO DEVE ser alterado nem duplicado dentro de `knowledge/`. A verificação
SHALL falhar quando o hash divergir.

#### Scenario: hash confere

- **WHEN** a verificação de fontes é executada sobre o IPC07
- **THEN** o hash confere e o exit é `0`

#### Scenario: PDF substituído por outra edição

- **WHEN** a verificação de fontes é executada após troca do arquivo
- **THEN** o erro nomeia o documento, o hash esperado e o obtido, e o exit é `1`

### Requirement: Versionamento por edição de documento

Toda regra SHALL declarar `version` com `source_document: IPC07`, `edition: "2020-01"` e
`valid_from`. `valid_until` SHALL ser `null`, porque o IPC07 não declara fim de vigência.
Edição futura do IPC07 NÃO DEVE sobrescrever estas regras.

#### Scenario: fim de vigência não declarado

- **WHEN** qualquer regra do BO é lida
- **THEN** `valid_until` é `null`
- **AND** a base NÃO contém data de fim inferida

### Requirement: Proveniência e estado de revisão explícitos

Toda regra SHALL declarar `status` em
`draft | extracted | review_required | validated | deprecated` e `provenance` com
`extraction_method` e `extracted_at`. Regra extraída automaticamente NÃO DEVE nascer `validated`.
Campo de revisor NÃO DEVE ser preenchido com nome inventado.

#### Scenario: extração automática não é validada

- **WHEN** uma regra é gerada por extração automática
- **THEN** seu `status` é `extracted` ou `review_required`, e `review.required` é `true`

#### Scenario: revisor ausente

- **WHEN** nenhuma revisão humana ocorreu
- **THEN** o bloco `review` não declara revisor
- **AND** a validação NÃO exige revisor para aceitar a regra

### Requirement: Cobertura completa dos três quadros do IPC 07

A base SHALL conter uma regra para cada uma das 69 linhas dos 3 quadros do IPC07. A validação SHALL
reportar a contagem por quadro e por status. A seção "ESTRUTURA DO BALANÇO ORÇAMENTÁRIO" NÃO DEVE
gerar regra executável.

#### Scenario: contagem por quadro

- **WHEN** a validação é executada sobre a base do BO
- **THEN** ela reporta `quadro_principal 51 · rp_nao_processados 9 · rp_processados 9`, total 69

#### Scenario: contagem por status

- **WHEN** a validação é executada
- **THEN** ela reporta `extracted 69 · review_required 0 · validated 0 · draft 0`
- **AND** `L27`–`L30` e `L51` aparecem como `extracted` com `provenance.decision: B6`

#### Scenario: estrutura de publicação não gera regra

- **GIVEN** as pp. 14–17, que trazem o layout de publicação do BO
- **WHEN** a base é lida
- **THEN** nenhuma regra executável é derivada dessas páginas
- **AND** os rótulos e a ordem delas aparecem apenas como metadado de apresentação

### Requirement: Regra legível sem consultar o PDF

Dado apenas um `rule_id`, SHALL ser possível obter quadro, grupo, linha e descrição, filtros,
colunas com contas e sinais, cálculo, dependências, status e a referência exata de página — sem
abrir o PDF.

#### Scenario: leitura cega de uma linha composta

- **GIVEN** apenas o `rule_id` `bo.quadro_principal.despesas.l48`
- **WHEN** a regra é lida da base
- **THEN** ficam determinados: quadro principal, bloco de despesas, linha
  `L48 SUBTOTAL COM REFINANCIAMENTO (XIII) = (XI + XII)`, cálculo `L40 + L41`, e `source` IPC07
  p. 11
- **AND** nenhuma informação necessária para implementar a regra fica só no PDF

### Requirement: Índice de regras para localização direta

A base SHALL manter um índice mapeando cada `rule_id` para arquivo, demonstrativo, quadro,
documento e página. O índice SHALL ser gerado a partir dos YAMLs, nunca editado à mão.

#### Scenario: localizar regra pelo índice

- **WHEN** `bo.quadro_principal.receitas.l2` é consultado no índice
- **THEN** o índice devolve `file`, `demonstrativo: BO`, `quadro: QUADRO_PRINCIPAL`,
  `document: IPC07` e `page: 8`

#### Scenario: índice desatualizado é detectado

- **GIVEN** uma regra que não está no índice
- **WHEN** a validação é executada
- **THEN** ela reporta o índice desatualizado e termina com exit `1`
