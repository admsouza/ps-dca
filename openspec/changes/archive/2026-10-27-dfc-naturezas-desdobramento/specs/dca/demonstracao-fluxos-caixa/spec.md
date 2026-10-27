# dca/demonstracao-fluxos-caixa — Delta spec

## Purpose

Fazer o `pattern` da natureza de receita alcançar o que a MSC entrega, sem tocar no literal do
IPC 08.

## ADDED Requirements

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
