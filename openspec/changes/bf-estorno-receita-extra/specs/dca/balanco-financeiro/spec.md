# dca/balanco-financeiro — Delta spec

## MODIFIED Requirements

### Requirement: Estorno de receita extra só na PublicSoft
Quando a fonte expõe os relatórios de estorno extra, o sistema SHALL apresentar
`bf.quadro_principal.ingressos.l27` como movimento da MSC menos o `totalGeral` de
`estorno-receita-extra` do exercício da coluna, e `bf.quadro_principal.dispendios.l60`
como o mesmo movimento menos esse total e menos o `totalGeral` de `estorno-despesa-extra`
do mesmo exercício. `totalGeral` zero SHALL abater zero. As linhas que somam `L27` ou `L60`
SHALL refletir o abatimento da filha. Fonte que não expõe os relatórios SHALL manter o
movimento da MSC, sem consulta.

#### Scenario: PublicSoft abate receita em L27 e L60, e despesa só em L60
- **GIVEN** movimento de crédito 100.00 e de débito 80.00 nas contas de `L27`/`L60` em 2025 e em 2024
- **AND** estorno de receita 10.00 em 2025 e 3.00 em 2024
- **AND** estorno de despesa 4.00 em 2025 e 1.00 em 2024
- **WHEN** o BF de 2025 é apurado nessa fonte
- **THEN** `L27` atual é 90.00 e anterior é 97.00
- **AND** `L60` atual é 66.00 e anterior é 76.00
- **AND** `L24` atual é 90.00 e `L57` atual é 66.00

#### Scenario: SICONFI não abate
- **GIVEN** o mesmo movimento e uma fonte sem o relatório
- **WHEN** o BF de 2025 é apurado
- **THEN** `L27` atual é 100.00 e `L60` atual é 80.00

#### Scenario: Relatório sem total geral não publica o bruto
- **GIVEN** a fonte expõe o relatório e a resposta não traz `data.totalGeral`
- **WHEN** o BF é apurado
- **THEN** a apuração falha e não devolve `L27` pelo movimento bruto
