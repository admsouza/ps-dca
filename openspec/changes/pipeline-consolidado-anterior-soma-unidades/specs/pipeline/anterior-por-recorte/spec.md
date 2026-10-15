# pipeline/anterior-por-recorte — Delta spec

## ADDED Requirements

### Requirement: Consolidado anterior é a soma das unidades

No BF e no BP, a coluna do exercício anterior do `consolidado` SHALL ser derivada exclusivamente das
colunas anteriores já resolvidas dos recortes de unidade `ug:` ou `po:` do mesmo job. O consolidado
NÃO DEVE resolver, ler, persistir nem reaplicar origem própria.

Cada folha SHALL ser a soma em centavos das unidades. As totalizadoras SHALL ser recalculadas a partir
das folhas consolidadas. No Superávit/Déficit do BP, SHALL ser usada a união das fontes; fonte ausente
em uma unidade conta `0,00`. Se qualquer unidade tiver uma célula não apurada, a célula consolidada
correspondente SHALL permanecer não apurada, com o motivo preservado — nunca convertida em zero.

A procedência do consolidado SHALL declarar
`origem_exercicio_anterior=soma_das_unidades`, sem `escolha_anterior`,
`anterior_processado` ou `valores_anteriores` próprios do consolidado.

#### Scenario: Cuitegi consolidado pela soma dos POs

- **GIVEN** os três POs do BP de Cuitegi/PB (`2505204`) com `L1` atual de 2025 somando `76.314.331,92`
- **WHEN** esses recortes alimentam a coluna anterior do BP 2026
- **THEN** o `L1` anterior do consolidado é `76.314.331,92`
- **AND** a diferença entre consolidado e soma dos POs é `0,00`
- **AND** a procedência declara `soma_das_unidades`

#### Scenario: origens diferentes entram na mesma soma

- **GIVEN** uma UG em `processado`, uma em `msce` e uma em `manual`
- **WHEN** o BF ou o BP é apurado
- **THEN** cada célula anterior do consolidado é a soma das células resolvidas dessas UGs
- **AND** nenhuma origem adicional é consultada para o consolidado

#### Scenario: fonte do Superávit ausente em uma unidade

- **GIVEN** uma fonte do Superávit/Déficit presente em apenas uma das unidades do BP
- **WHEN** o consolidado é formado
- **THEN** a fonte aparece no consolidado com o valor dessa unidade
- **AND** as demais unidades contribuem com `0,00` para essa fonte

#### Scenario: célula não apurada não vira zero

- **GIVEN** uma unidade com uma célula anterior não apurada
- **WHEN** o consolidado é formado
- **THEN** a célula consolidada correspondente fica não apurada
- **AND** o diagnóstico identifica a unidade e o motivo sem expor valores sensíveis

### Requirement: Toda parcela anterior pertence a uma unidade

Toda contribuição que afete a coluna anterior do consolidado SHALL pertencer a exatamente um recorte
`ug:` ou `po:` emitido no resultado. `po:` sem código continua sendo um recorte válido quando a fonte
o produzir. Contribuição sem recorte ou atribuída a mais de um recorte SHALL falhar de forma segura:
o job termina em `erro` e nenhum resultado parcial é publicado como `ok`.

#### Scenario: contribuição sem UG ou PO

- **GIVEN** uma parcela da coluna anterior que afeta o consolidado e não pertence a nenhum recorte
- **WHEN** o BF ou o BP é apurado
- **THEN** o job termina em `erro` com diagnóstico de parcela sem unidade
- **AND** nenhum consolidado parcial é gravado como `ok`

#### Scenario: nenhuma unidade emitida

- **GIVEN** uma fonte sem qualquer recorte `ug:` ou `po:` para o exercício
- **WHEN** o BF ou o BP é apurado
- **THEN** o job termina em `erro`
- **AND** um consolidado vazio não é publicado

### Requirement: Origem anterior é configurável somente por unidade

As escolhas de origem SHALL ser recebidas apenas em `anterior_por_recorte`, com chaves `ug:` ou
`po:`. No BF e no BP, `origem_exercicio_anterior` e `valores_anteriores` próprios do consolidado
NÃO DEVEM ser aceitos. No corpo, SHALL responder `422`; na query, SHALL responder `400`. A validação
SHALL ocorrer antes de enfileirar job ou alterar cache.

Preferências antigas do consolidado presentes no cache NÃO DEVEM ser reaplicadas. Um novo resultado
válido SHALL substituí-las pela procedência `soma_das_unidades`.

#### Scenario: origem própria no corpo é recusada

- **WHEN** `POST /dca/BF/reprocessar` ou `POST /dca/BP/reprocessar` recebe `origem_exercicio_anterior`
- **THEN** responde `422`
- **AND** nenhum job é enfileirado

#### Scenario: mapa manual consolidado é recusado

- **WHEN** o corpo contém `valores_anteriores` no topo, em vez de um manual por unidade
- **THEN** responde `422`
- **AND** o cache não é alterado

#### Scenario: preferência antiga não é reaplicada

- **GIVEN** cache anterior à change com origem própria ou manual do consolidado
- **WHEN** ocorre novo processamento sem esses campos
- **THEN** o consolidado é formado pela soma das unidades
- **AND** a nova procedência não contém a preferência antiga

## REMOVED Requirements

### Requirement: Consolidado com origem processada

**Motivo:** o consolidado deixa de ter qualquer origem própria e passa a derivar das unidades. ·
**Migração:** usar `anterior_por_recorte` para escolher a origem de cada `ug:`/`po:`; o consolidado
declara `soma_das_unidades`.
