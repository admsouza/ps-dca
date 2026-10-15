# pipeline/anterior-por-recorte — Delta spec

## ADDED Requirements

### Requirement: Escolha por unidade restrita ao poder do usuário
O `reprocessar` do BF e do BP SHALL aceitar uma chave em `anterior_por_recorte` só quando a unidade
for visível ao usuário pela mesma regra da leitura: quem tem `consolidado` vê todas; os demais veem
as unidades cujo `poder_orgao` pertence a um dos seus poderes.

O poder da unidade é resolvido assim: `po:` pelo código; `ug:` pelo `poderOrgao` gravado no cache
de N, ou no de N−1 na falta dele. Unidade sem poder resolvido MUST ser tratada como visível só para
`consolidado`.

Uma chave fora do poder MUST recusar o pedido inteiro com `403`, sem job e sem gravar nenhuma
escolha. Sem `poderes` no estado da requisição, todo `anterior_por_recorte` MUST receber `403`.
A validação de formato (`422`) vem antes da de poder.

#### Scenario: Unidade do próprio poder
- **GIVEN** Cuitegi 2025, cache do BP de N com a Prefeitura (`poderOrgao` 10131)
- **WHEN** um usuário com o poder `executivo` reprocessa com `{"ug:<Prefeitura>": {"origem": "msce_exercicio_anterior"}}`
- **THEN** a resposta é `202` e a escolha é gravada

#### Scenario: Unidade de outro poder
- **GIVEN** o mesmo cache, com a Câmara (`poderOrgao` 20231)
- **WHEN** um usuário só do `executivo` envia `{"ug:<Câmara>": {"origem": "manual", "valores": {"P:L3": "1.00"}}}`
- **THEN** a resposta é `403` "sem acesso à unidade ug:<Câmara>", nenhum job é enfileirado e a escolha gravada da Câmara não muda

#### Scenario: Pedido misto é tudo ou nada
- **WHEN** um usuário só do `executivo` envia a Prefeitura e a Câmara no mesmo pedido
- **THEN** a resposta é `403` e nenhuma das duas escolhas é gravada

#### Scenario: Poder/Órgão pelo código
- **WHEN** um usuário só do `executivo` envia `po:20231`
- **THEN** a resposta é `403`

#### Scenario: Consolidado escolhe qualquer unidade
- **WHEN** um usuário com `consolidado` envia a Câmara
- **THEN** a resposta é `202`, igual ao comportamento atual

#### Scenario: UG desconhecida
- **GIVEN** `ug:999` fora do cache de N e de N−1
- **WHEN** um usuário só do `executivo` a envia
- **THEN** a resposta é `403`
