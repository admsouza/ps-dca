# dca/balanco-financeiro — Delta spec

## MODIFIED Requirements

### Requirement: Coluna do exercício anterior com origem escolhida por quem apura

A coluna do exercício anterior SHALL aceitar duas origens:

1. **`MSCE` do exercício anterior** (padrão, enquanto não houver mapa salvo) — apurada pelas mesmas regras do IPC 06.
2. **Preenchimento manual**, linha a linha, informado por quem apura.

A segunda existe porque o ente pode ter publicado o exercício anterior com números que a matriz daquele ano não reproduz: medido em Recife, `L17` e `L50` de 2024 saem 628.456.869,17 da MSC contra **0,00** publicado.

O mapa informado SHALL ser gravado em `procedencia.valores_anteriores` da linha de cache do BF. Pedido seguinte do mesmo ente e exercício **sem** origem SHALL reaplicar esse mapa: a coluna do exercício anterior sai dele, e o exercício corrente é recalculado na MSC. A procedência SHALL continuar declarando `manual`.

Só a origem explícita `msce_exercicio_anterior` SHALL deixar de reaplicar o mapa e SHALL removê-lo da procedência. Ausência de origem NÃO DEVE ser lida como MSC quando há mapa salvo.

A procedência SHALL declarar a origem usada. No modo manual, linha não informada SHALL ser `None` com motivo — nunca zero. Linha informada que o IPC 06 não declara SHALL ser recusada antes de apurar, e o mapa já salvo NÃO DEVE ser substituído. A coluna do exercício **atual** NÃO DEVE aceitar preenchimento manual.

Falha do job NÃO DEVE apagar `procedencia.valores_anteriores` já gravado.

#### Scenario: coluna anterior apurada da MSCE do exercício anterior

- **GIVEN** nenhum mapa manual salvo para o ente e o exercício
- **WHEN** a apuração corre sem origem informada
- **THEN** `exercicio_anterior` vem da matriz do exercício anterior, pelas mesmas regras
- **AND** a procedência declara `msce_exercicio_anterior`

#### Scenario: coluna anterior preenchida manualmente

- **GIVEN** o corpo com `L17` = `628456869.17` para Recife (`2611606`), exercício 2025
- **WHEN** a apuração corre no modo manual
- **THEN** `exercicio_anterior` de `L17` é `628456869.17`
- **AND** as linhas não informadas saem `None`, com `não informado` no diagnóstico
- **AND** a procedência declara `manual` e `valores_anteriores` contém `L17`

#### Scenario: processamento seguinte reaplica o mapa salvo

- **GIVEN** a procedência do BF de Recife/2025 já contém `L17` = `628456869.17`
- **WHEN** um `GET /dca/BF`, um reprocessamento ou o percurso completo roda sem origem e sem mapa
- **THEN** `exercicio_anterior` de `L17` continua `628456869.17`
- **AND** a procedência continua `manual`

#### Scenario: MSC explícita remove o mapa

- **GIVEN** um mapa manual já salvo
- **WHEN** a apuração é pedida com `origem_exercicio_anterior=msce_exercicio_anterior`
- **THEN** a coluna anterior sai da MSC do exercício anterior
- **AND** `procedencia.valores_anteriores` deixa de existir
- **AND** a procedência declara `msce_exercicio_anterior`

#### Scenario: linha informada fora do IPC 06

- **WHEN** o preenchimento manual traz um código que a base canônica não declara
- **THEN** a apuração é recusada, nomeando o código
- **AND** o mapa já salvo permanece

#### Scenario: job que falha conserva o mapa

- **GIVEN** um mapa manual já salvo
- **WHEN** um job posterior do BF termina em erro
- **THEN** `procedencia.valores_anteriores` continua o mapa anterior
