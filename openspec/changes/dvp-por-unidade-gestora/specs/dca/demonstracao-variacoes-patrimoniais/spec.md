# dca/demonstracao-variacoes-patrimoniais — Delta spec

## ADDED Requirements

### Requirement: Coluna do exercício anterior da DVP por unidade

Fora do consolidado, a coluna `exercicio_anterior` de cada unidade SHALL vir de uma de três
origens: `processado_exercicio_anterior`, `msce_exercicio_anterior` ou `manual`. O pedido SHALL
escolher `processado_exercicio_anterior`, `manual` ou `padrao`; `msce_exercicio_anterior` NÃO DEVE
ser aceito como escolha do pedido — ele é o padrão resolvido quando não há processado de N−1, como
já vale para BF e BP. A escolha explícita SHALL ficar gravada e ser reaplicada em pedido que não a
mencione.

O consolidado e o grupo de poder NÃO DEVEM ter origem própria: a coluna anterior de cada um SHALL
ser a soma das colunas já resolvidas das unidades que o compõem. A DVP NÃO DEVE oferecer
`publicado_siconfi` por unidade — o `DCA-Anexo I-HI` é publicado só para o ente inteiro.

#### Scenario: processado traz a procedência do N−1

- **GIVEN** uma unidade com resultado `ok` de N−1 no cache
- **WHEN** a DVP de N é apurada com `processado_exercicio_anterior` para ela
- **THEN** a coluna anterior dela é a coluna atual daquele resultado
- **AND** `procedencia.anterior_processado` traz o exercício e a versão de regras de N−1

#### Scenario: unidade sem MSC no exercício anterior

- **GIVEN** uma unidade no padrão sem registros de N−1
- **WHEN** a DVP é apurada
- **THEN** a coluna anterior dela é 0,00
- **AND** `diagnostico.sem_dados_exercicio_anterior` registra a unidade

#### Scenario: msce não é escolha do pedido

- **WHEN** um pedido informa `origem: msce_exercicio_anterior` para uma unidade
- **THEN** a resposta é 422, pela mesma regra que vale para BF e BP

#### Scenario: consolidado soma as unidades

- **WHEN** a DVP é apurada com unidades de origens diferentes
- **THEN** a coluna anterior do consolidado é a soma das colunas anteriores já resolvidas das
  unidades do job

### Requirement: Manual da DVP por unidade

No `manual`, SHALL ser digitáveis apenas as linhas sem `referencias` — na DVP, L2–L8 e L10–L18.
Linha totalizadora SHALL ser recusada pela estrutura do mapa, como no manual por unidade do BP, e
seu valor SHALL sair da `calculation`. A chave informada SHALL ser o código da linha, sem prefixo
de quadro: a DVP tem um quadro só. Manual sem valores SHALL responder 422 antes de enfileirar.

#### Scenario: manual recusa linha totalizadora

- **WHEN** um pedido manual informa valor para L1, L9 ou L19
- **THEN** a resposta é 422
- **AND** nenhum job é enfileirado

#### Scenario: totalizadora sai da calculation

- **GIVEN** um manual que informa todas as linhas-base de `VPA` para uma unidade
- **WHEN** a DVP é apurada
- **THEN** L1 da coluna anterior é a soma delas, e não um valor digitado

#### Scenario: manual sem valores

- **WHEN** um pedido escolhe `manual` para uma unidade e não informa valores
- **THEN** a resposta é 422, sem job
