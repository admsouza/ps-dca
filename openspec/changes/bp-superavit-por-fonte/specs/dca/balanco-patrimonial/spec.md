# dca/balanco-patrimonial — Delta spec

## ADDED Requirements

### Requirement: Quadro do Superávit / Déficit Financeiro por fonte

O sistema SHALL apurar o Quadro do Superávit / Déficit Financeiro (IPC 04, p. 13) com uma linha para cada par fonte + complemento que tenha saldo em `8.2.1.1.1` no exercício ou no exercício anterior.

O código da linha SHALL ter 8 dígitos: os 4 de `fonte_recursos` e os 4 de `complemento_fonte`. Complemento ausente SHALL valer `0000`. O rótulo SHALL ser a nomenclatura de `docs/contas-stn/fonte-recursos.md` para os dígitos 2 a 4 da fonte. Complemento diferente de `0000` SHALL identificar também a nomenclatura de `docs/contas-stn/complemento-fonte.md`.

O saldo SHALL ser `C − D` das folhas `821110100` e `821110200`, em centavos. Superávit positivo, déficit negativo. A coluna do exercício SHALL ser o saldo de encerramento desse ano. A coluna do exercício anterior SHALL ser o mesmo saldo no ano anterior, lido da MSC, e NÃO o valor publicado no `I-AB`.

Fonte cujo `fonte_recursos` começa com `2` SHALL entrar nas duas colunas (PO 2026-10-08: a exclusão foi revogada). Linha com as duas colunas iguais a zero SHALL ser omitida. O `Total` SHALL ser a soma das linhas que entraram. As visões `isolado` e `consolidado` SHALL devolver o mesmo quadro.

#### Scenario: CIDE de Cuitegi 2025

- **GIVEN** a MSC de encerramento de Cuitegi/PB (`2505204`), exercícios 2025 e 2024
- **WHEN** o BP é apurado
- **THEN** a linha `17500000` vale 12.879,61 no exercício e 835,46 no anterior

#### Scenario: taxa de administração do RPPS

- **GIVEN** a mesma MSC
- **WHEN** o BP é apurado
- **THEN** a linha `18020000` vale 61.862,85 no exercício e (212.922,03) no anterior

#### Scenario: complemento é linha própria

- **GIVEN** saldo na fonte `1500` com complemento `1001` e saldo na fonte `1500` com complemento `0000`
- **WHEN** o BP é apurado
- **THEN** existem as linhas `15000000` e `15001001`
- **AND** `15001001` não é somada em `15000000`

#### Scenario: fonte de exercício anterior da vinculação entra

- **GIVEN** saldo em `fonte_recursos` `2500` (código `25000000`) na MSC de Cuitegi 2025 e 2024
- **WHEN** o BP é apurado
- **THEN** a linha `25000000` vale (15.855,84) no exercício e (1.984.731,88) no anterior
- **AND** esse saldo entra no `Total`

#### Scenario: totais de Cuitegi

- **GIVEN** a MSC de encerramento de Cuitegi 2025 e 2024
- **WHEN** o BP é apurado
- **THEN** o `Total` é 48.827.308,73 no exercício e 13.279.106,25 no anterior

#### Scenario: saldo só no ano anterior ainda aparece

- **GIVEN** uma fonte com saldo zero em 2025 e saldo diferente de zero em 2024
- **WHEN** o BP é apurado
- **THEN** a linha existe, com exercício 0,00 e o saldo de 2024 na coluna anterior

#### Scenario: as duas visões são iguais

- **WHEN** o BP é lido em `isolado` e em `consolidado`
- **THEN** as linhas e os valores do quadro são os mesmos

## MODIFIED Requirements

### Requirement: BP no pipeline

O BP SHALL ser apurado pelo mesmo job, rota e cache dos demais anexos implementados, com base
canônica `bp`, e SHALL constar no percurso completo (`POST /batch-jobs`). A procedência SHALL
declarar matriz `MSCE`, tipo de saldo `encerramento`, competência e `versao_regras` do IPC 04.

#### Scenario: resumo deixa de reportar sem_cache

- **WHEN** o percurso completo roda para um ente com MSC de encerramento
- **THEN** o BP aparece com status de apurado, não `sem_cache`

#### Scenario: leitura só pelo par do BP

- **WHEN** o BP é apurado pela MSC nos dois anos
- **THEN** toda leitura da MSC usa a matriz `MSCE` com saldo de encerramento, classes 1, 2, 6 e 8,
  no exercício e no exercício anterior
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

O Quadro do Superávit / Déficit Financeiro é a exceção: as duas colunas saem da MSC de encerramento
(classe 8), inclusive quando a origem escolhida é `publicado_siconfi`. As demais linhas da coluna
anterior NÃO DEVEM cair para a MSC.

Ente sem `I-AB` publicado no ano anterior SHALL ter a coluna anterior `None` nas linhas que não são
desse quadro e `diagnostico.sem_publicacao_exercicio_anterior: true`.

#### Scenario: publicado é o padrão

- **WHEN** o BP é pedido sem `origem_exercicio_anterior`
- **THEN** a coluna anterior do Quadro Principal vem do `I-AB` do exercício anterior
- **AND** `procedencia.origem_exercicio_anterior` é `publicado_siconfi`
- **AND** a única leitura da MSC do exercício anterior é a classe 8, usada só pelo quadro do superávit

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
- **THEN** a coluna anterior é `None` nas linhas que não são do quadro do superávit
- **AND** `diagnostico.sem_publicacao_exercicio_anterior` é `true`
- **AND** a coluna atual é apurada normalmente
- **AND** a MSC do exercício anterior é lida só na classe 8

#### Scenario: origens não se misturam no cache

- **GIVEN** o BP em cache pela origem publicado
- **WHEN** chega um `GET` com `origem_exercicio_anterior=msce_exercicio_anterior`
- **THEN** o cache é servido marcado `desatualizado` com motivo `pedido`
- **AND** o resultado publicado nunca é apresentado como MSC atual

### Requirement: Linhas e quadros não apuráveis declarados

Linha com `status: review_required` e o quadro fora de escopo (Contas de Compensação) SHALL produzir células `None` com o motivo citando o `review.blocker` da regra. Nenhuma dessas células SHALL valer `0`. O total que as contém SHALL somar as parcelas apuradas e nomear as bloqueadas no diagnóstico. O Quadro do Superávit / Déficit Financeiro por fonte não faz parte deste requisito.

#### Scenario: compensação fora de escopo

- **WHEN** o BP é apurado
- **THEN** as 10 linhas de `bp.contas_compensacao` são `None`
- **AND** cada uma traz em `diagnostico.nao_apuradas` o motivo do IPC 04 itens 12–13

#### Scenario: linha bloqueada não zera o total

- **GIVEN** uma linha do PL com `review.blocker` e as demais linhas do PL apuradas
- **WHEN** `L32` Patrimônio Líquido é calculada
- **THEN** `L32` é a soma das parcelas apuradas
- **AND** a linha bloqueada aparece no diagnóstico como parcela bloqueada

#### Scenario: L34 apurada pela 2.3.2

- **GIVEN** saldos em `2.3.2` (inclusive o intra `2.3.2.1.2`, literal corrigido do `2.3.2.0.2.00.00` do IPC 04 por decisão do PO em 2026-10-08)
- **WHEN** o BP é apurado
- **THEN** `L34` é o saldo de `2.3.2`, sem exclusão intra (espelho do `I-AB`)
- **AND** `L32` inclui `L34`
