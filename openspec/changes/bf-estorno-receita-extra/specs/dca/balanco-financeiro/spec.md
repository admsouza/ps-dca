# dca/balanco-financeiro — Delta spec

## MODIFIED Requirements

### Requirement: Estorno de receita extra só na PublicSoft
Quando a fonte expõe o relatório de estorno de receita extra, o sistema SHALL apresentar
`bf.quadro_principal.ingressos.l27` e `bf.quadro_principal.dispendios.l60` líquidos:
movimento da MSC da coluna menos `data.totalGeral` do exercício daquela coluna
(`exercicio` atual e `exercicio` anterior, cada um com a própria consulta
`tipo=sintetico`). As linhas que somam essas duas SHALL refletir o mesmo abatimento.
Fonte que não expõe o relatório SHALL manter o movimento da MSC, sem consulta.

#### Scenario: PublicSoft abate o total geral nas duas colunas
- **GIVEN** movimento de crédito 100.00 e de débito 80.00 nas contas de `L27`/`L60` em 2025 e em 2024
- **AND** `totalGeral` 10.00 em 2025 e 3.00 em 2024
- **WHEN** o BF de 2025 é apurado nessa fonte
- **THEN** `L27` atual é 90.00 e anterior é 97.00
- **AND** `L60` atual é 70.00 e anterior é 77.00
- **AND** `L24` atual é 90.00 e `L57` atual é 70.00

#### Scenario: SICONFI não abate
- **GIVEN** o mesmo movimento e uma fonte sem o relatório
- **WHEN** o BF de 2025 é apurado
- **THEN** `L27` atual é 100.00 e `L60` atual é 80.00

#### Scenario: Relatório sem total geral não publica o bruto
- **GIVEN** a fonte expõe o relatório e a resposta não traz `data.totalGeral`
- **WHEN** o BF é apurado
- **THEN** a apuração falha e não devolve `L27` pelo movimento bruto
