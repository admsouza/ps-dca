# dca/balanco-patrimonial — Delta spec

## Purpose

Apurar o Balanço Patrimonial (IPC 04, ed. 2020-01) a partir da base canônica em
`knowledge/rules/bp/` e da MSC de encerramento, produzindo matriz, template de apresentação,
procedência e diagnóstico no mesmo contrato do Balanço Orçamentário e do Balanço Financeiro, e
conferível contra o `DCA-Anexo I-AB` publicado pelo `tt/dca`.

O motor de matriz, saldo e filtros é o mesmo do BO e do BF. Esta capability acrescenta o atributo
Financeiro/Permanente do registro da MSC. Nada aqui altera o comportamento do BO nem do BF.

## ADDED Requirements

### Requirement: Quadro Principal apurado pela posição de encerramento

O sistema SHALL apurar as 40 linhas do Quadro Principal do BP nas colunas `exercicio_atual` e
`exercicio_anterior`. As contas SHALL ser lidas da `MSCE` com saldo de **encerramento** da
competência 12: do exercício apurado na coluna atual e do exercício imediatamente anterior na
coluna anterior, ambas pelo **mesmo** mapa de regras. Linhas totalizadoras SHALL sair da
`calculation` declarada na regra, nunca de soma implícita por nível.

#### Scenario: caixa de Cuitegi 2025

- **GIVEN** a MSC de encerramento de Cuitegi/PB (`2505204`), exercício 2025
- **WHEN** o BP é apurado
- **THEN** `L3` Caixa e Equivalentes de Caixa, coluna `exercicio_atual`, é 26.286.597,15
- **AND** a coluna `exercicio_anterior` da mesma linha é 19.812.433,77

#### Scenario: exclusão declarada na linha

- **GIVEN** `bp.quadro_principal.ativo.l3`, que declara `1.1.1` com exclusão de `1.1.1.1.2`
- **WHEN** existe saldo em `111120000`
- **THEN** esse saldo NÃO entra em `L3`

#### Scenario: coluna anterior lê o encerramento do exercício anterior

- **WHEN** o BP de 2025 é apurado
- **THEN** a coluna `exercicio_anterior` é igual, célula a célula, à coluna `exercicio_atual` do BP
  de 2024 apurado com o mesmo mapa

### Requirement: Equilíbrio do balanço declarado

O resultado SHALL conferir `L1 ATIVO = L15 PASSIVO E PATRIMÔNIO LÍQUIDO` em cada coluna e publicar a
diferença em `diagnostico.equilibrio`. Quebra de equilíbrio NÃO DEVE impedir a publicação nem ser
compensada em nenhuma linha.

As exclusões intra-OFSS que o IPC 04 declara linha a linha (5º nível = 2) SHALL ser aplicadas mesmo
quando quebram o equilíbrio (decisão P8 do PO, 2026-10-07). O balanço do ente só fecha quando o intra
é recíproco entre ativo e passivo e o PL intra é zero. Medido em 2025: João Pessoa +5.946.040.575,02
(superávit acumulado intra em `2.3.7.x.2`) e Cuitegi −2.004.721,69.

#### Scenario: balanço fecha

- **GIVEN** o BP de Cuitegi 2025
- **WHEN** a apuração termina
- **THEN** `L1` e `L15` da coluna `exercicio_atual` valem 76.314.331,92
- **AND** `diagnostico.equilibrio.exercicio_atual` é 0,00

#### Scenario: balanço não fecha

- **GIVEN** uma MSC em que ativo e passivo + PL diferem em 10,00
- **WHEN** o BP é apurado
- **THEN** o resultado é publicado
- **AND** `diagnostico.equilibrio` declara a diferença de 10,00 na coluna afetada

### Requirement: Atributo Financeiro/Permanente lido do registro da MSC

O registro da MSC SHALL carregar o atributo Financeiro/Permanente informado pela fonte
(`financeiro_permanente` no SICONFI, `financeiroPermanente` na PublicSoft; `1` = F, `2` = P). O
atributo SHALL ser declarado **por termo de conta**, como o IPC 04 o escreve ("2.1.0.0.0.00.00,
Atributo Financeiro (F) + … + 6.3.1.1.0.00.00"): o termo qualificado só soma registros com o mesmo
atributo, e o termo sem qualificador soma todos. O atributo NÃO DEVE ser inferido do grupo da conta
nem do indicador do PCASP.

Registro sem atributo, ou com valor fora de `1`/`2`, numa conta coberta por termo qualificado NÃO DEVE
entrar na linha e SHALL aparecer em `diagnostico.residuos` com `campo: financeiro_permanente`.

#### Scenario: ativo financeiro pelo atributo do fato

- **GIVEN** dois registros da conta `111110100`, um com `financeiro_permanente: "1"` (100,00) e
  outro com `"2"` (30,00)
- **WHEN** o Quadro dos Ativos e Passivos Financeiros e Permanentes é apurado
- **THEN** `L2` Ativo Financeiro recebe 100,00
- **AND** `L3` Ativo Permanente recebe 30,00

#### Scenario: termo sem qualificador soma todos os registros

- **GIVEN** `L5` Passivo Financeiro, com `2.1` qualificado F e `6.3.1.1` sem qualificador
- **AND** um registro de `631100000` sem atributo (70.972,63) e um de `211110100` com F (100,00)
- **WHEN** o quadro F/P é apurado
- **THEN** `L5` é 71.072,63

#### Scenario: atributo ausente vira resíduo

- **GIVEN** um registro de conta de classe 1 sem `financeiro_permanente`
- **WHEN** o quadro F/P é apurado
- **THEN** o registro não entra em `L2` nem em `L3`
- **AND** aparece em `diagnostico.residuos` com `campo: financeiro_permanente`

#### Scenario: as duas fontes normalizam para o mesmo valor

- **WHEN** a PublicSoft entrega `financeiroPermanente: 1` e o SICONFI entrega
  `financeiro_permanente: "1"`
- **THEN** os dois registros têm o mesmo atributo `F`

### Requirement: Quadro dos Ativos e Passivos Financeiros e Permanentes

O sistema SHALL apurar as 7 linhas do quadro (Lei 4.320/64, IPC 04) nas duas colunas.
`L1 ATIVO` SHALL ser igual a `L1` do Quadro Principal na mesma coluna, e `L7 Saldo Patrimonial`
SHALL ser `L1 − L4`.

#### Scenario: saldo patrimonial de Cuitegi 2025

- **GIVEN** o BP de Cuitegi 2025 com o atributo F/P presente na MSC
- **WHEN** o quadro F/P é apurado
- **THEN** `L7` Saldo Patrimonial é `L1 − L4` em centavos
- **AND** o valor é confrontado com (46.103.363,20) publicado, e a divergência, se houver, vai ao
  relatório de auditoria

#### Scenario: fonte sem o atributo

- **GIVEN** uma fonte cuja MSC não traz o atributo F/P em nenhum registro
- **WHEN** o BP é apurado
- **THEN** `L2`, `L3`, `L5` e `L6` do quadro F/P são `None`
- **AND** `diagnostico.sem_atributo_fp` é `true`
- **AND** o Quadro Principal sai íntegro

### Requirement: Linhas e quadros não apuráveis declarados

Linha com `status: review_required` e os quadros fora de escopo (Contas de Compensação e
Superávit/Déficit Financeiro por fonte) SHALL produzir células `None` com o motivo citando o
`review.blocker` da regra. Nenhuma dessas células SHALL valer `0`. O total que as contém SHALL somar
as parcelas apuradas e nomear as bloqueadas no diagnóstico.

#### Scenario: compensação fora de escopo

- **WHEN** o BP é apurado
- **THEN** as 10 linhas de `bp.contas_compensacao` são `None`
- **AND** cada uma traz em `diagnostico.nao_apuradas` o motivo do IPC 04 itens 12–13

#### Scenario: linha bloqueada não zera o total

- **GIVEN** `L34` `review_required` e as demais linhas do PL apuradas
- **WHEN** `L32` Patrimônio Líquido é calculada
- **THEN** `L32` é a soma das parcelas apuradas
- **AND** `L34` aparece no diagnóstico como parcela bloqueada

### Requirement: Conferência contra o DCA-Anexo I-AB

A homologação SHALL confrontar as linhas do IPC 04 com as contas publicadas pelo `tt/dca` no
`I-AB`, por de-para fixo (`P1`→`L1`, `P1.1`→`L2`, `P1.2`→`L9`, `P2.1`→`L16`, `P2.2`→`L24`,
`P2.3`→`L32`, `AtivoFinanceiro`→F/P `L2`, `AtivoPermanente`→F/P `L3`). O de-para NÃO DEVE ser
usado na apuração.

#### Scenario: âncoras de João Pessoa 2025

- **GIVEN** o `I-AB` de João Pessoa/PB (`2507507`), exercício 2025, obtido do `tt/dca`
- **WHEN** o BP apurado da MSC é conferido
- **THEN** cada uma das 8 âncoras é listada com apurado, publicado e diferença
- **AND** nenhuma divergência é omitida

### Requirement: BP no pipeline

O BP SHALL ser apurado pelo mesmo job, rota e cache dos demais anexos implementados, com base
canônica `bp`, e SHALL constar no percurso completo (`POST /batch-jobs`). A procedência SHALL
declarar matriz `MSCE`, tipo de saldo `encerramento`, competência e `versao_regras` do IPC 04.

#### Scenario: resumo deixa de reportar sem_cache

- **WHEN** o percurso completo roda para um ente com MSC de encerramento
- **THEN** o BP aparece com status de apurado, não `sem_cache`

#### Scenario: leitura só pelo par do BP

- **WHEN** o BP é apurado
- **THEN** toda leitura da MSC usa a matriz `MSCE` com saldo de encerramento, classes 1, 2 e 6, no
  exercício e no exercício anterior
- **AND** nenhum parâmetro do pedido permite outro par: o par é do demonstrativo (`fonte-msc`)
