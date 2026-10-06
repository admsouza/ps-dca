# dca/balanco-financeiro — Delta spec

## ADDED Requirements

### Requirement: Totais extraorçamentários no caso Cuitegi da SPEC-0001

No caso PM Cuitegi/PB (`2505204`), outubro/2025, da SPEC-0001, o sistema SHALL apurar:

- `L24` Recebimentos Extraorçamentários (IV) = R$ 387.665,33
- `L57` Pagamentos Extraorçamentários (X) = R$ 520.551,46

A comparação é em centavos. A competência que realiza "outubro/2025" fica em aberto até o PO
fechar D1 do design; o número do gabarito não muda com essa escolha.

`L24` continua `L25 + L26 + L27 + L28`. `L57` continua `L58 + L59 + L60 + L61`. A revisão atinge
`L27`, `L28`, `L60` e `L61`. A fórmula de `L25`, `L26`, `L58` e `L59` NÃO muda.

#### Scenario: recebimentos extraorçamentários de Cuitegi

- **GIVEN** PM Cuitegi (`2505204`) no caso outubro/2025 da SPEC-0001
- **AND** a composição informada da receita extraorçamentária é ativo R$ 0,00 e passivo
  R$ 394.823,97 − R$ 7.158,64
- **WHEN** o Balanço Financeiro desse caso é apurado
- **THEN** `L24` Recebimentos Extraorçamentários (IV) é R$ 387.665,33

#### Scenario: pagamentos extraorçamentários de Cuitegi

- **GIVEN** o mesmo caso
- **AND** a composição informada da despesa extraorçamentária é ativo R$ 1.583,00 e passivo
  R$ 526.127,10 − R$ 7.158,64 = R$ 518.968,46
- **WHEN** o Balanço Financeiro desse caso é apurado
- **THEN** `L57` Pagamentos Extraorçamentários (X) é R$ 520.551,46

### Requirement: Origem das linhas extraorçamentárias revisadas

Depois da revisão, a procedência SHALL identificar a origem do valor de `L27`, `L28`, `L60` e
`L61` no caso apurado. Linha sem origem identificável NÃO está revisada.

#### Scenario: procedência nomeia a origem das quatro linhas

- **GIVEN** o Balanço Financeiro do caso Cuitegi da SPEC-0001 já apurado
- **WHEN** a procedência é lida
- **THEN** ela identifica a origem de `L27`, de `L28`, de `L60` e de `L61`

### Requirement: Revisão extraorçamentária não altera as outras linhas

Linha cuja fórmula não depende de `L27`, `L28`, `L60` ou `L61` SHALL manter o valor que já produz
com a spec em vigor. Totalizadora que inclui uma destas quatro SHALL refletir a parcela revisada
e SHALL manter as demais parcelas.

#### Scenario: linha fora do grupo extraorçamentário permanece

- **GIVEN** uma linha do Balanço Financeiro que não é `L27`, `L28`, `L60`, `L61` nem totalizadora
  que as soma
- **WHEN** a revisão desta change é aplicada ao mesmo ente e exercício
- **THEN** o valor dessa linha é o mesmo de antes da revisão
