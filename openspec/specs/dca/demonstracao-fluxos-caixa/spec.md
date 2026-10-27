# dca/demonstracao-fluxos-caixa

> Comportamento acordado e em vigor. Mesclado das changes `ipc08-dfc-regras-canonicas`
> (arquivada em 2026-10-26), `dfc-apuracao-f1` e `dfc-naturezas-desdobramento`
> `dfc-naturezas-desdobramento` e `dfc-l25-residual` (arquivadas em 2026-10-27).
> Alterações entram por nova change, nunca por edição direta deste arquivo.

## Purpose

Garantir que cada uma das 84 linhas de regra da Demonstração dos Fluxos de Caixa definidas no
IPC 08 exista como regra canônica versionada e rastreável até a página do documento, no mesmo
contrato de BO, BF, BP e DVP. A apuração em Python fica para change posterior.

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

### Requirement: Apuração das 84 linhas pela MSC
A apuração SHALL ler a MSC pelo par já declarado em `dca/fonte-msc` — matriz de encerramento,
saldo de abertura, classes 1 a 6 — e produzir as 84 linhas em `exercicio_atual` e
`exercicio_anterior`. O saldo de cada célula SHALL ser tomado na direção da coluna. NÃO DEVE haver
alteração em `app/domain/` nem em `knowledge/rules/dfc/`.

#### Scenario: as 84 linhas apuram
- **GIVEN** a MSC de um ente com registros nas classes 1 a 6
- **WHEN** a DFC é apurada
- **THEN** nenhuma das 84 linhas fica não apurada por "referências sem coluna em comum"

#### Scenario: fonte sem registros não vira zero
- **GIVEN** uma fonte que não devolve registro nenhum
- **WHEN** a DFC é apurada
- **THEN** a coluna sai não apurada (`None`) e o diagnóstico marca `sem_dados`

### Requirement: Linha sem conta é informada, não contamina o total
`L16`, `L21` e `L30` NÃO DEVEM ter conta apurada: SHALL aceitar valor digitado pelo contador, no
mesmo mecanismo do Balanço Financeiro, e SHALL valer `0,00` na agregadora quando não informadas.
Código fora de `{L16, L21, L30}` e valor não decimal SHALL ser recusado antes de apurar. A
agregadora que as referencia NÃO DEVE ficar não apurada por causa delas.

#### Scenario: L16 não informada não derruba L12
- **WHEN** a DFC é apurada sem valor informado para `L16`
- **THEN** `L16` vale `0,00` na soma de `L12`, `L12` apura, e `L16` consta como informável no
  diagnóstico

#### Scenario: L16 informada entra no total
- **WHEN** o contador informa `L16`
- **THEN** o valor aparece em `L16` e soma em `L12`

#### Scenario: código fora da whitelist é recusado
- **WHEN** chega um valor informado para `L15`
- **THEN** a apuração é recusada antes de ler a MSC

### Requirement: Caixa inicial vem do exercício anterior
`L35` SHALL ser o saldo de `1.1.1.0.0.00.00` na MSC de **N−1**, e `L36` SHALL resultar de
`L34 + L35`. NÃO DEVE ser lido da MSC de N, que traz a posição final do exercício.

#### Scenario: L35 e L36 são as duas pontas do caixa
- **GIVEN** um ente cujo `1.1.1` vale `A` na MSC de N−1 e `B` na MSC de N
- **WHEN** a DFC é apurada para N
- **THEN** `L35` é `A` e `L36` é `B`

#### Scenario: sem MSC do exercício anterior
- **WHEN** não há MSC em N−1
- **THEN** `L35` sai não apurada, no mesmo contrato de BP, BF e DVP

### Requirement: A geração líquida fecha a variação do caixa
`L34` apurado SHALL ser igual à variação de `1.1.1.0.0.00.00` entre as MSC de N−1 e N, para o
mesmo conjunto de unidades. Esta é a conferência de aceite da apuração e NÃO DEVE depender do
demonstrativo publicado pelo ente, cujo recorte pode ser outro.

#### Scenario: identidade de caixa em Porto Alegre 2025
- **GIVEN** `1.1.1` valendo 2.785.855.199,20 na MSC de 2024 e 2.854.802.415,12 na de 2025
- **WHEN** a DFC de 2025 é apurada
- **THEN** `L34` é 68.947.215,92

#### Scenario: identidades do demonstrativo fecham sobre o apurado
- **WHEN** a DFC é apurada
- **THEN** `L2 = L3+…+L11`, `L12 = L13+…+L16`, `L1 = L2−L12`, `L34 = L1+L17+L26` e
  `L36 = L34+L35` fecham nas duas colunas

#### Scenario: os quadros auxiliares amarram no principal
- **WHEN** a DFC é apurada
- **THEN** `P.L10 = T.L7`, `P.L13 = F.L29`, `P.L14 = J.L4` e `P.L15 = T.L15`

### Requirement: A DFC é verificável sem rota
SHALL existir `python -m app.cli.dfc <ibge> <exercicio>`, imprimindo os quatro quadros com a
procedência e o diagnóstico, e `--json` com o mesmo conteúdo. NÃO DEVE exigir banco, fila nem
container.

#### Scenario: CLI imprime os quatro quadros
- **WHEN** `python -m app.cli.dfc 4314902 2025` roda contra a MSC
- **THEN** a saída traz as 84 linhas nos quatro quadros, a procedência com documento `IPC08` e o
  número de células não apuradas

### Requirement: O 00 do IPC 08 é a posição do desdobramento
Onde o IPC 08 grafa `00` seguido de um dígito na posição do desdobramento `DD2`, o `pattern`
SHALL ser o `DD2` real — `1.3.21.00.1.x` vira `132101`, que alcança `13210101`. O `literal` e o
`evidence.text` SHALL permanecer como o PDF grafa. A correção SHALL valer para os quatro
desdobramentos de `1.3.2.1` e os quatro de `7.3.2.1`, em `L9` (`in`) e `L5` (`not_in`), e NÃO
DEVE ser estendida por inferência às naturezas que a tabela da STN não confirma.

#### Scenario: a remuneração das disponibilidades apura
- **GIVEN** a MSC entrega `13210101` e `13210401`
- **WHEN** `dfc.quadro_principal.operacionais.l9` é lida
- **THEN** os patterns são `132101`, `132102`, `132103` e `132104` e os literais seguem
  `1.3.21.00.1.x` a `1.3.21.00.4.x`

#### Scenario: a exclusão que não casa fica declarada
- **GIVEN** que `7.3.21.00.31.x` tem dois dígitos onde as irmãs têm um
- **WHEN** `dfc.quadro_principal.operacionais.l5` é lida
- **THEN** o `status` é `review_required` e o `blocker` registra que a leitura não foi adivinhada

### Requirement: Outros desembolsos de investimentos é residual
`L25` SHALL ser apurada apenas sobre os registros que **não** atendem aos filtros de `L23` nem aos
de `L24`. A exclusão SHALL ser por registro, nunca por subtração de totais, e `L25` NÃO DEVE
resultar negativa por esse motivo. Os filtros declarados no YAML NÃO DEVEM mudar.

#### Scenario: aquisição de ativo não entra duas vezes
- **GIVEN** uma despesa paga de elemento 52 e modalidade 90, que atende aos filtros de `L23` e
  também aos de `L25`
- **WHEN** a DFC é apurada
- **THEN** o valor aparece só em `L23`, `L25` fica `0,00` e `L22` é igual a `L23`

#### Scenario: o que L23 exclui continua em L25
- **GIVEN** uma despesa que o `not_in` de `L23` recusa e que atende aos filtros de `L25`
- **WHEN** a DFC é apurada
- **THEN** ela entra em `L25` — a exclusão mútua tira de `L25` apenas o que de fato entrou em
  `L23` ou `L24`
