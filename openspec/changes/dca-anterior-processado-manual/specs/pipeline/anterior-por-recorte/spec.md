# pipeline/anterior-por-recorte — Delta spec

## MODIFIED Requirements

### Requirement: A coluna anterior aceita somente Processado ou Manual por unidade

A origem da coluna do exercício anterior de BF e BP SHALL ser resolvida por unidade `ug:` ou `po:`.
Sem escolha manual válida, a origem SHALL ser `processado_exercicio_anterior`, usando a coluna atual
do mesmo recorte no resultado `ok` de N−1. A única alternativa SHALL ser `manual`, com mapa válido da
própria unidade. O sistema NÃO DEVE oferecer, aceitar ou aplicar MSCE de N−1 como origem ou fallback.

O consolidado e os grupos SHALL continuar sendo a soma das unidades. A coluna atual NÃO DEVE mudar.

#### Scenario: padrão usa Processado
- **GIVEN** que BF ou BP de 2024 contém a unidade no cache com status `ok`
- **WHEN** 2025 é processado sem escolha explícita para a unidade
- **THEN** a coluna anterior vem da coluna atual processada em 2024
- **AND** nenhuma leitura de MSC de 2024 preenche essa coluna

#### Scenario: padrão sem Processado orienta a correção
- **GIVEN** que a unidade não tem resultado processado em 2024
- **WHEN** BF ou BP de 2025 é solicitado sem mapa manual válido
- **THEN** a resposta é `409`
- **AND** a mensagem orienta processar 2024 ou informar os valores manualmente
- **AND** nenhum resultado parcial é publicado

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
- **AND** sem N−1 processado o processamento falha de forma segura
