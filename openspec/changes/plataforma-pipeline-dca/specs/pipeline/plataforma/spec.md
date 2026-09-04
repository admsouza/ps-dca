# pipeline/plataforma — Delta spec

## Purpose

Garantir que todo anexo da DCA seja servido pelo **mesmo ciclo** — requisição → cache → job →
worker → cache → leitura — já em produção no `regras-rreo-api` e no `regras-rgf-api`, com um único
mecanismo de cache, lock e registry, e com o núcleo de apuração isolado de HTTP, banco e fila.

Esta capability define o **fluxo**, nunca a regra de um anexo: o que cada demonstrativo calcula
pertence às capabilities de `dca/`. Um anexo entra no pipeline registrando-se; não reimplementando
o ciclo.

## ADDED Requirements

### Requirement: Ciclo único de requisição, cache e job

Toda leitura de anexo SHALL responder por um destes quatro caminhos, decididos pelo estado do cache
para a identidade solicitada: resultado pronto → `200`; processamento em voo → `202` sem `job_id`;
ausente ou inválido → job criado, enfileirado e `202` com `job_id`; falha na criação do job →
erro explícito. A rota NÃO DEVE executar apuração, e NÃO DEVE devolver resultado parcial.

#### Scenario: cache válido

- **GIVEN** cache `ok` para `(ente, exercício, anexo)` com versão de API e de regras atuais
- **WHEN** o anexo é solicitado
- **THEN** a resposta é `200` com o resultado
- **AND** nenhum job é enfileirado

#### Scenario: cache ausente

- **WHEN** não há registro de cache para a identidade
- **THEN** a resposta é `202` com `job_id`, `poll_url` e `sse_url`
- **AND** o registro passa a `processando` antes de a resposta ser devolvida

#### Scenario: processamento já em voo

- **GIVEN** um job legítimo em execução para a mesma identidade
- **WHEN** um segundo cliente solicita o mesmo anexo
- **THEN** a resposta é `202` sem `job_id`, orientando a aguardar
- **AND** nenhum segundo job é enfileirado

#### Scenario: apuração falhou

- **GIVEN** cache com `status: erro` e `erro_detalhe` preenchido
- **WHEN** o anexo é solicitado
- **THEN** um novo job é criado
- **AND** o `erro_detalhe` anterior é substituído, nunca acumulado

### Requirement: Identidade do resultado e invalidação por versão

A identidade de um resultado SHALL ser `(id_ente, an_referencia, anexo)`. O cache SHALL ser tratado
como inválido quando `versao_api` ou `versao_regras` divergirem das atuais. A apuração NÃO DEVE
servir resultado cuja versão de regras não seja a vigente.

#### Scenario: regra alterada invalida o cache

- **GIVEN** cache `ok` gravado com `versao_regras` `A`
- **WHEN** a base canônica passa a `B` e o anexo é solicitado
- **THEN** o cache é tratado como miss e um novo job é enfileirado
- **AND** o resultado antigo NÃO é servido

#### Scenario: identificador de regra é estável a formatação

- **GIVEN** um resultado em cache
- **WHEN** os arquivos de regra são reescritos com outra quebra de linha, outra indentação ou outra
  ordem de chaves, sem alterar conteúdo
- **THEN** o cache permanece válido
- **AND** nenhuma reapuração é disparada

#### Scenario: alteração real de regra invalida

- **WHEN** uma conta, filtro ou cálculo de uma regra carregada muda
- **THEN** o cache passa a ser tratado como miss

#### Scenario: regra de outro anexo não invalida

- **GIVEN** cache válido de um anexo
- **WHEN** a regra de um anexo diferente é alterada
- **THEN** o cache do primeiro permanece válido

#### Scenario: versão da API alterada invalida o cache

- **WHEN** `versao_api` do registro difere da atual
- **THEN** o cache é tratado como miss

#### Scenario: entes e exercícios não colidem

- **GIVEN** resultados do mesmo anexo para dois entes e dois exercícios
- **WHEN** cada um é solicitado
- **THEN** cada resposta traz o resultado da sua identidade
- **AND** nenhuma leitura devolve o resultado de outra

### Requirement: Um único mecanismo de cache para todos os anexos

O resultado de qualquer anexo SHALL ser persistido pelo mesmo serviço, na mesma tabela,
discriminado pela coluna de anexo. NÃO DEVE existir tabela, model ou serviço de cache por anexo.

#### Scenario: anexo novo não cria estrutura de cache

- **WHEN** um anexo novo passa a ser apurado
- **THEN** ele grava e lê pelo mesmo serviço, sem migration de tabela nova
- **AND** o resumo agregado o inclui sem alteração de código de cache

#### Scenario: status permitido

- **WHEN** um registro de cache é gravado
- **THEN** seu `status` é `ok`, `processando` ou `erro`
- **AND** qualquer outro valor é rejeitado pela persistência

### Requirement: Anexo é um conjunto fechado

O identificador de anexo SHALL pertencer a um conjunto fechado e conhecido, validado tanto na
entrada da requisição quanto na persistência. Valor fora do conjunto SHALL ser rejeitado; NÃO DEVE
ser gravado, nem aparecer no resumo agregado.

#### Scenario: anexo desconhecido é rejeitado na entrada

- **WHEN** um anexo fora do conjunto é solicitado
- **THEN** a resposta é `400`, nomeando os valores aceitos
- **AND** nenhum job é criado

#### Scenario: grafia divergente não fragmenta o cache

- **GIVEN** um resultado gravado para um anexo do conjunto
- **WHEN** o mesmo anexo é solicitado com grafia diferente em maiúsculas/minúsculas
- **THEN** ou a requisição resolve para a mesma identidade, ou é rejeitada
- **AND** em nenhum caso um segundo registro de cache é criado para o mesmo demonstrativo

#### Scenario: persistência recusa anexo inválido

- **WHEN** uma gravação tenta usar identificador fora do conjunto
- **THEN** a persistência a rejeita

### Requirement: Rota e worker apenas orquestram

A rota de anexo SHALL se limitar a validar entrada e autorização, ler o cache, enfileirar e
responder. A função registrada no worker SHALL se limitar a delegar ao serviço de apuração e
registrar o resultado. Nenhuma das duas SHALL conter regra de cálculo, consulta a fonte de dados ou
composição de demonstrativo.

#### Scenario: apuração é alcançável sem rota e sem worker

- **GIVEN** o serviço de apuração de um anexo
- **WHEN** ele é chamado diretamente, sem rota e sem worker
- **THEN** o resultado é completo e idêntico ao do ciclo HTTP
- **AND** nenhuma etapa do cálculo depende de código que só existe na rota ou no worker

#### Scenario: fonte de dados não é consultada pela rota

- **WHEN** uma requisição de anexo é atendida
- **THEN** nenhuma consulta a fonte MSC parte do processo da API

### Requirement: Lock por identidade com recuperação de órfão

Job em voo SHALL ser protegido por lock sobre a identidade. Lock cujo job não esteja mais em
execução SHALL ser tratado como órfão: liberado, registrado em log e o processamento reiniciado. O
mecanismo SHALL ser único; NÃO DEVE haver cópia por anexo.

#### Scenario: segundo job para a mesma identidade

- **GIVEN** lock ativo com job em `processing`
- **WHEN** outra requisição chega para a mesma identidade
- **THEN** ela recebe o `job_id` existente
- **AND** nenhum segundo job é enfileirado

#### Scenario: worker reiniciado deixa lock órfão

- **GIVEN** lock apontando para um job que não está mais em execução
- **WHEN** o anexo é solicitado
- **THEN** o lock é liberado, o evento é logado e um job novo é criado
- **AND** a identidade não fica permanentemente bloqueada

#### Scenario: limpeza no startup do worker

- **WHEN** o worker inicia
- **THEN** locks órfãos remanescentes são liberados antes de consumir a fila

### Requirement: Acompanhamento por polling e por stream

Todo job SHALL ser consultável por `job_id`, devolvendo estado `processing`, `done` ou `error`, e
SHALL ser acompanhável por stream de eventos. O resultado SHALL estar disponível quando o estado for
`done`; o motivo, quando for `error`.

#### Scenario: polling até a conclusão

- **GIVEN** um `job_id` devolvido por uma requisição
- **WHEN** o cliente consulta o job repetidamente
- **THEN** o estado evolui de `processing` para `done`
- **AND** o resultado fica disponível na conclusão

#### Scenario: job com erro expõe o motivo

- **WHEN** a apuração falha
- **THEN** o estado é `error` com a descrição da falha
- **AND** o cache da identidade fica com `status: erro` e o mesmo detalhe

### Requirement: Reprocessamento forçado de um anexo

SHALL existir forma de solicitar a reapuração de um anexo mesmo com cache válido. O
reprocessamento SHALL exigir a mesma autorização da leitura, SHALL registrar quem o solicitou e
SHALL seguir o mesmo ciclo de job e lock. O resultado anterior SHALL permanecer legível até o novo
substituí-lo; NÃO DEVE haver janela em que o anexo fique sem resultado por causa de um
reprocessamento.

#### Scenario: reprocessamento com cache válido

- **GIVEN** cache `ok` com versões atuais
- **WHEN** o reprocessamento do anexo é solicitado
- **THEN** um job é criado e a resposta traz `job_id`
- **AND** o solicitante é registrado no cache do novo resultado

#### Scenario: resultado anterior continua legível

- **GIVEN** um reprocessamento em andamento
- **WHEN** outro cliente solicita o mesmo anexo
- **THEN** ele recebe o resultado anterior ou a indicação de processamento
- **AND** em nenhum momento a resposta é "sem resultado"

#### Scenario: reprocessamento não escapa do lock

- **GIVEN** um job já em voo para a identidade
- **WHEN** o reprocessamento é solicitado
- **THEN** ele recebe o `job_id` existente
- **AND** nenhum segundo job é enfileirado

#### Scenario: reprocessamento exige autorização

- **WHEN** o reprocessamento é solicitado sem autorização para o ente
- **THEN** a resposta é `403`
- **AND** nenhum job é criado

### Requirement: Resumo agregado responde sempre

O resumo do estado de todos os anexos SHALL responder `200` mesmo quando nenhum tiver cache, SHALL
listar os anexos na ordem canônica e SHALL trazer, por anexo, apenas metadados — nunca o resultado.
Anexo ainda sem implementação SHALL aparecer como `sem_cache`; NÃO DEVE ser omitido. O resumo NÃO
DEVE iniciar cálculo.

#### Scenario: bootstrap sem nenhum cache

- **WHEN** o resumo é solicitado para um ente sem nenhuma apuração
- **THEN** a resposta é `200` com todos os anexos em `sem_cache`
- **AND** nenhum job é enfileirado

#### Scenario: metadados sem payload

- **WHEN** o resumo é solicitado com anexos já apurados
- **THEN** cada entrada traz status, data de cálculo, versões e duração
- **AND** nenhuma entrada traz o resultado do demonstrativo

### Requirement: Apuração não roda no processo da API

A apuração SHALL ocorrer no worker. A API NÃO DEVE executar cálculo de anexo no ciclo da
requisição, mesmo em cache miss.

#### Scenario: cache miss não bloqueia a resposta

- **WHEN** um anexo sem cache é solicitado
- **THEN** a resposta é devolvida imediatamente, sem aguardar a apuração
- **AND** a apuração ocorre no worker

#### Scenario: redeploy da API não interrompe job

- **GIVEN** um job em execução no worker
- **WHEN** a API é reiniciada
- **THEN** o job continua e grava seu resultado
- **AND** o cliente recupera o resultado ao voltar a consultar

### Requirement: Serviço de apuração chamável por rota, worker e CLI

O serviço que apura um anexo SHALL ser síncrono, sem estado e independente de framework — a mesma
chamada SHALL servir à rota, ao worker e a uma execução por linha de comando. Ele NÃO DEVE receber
sessão de banco, dependência de framework nem cliente HTTP construído por quem chama.

#### Scenario: mesma apuração por caminhos diferentes

- **GIVEN** o mesmo ente, exercício e anexo
- **WHEN** a apuração é executada pelo worker e por linha de comando
- **THEN** os dois resultados são iguais célula a célula
- **AND** nenhum dos dois exige que o outro esteja disponível

### Requirement: Regra vigente é resolvida pelo exercício apurado

A apuração SHALL obter a regra pela vigência correspondente ao **exercício apurado**, resolvida como
a maior vigência menor ou igual à competência pedida. O exercício SHALL ser parâmetro explícito da
carga de regras; NÃO DEVE ser constante implícita nem depender de existir uma única vigência
publicada.

#### Scenario: exercício é parâmetro da carga de regras

- **WHEN** um anexo é apurado para um exercício
- **THEN** a regra usada é a vigente para aquele exercício
- **AND** a apuração não presume que exista apenas uma edição

#### Scenario: exercício sem regra vigente

- **WHEN** o exercício apurado não é coberto por nenhuma vigência declarada
- **THEN** a apuração falha nomeando o exercício e as vigências disponíveis
- **AND** nenhuma regra é aplicada por aproximação

### Requirement: Mapeamento vigente é publicado sem sobrescrever o anterior

O mapeamento aplicado na apuração SHALL ser lido de um repositório de vigências em que publicar uma
correção **acrescenta** uma vigência nova. Vigência publicada NÃO DEVE ser alterada nem removida.
Cada vigência SHALL registrar sua origem — semente versionada ou publicação administrativa — e, no
segundo caso, quem a publicou. A transcrição normativa versionada no repositório SHALL ser a semente
desse repositório de vigências.

#### Scenario: correção publica nova vigência

- **GIVEN** uma vigência já publicada e usada em apurações
- **WHEN** uma correção do mapeamento é publicada
- **THEN** passa a existir uma vigência nova
- **AND** a anterior permanece legível, com sua data e origem

#### Scenario: alteração destrutiva é recusada

- **WHEN** uma publicação tenta alterar ou remover vigência existente
- **THEN** a operação é recusada

#### Scenario: origem e autoria registradas

- **WHEN** uma vigência é publicada por via administrativa
- **THEN** ficam registrados a origem administrativa e quem publicou

#### Scenario: semente a partir da transcrição normativa

- **GIVEN** um repositório de vigências vazio
- **WHEN** a semente é aplicada a partir da transcrição versionada
- **THEN** existe vigência utilizável, marcada com origem de semente
- **AND** a apuração passa a ler dali, não do arquivo

#### Scenario: um repositório para todos os anexos

- **WHEN** um anexo novo passa a ter mapeamento vigente
- **THEN** ele usa o mesmo repositório de vigências, discriminado pelo anexo
- **AND** nenhuma estrutura de vigência por anexo é criada

#### Scenario: publicar mapeamento de um anexo não afeta outro

- **GIVEN** cache válido de um anexo
- **WHEN** uma vigência de outro anexo é publicada
- **THEN** o cache do primeiro permanece válido

### Requirement: Procedência do valor apurado

Todo resultado SHALL informar a procedência do que apurou: as regras aplicadas, a edição do
documento normativo e a versão das tabelas de referência da STN. A procedência SHALL ser persistida
junto com o resultado, de modo que uma divergência possa ser explicada sem reapurar.

#### Scenario: divergência é explicável pelo resultado gravado

- **GIVEN** um resultado em cache que diverge do publicado pelo STN
- **WHEN** a procedência do resultado é consultada
- **THEN** ficam determinadas as regras aplicadas, a vigência e a edição normativa usadas, e a
  versão das tabelas de referência
- **AND** nada disso exige reexecutar a apuração

#### Scenario: mudança de tabela de referência é distinguível

- **GIVEN** dois resultados do mesmo anexo e exercício, apurados antes e depois de uma atualização
  das tabelas da STN
- **WHEN** os dois são comparados
- **THEN** a versão de tabela registrada em cada um os distingue

### Requirement: Diagnóstico da apuração acompanha o resultado

O resultado SHALL trazer, além dos valores, o diagnóstico da apuração: células não apuradas com o
motivo de cada uma, resíduos de classificação e a duração. O diagnóstico SHALL ser persistido com o
resultado e SHALL ser legível sem acesso a log.

#### Scenario: célula não apurada é visível ao consumidor

- **GIVEN** uma apuração em que uma célula ficou sem direção de saldo conhecida
- **WHEN** o resultado é lido do cache
- **THEN** a célula aparece como não apurada, com o motivo
- **AND** o consumidor NÃO precisa consultar log para saber disso

#### Scenario: apuração íntegra também declara diagnóstico

- **WHEN** nenhuma célula fica sem apurar e não há resíduo
- **THEN** o diagnóstico é declarado vazio, e não omitido

### Requirement: Núcleo de apuração isolado de infraestrutura

O núcleo de domínio NÃO DEVE importar HTTP, banco de dados, fila, YAML nem biblioteca de
DataFrame. Fontes de dados e tabelas de referência SHALL entrar por interface declarada no domínio
e implementada na borda.

#### Scenario: apuração testável sem infraestrutura

- **WHEN** o núcleo é exercitado com registros literais e uma implementação de teste das interfaces
- **THEN** a apuração ocorre sem Redis, Postgres, rede ou container

#### Scenario: troca de fonte não altera o domínio

- **GIVEN** duas fontes MSC distintas
- **WHEN** a apuração roda com cada uma
- **THEN** nenhum arquivo do domínio precisa mudar

### Requirement: Estado de execução isolado; cache de dados compartilhado

No Redis comum aos pipelines, o **estado de execução** da DCA — fila, jobs, locks e resultados —
SHALL ser isolado por prefixo próprio, e seu worker NÃO DEVE consumir job de outro pipeline. O
**cache de dados da MSC**, ao contrário, SHALL usar o espaço comum: os mesmos ente, exercício,
competência e classe produzem o mesmo dado para qualquer pipeline, e uma leitura já feita NÃO DEVE
ser refeita só porque partiu de outro módulo.

#### Scenario: job não vaza entre pipelines

- **GIVEN** RREO, RGF e DCA no mesmo Redis
- **WHEN** um job da DCA é enfileirado
- **THEN** apenas o worker da DCA o consome
- **AND** as chaves de job, lock e resultado da DCA trazem prefixo próprio

#### Scenario: dado de MSC já em cache é reaproveitado

- **GIVEN** que outro pipeline já leu e cacheou a MSC de um ente, exercício, competência e classe
- **WHEN** a DCA precisa exatamente desse recorte
- **THEN** ela reaproveita o dado cacheado
- **AND** nenhuma nova consulta à fonte é feita

#### Scenario: recortes diferentes não se confundem

- **GIVEN** dados cacheados para classes ou competências distintas
- **WHEN** um recorte é solicitado
- **THEN** o dado devolvido corresponde exatamente ao recorte pedido

### Requirement: Convivência com os demais pipelines no banco compartilhado

A DCA compartilha instância e schema com RREO e RGF. Suas tabelas SHALL ser distinguíveis por
prefixo próprio, e seu histórico de migrations SHALL ser registrado em tabela de versão própria.
Migration da DCA NÃO DEVE criar, alterar ou remover objeto pertencente a outro pipeline.

Migrations concorrentes no schema compartilhado SHALL ser serializadas, inclusive entre projetos
diferentes. A migração SHALL abortar quando detectar que o histórico da DCA foi registrado fora da
sua tabela de versão.

#### Scenario: migração em banco que já tem os irmãos

- **GIVEN** um banco contendo as tabelas de RREO e RGF
- **WHEN** as migrations da DCA são aplicadas
- **THEN** apenas objetos da DCA são criados
- **AND** nenhuma tabela dos outros pipelines é alterada
- **AND** o histórico fica na tabela de versão da DCA, sem tocar na dos irmãos

#### Scenario: histórico registrado na tabela errada

- **GIVEN** que o marcador de versão da DCA foi gravado na tabela de versão genérica
- **WHEN** uma migration é executada
- **THEN** ela aborta explicando qual tabela reflete o histórico real
- **AND** nenhuma revisão é aplicada

#### Scenario: migrations simultâneas de projetos diferentes

- **GIVEN** DCA e outro pipeline subindo ao mesmo tempo, ambos migrando o schema compartilhado
- **WHEN** as duas migrations começam
- **THEN** elas são serializadas, uma esperando a outra
- **AND** nenhuma falha por concorrência

#### Scenario: réplicas subindo juntas

- **GIVEN** duas réplicas do mesmo serviço iniciando simultaneamente com migração no boot
- **WHEN** ambas tentam migrar
- **THEN** apenas uma aplica as revisões e a outra observa o resultado

### Requirement: Conclusão de job é notificada

O fim de um job SHALL ser notificado no canal de operação configurado, informando ente, exercício,
anexo, duração e desfecho. A notificação NÃO DEVE alterar o desfecho do job: falha ao notificar é
registrada em log e o resultado permanece gravado.

#### Scenario: job concluído com sucesso

- **WHEN** um job termina e grava o resultado
- **THEN** a notificação informa ente, exercício, anexo, duração e sucesso

#### Scenario: job com erro também notifica

- **WHEN** um job termina em erro
- **THEN** a notificação informa a falha e o motivo

#### Scenario: canal de notificação indisponível

- **GIVEN** o canal de notificação fora do ar
- **WHEN** um job termina
- **THEN** o resultado permanece gravado no cache
- **AND** a falha de notificação é registrada em log, sem alterar o estado do job

#### Scenario: notificação não configurada

- **WHEN** nenhum canal está configurado
- **THEN** o job roda normalmente e nada é notificado

### Requirement: Autorização por unidade em toda rota de anexo

Toda rota de anexo SHALL exigir JWT válido e a unidade (`cod_ibge`) do requisitante, e SHALL
recusar acesso a ente diferente do autorizado. Credencial de fonte de dados enviada por browser
SHALL ser rejeitada. Token de fonte guardado para uso do job SHALL ser cifrado e expirar com o job.

#### Scenario: token ausente ou inválido

- **WHEN** a requisição chega sem JWT válido
- **THEN** a resposta é `401`
- **AND** nenhum job é criado

#### Scenario: ente diferente do autorizado

- **WHEN** a unidade do requisitante não corresponde ao ente solicitado
- **THEN** a resposta é `403`
- **AND** nenhum dado do ente é devolvido

#### Scenario: credencial de fonte vinda do browser

- **WHEN** a requisição traz cabeçalho de credencial de fonte de dados
- **THEN** ela é rejeitada
- **AND** a credencial NÃO é usada para consultar a fonte

#### Scenario: token de fonte no armazenamento do job

- **WHEN** um job precisa da credencial da fonte
- **THEN** ela é armazenada cifrada e expira junto com o job
- **AND** NÃO é legível por quem apenas leia o armazenamento

### Requirement: Estado do job é serializado sem execução de código

Estado e resultado de job SHALL ser serializados em formato de dados. Desserialização que execute
código arbitrário NÃO DEVE ser usada.

#### Scenario: payload de job não executa código

- **WHEN** o resultado de um job é gravado e lido de volta
- **THEN** a serialização é de dados, sem execução de código na leitura

### Requirement: Falha de infraestrutura é reportada, não mascarada

Indisponibilidade de Redis, Postgres ou fonte MSC SHALL ser reportada com a causa. A plataforma NÃO
DEVE gravar cache `ok` com resultado incompleto, nem devolver `200` quando a apuração não ocorreu.

#### Scenario: fonte MSC indisponível

- **WHEN** a fonte não responde durante a apuração
- **THEN** o job termina em `error` com a causa
- **AND** o cache fica `erro`, nunca `ok`

#### Scenario: verificação de dependências no startup do worker

- **WHEN** o worker inicia
- **THEN** ele verifica Redis e Postgres e registra o resultado
- **AND** falha de dependência é visível em log, não silenciosa
