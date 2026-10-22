# pipeline/anterior-por-recorte — Delta spec

## MODIFIED Requirements

### Requirement: A coluna anterior nunca impede a apuração do exercício atual

A origem da coluna do exercício anterior de BF e BP SHALL ser resolvida por unidade `ug:` ou `po:`.
Havendo resultado `ok` de N−1 para a unidade, a origem SHALL ser `processado_exercicio_anterior`,
usando a coluna atual do mesmo recorte. Havendo mapa `manual` válido da própria unidade, a origem
SHALL ser `manual`. Não havendo nem um nem outro, a origem SHALL ser `sem_anterior`: a coluna do
exercício anterior daquela unidade SHALL ser `0,00` em todas as células — nunca célula não apurada,
para não apagar a coluna anterior dos grupos e do consolidado que a somam —, e a unidade SHALL ser
marcada no diagnóstico como sem dados do exercício anterior.

O sistema NÃO DEVE recusar o pedido, falhar o processamento nem publicar resultado parcial por causa
da coluna anterior. O sistema NÃO DEVE oferecer, aceitar ou aplicar MSCE de N−1 como origem ou
fallback. O consolidado e os grupos SHALL continuar sendo a soma das unidades. A coluna atual NÃO
DEVE mudar.

#### Scenario: padrão usa Processado
- **GIVEN** que BF ou BP de 2024 contém a unidade no cache com status `ok`
- **WHEN** 2025 é processado sem escolha explícita para a unidade
- **THEN** a coluna anterior vem da coluna atual processada em 2024
- **AND** nenhuma leitura de MSC de 2024 preenche essa coluna

#### Scenario: primeira apuração sem exercício anterior conclui
- **GIVEN** um ente com duas unidades e nenhum resultado de BP 2024 em cache
- **WHEN** BP 2025 é processado sem nenhuma escolha explícita
- **THEN** o job conclui com status `ok`
- **AND** a coluna anterior das duas unidades é `0,00` em todas as células
- **AND** o diagnóstico das duas unidades marca a ausência de dados do exercício anterior
- **AND** nenhuma resposta `409` é devolvida

#### Scenario: Manual e zero convivem no mesmo job
- **GIVEN** duas unidades sem resultado processado em 2024
- **WHEN** BP 2025 é processado com mapa `manual` válido só para a primeira
- **THEN** a primeira usa o mapa informado
- **AND** a segunda fica com a coluna anterior em `0,00` e marcada no diagnóstico
- **AND** o consolidado traz o Manual da primeira somado ao `0,00` da segunda

#### Scenario: exercício anterior em processamento ou com erro
- **GIVEN** que BP 2024 está em cache com status `processando` ou `erro`
- **WHEN** BP 2025 é processado sem escolha explícita
- **THEN** a coluna anterior fica em `0,00`
- **AND** o aviso do diagnóstico registra o motivo pelo qual N−1 não serviu

#### Scenario: Manual permanece disponível
- **WHEN** uma unidade recebe `manual` com mapa válido
- **THEN** o mapa preenche a coluna anterior dessa unidade
- **AND** participa da soma dos grupos e do consolidado

#### Scenario: MSCE deixa de ser escolha pública
- **WHEN** `anterior_por_recorte` recebe `msce_exercicio_anterior`
- **THEN** a resposta é `422`
- **AND** nenhum job é enfileirado nem cache alterado

#### Scenario: escolha antiga de MSCE não mantém fallback oculto
- **GIVEN** procedência antiga com escolha `msce_exercicio_anterior`
- **WHEN** o anexo é reprocessado sem nova escolha
- **THEN** a escolha antiga é tratada como padrão Processado
- **AND** sem N−1 processado a coluna anterior fica em `0,00`, marcada no diagnóstico

## REMOVED Requirements

### Requirement: Padrão sem Processado recusa o pedido com `409`

**Motivo:** a coluna anterior deixa de ser pré-requisito da apuração — o usuário apura para conferir
o exercício atual, e a recusa criava impasse na primeira apuração, quando a lista de unidades ainda
não existe. **Migração:** a unidade cai em `sem_anterior` (coluna `0,00`) e é marcada no diagnóstico;
a exigência de dado conferido passa ao módulo de homologação da DCA.
