# pipeline/plataforma

> Comportamento acordado e em vigor. Consolidado das changes `plataforma-pipeline-dca`,
> `2026-09-18-bf-no-pipeline`, `vigencia-por-anexo` e `bf-anterior-manual-persistido`,
> arquivado em 2026-10-01, e `pipeline-visualizar-sem-reprocessar`, arquivada em 2026-10-07.
> O mapa manual do BF passou a ser por unidade, e o consolidado deixou de ter origem própria,
> por `pipeline-consolidado-anterior-soma-unidades`.
> Alterações entram por nova change, nunca por edição direta deste arquivo.

## Purpose

Garantir que todo anexo da DCA seja servido pelo **mesmo ciclo** — requisição → cache → job →
worker → cache → leitura — já em produção no `regras-rreo-api` e no `regras-rgf-api`, com um único
mecanismo de cache, lock e registry, e com o núcleo de apuração isolado de HTTP, banco e fila.

Esta capability define o **fluxo**, nunca a regra de um anexo: o que cada demonstrativo calcula
pertence às capabilities de `dca/`. Um anexo entra no pipeline registrando-se; não reimplementando
o ciclo.

## Requirements

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
- **THEN** ela recebe o `job_id` existente, com `status: already_queued`
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

### Requirement: Estado de execução isolado; dado da MSC não persistido

No Redis comum aos pipelines, o **estado de execução** da DCA — fila, jobs, locks e resultados —
SHALL ser isolado por prefixo próprio, e seu worker NÃO DEVE consumir job de outro pipeline. O
**dado da MSC** NÃO DEVE ser persistido entre execuções: o ente pode retificar declaração já
publicada, de qualquer exercício, e um recorte guardado serviria o número anterior à retificação
sem que nada acusasse a diferença. A leitura SHALL valer apenas para a execução que a fez — dentro
dela, o mesmo recorte NÃO DEVE ser consultado duas vezes.

#### Scenario: job não vaza entre pipelines

- **GIVEN** RREO, RGF e DCA no mesmo Redis
- **WHEN** um job da DCA é enfileirado
- **THEN** apenas o worker da DCA o consome
- **AND** as chaves de job, lock e resultado da DCA trazem prefixo próprio

#### Scenario: dado de MSC não é reaproveitado entre execuções

- **GIVEN** um recorte de MSC lido durante a apuração de um anexo
- **WHEN** o mesmo recorte é pedido de novo na mesma execução
- **THEN** a fonte não é consultada outra vez
- **AND** numa execução seguinte a fonte é consultada de novo, porque a declaração pode ter sido
  retificada

#### Scenario: recortes diferentes não se confundem

- **GIVEN** recortes lidos para classes ou competências distintas
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

O fim de um job SHALL ser notificado no canal de operação configurado, no mesmo padrão do RREO e do
RGF: título `DCA <anexo> — Concluído ✅` (verde) ou `DCA <anexo> — Falhou ❌` (vermelho), e corpo com
o ente, o exercício e a duração. O ente SHALL aparecer como `Cidade - UF`, lido de
`public.unidade_gestora` pelo `cod_ibge`. Ente ausente da tabela, ou consulta que falhe, SHALL cair
no código IBGE sem impedir a notificação. A duração SHALL seguir o formato dos irmãos: segundos com
uma casa abaixo de um minuto (`18.7s`) e minutos com segundos inteiros acima (`1m 13s`).

Nenhum campo da mensagem SHALL sair como `None`. A notificação NÃO DEVE alterar o desfecho do job:
falha ao notificar é registrada em log e o resultado permanece gravado.

#### Scenario: job concluído com sucesso

- **GIVEN** o BF de Cuitegi (`2505204`), exercício 2025, apurado em 18.700 ms
- **AND** `unidade_gestora` com `cod_ibge = 2505204`, `cidade = Cuitegi`, `uf = PB`
- **WHEN** o job termina e grava o resultado
- **THEN** o título é `DCA BF — Concluído ✅` e a cor é verde
- **AND** o corpo é `**Cuitegi - PB** | 2025 | Tempo: 18.7s`

#### Scenario: job com erro também notifica

- **WHEN** um job termina em erro
- **THEN** o título é `DCA <anexo> — Falhou ❌` e a cor é vermelha
- **AND** o corpo traz o ente, o exercício e o motivo em bloco de código, truncado em 900 caracteres

#### Scenario: ente ausente da tabela de unidades

- **GIVEN** um `cod_ibge` que não está em `unidade_gestora`
- **WHEN** a notificação é montada
- **THEN** o ente aparece como o código IBGE

#### Scenario: banco indisponível ao resolver o ente

- **GIVEN** o banco fora do ar no momento da notificação
- **WHEN** um job termina
- **THEN** a notificação sai com o código IBGE
- **AND** o desfecho do job não muda

#### Scenario: duração no padrão dos irmãos

- **WHEN** a duração é 850 ms, 18.700 ms, 73.000 ms e 128.000 ms
- **THEN** ela é exibida como `0.9s`, `18.7s`, `1m 13s` e `2m 8s`

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

### Requirement: O envelope de cache de dados preserva o par de leitura

O envelope que envolve a fonte no cache de dados SHALL repassar `matriz` e `tipo_saldo` à fonte,
tal como recebidos. Ele NÃO DEVE omiti-los nem assumir valor padrão.

Omitir é falha **silenciosa**: o demonstrativo que lê três origens receberia três vezes a mesma, e
as linhas afetadas sairiam com valores plausíveis e errados, sem exceção, sem log e sem célula não
apurada. No BF, `L25`, `L26` e `L29`–`L32` são exatamente essas linhas.

#### Scenario: as três origens do BF chegam à fonte

- **GIVEN** a apuração do BF pela plataforma, com cache de dados ativo
- **WHEN** o serviço pede a matriz de encerramento pela abertura, pelo encerramento e a do
  exercício anterior
- **THEN** a fonte recebe as três chamadas com o `tipo_saldo` e o exercício de cada uma
- **AND** cada origem ocupa uma entrada de cache própria

#### Scenario: o par de leitura não é inventado pelo envelope

- **WHEN** o chamador não informa `matriz` nem `tipo_saldo`
- **THEN** o envelope repassa a ausência, e é a fonte que aplica o padrão dela
- **AND** o envelope NÃO escolhe matriz nem tipo de saldo

### Requirement: Ordem de apresentação declarada pelo demonstrativo

A ordem em que as linhas são publicadas SHALL vir do demonstrativo apurado, não de constante do
serializador. Quadro e grupo desconhecidos SHALL ir para o fim, sem quebrar a serialização.

O serializador NÃO DEVE conhecer o vocabulário de cada norma: `RECEITAS`/`DESPESAS` é do IPC 07 e
`INGRESSOS`/`DISPENDIOS` é do IPC 06; codificar os dois no mesmo módulo faz cada anexo novo
acrescentar vocabulário alheio a ele.

#### Scenario: o BF sai na ordem do IPC 06

- **WHEN** o resultado do BF é serializado
- **THEN** as linhas de `INGRESSOS` vêm antes das de `DISPENDIOS`
- **AND** dentro de cada grupo a sequência é a `ordem` declarada na base canônica
- **AND** o quadro principal vem antes do quadro anexo

#### Scenario: o BO mantém a ordem que já publicava

- **WHEN** o resultado do BO é serializado
- **THEN** a ordem das 69 linhas é idêntica à anterior a esta change

### Requirement: A origem da coluna do exercício anterior integra a identidade do resultado

A identidade do resultado cacheado SHALL incluir a **origem da coluna do exercício anterior por
unidade** (`anterior_por_recorte`) e, quando ela for o preenchimento manual, a identidade do
conjunto informado. Dois pedidos que diferem nisso SHALL ser resultados distintos e NÃO DEVEM
compartilhar entrada de cache. O consolidado não contribui origem própria para a identidade
(`pipeline-consolidado-anterior-soma-unidades`).

Sem isso, um resultado com a coluna preenchida à mão seria servido a quem pediu a coluna apurada da
matriz — e a diferença não apareceria em `versao_api` nem em `versao_regras`, que não mudam.

#### Scenario: origens diferentes não se misturam no cache

- **GIVEN** um resultado já cacheado com a coluna anterior apurada da MSCE
- **WHEN** o mesmo ente e exercício é pedido com a coluna anterior informada manualmente
- **THEN** o cache não é servido
- **AND** o resultado produzido declara a origem manual na procedência

#### Scenario: dois preenchimentos manuais diferentes são resultados diferentes

- **GIVEN** dois conjuntos de valores informados para o mesmo ente e exercício
- **WHEN** os dois são apurados
- **THEN** ocupam entradas de cache distintas

### Requirement: Procedência e diagnóstico específicos do demonstrativo são publicados

A serialização SHALL publicar os campos de procedência e diagnóstico que o demonstrativo produz,
sem lista fixa no serializador. No BF isso inclui `origens_por_linha`,
`origem_exercicio_anterior`, `policies_nao_aplicadas` e `sem_dados_exercicio_anterior`.

Sem eles o cliente recebe célula vazia sem saber se é zero, se é linha sem mapeamento no IPC 06 ou
se é exercício anterior indisponível — três coisas diferentes com a mesma aparência.

#### Scenario: o cliente sabe por que a célula está vazia

- **WHEN** o BF é servido pela rota
- **THEN** `diagnostico.nao_apuradas` nomeia linha, coluna e motivo
- **AND** `procedencia.origens_por_linha` diz de qual saldo cada linha veio
- **AND** `diagnostico.policies_nao_aplicadas` cita o item 38 e o motivo

#### Scenario: a rota e o CLI publicam o mesmo JSON

- **GIVEN** o mesmo ente, exercício e competência
- **WHEN** o BF é obtido pela rota e pelo `python -m app.cli.bf --json`
- **THEN** os dois JSON são iguais
- **AND** a serialização é a mesma função nos dois caminhos

### Requirement: BF no conjunto fechado de anexos

`BF` SHALL constar do registry com serviço implementado, e SHALL ser aceito pela rota nas grafias
canonizadas (`bf`, `B-F`, `B_F`). O resumo SHALL deixar de reportá-lo como anexo sem serviço.

#### Scenario: a rota do BF responde

- **WHEN** `GET /anexos/BF?ente=2611606&exercicio=2025` é chamado
- **THEN** o demonstrativo é servido, com as 66 linhas do quadro principal nas duas colunas
- **AND** grafias equivalentes apontam a mesma entrada de cache

### Requirement: A semente de vigência cobre todos os anexos implementados

A semente de boot SHALL publicar a vigência de **cada anexo com serviço implementado** no registry,
usando a base canônica declarada por ele e o ano da edição correspondente. NÃO DEVE publicar apenas
o Balanço Orçamentário.

Anexo sem serviço SHALL ser ignorado, sem falhar o boot. Base canônica sem edição que cubra o ano
SHALL ser registrada em aviso, e os demais anexos SHALL ser semeados mesmo assim — um anexo sem
transcrição não pode impedir a publicação dos outros.

A semente SHALL continuar idempotente: vigência já publicada é mantida, e a recusa da chave
primária é tratada como "já semeado".

#### Scenario: BO e BF semeados no boot

- **WHEN** a semente roda num banco vazio
- **THEN** a vigência do BO é publicada com a edição do IPC 07
- **AND** a vigência do BF é publicada com a edição do IPC 06
- **AND** cada uma no ano da sua própria edição

#### Scenario: apuração do BF deixa de cair no YAML

- **GIVEN** a semente aplicada
- **WHEN** o worker apura o BF
- **THEN** o mapa vem do banco
- **AND** nenhum aviso de vigência ausente é registrado

#### Scenario: segundo boot não reescreve

- **GIVEN** a semente já aplicada
- **WHEN** o boot roda de novo
- **THEN** nada é publicado
- **AND** o boot conclui sem erro

### Requirement: A completação de apresentação usa a transcrição do próprio anexo

Ao carregar a vigência do banco, a completação de nível, ordem e colunas ausentes SHALL usar a
transcrição **do anexo carregado**, não a do Balanço Orçamentário.

Completar o BF com a transcrição do BO não casa `rule_id` nenhum (`bf.*` contra `bo.*`) e devolve o
mapa inalterado — sem erro e sem efeito, que é a forma mais cara de não fazer nada.

#### Scenario: BF completado pela transcrição do IPC 06

- **GIVEN** uma vigência do BF publicada sem `nivel` em alguma linha
- **WHEN** o mapa é carregado do banco
- **THEN** o nível vem da transcrição do IPC 06
- **AND** o `documento` da vigência é o do próprio anexo

### Requirement: Mapa manual por unidade não viaja na query; consolidado não aceita mapa próprio

A gravação do mapa manual do exercício anterior SHALL ser feita por unidade (`ug:`/`po:`), dentro
de `anterior_por_recorte`, só no corpo JSON do `POST /dca/{BF|BP}/reprocessar`.
`origem_exercicio_anterior` e `valores_anteriores` na query, ou no topo do corpo, SHALL ser
recusados antes de enfileirar job ou alterar a linha de cache
(`pipeline-consolidado-anterior-soma-unidades`): o consolidado não tem mapa próprio.

`GET /dca/{anexo}`, `POST /dca/{anexo}/reprocessar` sem corpo e `POST /batch-jobs` SHALL reaplicar
a escolha já gravada por unidade quando o pedido não trouxer escolha explícita para ela. NÃO DEVEM
exigir que o cliente reenvie o mapa.

A autorização SHALL ser a mesma das demais rotas de anexo. O mapa NÃO DEVE aparecer em log.

#### Scenario: mapa no corpo é gravado

- **GIVEN** uma unidade `ug:` do BF com manual válido em `anterior_por_recorte`
- **WHEN** `POST /dca/BF/reprocessar` é enviado, para um ente autorizado
- **THEN** a resposta é `202`
- **AND** ao fim do job a procedência do recorte guarda o mapa

#### Scenario: mapa na query é recusado

- **WHEN** `GET /dca/BF` ou `POST /dca/BF/reprocessar` traz `origem_exercicio_anterior` ou
  `valores_anteriores` na query
- **THEN** a resposta é `400`
- **AND** nenhum job é enfileirado
- **AND** a linha de cache não muda

#### Scenario: percurso completo reaplica o mapa

- **GIVEN** uma unidade do BF com mapa manual na procedência do recorte
- **WHEN** `POST /batch-jobs` roda sem escolha explícita para ela
- **THEN** o desfecho do `BF` conserva a coluna anterior dessa unidade, do mapa salvo

#### Scenario: ente não autorizado

- **WHEN** o `POST` do mapa pede um ente fora da unidade do token
- **THEN** a resposta é `403`
- **AND** a linha de cache não muda

### Requirement: Requisição recebida é notificada

Todo pedido que enfileira job SHALL ser notificado no canal de operação ao ser aceito, em azul, com
o título `DCA <anexo> — Requisição Recebida (<modo>) [Anual] — <e-mail>` para um anexo e
`DCA — Requisição Recebida (<modo>) [Anual] — <e-mail>` para o percurso completo. `<modo>` é
`Processar` ou `Reprocessar`. O corpo SHALL trazer o ente (`Cidade - UF`), o exercício, a fonte MSC
(`SICONFI` ou `MSC-SIAFIC`) e a fila (`Fila => BO, BF, BP`). Pedido respondido do cache, sem job, NÃO
DEVE notificar. Falha ao notificar NÃO DEVE mudar a resposta do pedido.

#### Scenario: anexo enfileirado

- **GIVEN** `POST /dca/BP/reprocessar` de `jackson@x` para Cuitegi 2025, fonte SICONFI
- **WHEN** o job é enfileirado
- **THEN** sai `DCA BP — Requisição Recebida (Reprocessar) [Anual] — jackson@x`, em azul
- **AND** o corpo traz `Cuitegi - PB`, `2025`, `Fonte MSC: SICONFI` e `Fila => BP`

#### Scenario: percurso enfileirado

- **WHEN** `POST /batch-jobs` enfileira BO, BF e BP
- **THEN** sai `DCA — Requisição Recebida (Processar) [Anual] — <e-mail>`
- **AND** o corpo traz `Fila => BO, BF, BP`, só com os anexos que serão apurados

#### Scenario: leitura servida do cache não notifica

- **WHEN** `GET /dca/{anexo}` responde `200` do cache
- **THEN** nenhuma mensagem de requisição recebida é enviada

<!-- Mesclado de `dvp-no-pipeline`, arquivada em 2026-10-23. -->

### Requirement: Ordem de apresentação da DVP vem do documento

O serializador SHALL ordenar as linhas da DVP pelos quadros e grupos declarados para o documento
`IPC05`: quadro `QUADRO_PRINCIPAL` e grupos `VPA`, `VPD` e `RESULTADO`, nessa ordem. A ordem NÃO
DEVE depender de a numeração das linhas ser global e crescente.

Hoje as 19 linhas têm `ordem` de 1 a 19 sem repetição, e a saída sairia na ordem certa mesmo sem
declaração — por coincidência. Linha nova com `ordem` relativa ao grupo sairia fora de lugar, sem
erro e sem célula não apurada.

#### Scenario: VPA antes de VPD, resultado por último

- **WHEN** a DVP apurada é serializada
- **THEN** `L1` é a primeira linha e o grupo dela é `VPA`
- **AND** toda linha de `VPA` vem antes de toda linha de `VPD`
- **AND** `L19`, do grupo `RESULTADO`, é a última

#### Scenario: linha nova com ordem relativa ao grupo

- **GIVEN** uma linha de `VPD` com `ordem` 1, relativa ao grupo
- **WHEN** o demonstrativo é serializado
- **THEN** ela aparece dentro de `VPD`, e não antes de `L1`

### Requirement: `I-HI` é anexo implementado

O registry SHALL declarar o anexo `I-HI` com o serviço de apuração da DVP e a base canônica `dvp`.
O carregador de regras SHALL receber essa base — nunca a do BO.

Carregar o mapa do BO para a DVP não levanta exceção: devolve 51 linhas do IPC 07 e um
demonstrativo plausível e errado. Foi o defeito corrigido em `bf-no-pipeline` (2.6a).

#### Scenario: resumo deixa de reportar anexo sem serviço

- **WHEN** `GET /dca/resumo` é lido para um ente e exercício
- **THEN** a entrada de `I-HI` traz `implementado: true`

#### Scenario: percurso completo inclui a DVP

- **WHEN** o percurso completo é montado para um ente e exercício sem cache
- **THEN** os anexos a apurar são `BO`, `BF`, `BP` e `I-HI`
- **AND** a notificação lista os quatro

#### Scenario: grafia não canônica

- **WHEN** o anexo chega como `i-hi` ou `I_HI`
- **THEN** é canonizado para `I-HI`, sem criar entrada de cache separada

### Requirement: Uma serialização só

O JSON servido pela rota da DVP SHALL ser idêntico ao produzido pelo CLI da DVP para o mesmo ente,
exercício e fonte.

#### Scenario: rota e CLI não divergem

- **WHEN** o mesmo ente e exercício são apurados pela rota e por `python -m app.cli.dvp --json`
- **THEN** os dois JSON são iguais
