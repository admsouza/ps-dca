# dca/balanco-patrimonial — Delta spec

## ADDED Requirements

### Requirement: Compensação atual informada por recorte individual

O sistema SHALL preencher a coluna `exercicio_atual` do quadro `CONTAS_COMPENSACAO` exclusivamente
por valores manuais de cada recorte individual `ug:` ou `po:`. O pedido SHALL usar
`valores_atuais_por_recorte`, com chaves de folha `C:<codigo>` e valores decimais. Linhas
totalizadoras SHALL ser derivadas das folhas pelo mapa vigente e NÃO DEVEM aceitar valor direto.

Grupo `poder:*` e `consolidado` SHALL ser somente leitura e SHALL resultar da soma célula a célula
dos individuais participantes. Valor explicitamente informado como `0.00` SHALL ser zero; valor não
informado SHALL permanecer `None`. Se qualquer individual participante tiver `None` numa célula, a
célula agregada SHALL ser `None`, nunca uma soma parcial.

#### Scenario: folhas atuais de uma unidade e totalizadora

- **GIVEN** `ug:3` com `C:L2 = 100,00`, `C:L3 = 50,00` e as demais folhas não informadas
- **WHEN** o BP é reprocessado
- **THEN** `L2` e `L3`, coluna `exercicio_atual`, valem respectivamente 100,00 e 50,00 em `ug:3`
- **AND** a totalizadora que contém essas folhas é calculada pelo mapa, sem valor direto no pedido
- **AND** as folhas não informadas permanecem `None`

#### Scenario: poder e consolidado somam os individuais

- **GIVEN** `po:10131` com `C:L2 = 100,00`, `po:10132` com `C:L2 = 50,00` e `po:20231` com
  `C:L2 = 0,00`
- **WHEN** os recortes do BP de Cuitegi/PB (`2505204`), exercício 2025, são produzidos
- **THEN** `poder:executivo` tem `C:L2 = 150,00`
- **AND** `poder:legislativo` tem `C:L2 = 0,00`
- **AND** `consolidado` tem `C:L2 = 150,00`, com diferença 0,00 para a soma dos três POs

#### Scenario: célula incompleta não vira soma parcial

- **GIVEN** duas unidades participantes, uma com `C:L2 = 100,00` e outra sem `C:L2`
- **WHEN** o grupo e o consolidado são produzidos
- **THEN** `C:L2` é `None` nos agregados
- **AND** o diagnóstico declara que a célula não foi informada em todos os individuais

### Requirement: Pedido atual validado, autorizado e reaplicável

`valores_atuais_por_recorte` SHALL aceitar somente chaves `ug:<id>` ou `po:<codigo>` visíveis ao
usuário no ente. Todas as chaves e valores SHALL ser validados antes de enfileirar. A operação SHALL
ser tudo ou nada. O mapa efetivo SHALL compor a identidade do pedido e a procedência do resultado.

Campo omitido SHALL reaplicar os mapas gravados. Mapa vazio de um recorte SHALL limpar apenas esse
recorte. A coluna atual SHALL ser independente de `anterior_por_recorte`; ambos MAY ser enviados no
mesmo corpo sem um substituir o outro.

#### Scenario: entrada inválida ou não autorizada falha antes do job

- **WHEN** o pedido contém `consolidado`, `poder:*`, prefixo diferente de `C:`, linha inexistente,
  totalizadora, valor não decimal ou recorte individual sem autorização
- **THEN** a API responde `422` para forma/valor inválido ou `403` para acesso negado
- **AND** cria 0 jobs e não persiste estado parcial

#### Scenario: omitir reaplica e vazio limpa

- **GIVEN** `ug:3` com `C:L2 = 100,00` gravado
- **WHEN** um reprocessamento omite `valores_atuais_por_recorte`
- **THEN** `C:L2 = 100,00` é reaplicado em `ug:3`
- **WHEN** outro pedido envia `"ug:3": {}`
- **THEN** o mapa de `ug:3` é limpo e `C:L2` volta a `None`

#### Scenario: atual e anterior são independentes

- **GIVEN** `ug:3` com origem anterior Processado
- **WHEN** o pedido altera somente `valores_atuais_por_recorte["ug:3"]`
- **THEN** a coluna anterior de `ug:3`, dos grupos e do consolidado sai bit a bit igual
- **AND** a procedência mantém separadas a origem anterior e os valores atuais

## MODIFIED Requirements

### Requirement: Linhas e quadros não apuráveis declarados

Linha com `status: review_required` SHALL produzir células `None` com o motivo da regra, salvo
quando uma capability aprovada declarar outra origem. As dez linhas de Contas de Compensação NÃO
DEVEM ser apuradas pela matriz: no `exercicio_atual`, as folhas vêm do manual por `ug:`/`po:` e os
agregados vêm da soma dos individuais; no `exercicio_anterior`, vale a origem resolvida pela
capability `pipeline/anterior-por-recorte`. Célula sem valor SHALL continuar `None`, nunca `0`.

#### Scenario: compensação não usa a matriz

- **GIVEN** registros de classes 7 ou 8 na matriz do exercício atual
- **WHEN** o BP é apurado sem valor manual de Compensação
- **THEN** as folhas de `bp.contas_compensacao` permanecem `None`
- **AND** nenhum registro da matriz preenche essas células

#### Scenario: valor manual substitui somente a célula informada

- **GIVEN** `C:L2 = 100,00` informado para uma unidade e nenhuma outra folha informada
- **WHEN** o BP é apurado
- **THEN** `L2.exercicio_atual` vale 100,00 nessa unidade
- **AND** as demais folhas atuais e toda a coluna anterior permanecem conforme suas próprias origens
