# dca/base-canonica-regras — Delta spec

## Purpose

Garantir que toda regra contábil dos demonstrativos do setor público usada neste repositório
exista primeiro como **regra canônica versionada e rastreável até a página do IPC de origem**, e
que ambiguidade documental seja declarada em vez de interpretada. A base canônica é a única fonte
executável das regras; o código é implementação dela.

## ADDED Requirements

### Requirement: Rastreabilidade obrigatória até a origem documental

Toda regra canônica SHALL declarar `source` com, no mínimo, `document`, `document_version`,
`page` e `section`, e SHALL declarar `quadro` e `linha` quando a regra corresponder a uma linha de
quadro. A validação SHALL rejeitar qualquer regra sem esses campos.
`source.page` SHALL estar dentro do intervalo de páginas declarado para o documento.
A validação NÃO DEVE aceitar `source.page` ausente, nulo, zero ou fora do intervalo.

#### Scenario: regra com origem completa é aceita

- **GIVEN** uma regra com `source.document: IPC07`, `document_version: "2020-01"`, `page: 8`,
  `section: "REGRAS DE PREENCHIMENTO DO BALANÇO ORÇAMENTÁRIO"`, `quadro: QUADRO_PRINCIPAL`,
  `linha: L2`
- **WHEN** a validação é executada
- **THEN** a regra é contada como válida e a validação termina com exit `0`

#### Scenario: regra sem source é rejeitada

- **WHEN** um arquivo de regra não possui o bloco `source`
- **THEN** a validação reporta o `rule_id` e o caminho `arquivo:linha`, e termina com exit `1`,
  sem gerar índice

#### Scenario: página fora do documento é rejeitada

- **GIVEN** que `IPC07` tem 17 páginas registradas em `knowledge/sources/ipc07/metadata.yaml`
- **WHEN** uma regra declara `source.page: 40`
- **THEN** a validação reporta página inválida para o documento e termina com exit `1`

### Requirement: Identificador legível e estável

Toda regra SHALL ter um `rule_id` no formato
`<demonstrativo>.<quadro>.<grupo>.<linha>`, em minúsculas, com segmentos separados por ponto.
O `rule_id` SHALL ser único em toda a base. O `rule_id` NÃO DEVE depender do caminho do arquivo
nem conter UUID.

#### Scenario: identificador único

- **WHEN** a validação carrega todas as regras
- **THEN** o número de `rule_id` distintos é igual ao número de regras carregadas

#### Scenario: identificador duplicado é rejeitado

- **GIVEN** duas regras com `rule_id: bo.quadro_principal.receitas.l2` em arquivos diferentes
- **WHEN** a validação é executada
- **THEN** o erro nomeia o `rule_id` e **os dois** caminhos de arquivo, e o exit é `1`

### Requirement: Regra por linha, com mapa de colunas

Uma regra canônica SHALL representar **uma linha** de um quadro e SHALL conter as colunas de
valor daquela linha em `columns`. Os filtros declarados em `filters` SHALL valer para todas as
colunas da regra. Cada coluna SHALL declarar suas contas com sinal explícito (`+` ou `-`).
NÃO DEVE existir uma regra por célula.

#### Scenario: linha do BO com quatro colunas

- **GIVEN** o IPC07 p. 8, Quadro Principal, linha `L2`
- **WHEN** a regra `bo.quadro_principal.receitas.l2` é lida
- **THEN** ela declara `filters` com `natureza_receita in ("1100.00.00", "7100.00.00")`
- **AND** declara 4 colunas: `previsao_inicial`, `previsao_atualizada`, `receitas_realizadas` e
  `saldo`
- **AND** `previsao_atualizada` inclui `5.2.1.1.0.00.00` e `5.2.1.2.0.00.00` com sinal `+`
- **AND** `saldo` é calculada como `receitas_realizadas - previsao_atualizada`

#### Scenario: coluna com conta de sinal negativo

- **GIVEN** o IPC06 p. 10, linha `L2`, cuja regra é `6.2.1.2.0.00.00 - 6.2.1.3.0.00.00`
- **WHEN** a regra é lida
- **THEN** a coluna declara `6.2.1.2.0.00.00` com sinal `+` e `6.2.1.3.0.00.00` com sinal `-`

### Requirement: Filtros com operadores de conjunto fechado

Um filtro SHALL declarar `field`, `operator` e `values`. `field` SHALL pertencer ao conjunto
definido no schema; `operator` SHALL pertencer ao enum definido no schema. A validação SHALL
rejeitar `field` ou `operator` fora desses conjuntos.

#### Scenario: operador inválido é rejeitado

- **WHEN** uma regra declara `operator: matches_regex`
- **THEN** a validação reporta operador inválido para o filtro e termina com exit `1`

#### Scenario: campo de filtro inválido é rejeitado

- **WHEN** uma regra declara `field: cod_ibge`
- **THEN** a validação reporta campo de filtro não suportado e termina com exit `1`

### Requirement: Cálculo por referência a outras regras, sem ciclos

Uma linha composta por outras linhas SHALL declarar o cálculo por `calculation.references`,
apontando para `rule_id` existentes, com o sinal de cada componente. A regra composta NÃO DEVE
duplicar os filtros nem as contas das regras referenciadas. A validação SHALL rejeitar referência
a `rule_id` inexistente e SHALL rejeitar ciclo de dependência.

#### Scenario: soma de linhas

- **GIVEN** o IPC07 p. 8, linha `L1 Receitas Correntes (I) = (L2 + L3 + L4 + L5 + L6 + L7 + L8 + L9)`
- **WHEN** a regra `bo.quadro_principal.receitas.l1` é lida
- **THEN** ela declara 8 referências, todas com sinal `+`, e **nenhuma** conta contábil própria

#### Scenario: subtração de linhas

- **GIVEN** o IPC05 p. 9, linha `L19 RESULTADO PATRIMONIAL DO PERÍODO = (L1 – L9)`
- **WHEN** a regra é lida
- **THEN** ela declara `L1` com sinal `+` e `L9` com sinal `-`

#### Scenario: referência inexistente é rejeitada

- **WHEN** uma regra referencia `bo.quadro_principal.receitas.l99`, que não existe
- **THEN** o erro nomeia o `rule_id` órfão, a regra de origem e o `arquivo:linha`, e o exit é `1`

#### Scenario: ciclo de dependência é rejeitado

- **GIVEN** `A` referencia `B` e `B` referencia `A`
- **WHEN** a validação é executada
- **THEN** o erro imprime o caminho completo do ciclo e termina com exit `1`

### Requirement: Guarda condicional no cálculo

Quando o documento condiciona a linha ao sinal do resultado, a regra SHALL declarar essa condição
de forma explícita em `calculation.condition`. A regra NÃO DEVE registrar a condição apenas como
texto descritivo.

#### Scenario: déficit do BO

- **GIVEN** o IPC07 p. 9, linha `L25 Déficit (VI) = (L48 - L24)`, "Somente quando o resultado for
  deficitário"
- **WHEN** a regra é lida
- **THEN** o cálculo declara as referências `L48` (`+`) e `L24` (`-`)
- **AND** declara a condição de que o valor só é apresentado quando o resultado for positivo após
  essa subtração
- **AND** a condição é legível por máquina, não somente em `description`

### Requirement: Ambiguidade documental é declarada, nunca interpretada

Quando o documento não permitir determinar a regra com segurança, a regra SHALL ter
`status: review_required` e `review.reason` descrevendo a lacuna e citando o item do documento.
A regra NÃO DEVE escolher uma interpretação. Regra que dependa de placeholder não resolvido do
documento (por exemplo `<nas fontes aplicáveis>`, `<conta de controle>`, `<contas sob demanda>`,
`(somente saldo a executar)`) NÃO DEVE ter `status: validated`.

#### Scenario: placeholder sem resolução documental no IPC06

- **GIVEN** as linhas `L22`, `L23`, `L55`, `L56` do IPC06, que declaram `<conta de controle>`, e
  `L28`, `L61`, que declaram `<contas sob demanda>`
- **WHEN** a validação é executada
- **THEN** nenhuma dessas regras tem `status: validated`
- **AND** a validação falha com exit `1` caso alguma tenha

#### Scenario: erro de digitação do PDF é preservado

- **GIVEN** o IPC08 p. 14, quadro b, que grafa `45.80.66` sem o primeiro ponto
- **WHEN** a regra correspondente é lida
- **THEN** `evidence.text` preserva a grafia literal do documento
- **AND** a regra tem `status: review_required` com o motivo declarado
- **AND** a base NÃO contém uma versão corrigida sem decisão registrada

### Requirement: Regras gerais do documento como policy referenciável

Regra geral que valha para todo um demonstrativo SHALL ser representada uma única vez como
policy, com sua própria `source`, e SHALL ser referenciada pelas regras que a ela se sujeitam.
NÃO DEVE ser replicada dentro de cada regra de linha.

#### Scenario: exclusão de contas intraorçamentárias

- **GIVEN** o IPC04 item 9 e o IPC05 item 16, que determinam deduzir as contas de nível
  intraorçamentário (5º nível = 2) **inclusive as eventualmente criadas pelo ente**
- **WHEN** a base é lida
- **THEN** existe uma policy declarando essa exclusão estrutural, com `source` própria
- **AND** as regras de linha do BP e da DVP referenciam essa policy
- **AND** as exclusões nominais que a matriz do PDF lista continuam registradas na regra, como
  exemplificação da policy, não como lista fechada

#### Scenario: consolidado versus órgão isolado

- **GIVEN** o IPC04 item 8 e o IPC05 item 15, que restringem as exclusões de intra ao
  consolidado do ente
- **WHEN** a policy de exclusão de intra é lida
- **THEN** ela declara explicitamente que se aplica ao consolidado do ente e não ao levantamento
  de órgão ou unidade isolada

### Requirement: Versionamento por edição de documento

Toda regra SHALL declarar `version` com `source_document`, `edition` e `valid_from`.
`valid_until` SHALL ser `null` quando o documento não declarar fim de vigência.
Atualização de um IPC NÃO DEVE sobrescrever as regras da edição anterior.

#### Scenario: duas edições coexistem

- **GIVEN** que o IPC06 está na edição 2024-06 e o IPC07 na edição 2020-01
- **WHEN** a base é lida
- **THEN** cada regra declara a edição do seu próprio documento de origem
- **AND** nenhuma regra herda a edição de outro documento

#### Scenario: fim de vigência não declarado

- **WHEN** o documento de origem não declara data de fim de vigência
- **THEN** a regra tem `valid_until: null`
- **AND** a base NÃO contém uma data de fim inferida

### Requirement: Integridade dos documentos de origem

Cada documento de origem SHALL ter `metadata.yaml` registrando nome do arquivo, número de
páginas e SHA-256. Os PDFs originais NÃO DEVEM ser alterados. A verificação de integridade SHALL
falhar quando o hash divergir.

#### Scenario: hash confere

- **WHEN** a verificação de fontes é executada sobre os 5 PDFs
- **THEN** os 5 hashes conferem e o exit é `0`

#### Scenario: hash divergente

- **GIVEN** que um PDF foi substituído por outra edição
- **WHEN** a verificação de fontes é executada
- **THEN** o erro nomeia o documento, o hash esperado e o obtido, e o exit é `1`

### Requirement: Índice de regras para localização direta

A base SHALL manter um índice mapeando cada `rule_id` para arquivo, demonstrativo, quadro,
documento e página. O índice SHALL ser gerado a partir dos YAMLs, nunca editado à mão.

#### Scenario: localizar regra pelo índice

- **GIVEN** o índice gerado
- **WHEN** `bo.quadro_principal.receitas.l2` é consultado
- **THEN** o índice devolve `file`, `demonstrativo: BO`, `quadro: QUADRO_PRINCIPAL`,
  `document: IPC07` e `page: 8`

#### Scenario: índice desatualizado é detectado

- **GIVEN** uma regra nova que não está no índice
- **WHEN** a validação é executada
- **THEN** ela reporta o índice desatualizado e termina com exit `1`

### Requirement: Proveniência e estado de revisão explícitos

Toda regra SHALL declarar `status` em `draft | extracted | review_required | validated |
deprecated` e SHALL declarar `provenance` com `extraction_method` e `extracted_at`. Regra
extraída automaticamente NÃO DEVE nascer `validated`. Campo de revisor NÃO DEVE ser preenchido
com nome inventado.

#### Scenario: extração automática não é validada

- **WHEN** uma regra é gerada por extração automática
- **THEN** seu `status` é `extracted` ou `review_required`, e `review.required` é `true`

#### Scenario: revisor ausente

- **WHEN** nenhuma revisão humana ocorreu
- **THEN** o bloco `review` não declara revisor
- **AND** a validação NÃO exige revisor para aceitar a regra

### Requirement: Decisão que resolve ambiguidade é registrada na regra

Quando uma ambiguidade documental for resolvida por decisão registrada, e não pela leitura do
documento, a regra SHALL declarar a decisão em `provenance` com a data, e SHALL manter em
`evidence.text` a grafia literal do documento. A regra NÃO DEVE aparecer como se o documento
tivesse sido inequívoco.

#### Scenario: exclusões do IPC05 resolvidas por decisão

- **GIVEN** a decisão de 2026-08-27 de tratar como equivalentes as exclusões do IPC05 escritas
  entre parênteses e sem parênteses, apesar de a nota de rodapé da coluna "Exclusões¹" não existir
  no PDF
- **WHEN** uma regra da DVP afetada é lida
- **THEN** todas as entradas da coluna "Exclusões" constam como exclusão, independentemente de
  parênteses
- **AND** `evidence.text` preserva a grafia original, com os parênteses onde o PDF os traz
- **AND** `provenance` registra que a equivalência vem de decisão datada, não do documento
- **AND** a regra NÃO fica `review_required` por causa dessa ambiguidade

### Requirement: Atributo Financeiro / Permanente lido do registro do fato

O filtro de atributo Financeiro / Permanente SHALL usar o campo canônico
`financeiro_permanente`, com valores `1` para Financeiro e `2` para Permanente, lidos do registro
do fato. A regra NÃO DEVE derivar o atributo da conta contábil. A chave concreta em cada fonte de
dados SHALL vir de um arquivo de binding, não da regra.

#### Scenario: ativo financeiro do BP

- **GIVEN** o IPC04 p. 11, `L2 Ativo Financeiro`
- **WHEN** a regra `bp.ativos_passivos.l2` é lida
- **THEN** ela filtra contas de classe 1 com `financeiro_permanente equals 1`
- **AND** referencia a policy de exclusão das contas intraorçamentárias
- **AND** NÃO contém lista de contas classificadas como financeiras

#### Scenario: chave da fonte de dados fora da regra

- **WHEN** o binding do campo `financeiro_permanente` é lido
- **THEN** ele mapeia `siconfi -> financeiro_permanente` e `publicsoft -> financeiroPermanente`
- **AND** nenhuma regra canônica menciona `financeiroPermanente`

#### Scenario: valor incompatível com o indicador da conta

- **GIVEN** que o PCASP marca a conta como `Permanente`
- **WHEN** um registro dessa conta traz `financeiro_permanente = 1`
- **THEN** a validação de domínio reporta incompatibilidade entre registro e indicador da conta
- **AND** o valor NÃO é reclassificado em silêncio

#### Scenario: conta que aceita os dois valores

- **GIVEN** que 924 das 2.565 contas de classe 1 e 2 do PCASP têm indicador
  `Financeiro/Permanente`
- **WHEN** um registro dessas contas traz `1` ou `2`
- **THEN** ambos são aceitos, e é o valor do registro que decide a linha

### Requirement: Fonte de recurso resolvida por nomenclatura, com as exceções declaradas

Quando a linha do demonstrativo se referir a fonte / destinação de recurso, a regra SHALL declarar
as fontes por código, e SHALL marcar `provenance.extraction_method: derived` com o critério de
derivação por escrito. Quando não houver correspondência de nomenclatura que sustente a
derivação, a regra SHALL ficar `status: review_required`.

#### Scenario: vinculação com correspondência de nome literal

- **GIVEN** o IPC06 `L12 Recursos Vinculados ao RPPS - Fundo em Capitalização (Plano
  Previdenciário)` e a fonte `800`, de nomenclatura idêntica na tabela da STN
- **WHEN** a regra é lida
- **THEN** ela filtra `fonte_recurso in ("800")`
- **AND** `provenance.extraction_method` é `derived`, com o critério de igualdade de nomenclatura
  declarado

#### Scenario: vinculação sem correspondência permanece em revisão

- **GIVEN** o IPC06 `L7 Recursos Vinculados à Previdência Social (Exceto ao RPPS)`, onde a fonte
  `803` (SPSM) está citada na nota de rodapé 2 mas a fonte `804` não é citada por nenhum documento
- **WHEN** a regra é lida
- **THEN** ela tem `status: review_required`
- **AND** `review.reason` nomeia a fonte `804` como não confirmada

#### Scenario: colisão entre outras vinculações e fontes extraorçamentárias

- **GIVEN** o IPC06 `L10 Outras Vinculações` e as fontes `860`–`869`, nomeadas "Recursos
  Extraorçamentários", já alcançadas pelo filtro `<fontes extraorçamentárias>` de `L27`/`L60`
- **WHEN** a regra é lida
- **THEN** ela tem `status: review_required`
- **AND** `review.reason` declara o risco de contagem em duplicidade

### Requirement: Códigos conferidos contra as tabelas oficiais da STN

Todo código citado em regra — conta contábil, natureza de receita, natureza de despesa, função,
subfunção e fonte de recurso — SHALL ser conferido contra as tabelas de `docs/contas-stn/`. Código
ausente da tabela oficial SHALL levar a regra a `status: review_required`, com o candidato mais
próximo registrado em `review.reason`. A validação NÃO DEVE substituir o código pelo candidato.
As tabelas da STN NÃO DEVEM ser alteradas.

#### Scenario: código válido

- **WHEN** uma regra cita a conta `6.2.1.2.0.00.00`, presente no PCASP
- **THEN** a validação aceita o código

#### Scenario: erro de digitação do PDF é detectado, não corrigido

- **GIVEN** o IPC08 p. 14, quadro b, que grafa `45.80.66` sem o primeiro ponto
- **WHEN** a validação confere o código contra a tabela de natureza de despesa
- **THEN** ela reporta código inexistente
- **AND** a regra fica `review_required` com o candidato registrado em `review.reason`
- **AND** o valor de `literal` na regra continua sendo `45.80.66`

#### Scenario: tabela da STN alterada

- **GIVEN** que o SHA-256 de `docs/contas-stn/PCASP.md` registrado em
  `knowledge/sources/stn/metadata.yaml` não confere com o arquivo
- **WHEN** a verificação de fontes é executada
- **THEN** ela reporta a tabela, o hash esperado e o obtido, e termina com exit `1`

### Requirement: Cobertura completa dos quadros dos IPC 04 a 08

A base SHALL conter uma regra para cada uma das 309 linhas de regra dos 15 quadros dos IPC 04 a
08, conforme a contagem medida em `docs/source-analysis.md` §3. A validação SHALL reportar a
contagem por demonstrativo. Linhas declaradas não normativas pelo próprio documento NÃO DEVEM
gerar regra.

#### Scenario: contagem por demonstrativo

- **WHEN** a validação é executada sobre a base completa
- **THEN** ela reporta BP 57, DVP 19, BF 80, BO 69, DFC 84 — total 309 regras de linha

#### Scenario: quadros anexos sugeridos não geram regra

- **GIVEN** que o IPC05 item 21 declara os 16 quadros anexos como sugestões e não exaustivos
- **WHEN** a base é lida
- **THEN** nenhuma regra executável é derivada desses quadros

### Requirement: Regra legível sem consultar o PDF

Dado apenas um `rule_id`, SHALL ser possível obter demonstrativo, quadro, linha e sua descrição,
filtros, colunas com suas contas e sinais, cálculo, dependências, status e a referência exata de
página — sem abrir o PDF de origem.

#### Scenario: leitura cega de uma regra

- **GIVEN** apenas o `rule_id` `bp.ativos_passivos.l7`
- **WHEN** a regra é lida da base
- **THEN** ficam determinados: demonstrativo BP, quadro dos Ativos e Passivos Financeiros e
  Permanentes, linha `L7 Saldo Patrimonial`, cálculo `L1 - L4`, e `source` IPC04 p. 11
- **AND** nenhuma informação necessária para implementar a regra fica só no PDF
