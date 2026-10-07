# dca/balanco-patrimonial

> Comportamento acordado e em vigor. Mesclado da change `bp-apuracao-f1`, arquivada em 2026-10-07.
> Inclui `bp-anterior-publicado-siconfi` e `bp-espelho-iab`, arquivadas em 2026-10-07.
> Alterações entram por nova change, nunca por edição direta deste arquivo.

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

#### Scenario: coluna anterior lê o encerramento do exercício anterior

- **WHEN** o BP de 2025 é apurado
- **THEN** a coluna `exercicio_anterior` é igual, célula a célula, à coluna `exercicio_atual` do BP
  de 2024 apurado com o mesmo mapa

### Requirement: Equilíbrio do balanço declarado

O resultado SHALL conferir `L1 ATIVO = L15 PASSIVO E PATRIMÔNIO LÍQUIDO` em cada coluna e publicar a
diferença em `diagnostico.equilibrio`. Quebra de equilíbrio NÃO DEVE impedir a publicação nem ser
compensada em nenhuma linha.

O BP espelha o `DCA-Anexo I-AB` declarado (`bp-espelho-iab`, PO 2026-10-07): as exclusões
intra-OFSS do IPC 04 não são aplicadas, e o balanço fecha. Diferença diferente de zero aponta
inconsistência na matriz enviada pelo ente. Revoga a decisão P8-a de `bp-apuracao-f1`.

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

### Requirement: Origem da coluna do exercício anterior escolhida pelo usuário

A coluna `exercicio_anterior` do BP SHALL ter duas origens, escolhidas por quem apura no parâmetro
`origem_exercicio_anterior`:

| Origem | Valor | Como é apurada |
|---|---|---|
| Publicado (**padrão**) | `publicado_siconfi` | regras do IPC 04 sobre as contas folha do `DCA-Anexo I-AB` do exercício anterior, lido do `tt/dca` |
| MSC | `msce_exercicio_anterior` | `MSCE`/encerramento do exercício anterior, como hoje |

Pedido sem o parâmetro SHALL usar `publicado_siconfi`. A origem SHALL entrar na identidade do pedido
e na procedência (`origem_exercicio_anterior`). A coluna `exercicio_atual` SHALL continuar apurada da
MSC nas duas origens.

Conta folha é a conta publicada que não tem filha publicada. O valor publicado SHALL ser convertido
para saldo na direção da conta (o sinal do `I-AB` é o da posição) e passar pelas mesmas regras das
linhas do Quadro Principal (sem exclusão intra, `bp-espelho-iab`). NÃO DEVE haver dupla contagem da hierarquia publicada.

No quadro dos Ativos e Passivos Financeiros e Permanentes, `L2`, `L3`, `L5` e `L6` SHALL receber
`AtivoFinanceiro`, `AtivoPermanente`, `PassivoFinanceiro` e `PassivoPermanente` publicados; `L1`,
`L4` e `L7` saem da `calculation`, e `L7` SHALL ser conferido contra `SaldoPatrimonial` em
`diagnostico.conferencia_publicado`.

Ente sem `I-AB` publicado no ano anterior SHALL ter a coluna anterior `None` e
`diagnostico.sem_publicacao_exercicio_anterior: true`. A apuração NÃO DEVE cair para a MSC por
omissão.

#### Scenario: publicado é o padrão

- **WHEN** o BP é pedido sem `origem_exercicio_anterior`
- **THEN** a coluna anterior vem do `I-AB` do exercício anterior
- **AND** `procedencia.origem_exercicio_anterior` é `publicado_siconfi`

#### Scenario: MSC continua disponível e igual

- **WHEN** o BP é pedido com `origem_exercicio_anterior=msce_exercicio_anterior`
- **THEN** a coluna anterior sai igual, célula a célula, à apuração vigente antes desta change

#### Scenario: folha publicada, sem dupla contagem

- **GIVEN** o `I-AB` com `P1.1.1.0.0.00.00`, `P1.1.1.1.0.00.00` e `P1.1.1.1.1.00.00`, todos 100,00
- **WHEN** a coluna anterior é apurada pelo publicado
- **THEN** `L3` é 100,00, não 300,00

#### Scenario: intra entra no publicado

- **GIVEN** o `I-AB` com `P1.2.1.1.1.00.00` = 10,00 e `P1.2.1.1.2.00.00` (intra) = 90,00
- **WHEN** `L10` é apurada pelo publicado
- **THEN** `L10` é 100,00 — o BP espelha o `I-AB`, sem exclusão intra (`bp-espelho-iab`)

#### Scenario: quadro F/P pelo publicado

- **GIVEN** `AtivoFinanceiro`, `AtivoPermanente`, `PassivoFinanceiro`, `PassivoPermanente` e
  `SaldoPatrimonial` publicados
- **WHEN** o quadro F/P é apurado pelo publicado
- **THEN** `L2`, `L3`, `L5` e `L6` da coluna anterior são os valores publicados
- **AND** `diagnostico.conferencia_publicado` traz `L7` apurado × `SaldoPatrimonial` e a diferença

#### Scenario: ente sem publicação no ano anterior

- **GIVEN** o `tt/dca` sem `I-AB` do ente no exercício anterior
- **WHEN** o BP é apurado pelo publicado
- **THEN** a coluna anterior é `None` em todas as linhas
- **AND** `diagnostico.sem_publicacao_exercicio_anterior` é `true`
- **AND** a coluna atual é apurada normalmente

#### Scenario: origens não se misturam no cache

- **GIVEN** o BP em cache pela origem publicado
- **WHEN** chega um `GET` com `origem_exercicio_anterior=msce_exercicio_anterior`
- **THEN** o cache é servido marcado `desatualizado` com motivo `pedido`
- **AND** o resultado publicado nunca é apresentado como MSC atual

### Requirement: O BP espelha o DCA-Anexo I-AB declarado

O Balanço Patrimonial SHALL reproduzir em centavos o `DCA-Anexo I-AB` que o ente declara ao SICONFI
(decisão do PO, 2026-10-07; aceite do projeto: espelho 1:1 contra `tt/dca`). Para isso:

- as linhas do Quadro Principal NÃO DEVEM excluir as contas intra-OFSS (5º nível = 2); o resultado é o
  consolidado declarado. Revoga a decisão P8-a.
- `L5` Passivo Financeiro SHALL ser `2.1` Financeiro + `2.2` Financeiro + `6.3.1.1` + `6.3.1.5` +
  `6.3.1.7.1`, a composição que o `I-AB` detalha. NÃO DEVE incluir `6.2.2.1.3.01` nem
  `6.2.2.1.3.05`. Revoga a decisão P7-a.

Vale para as duas colunas e para as duas origens da coluna do exercício anterior.

#### Scenario: Cuitegi 2025 igual ao I-AB declarado

- **GIVEN** a MSC de encerramento de Cuitegi (`2505204`), 2025
- **WHEN** o BP é apurado
- **THEN** `L1` e `L15` valem 76.314.331,92, `L32` vale −45.644.857,64
- **AND** `diagnostico.equilibrio` é 0,00 no exercício atual

#### Scenario: conta intra entra na linha

- **GIVEN** registros de `121120400` (intra, 90,00) e `121110400` (consolidação, 10,00)
- **WHEN** `L10` é apurada
- **THEN** `L10` é 100,00

#### Scenario: passivo financeiro pela composição do I-AB

- **GIVEN** `2.1` Financeiro = 2.647.434,03, `6.3.1.1` = 70.972,63, `6.3.1.7.1` = 387.532,93 e
  `6.2.2.1.3.05` = 0,00
- **WHEN** o quadro F/P é apurado
- **THEN** `L5` é 3.105.939,59

#### Scenario: inscrição em duas contas não é contada duas vezes

- **GIVEN** `6.2.2.1.3.05` = 48.335,00 e `6.3.1.7.1` = 48.335,00 (Cuitegi 2024)
- **WHEN** `L5` é apurada
- **THEN** só `6.3.1.7.1` entra, e `L5` é 6.618.515,01 com `2.1` F = 6.496.569,60 e `6.3.1.1` = 73.610,41
