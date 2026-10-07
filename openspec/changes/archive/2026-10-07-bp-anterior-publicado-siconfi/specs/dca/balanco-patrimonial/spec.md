# dca/balanco-patrimonial — Delta spec

## ADDED Requirements

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
para saldo na direção da conta (o sinal do `I-AB` é o da posição) e passar pelas mesmas regras e
exclusões das linhas do Quadro Principal. NÃO DEVE haver dupla contagem da hierarquia publicada.

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

#### Scenario: exclusão intra aplicada ao publicado

- **GIVEN** o `I-AB` com `P1.2.1.1.1.00.00` = 10,00 e `P1.2.1.1.2.00.00` (intra) = 90,00
- **WHEN** `L10` é apurada pelo publicado
- **THEN** `L10` é 10,00

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
