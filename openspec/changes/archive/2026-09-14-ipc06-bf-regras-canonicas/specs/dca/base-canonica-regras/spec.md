# dca/base-canonica-regras — Delta spec

> Change `ipc06-bf-regras-canonicas`. Estende a capability para o Balanço Financeiro (IPC 06,
> edição 2024-06). Os requisitos do IPC 07 continuam valendo sem alteração, exceto o de
> identificador, generalizado abaixo.

## ADDED Requirements

### Requirement: Cobertura completa dos dois quadros do IPC 06

A base SHALL conter uma regra para cada uma das **80** linhas dos 2 quadros do IPC 06:
**66** no Quadro Principal (`L1`–`L66`, pp. 10–13) e **14** no Quadro Anexo (`L1`–`L14`, pp. 14–15).
A seção "ESTRUTURA DO BALANÇO FINANCEIRO" (pp. 16–19) NÃO DEVE gerar regra executável; seus
rótulos e ordem entram apenas como metadado de apresentação. A validação SHALL reportar a
contagem por quadro e por status.

#### Scenario: contagem por quadro

- **WHEN** a validação é executada sobre a base do BF
- **THEN** ela reporta `quadro_principal 66 · quadro_anexo 14`, total 80
- **AND** a contagem do BO segue `quadro_principal 51 · rp_nao_processados 9 · rp_processados 9`

#### Scenario: os dois blocos do Quadro Principal são distinguidos

- **WHEN** as regras do Quadro Principal são lidas
- **THEN** `L1`–`L33` declaram `grupo: INGRESSOS` e `L34`–`L66` declaram `grupo: DISPENDIOS`
- **AND** o Quadro Anexo NÃO declara `grupo`

#### Scenario: estrutura de publicação não gera regra

- **GIVEN** as pp. 16–19, que trazem o layout de publicação do BF
- **WHEN** a base é lida
- **THEN** nenhuma regra executável é derivada dessas páginas

### Requirement: Identificador do Balanço Financeiro

Toda regra do BF SHALL ter `rule_id` no formato `bf.<quadro>.<grupo?>.<linha>`, único em toda a
base, com o segmento `<grupo>` presente no Quadro Principal e ausente no Quadro Anexo. Linhas
homônimas entre BO e BF NÃO DEVEM colidir.

#### Scenario: identificador de linha de ingresso

- **WHEN** a regra da linha `L2 Recursos Não Vinculados` do Quadro Principal é lida
- **THEN** seu `rule_id` é `bf.quadro_principal.ingressos.l2`

#### Scenario: linha do Quadro Anexo não colide com a do Quadro Principal

- **GIVEN** que ambos os quadros do BF têm uma linha `L1`
- **WHEN** a base é lida
- **THEN** os identificadores são `bf.quadro_principal.ingressos.l1` e `bf.quadro_anexo.l1`
- **AND** nenhum deles colide com `bo.quadro_principal.receitas.l1`

### Requirement: Colunas de valor do Balanço Financeiro

O número de colunas de valor por quadro do BF SHALL ser: Quadro Principal **2** —
`exercicio_atual` e `exercicio_anterior`; Quadro Anexo **6** —
`receita_orcamentaria_atual (a)`, `deducoes_atual (b)`, `saldo_atual (c)`,
`receita_orcamentaria_anterior (d)`, `deducoes_anterior (e)`, `saldo_anterior (f)`.
As colunas `(c)` e `(f)` SHALL ser calculadas como `(a) - (b)` e `(d) - (e)` e NÃO DEVEM declarar
contas próprias. A coluna "Nota" (item 26) NÃO É coluna de valor e NÃO DEVE virar coluna da regra.
A validação SHALL rejeitar coluna fora do conjunto do quadro.

#### Scenario: linha de ingresso com duas colunas

- **GIVEN** o IPC 06 p. 10, `L2 Recursos Não Vinculados`, `6.2.1.2.0.00.00 - 6.2.1.3.0.00.00`
- **WHEN** `bf.quadro_principal.ingressos.l2` é lida
- **THEN** ela declara as colunas `exercicio_atual` e `exercicio_anterior`
- **AND** cada coluna declara `6.2.1.2.0.00.00` com sinal `+` e `6.2.1.3.0.00.00` com sinal `-`

#### Scenario: saldo do Quadro Anexo é calculado, não somado de contas

- **GIVEN** o IPC 06 p. 14, Quadro Anexo, `L1 Recursos Não vinculados`
- **WHEN** a regra `bf.quadro_anexo.l1` é lida
- **THEN** `saldo_atual` declara `calculation.references` com `receita_orcamentaria_atual` (`+`) e
  `deducoes_atual` (`-`)
- **AND** `saldo_atual` NÃO declara `accounts`

#### Scenario: coluna inexistente é rejeitada

- **WHEN** uma regra do BF declara a coluna `previsao_inicial`
- **THEN** a validação reporta coluna não suportada para o quadro e termina com exit `1`

### Requirement: Filtro por fonte ou destinação de recursos

O conjunto de `field` do IPC 06 SHALL ser `{ conta_contabil, fonte_recurso }`; `operator` segue
`{ in, not_in }`. Toda linha cujo literal traga `<nas fontes aplicáveis>` SHALL declarar um filtro
`fonte_recurso`, e o subgrupo normativo dos itens 23 e 24 SHALL ser identificável na regra. A
regra NÃO DEVE enumerar as fontes criadas livremente pelo ente (item 22). A validação SHALL
rejeitar `fonte_recurso` em regra do IPC 07 e `natureza_receita`, `natureza_despesa`, `funcao` ou
`subfuncao` em regra do IPC 06.

Os valores de `fonte_recurso` SHALL ser os **códigos principais de 3 dígitos** do bloco 500–999 do
Anexo I da Portaria STN nº 710/2021, conforme `docs/contas-stn/fontes-recursos-stn-2026.xlsx`. O
prefixo de exercício (`1` corrente, `2` anteriores, `9` condicionados) NÃO DEVE entrar no valor: ele
não separa subgrupo. O agrupamento SHALL ser:

| Linha (ingresso / dispêndio) | Subgrupo | Fontes |
|---|---|---|
| L2 / L35 | Não Vinculados | `500`–`503` |
| L4 / L37 | Educação | `540`–`599` |
| L5 / L38 | Saúde | `600`–`659` |
| L6 / L39 | Assistência Social | `660`–`669` |
| L7 / L40 | Previdência Social (exceto RPPS) | `803`, `804` |
| L8 / L41 | Demais Vinculações Decorrentes de Transferências | `700`–`749` |
| L9 / L42 | Demais Vinculações Legais | `750`–`799` |
| L10 / L43 | Outras Vinculações | `880`–`899` |
| L12 / L45 | RPPS — Fundo em Capitalização | `800` |
| L13 / L46 | RPPS — Fundo em Repartição | `801` |
| L14 / L47 | RPPS — Taxa de Administração | `802` |
| L27 / L60 | fontes extraorçamentárias | `860`–`869` |

Todo código citado SHALL existir em `docs/contas-stn/fonte-recursos.md`; código ausente SHALL levar
a regra a `review_required`, como já vale para os demais domínios. O bloco 000–499 (União) NÃO DEVE
aparecer em regra do BF.

#### Scenario: linhas de mesmo mapeamento contábil separadas por fonte

- **GIVEN** o IPC 06 pp. 10–11, em que `L2`, `L4`, `L5`, `L6`, `L7`, `L8`, `L9`, `L10`, `L12`,
  `L13` e `L14` declaram todas `6.2.1.2.0.00.00 - 6.2.1.3.0.00.00 <nas fontes aplicáveis>`
- **WHEN** essas regras são lidas
- **THEN** todas declaram o mesmo par de contas nas duas colunas
- **AND** cada uma declara um filtro `fonte_recurso` distinto, correspondente ao seu subgrupo
- **AND** nenhuma delas fica `review_required` por repetir as contas

#### Scenario: campo do BO é rejeitado no BF

- **WHEN** uma regra do BF declara `field: natureza_despesa`
- **THEN** a validação reporta campo não suportado para o IPC 06 e termina com exit `1`

#### Scenario: campo do BF é rejeitado no BO

- **WHEN** uma regra do BO declara `field: fonte_recurso`
- **THEN** a validação reporta campo não suportado para o IPC 07 e termina com exit `1`

#### Scenario: RPPS separado em três linhas por fonte única

- **GIVEN** o IPC 06 p. 11, `L12`, `L13` e `L14`
- **WHEN** as três regras são lidas
- **THEN** declaram, respectivamente, `fonte_recurso in ("800")`, `("801")` e `("802")`
- **AND** `L11 Recursos Vinculados ao RPPS` é `L12 + L13 + L14`, sem filtro de fonte próprio

#### Scenario: previdência exceto RPPS exclui as três fontes do RPPS

- **GIVEN** o IPC 06 p. 11 `L7` e o item 25, que cita o SPSM e os benefícios mantidos pelo ente
- **WHEN** `bf.quadro_principal.ingressos.l7` é lida
- **THEN** ela declara `fonte_recurso in ("803", "804")`
- **AND** NÃO inclui `800`, `801` nem `802`

#### Scenario: prefixo de exercício não entra no valor da fonte

- **WHEN** qualquer regra do BF com filtro de fonte é lida
- **THEN** todos os valores têm 3 dígitos
- **AND** nenhum valor é `1540`, `2540` ou `9540`

#### Scenario: fonte da União é rejeitada

- **WHEN** uma regra do BF declara `fonte_recurso in ("100")`
- **THEN** a validação reporta fonte fora do bloco 500–999 e termina com exit `1`

#### Scenario: linha sem fonte não declara o filtro

- **GIVEN** o IPC 06 p. 11, `L16 Transferências Recebidas para a Execução Orçamentária`,
  `4.5.1.1.0.00.00`, sem `<nas fontes aplicáveis>`
- **WHEN** a regra é lida
- **THEN** ela NÃO declara filtro `fonte_recurso`

### Requirement: Conta patrimonial apurada por saldo em data, não por movimento do período

As linhas de Saldo do Exercício Anterior (`L29`–`L32`) e de Saldo para o Exercício Seguinte
(`L62`–`L65`) SHALL declarar, em cada conta, o momento do saldo: `saldo: inicial` ou
`saldo: final`, conforme o literal do IPC 06. Conta de classe 1 ou 2 usada nessas linhas SHALL
declarar `saldo`; a validação SHALL rejeitar a omissão. Linha de execução orçamentária ou de
movimento NÃO DEVE declarar `saldo`.

#### Scenario: caixa e equivalentes exceto RPPS, no saldo inicial

- **GIVEN** o IPC 06 p. 11, `L30 Caixa e Equivalentes de Caixa (exceto RPPS)`
- **WHEN** `bf.quadro_principal.ingressos.l30` é lida
- **THEN** ela declara `1.1.1.0.0.00.00` com sinal `+`, `1.1.1.1.1.06.00` com sinal `-` e
  `1.1.1.3.0.00.00` com sinal `-`
- **AND** as três contas declaram `saldo: inicial`

#### Scenario: a linha homóloga dos dispêndios usa o saldo final

- **GIVEN** o IPC 06 p. 13, `L63 Caixa e Equivalentes de Caixa (exceto RPPS)`
- **WHEN** `bf.quadro_principal.dispendios.l63` é lida
- **THEN** ela declara as mesmas três contas e sinais de `L30`
- **AND** as três declaram `saldo: final`

#### Scenario: saldo omitido em conta patrimonial é rejeitado

- **WHEN** `L31` declara `1.1.1.1.1.06.00` sem `saldo`
- **THEN** a validação reporta saldo não declarado, nomeia o `rule_id` e termina com exit `1`

#### Scenario: saldo declarado em linha de execução é rejeitado

- **WHEN** `bf.quadro_principal.ingressos.l25` declara `saldo` em `5.3.1.7.0.00.00`
- **THEN** a validação reporta saldo indevido e termina com exit `1`

### Requirement: Sentido do movimento nas linhas de depósitos restituíveis

`L27 Depósitos Restituíveis e Valores Vinculados` (ingressos, p. 11) e `L60` (dispêndios, p. 13)
declaram as mesmas contas `2.1.8.8.0.00.00` e `2.2.8.8.0.00.00`, distinguidas apenas pelo sentido
do movimento. A regra SHALL declarar `movimento: credor` em `L27` e `movimento: devedor` em `L60`.
NÃO DEVE ser usado o sinal da conta para representar esse sentido, porque as duas linhas somam
positivamente em seus respectivos totais.

#### Scenario: as duas linhas se distinguem pelo movimento

- **WHEN** `bf.quadro_principal.ingressos.l27` e `bf.quadro_principal.dispendios.l60` são lidas
- **THEN** ambas declaram `2.1.8.8.0.00.00` e `2.2.8.8.0.00.00` com sinal `+`
- **AND** a primeira declara `movimento: credor` e a segunda `movimento: devedor`
- **AND** ambas declaram o filtro de fontes extraorçamentárias do literal

### Requirement: Mapeamento não determinado pelo IPC 06 é declarado, nunca inventado

Linha cujo literal seja `<conta de controle>` (`L22`, `L23`, `L55`, `L56`) ou
`<contas sob demanda>` (`L28`, `L61`) SHALL ter `status: review_required` e `review.blocker`
citando o item e a página, enquanto não houver decisão registrada do PO. O candidato provável
SHALL ficar em `review.candidate` e NÃO DEVE ser aplicado em `columns` nem em `filters`. Havendo
decisão do PO, a regra SHALL registrar `provenance.decision` e sair de `review_required`, com o
literal preservado em `evidence.text`.

#### Scenario: conta de controle sem decisão

- **GIVEN** o IPC 06 p. 11, `L22 Resgates de Investimentos e Aplicações Financeiras`,
  `<conta de controle>`
- **WHEN** a regra é lida sem decisão do PO registrada
- **THEN** `status` é `review_required`, `review.blocker` cita o item 32 e a p. 9
- **AND** `columns` não declara conta alguma
- **AND** o candidato das classes 7 e 8 aparece apenas em `review.candidate`

#### Scenario: decisão do PO fecha o bloqueio

- **GIVEN** uma decisão registrada do PO para as contas de controle
- **WHEN** `L22`, `L23`, `L55` e `L56` são lidas
- **THEN** cada uma declara as contas decididas, registra `provenance.decision` e NÃO fica
  `review_required`
- **AND** `evidence.text` continua trazendo o literal `<conta de controle>`

### Requirement: Equilíbrio estrutural entre ingressos e dispêndios

`L33 TOTAL (VI) = (L1 + L15 + L21 + L24 + L29)` e `L66 TOTAL (XII) = (L34 + L48 + L54 + L57 + L62)`
SHALL ser declaradas como linhas de cálculo, sem contas próprias, e o Quadro Anexo SHALL fechar
`L14 TOTAL = (L1 + L2 + L10)` em cada uma das 6 colunas. A validação SHALL rejeitar total do BF
que declare conta contábil própria. `L33` SHALL pertencer ao grupo `INGRESSOS`, ainda que impressa
na p. 12 depois do bloco de dispêndios; o literal da ordem de impressão SHALL ficar em `evidence`.

#### Scenario: totais só agregam linhas

- **WHEN** `bf.quadro_principal.ingressos.l33` e `bf.quadro_principal.dispendios.l66` são lidas
- **THEN** cada uma declara 5 referências, todas com sinal `+`, para `rule_id` existentes
- **AND** nenhuma das duas declara `columns[*].accounts`
- **AND** a validação não detecta ciclo

#### Scenario: L33 é linha de ingresso, apesar da posição no PDF

- **GIVEN** que a p. 12 imprime `L33` após `L56`
- **WHEN** a regra é lida
- **THEN** seu `rule_id` é `bf.quadro_principal.ingressos.l33` e sua `ordem` é a do fim do bloco de
  ingressos
- **AND** `evidence.text` registra a posição física na p. 12

#### Scenario: total com conta própria é rejeitado

- **WHEN** `L66` declara `1.1.1.0.0.00.00` em `exercicio_atual`
- **THEN** a validação reporta total com conta própria e termina com exit `1`

### Requirement: Regras gerais do IPC 06 registradas como policies

As instruções gerais do IPC 06 que não pertencem a uma linha específica SHALL existir em
`knowledge/policies/ipc06.yaml`, cada uma com `policy_id`, `descricao`, `aplica_a`, `source` e
`evidence`, cobrindo no mínimo: receita orçamentária líquida das deduções (item 27), regime de
caixa para as contas de classes 3 e 4 (item 30), apenas o valor principal em `L22` e `L55`
(item 33), aberturas de saldo não exaustivas (item 37) e exclusão das transferências financeiras
intraorçamentárias já acompanhadas de execução orçamentária (item 38). Regra de linha afetada por
uma policy SHALL referenciá-la em `policies`.

#### Scenario: exclusão de intraorçamentárias vale para as linhas de execução

- **WHEN** as linhas de receita orçamentária (`L2`–`L14`) e de despesa orçamentária (`L35`–`L47`)
  são lidas
- **THEN** todas referenciam a policy do item 38
- **AND** a policy declara `source.page` 10 e `evidence.text` com o literal do item

#### Scenario: policy sem origem é rejeitada

- **WHEN** uma policy do IPC 06 não declara `source.page`
- **THEN** a validação reporta e termina com exit `1`

### Requirement: Integridade e versionamento da fonte IPC 06

`knowledge/sources/ipc06/metadata.yaml` SHALL registrar `document: IPC06`, arquivo, `pages: 19`,
`edition: "2024-06"` e o SHA-256 do PDF. Toda regra do BF SHALL declarar `version` com
`source_document: IPC06`, `edition: "2024-06"`, `valid_from` e `valid_until: null`. O PDF NÃO DEVE
ser copiado para dentro de `knowledge/`.

`knowledge/sources/stn/metadata.yaml` SHALL registrar também
`docs/contas-stn/fontes-recursos-stn-2026.xlsx` com seu SHA-256, por ser a evidência do
agrupamento de fontes por subgrupo. O arquivo é lido, nunca alterado.

#### Scenario: dois documentos íntegros

- **WHEN** a verificação de fontes é executada
- **THEN** ela reporta `2 documento(s)` e exit `0`
- **AND** confere as 8 tabelas da STN, incluindo o `.xlsx` do Anexo I

#### Scenario: Anexo I substituído por edição posterior

- **WHEN** `fontes-recursos-stn-2026.xlsx` é trocado sem atualizar o metadata
- **THEN** a verificação nomeia o arquivo, o hash esperado e o obtido, e o exit é `1`

#### Scenario: fim de vigência não declarado

- **WHEN** qualquer regra do BF é lida
- **THEN** `valid_until` é `null`

## MODIFIED Requirements

### Requirement: Identificador legível e estável

Toda regra SHALL ter `rule_id` no formato `<demonstrativo>.<quadro>.<grupo?>.<linha>`, em
minúsculas, com segmentos separados por ponto, único em toda a base. O primeiro segmento SHALL ser
o código do demonstrativo em minúsculas (`bo`, `bf`). O `rule_id` NÃO DEVE depender do caminho do
arquivo nem conter UUID. O segmento `<grupo>` SHALL estar presente sempre que o quadro separar
blocos — no Quadro Principal do BO (receitas × despesas) e no do BF (ingressos × dispêndios).

#### Scenario: identificador de linha de receita

- **WHEN** a regra da linha `L2` do Quadro Principal do BO é lida
- **THEN** seu `rule_id` é `bo.quadro_principal.receitas.l2`

#### Scenario: linhas homônimas em quadros diferentes

- **GIVEN** que o quadro de RP Não Processados e o de RP Processados **ambos** têm linhas `L1`–`L9`
- **WHEN** a base é lida
- **THEN** os identificadores são `bo.rp_nao_processados.l1` e `bo.rp_processados.l1`, distintos
- **AND** o número de `rule_id` distintos é igual ao número de regras carregadas

#### Scenario: linhas homônimas em demonstrativos diferentes

- **GIVEN** que o BO e o BF têm, cada um, uma linha `L1` no Quadro Principal
- **WHEN** a base é lida
- **THEN** os identificadores são `bo.quadro_principal.receitas.l1` e
  `bf.quadro_principal.ingressos.l1`, distintos

#### Scenario: identificador duplicado é rejeitado

- **GIVEN** duas regras com o mesmo `rule_id` em arquivos diferentes
- **WHEN** a validação é executada
- **THEN** o erro nomeia o `rule_id` e **os dois** caminhos de arquivo, e o exit é `1`
