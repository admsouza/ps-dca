# dca/balanco-financeiro — Delta spec (Quadro Anexo)

## Purpose

Apurar o *Demonstrativo da Receita Orçamentária por Fonte/Destinação de Recursos* — o Quadro Anexo
do Balanço Financeiro —, que abre em bruto, dedução e líquido a receita que o quadro principal
apresenta já líquida.

## ADDED Requirements

### Requirement: Quadro Anexo apurado nas seis colunas

O Quadro Anexo SHALL ser apurado com as seis colunas do IPC 06: `(a)` e `(d)` a receita
orçamentária, `(b)` e `(e)` as deduções, `(c)` e `(f)` **derivadas** como `(a) − (b)` e `(d) − (e)`.
As colunas derivadas SHALL ser calculadas da própria linha, nunca somadas das filhas. `L14 TOTAL`
SHALL fechar `L1 + L2 + L10` em cada uma das seis.

#### Scenario: saldo do anexo é derivado, não somado

- **GIVEN** `bf.quadro_anexo.l1` com `(a)` = 1.000,00 e `(b)` = 150,00
- **WHEN** a matriz é apurada
- **THEN** `(c)` vale 850,00, calculada da própria linha
- **AND** `L14 (c)` é a soma de `L1 (c)`, `L2 (c)` e `L10 (c)`

#### Scenario: coluna derivada com parcela não apurada

- **GIVEN** uma linha do anexo cuja coluna `(a)` saiu não apurada
- **WHEN** `(c)` é calculada
- **THEN** `(c)` é `None`
- **AND** NÃO é a subtração feita com a parcela que existe

### Requirement: Conferência entre o anexo e o quadro principal

`L14 (c)` do anexo SHALL ser comparada a `L1 exercicio_atual` do quadro principal, e a diferença,
quando houver, SHALL entrar no diagnóstico com o valor medido. A conferência NÃO DEVE alterar
nenhum dos dois quadros.

#### Scenario: o anexo detalha o que o principal traz líquido

- **GIVEN** o caso de referência
- **WHEN** `bf.quadro_anexo.l14` coluna `(c)` e `bf.quadro_principal.ingressos.l1`
  `exercicio_atual` são comparadas
- **THEN** a diferença entre as duas é registrada no diagnóstico, com o valor medido
- **AND** a comparação não altera nenhum dos dois

### Requirement: Receita sem fonte de recursos declarada como resíduo do anexo

Registro de receita sem fonte de recursos na MSC NÃO DEVE entrar em nenhuma linha por fonte nem ser
rateado entre elas. Ele SHALL aparecer como **resíduo** do anexo, com o valor.

Medido em Recife, 2026-09-18: 450.202.814,72 em dois registros da conta sintética
`6.2.1.2.0.00.00`, que o ente classificou por critério próprio e a MSC não qualifica.

#### Scenario: fonte ausente vira resíduo, não rateio

- **GIVEN** registros de receita sem fonte de recursos
- **WHEN** o anexo é apurado
- **THEN** o valor aparece no diagnóstico como resíduo de fonte
- **AND** nenhuma linha por fonte o recebe
