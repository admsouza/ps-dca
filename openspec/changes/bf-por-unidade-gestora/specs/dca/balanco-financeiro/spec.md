# dca/balanco-financeiro — Delta spec

## ADDED Requirements

### Requirement: Estorno extra abatido por unidade

Com uma fonte que tem o estorno de receita e despesa extra, o BF de cada recorte SHALL abater de
`L27` (receita) e de `L60` (receita + despesa) a soma dos estornos das unidades do recorte, por
exercício da coluna:

| Recorte | Estorno abatido |
|---|---|
| `consolidado` | `totalGeral` (igual a hoje) |
| `ug:<id>` | `totaisPorUnidadeGestora` com `idInstituicao = id` (0,00 se ausente) |
| `po:<código>` | soma de `totaisPorUnidadeGestora` com `poderOrgao = código` |
| `poder:*` | soma das unidades do grupo |

As totalizadoras que somam `L27`/`L60` SHALL acompanhar o abatimento. O relatório SHALL ser chamado
uma vez por exercício e tipo no job. Num exercício sem nenhuma leitura no recorte, o estorno NÃO
DEVE ser abatido. A procedência do recorte SHALL declarar o valor abatido nele.

Num recorte por PO, se a resposta não tiver o campo `poderOrgao` (`ps-erp` anterior à change) e
`totalGeral` for maior que zero, `L27` e `L60` dos `po:` SHALL ficar não apuradas, com o motivo
"estorno sem poder/órgão". O consolidado SHALL ser publicado.

#### Scenario: UG
- **GIVEN** Cuitegi 2025, `ug:3` com `L27` bruto B e `totaisPorUnidadeGestora[3]` = E
- **WHEN** `GET /dca/BF?recorte=ug:3`
- **THEN** `L27` atual = B − E e `procedencia.estorno_receita_extra["2025"]` = E

#### Scenario: PO
- **GIVEN** fonte SICONFI com `token_ps`, Câmara com `poderOrgao = "20231"` e estorno de 10,00
- **THEN** `po:20231` abate 10,00 de `L27`

#### Scenario: consolidado inalterado
- **WHEN** o BF de Cuitegi 2025 é lido em `consolidado`
- **THEN** `L27` = 4486188.21 e `L60` = 4479755.61, como antes da change

#### Scenario: partição do estorno
- **THEN** Σ do estorno abatido nas unidades + Σ `estorno_sem_unidade` = `totalGeral`, por exercício e tipo, por UG e por PO

#### Scenario: uma chamada por exercício
- **GIVEN** um job com consolidado, 3 grupos e 4 UGs
- **THEN** cada relatório de estorno é chamado uma vez por exercício lido

#### Scenario: resposta sem o campo poderOrgao
- **GIVEN** um recorte por PO e uma resposta de estorno sem o campo `poderOrgao`, com `totalGeral` > 0
- **THEN** `L27` e `L60` dos recortes `po:` ficam não apuradas, com o motivo "estorno sem poder/órgão", e o consolidado é publicado

#### Scenario: resposta sem totais por unidade
- **WHEN** o relatório responde sem `totaisPorUnidadeGestora`
- **THEN** a apuração falha e nenhum recorte é publicado com `L27`/`L60` brutas

### Requirement: Estorno sem unidade declarado no consolidado

SHALL aparecer em `diagnostico.estorno_sem_unidade: [{exercicio, tipo, unidade, valor}]` do
consolidado:

- num job por UG, a instituição com estorno e sem nenhum registro na MSC daquele exercício;
- num job por PO, a instituição com `poderOrgao: null`, ou com um PO sem registro na MSC daquele
  exercício.

O job NÃO DEVE falhar, e o valor NÃO DEVE ser rateado entre as unidades.

#### Scenario: UG sem registro
- **GIVEN** estorno de 100,00 na instituição 9, sem registro na MSC de 2025
- **THEN** o consolidado abate 100,00, nenhuma UG abate e `estorno_sem_unidade` traz `{2025, receita, ug:9, 100.00}`

#### Scenario: PO nulo
- **GIVEN** recorte por PO e uma instituição com `poderOrgao: null` e 50,00 de estorno
- **THEN** nenhum `po:` abate os 50,00, e `estorno_sem_unidade` traz o valor com `unidade` = `ug:<id>` da instituição

### Requirement: Valores digitados valem só no consolidado

`valores_anteriores` (anterior manual) e `valores_sem_mapeamento` (G8) SHALL valer só para o recorte
`consolidado`. Nos demais:

- a coluna anterior SHALL ser a MSC de N−1 dos registros do recorte, com o estorno de N−1 das suas
  unidades;
- as linhas que o G8 completaria SHALL ficar não apuradas, com o motivo "informado só no
  consolidado".

A unidade sem registro na MSC de N−1 SHALL sair com a coluna anterior em zero e com
`diagnostico.sem_dados_exercicio_anterior = true`.

#### Scenario: G8 fora do consolidado
- **GIVEN** um BF processado com `valores_sem_mapeamento` em `L22`
- **THEN** `L22` traz o valor no `consolidado` e fica não apurada em `ug:3`

#### Scenario: anterior manual fora do consolidado
- **GIVEN** um BF processado com `origem_exercicio_anterior=manual`
- **THEN** o consolidado traz a coluna anterior digitada, e `ug:3` traz a MSC de 2024 da UG 3

#### Scenario: UG nova
- **GIVEN** uma UG sem registro na MSC de 2024
- **THEN** a coluna anterior dela sai em zero, com `sem_dados_exercicio_anterior = true`
