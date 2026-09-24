# dca/balanco-financeiro — Delta: Manual (I) + totalizadoras

## ADDED Requirements

### Requirement: Anexo Manual alimenta Receita Orçamentária (I)

No modo Manual, o sistema SHALL tratar o quadro anexo por fonte como origem do bloco
**Receita Orçamentária (I)** do quadro principal quando houver valores `A:…` no mapa.
O saldo `(f)` de cada linha do anexo SHALL preencher a linha do principal com o mesmo
rótulo (normalizado); o TOTAL do anexo SHALL preencher `L1`. O de-para MUST NOT usar
igualdade de código entre quadros.

#### Scenario: saldo (f) do anexo preenche a folha de mesmo rótulo sob (I)

- **GIVEN** origem Manual e mapa com `A:L1:receita` e `A:L1:deducoes`
- **WHEN** a apuração Manual conclui
- **THEN** `exercicio_anterior` de `L2` é a diferença receita − deduções
- **AND** a linha NÃO fica “não informado” por ausência de chave `L2`

#### Scenario: TOTAL do anexo alimenta Receita Orçamentária (I)

- **GIVEN** origem Manual e anexo com saldos `(f)`
- **WHEN** a apuração Manual conclui
- **THEN** `exercicio_anterior` de `L1` é o total `(f)` do anexo

#### Scenario: folhas fora de (I) continuam só pelo mapa

- **GIVEN** Manual com `L17` no mapa e anexo informado
- **WHEN** a apuração conclui
- **THEN** `L17` traz o valor informado

#### Scenario: MSC não deriva (I) do anexo Manual

- **GIVEN** origem `msce_exercicio_anterior`
- **WHEN** a apuração corre
- **THEN** a coluna anterior sai da MSC, sem de-para Manual

### Requirement: Totalizadoras Manual pela calculation

No modo Manual, após montar o mapa efetivo (informado + `(I)` derivado), o sistema SHALL
preencher linhas compostas do quadro principal (`calculation.references`) na coluna do
exercício anterior, incluindo totais de seção (`TOTAL (VI)`, `TOTAL (XII)`, …). Parcelas
`None` MUST NOT tornar o total indeterminado: soma-se o disponível.

#### Scenario: TOTAL (VI) oficial após Apurar Manual

- **GIVEN** Manual com `(I)` derivado e `L17` informado
- **WHEN** a apuração Manual conclui
- **THEN** `L15` / `exercicio_anterior` reflete as transferências informadas
- **AND** `L33` / `exercicio_anterior` é a soma das seções disponíveis (I+II+…)

#### Scenario: composta sem parcelas permanece não informada

- **GIVEN** Manual sem valores que alimentem uma composta
- **WHEN** a apuração conclui
- **THEN** essa linha permanece `None` com motivo de não informado

### Requirement: Conferência anexo × (I) no exercício anterior

O diagnóstico SHALL registrar a diferença entre `saldo_anterior` do TOTAL do anexo e
`L1` / `exercicio_anterior` quando ambos existirem, sem alterar a matriz.

#### Scenario: diferença (f) × L1 anterior no diagnóstico

- **GIVEN** Manual com anexo e `(I)` derivados
- **WHEN** a conferência corre
- **THEN** a diferença entra no diagnóstico

## MODIFIED Requirements

### Requirement: Coluna do exercício anterior com origem escolhida por quem apura

(Texto vigente, acrescido:) No Manual, o bloco `(I)` SHALL ser derivado do anexo quando
houver `A:…`; totalizadoras SHALL ser preenchidas pela calculation (Requirement
*Totalizadoras Manual pela calculation*). Chaves `(I)` no mapa, se o anexo informou, SHALL
ser ignoradas em favor do derivado.
