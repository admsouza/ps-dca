# pipeline/plataforma — Delta spec

## MODIFIED Requirements

### Requirement: Ciclo único de requisição, cache e job

Toda leitura de anexo SHALL responder por um destes quatro caminhos, decididos pelo estado do cache
para a identidade solicitada: resultado pronto (`ok`) → `200`, **mesmo que desatualizado**;
processamento em voo → `202` com o `job_id` **do job em voo** e `status: already_queued`; ausente ou
em erro → job criado, enfileirado e `202` com `job_id` e `status: processing`; falha na criação do
job → erro explícito. A leitura NÃO DEVE enfileirar job quando houver resultado `ok` para a
identidade: processar resultado existente é ação explícita (`reprocessar` ou percurso). A rota NÃO
DEVE executar apuração, e NÃO DEVE devolver resultado parcial.

#### Scenario: cache válido

- **GIVEN** cache `ok` para `(ente, exercício, anexo)` com versão de API e de regras atuais
- **WHEN** o anexo é solicitado
- **THEN** a resposta é `200` com o resultado, `desatualizado: false` e `motivos_desatualizado: []`
- **AND** nenhum job é enfileirado

#### Scenario: visualizar resultado desatualizado não processa

- **GIVEN** cache `ok` gravado com outra `versao_api`, outra `versao_regras` e outra fonte
- **WHEN** o anexo é solicitado por `GET`
- **THEN** a resposta é `200` com o resultado gravado
- **AND** `desatualizado` é `true` e `motivos_desatualizado` é `["versao_api", "versao_regras", "pedido"]`
- **AND** nenhum job é enfileirado e o cache não é alterado

#### Scenario: cache ausente

- **WHEN** não há registro de cache para a identidade
- **THEN** a resposta é `202` com `job_id`, `poll_url` e `sse_url`
- **AND** o registro passa a `processando` antes de a resposta ser devolvida

#### Scenario: processamento já em voo

- **GIVEN** um job legítimo em execução para a mesma identidade
- **WHEN** um segundo cliente solicita o mesmo anexo
- **THEN** a resposta é `202` com `status: already_queued`, o `job_id` do job em voo e as URLs de
  acompanhamento, orientando a aguardar
- **AND** nenhum segundo job é enfileirado
- **AND** o `status` — não a ausência do `job_id` — é o que informa que o job não é do cliente

#### Scenario: apuração falhou

- **GIVEN** cache com `status: erro` e `erro_detalhe` preenchido
- **WHEN** o anexo é solicitado
- **THEN** um novo job é criado
- **AND** o `erro_detalhe` anterior é substituído, nunca acumulado

### Requirement: Identidade do resultado e invalidação por versão

A identidade de um resultado SHALL ser `(id_ente, an_referencia, anexo)`. O cache SHALL ser tratado
como **desatualizado** quando `versao_api`, `versao_regras` ou os parâmetros do pedido (fonte,
competência, origem do exercício anterior) divergirem dos atuais. Desatualizado NÃO é ausente: a
leitura o serve marcado, e só o reprocessamento explícito ou o percurso o reapuram (decisão do PO,
2026-10-07).

O percurso completo SHALL gravar a mesma identidade de pedido que a leitura confere, com a fonte
padrão da instalação. Sem ela, todo anexo apurado pelo percurso sairia desatualizado na primeira
leitura.

**O resultado apurado persiste, e a retificação da declaração NÃO o invalida sozinha** (decisão do
PO, 2026-09-23). É a diferença deliberada em relação ao **dado** da MSC, que não é persistido em
lugar nenhum: o dado bruto é rebaixado a cada job porque o ente retifica declaração já publicada; o
demonstrativo apurado permanece e só é reapurado por pedido explícito. Reapurar depois de uma
retificação é **ação de quem pede** — `POST /dca/{anexo}/reprocessar` — e não efeito automático de
tempo nem de leitura. Não há TTL no resultado.

#### Scenario: regra alterada marca o cache como desatualizado

- **GIVEN** cache `ok` gravado com `versao_regras` `A`
- **WHEN** a base canônica passa a `B` e o anexo é solicitado por `GET`
- **THEN** o resultado gravado é servido com `motivos_desatualizado` contendo `versao_regras`
- **AND** nenhum job é enfileirado

#### Scenario: reprocessar e percurso reapuram o desatualizado

- **GIVEN** cache `ok` desatualizado por `versao_regras`
- **WHEN** o anexo é reprocessado, ou o percurso roda sem `forcar`
- **THEN** o anexo é reapurado

#### Scenario: identificador de regra é estável a formatação

- **GIVEN** um resultado em cache
- **WHEN** os arquivos de regra são reescritos com outra quebra de linha, outra indentação ou outra
  ordem de chaves, sem alterar conteúdo
- **THEN** o cache permanece atual
- **AND** nenhuma reapuração é disparada

#### Scenario: alteração real de regra desatualiza

- **WHEN** uma conta, filtro ou cálculo de uma regra carregada muda
- **THEN** o cache passa a ser servido como desatualizado, com motivo `versao_regras`

#### Scenario: regra de outro anexo não invalida

- **GIVEN** cache válido de um anexo
- **WHEN** a regra de um anexo diferente é alterada
- **THEN** o cache do primeiro permanece atual

#### Scenario: versão da API alterada desatualiza o cache

- **WHEN** `versao_api` do registro difere da atual e o anexo é solicitado por `GET`
- **THEN** o resultado gravado é servido com motivo `versao_api`
- **AND** nenhum job é enfileirado

#### Scenario: visualização depois do percurso reconhece o cache

- **GIVEN** um percurso concluído com a fonte padrão `siconfi`
- **WHEN** um anexo do percurso é solicitado por `GET` com `use_siconfi=true`
- **THEN** a resposta é `200` com `desatualizado: false`
- **AND** nenhum job é enfileirado

#### Scenario: entes e exercícios não colidem

- **GIVEN** resultados do mesmo anexo para dois entes e dois exercícios
- **WHEN** cada um é solicitado
- **THEN** cada resposta traz o resultado da sua identidade
- **AND** nenhuma leitura devolve o resultado de outra
