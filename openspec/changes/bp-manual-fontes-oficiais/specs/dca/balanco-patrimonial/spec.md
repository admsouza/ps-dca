# dca/balanco-patrimonial — Delta spec

## ADDED Requirements

### Requirement: Catálogo canônico de fontes para preenchimento manual

O sistema SHALL publicar `GET /dca/fontes-recursos` com as fontes permitidas no preenchimento manual
do Quadro do Superávit / Déficit Financeiro. A resposta SHALL ser derivada de
`docs/contas-stn/fonte-recursos.md`, sem cópia paralela e sem consulta externa em tempo de requisição.

Para cada código principal oficial de três dígitos, o catálogo SHALL conter exatamente uma opção com
prefixo `1` e uma com prefixo `2`. Cada item SHALL ter `codigo` com quatro dígitos e `nome` com a
nomenclatura oficial; o prefixo `2` SHALL acrescentar ` - Exercícios Anteriores`. A resposta SHALL
estar ordenada por código e não SHALL conter duplicidade.

A rota SHALL exigir autenticação, mas não SHALL ler dados de ente, MSC, cache ou fila.

#### Scenario: catálogo deriva duas opções por código principal

- **GIVEN** o catálogo canônico contém o código principal `621`
- **WHEN** `GET /dca/fontes-recursos` é consultado com JWT válido
- **THEN** a resposta contém uma única opção `1621`
- **AND** contém uma única opção `2621`
- **AND** ambas usam a nomenclatura oficial de `621`, com o sufixo de exercícios anteriores somente em `2621`

#### Scenario: catálogo não possui códigos arbitrários

- **GIVEN** que `999` não existe no catálogo canônico
- **WHEN** `GET /dca/fontes-recursos` é consultado
- **THEN** `1999` e `2999` aparecem zero vezes na resposta

#### Scenario: catálogo exige autenticação

- **WHEN** `GET /dca/fontes-recursos` é consultado sem JWT válido
- **THEN** a resposta é `401`
- **AND** nenhum dado interno é exposto

### Requirement: Fonte manual pertence ao catálogo canônico

Uma chave manual `S:<fonte>` SHALL ser aceita somente quando `<fonte>` tiver prefixo `1` ou `2` e os
três dígitos restantes existirem no catálogo canônico. A validação SHALL ocorrer na rota antes do
enfileiramento e SHALL usar o mesmo carregador do endpoint e dos rótulos das linhas apuradas.

#### Scenario: fonte oficial é aceita

- **GIVEN** o catálogo canônico contém `621`
- **WHEN** o BP é reprocessado no modo Manual com `S:1621 = 20000.00`
- **THEN** a entrada passa pela validação de fontes
- **AND** o processamento mantém a chave `S:1621`

#### Scenario: código principal inexistente é recusado

- **GIVEN** que `999` não existe no catálogo canônico
- **WHEN** o BP é reprocessado no modo Manual com `S:1999 = 20000.00`
- **THEN** a resposta é `422`
- **AND** nenhum job é enfileirado

#### Scenario: prefixo de exercício inválido é recusado

- **WHEN** o BP é reprocessado no modo Manual com `S:3621 = 20000.00`
- **THEN** a resposta é `422`
- **AND** nenhum job é enfileirado
