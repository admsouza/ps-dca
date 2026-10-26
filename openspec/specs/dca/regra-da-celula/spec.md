# dca/regra-da-celula

> Comportamento acordado e em vigor. Mesclado da change `dca-regra-na-celula` (arquivada em
> 2026-10-26).
> Alterações entram por nova change, nunca por edição direta deste arquivo.

## Purpose

O auditor consulta, no clique da célula, a regra que o motor aplicou naquela linha e coluna, sem recalcular o valor e sem ler a MSC.

### Requirement: Consulta da regra da célula

`GET /dca/{anexo}/regra` SHALL devolver a regra da linha e da coluna pedidas, lida do mapa vigente do exercício. A resposta SHALL trazer `tipo` (`contas` ou `soma`), `origem` (`period_change`, `encerramento`, `abertura` ou `exercicio_anterior`), `meses`, `natureza`, `contas`, `fontes` e `filhas`. A consulta NÃO DEVE chamar a fonte de saldos.

Quem não tem `auditor_mapeamentos` nem `adm_sistema` no hub SHALL receber `403`. Sem JWT válido, `401`. Hub indisponível, `503`. Anexo sem projeção, linha ambígua, linha ou coluna inexistente SHALL receber `404` com o texto "Consulta indisponível.", sem listar contas.

#### Scenario: L27 mostra a soma de créditos nas duas colunas

- **GIVEN** o mapa do BF do exercício 2025
- **WHEN** a regra de `L27` é consultada em `exercicio_atual` e em `exercicio_anterior`
- **THEN** as duas colunas têm origem `period_change` nos meses 1 a 12
- **AND** a natureza é crédito
- **AND** as contas são `2188` e `2288`
- **AND** as fontes são `860`, `861`, `862`, `863` e `869`

#### Scenario: L28 no exercício anterior é abertura

- **GIVEN** o mapa do BF do exercício 2025
- **WHEN** a regra de `L28` é consultada em `exercicio_anterior`
- **THEN** a origem é `abertura`
- **AND** as contas da coluna atual entram na resposta

#### Scenario: L24 é a soma das filhas

- **GIVEN** o mapa do BF do exercício 2025
- **WHEN** a regra de `L24` é consultada em `exercicio_atual`
- **THEN** o tipo é `soma`
- **AND** as filhas são `L25`, `L26`, `L27` e `L28`

#### Scenario: quem não é auditor recebe 403

- **GIVEN** um JWT válido de usuário sem `auditor_mapeamentos` e sem `adm_sistema`
- **WHEN** a regra de `L27` é consultada
- **THEN** a resposta é `403`
- **AND** o corpo não lista contas

#### Scenario: linha inexistente responde 404

- **GIVEN** um auditor autenticado
- **WHEN** a regra da linha `L99` é consultada
- **THEN** a resposta é `404` com o texto "Consulta indisponível."

#### Scenario: anexo sem projeção responde 404

- **GIVEN** um auditor autenticado
- **WHEN** a regra de uma linha do BO é consultada
- **THEN** a resposta é `404`
