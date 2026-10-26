# dca/demonstracao-fluxos-caixa — Delta spec

## Purpose

Garantir que cada uma das 84 linhas de regra da Demonstração dos Fluxos de Caixa definidas no
IPC 08 exista como regra canônica versionada e rastreável até a página do documento, no mesmo
contrato de BO, BF, BP e DVP. A apuração em Python fica para change posterior.

## ADDED Requirements

### Requirement: Oitenta e quatro regras em quatro quadros
A base canônica SHALL conter exatamente 84 regras da DFC, distribuídas em
`knowledge/rules/dfc/quadro_principal.yaml` (36, L1–L36),
`transferencias_recebidas_concedidas.yaml` (15, L1–L15),
`desembolsos_pessoal_por_funcao.yaml` (29, L1–L29) e
`juros_encargos_divida.yaml` (4, L1–L4). Cada `rule_id` SHALL seguir
`dfc.<quadro>.<grupo?>.l<n>`, em minúsculas. O demonstrativo SHALL ser `DFC`. NÃO DEVE existir
regra por célula nem por anexo `I-E`.

#### Scenario: contagem por quadro
- **GIVEN** a base em `knowledge/rules/dfc/`
- **WHEN** as regras são carregadas
- **THEN** o validador reporta DFC quadro_principal 36, transferencias_recebidas_concedidas 15,
  desembolsos_pessoal_por_funcao 29, juros_encargos_divida 4 — total 84

#### Scenario: identificadores de grupos do quadro principal
- **WHEN** as linhas L1, L17, L26 e L34 são lidas
- **THEN** os `rule_id` são `dfc.quadro_principal.operacionais.l1`,
  `dfc.quadro_principal.investimento.l17`, `dfc.quadro_principal.financiamento.l26` e
  `dfc.quadro_principal.caixa.l34`

### Requirement: Duas colunas, as mesmas contas
Toda linha com mapa de contas SHALL declarar `exercicio_atual` e `exercicio_anterior` com as
mesmas contas e o mesmo sinal. Linha agregadora NÃO DEVE declarar `columns`; SHALL declarar
`calculation.references` com `rule` e `sign`. A chave `on` é proibida.

#### Scenario: L3 nas duas colunas
- **WHEN** `dfc.quadro_principal.operacionais.l3` é lida
- **THEN** as duas colunas listam `6.2.1.2.0.00.00` com `sign: +` e `6.2.1.3.0.00.00` com
  `sign: '-'`

#### Scenario: L1 subtrai desembolsos
- **WHEN** `dfc.quadro_principal.operacionais.l1` é lida
- **THEN** as referências são L2 com `+` e L12 com `-`

#### Scenario: agregadora soma a própria linha Outros
- **GIVEN** o IPC 08 p. 11 grafa `L27 Ingressos (L28 + L29)`, sem L30, enquanto as demais
  agregadoras somam a própria linha Outros
- **WHEN** L2, L12, L18, L22, L27 e L31 do Quadro Principal são lidas
- **THEN** cada uma referencia com `+` a sua linha Outros — L11, L16, L21, L25, **L30** e L33 —
  e o literal do PDF permanece em `evidence.text` de L27, com a divergência em `review.reason`

### Requirement: Saldo inicial de caixa e geração líquida
L35 SHALL somar `1.1.1.0.0.00.00` com `saldo: inicial` nas duas colunas. L34 SHALL ser
L1 + L17 + L26. L36 SHALL ser L34 + L35. L36 NÃO DEVE declarar a conta de saldo final em
`columns`; a correspondência com o saldo final de `1.1.1.0.0.00.00` SHALL ficar na policy
`ipc08.soma_fluxos_igual_variacao_caixa`.

#### Scenario: L35 é saldo inicial
- **WHEN** `dfc.quadro_principal.caixa.l35` é lida
- **THEN** cada conta declara `pattern: '111'` e `saldo: inicial`

#### Scenario: L36 só referencia linhas
- **WHEN** `dfc.quadro_principal.caixa.l36` é lida
- **THEN** não há `columns` e as referências são L34 `+` e L35 `+`

### Requirement: Exclusões do PDF entram como filtro
A coluna Exclusões do IPC 08 SHALL virar `filters` com `operator: not_in` no campo da natureza
correspondente. NÃO DEVE virar `exclusion_groups` nem `visao: consolidado`. O IPC 08 não declara
a ressalva de órgão isolado do IPC 04 item 8.

#### Scenario: L5 exclui remuneração das disponibilidades
- **WHEN** `dfc.quadro_principal.operacionais.l5` é lida
- **THEN** há `natureza_receita` `in` `1.3.xx.xx.xx` e `7.3.xx.xx.xx` e `not_in` contendo
  `1.3.21.00.1.x` e `7.3.21.00.31.x`

### Requirement: Campos Outros sem mapeamento
L16, L21 e L30 do Quadro Principal SHALL existir, SHALL ter `status: review_required` e NÃO DEVE
declarar `columns`. Referenciam a policy `ipc08.outros_campos_nao_previstos` (item 17). L11, L25
e L33 TÊM mapeamento no quadro e SHALL declarar contas.

#### Scenario: L16 sem contas
- **WHEN** `dfc.quadro_principal.operacionais.l16` é lida
- **THEN** `status` é `review_required` e `columns` está ausente

### Requirement: Literal do PDF prevalece
Grafia divergente do PDF (N5) SHALL permanecer em `literal` e em `evidence.text`. O `pattern` é
a normalização em dígitos, inclusive quando o PDF omite ponto ou o duplica. NÃO DEVE haver
correção silenciosa.

#### Scenario: 45.80.66 permanece
- **GIVEN** o IPC 08 p. 9 e p. 14 grafam `45.80.66` sem o primeiro ponto
- **WHEN** L15 do Quadro Principal e L14 do quadro de transferências são lidas
- **THEN** o `literal` da exclusão é `45.80.66`

#### Scenario: ponto duplo em L9 das transferências concedidas
- **GIVEN** o IPC 08 p. 13 grafa `4.4..22.xx.xx`
- **WHEN** `dfc.transferencias_recebidas_concedidas.concedidas.l9` é lida
- **THEN** um valor de `natureza_despesa` tem `literal: 4.4..22.xx.xx`

### Requirement: Pessoal por função replica L13
L1–L28 do quadro de desembolsos por função SHALL usar as mesmas contas e as mesmas naturezas de
despesa de `dfc.quadro_principal.operacionais.l13`, cada uma com `funcao` igual ao número da
linha (`01`…`28`). L29 SHALL ser a soma de L1 a L28.

#### Scenario: L10 Saúde filtra função 10
- **WHEN** `dfc.desembolsos_pessoal_por_funcao.l10` é lida
- **THEN** `filters` inclui `funcao` `in` `10` e `natureza_despesa` contém `3.1.71.xx.xx`

### Requirement: Fonte MSC já decidida
A apuração futura SHALL usar `fonte_de("DFC")` = matriz de encerramento, saldo de abertura,
classes 1 a 6, já registrado em `dca/fonte-msc`. Esta change NÃO DEVE alterar esse par.

#### Scenario: DFC continua MSCE abertura
- **GIVEN** a spec `dca/fonte-msc`
- **WHEN** a base canônica da DFC é lida
- **THEN** nenhuma regra declara saldo de encerramento, salvo L35 que declara `saldo: inicial`
