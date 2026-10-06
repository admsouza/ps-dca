# dca/balanco-financeiro — Delta spec

## MODIFIED Requirements

### Requirement: Estorno de receita extra só na PublicSoft
Quando a fonte expõe os relatórios de estorno extra, o sistema SHALL apresentar `L27` como o
movimento da MSC menos o `totalGeral` de `estorno-receita-extra` do exercício da coluna, e
`L60` como esse movimento menos esse total e menos o `totalGeral` de `estorno-despesa-extra`.
A fonte SICONFI SHALL expor os relatórios da PublicSoft quando o pedido tiver `token_ps`.
Sem token, SHALL manter o movimento da MSC, sem consulta. Exercício sem nenhuma leitura da MSC
SHALL NÃO ser abatido.

#### Scenario: SICONFI com token_ps abate como a PublicSoft
- **GIVEN** `use_siconfi=true` e o hub resolve o `token_ps` do ente
- **WHEN** o BF é apurado
- **THEN** `L27` e `L60` saem líquidas, como na PublicSoft

#### Scenario: fonte sem o relatório (SICONFI sem token_ps) não abate
- **GIVEN** o mesmo movimento e uma fonte sem o relatório
- **WHEN** o BF de 2025 é apurado
- **THEN** `L27` atual é 100.00 e `L60` atual é 80.00

#### Scenario: exercício anterior com auditoria pendente não sai negativo
- **GIVEN** o exercício anterior responde `409` (sem dados) e há estorno de 3.00 em 2024
- **WHEN** o BF de 2025 é apurado
- **THEN** `L27` e `L60` anteriores são 0.00, não −3.00 / −4.00
- **AND** `L27` atual é 90.00 e o BF é publicado
- **AND** a procedência traz só o estorno de 2025
