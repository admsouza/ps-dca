# dca/balanco-orcamentario — Delta spec (L51)

## ADDED Requirements

### Requirement: Reserva do RPPS é apurada com o mapeamento de despesa

`bo.quadro_principal.despesas.l51` SHALL ser apurada com as mesmas colunas e contas da
`bo.quadro_principal.despesas.l39`. Os filtros da linha SHALL restringir a MSC a
`natureza_despesa` `9.9.00.00.00`, função `99` e subfunção `997`. A linha NÃO DEVE ser agregada
por `L40` nem por `L50`. Escrituração ausente nessa classificação SHALL produzir `0.00`, não
célula vazia nem aviso de não apurada.

#### Scenario: reserva do RPPS

- **GIVEN** um registro `622130400` com ND `9.9.00.00.00`, função `99`, subfunção `997` e saldo
  `100,00`, e outro idêntico com subfunção `999` e saldo `50,00`
- **WHEN** o quadro principal é apurado
- **THEN** `L51.pagas` é `100,00` e `L39.pagas` é `50,00`
- **AND** nenhum aviso de célula não apurada cita `l51`

#### Scenario: L51 fica fora do TOTAL (XV)

- **WHEN** `L50` é lida
- **THEN** suas referências são só `L48` e `L49`

## REMOVED Requirements

### Requirement: Linha sem coluna de valor não produz célula

**Motivo:** o único caso era `L51`, agora apurada. · **Migração:** o early-return de `columns`
vazio em `matriz.py` permanece como defesa, sem linha vigente que o exercite.
