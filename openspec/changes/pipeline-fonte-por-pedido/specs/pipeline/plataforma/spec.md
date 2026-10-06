# pipeline/plataforma — Delta spec

## ADDED Requirements

### Requirement: Fonte de dados escolhida por pedido

A leitura e o reprocessamento de anexo SHALL aceitar `use_siconfi` na query. `true` SHALL apurar
pela SICONFI; `false` SHALL apurar pela PublicSoft. Sem o parâmetro, vale `false`. A fonte do
pedido SHALL prevalecer sobre a fonte padrão do processo (`DATA_SOURCE`).

A fonte pedida SHALL fazer parte da identidade do resultado em cache. Um resultado apurado por uma
fonte NÃO DEVE ser servido a um pedido da outra.

#### Scenario: SIAFIC escolhido com worker padrão SICONFI

- **GIVEN** o worker com `DATA_SOURCE=siconfi`
- **WHEN** chega `GET /dca/BF?anReferencia=2025&id_ente=2505204&use_siconfi=false` sem cache válido
- **THEN** a resposta é `202`
- **AND** o job apura pela PublicSoft
- **AND** `L27` exercício atual sai `4486188.21` e `procedencia.estorno_receita_extra["2025"]` sai `"115679.40"`

#### Scenario: SICONFI escolhido

- **WHEN** chega `use_siconfi=true`
- **THEN** o job apura pela SICONFI
- **AND** nenhuma credencial de fonte é resolvida nem guardada

#### Scenario: pedido sem fonte

- **GIVEN** o worker com `DATA_SOURCE=siconfi`
- **WHEN** chega o `GET` sem `use_siconfi`
- **THEN** o job apura pela PublicSoft

#### Scenario: troca de fonte não serve o cache da outra

- **GIVEN** o BF apurado com `use_siconfi=true`, em cache `ok`
- **WHEN** chega o `GET` do mesmo ente e exercício com `use_siconfi=false`
- **THEN** a resposta é `202`
- **AND** o resultado SICONFI não é devolvido

#### Scenario: parâmetro inválido

- **WHEN** `use_siconfi=talvez`
- **THEN** a resposta é `422` e nenhum job é criado

### Requirement: Credencial PublicSoft resolvida no servidor

Pedido com fonte PublicSoft SHALL resolver o `token_ps` do ente no hub
(`POST /internal/resolve-tenant`, `{sub, cod_ibge}`, `X-Internal-Secret`) antes de criar o job, e
SHALL guardá-lo cifrado para o job, com a expiração do job. O token NÃO DEVE ir no payload da fila
nem em log. A credencial vinda do browser continua rejeitada.

#### Scenario: token guardado para o job

- **WHEN** um pedido com `use_siconfi=false` cria job
- **THEN** o worker consulta a PublicSoft com o `token_ps` do ente em `x-authorization`
- **AND** o payload do job não contém o token

#### Scenario: ente inexistente no hub

- **WHEN** o hub responde `404` para o ente
- **THEN** a resposta é `404` e nenhum job é criado

#### Scenario: ente sem token_ps

- **WHEN** o hub responde `409` para o ente
- **THEN** a resposta é `409` e nenhum job é criado

#### Scenario: hub indisponível

- **WHEN** o hub não responde ao resolver o token
- **THEN** a resposta é `503` e nenhum job é criado
