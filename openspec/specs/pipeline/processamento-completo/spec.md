# pipeline/processamento-completo

> Comportamento acordado e em vigor. Consolidado da change `pipeline-completo-dca`,
> arquivada em 2026-10-01.
> Alterações entram por nova change, nunca por edição direta deste arquivo.

## Purpose

Apurar **todos os anexos implementados** de um ente e exercício com uma chamada e um único
identificador de acompanhamento, sem que o consumidor precise conhecer a lista de anexos, a ordem
de execução ou o que fazer quando um deles falha.

## Requirements

### Requirement: Uma chamada apura todos os anexos implementados

A plataforma SHALL expor **uma** rota que enfileira um job para apurar todos os anexos com serviço
declarado no registry, na ordem canônica, para um ente e exercício, com um sinalizador que decide
entre respeitar o cache válido e reapurar tudo. A resposta SHALL ser `202` com um identificador
único de percurso, a lista dos anexos que entraram nele e as URLs de polling e stream, no mesmo
contrato de batch job que os pipelines irmãos publicam. A
rota NÃO DEVE apurar no processo da API, nem devolver o resultado dos anexos — quem quer o
demonstrativo lê `GET /dca/{anexo}` depois, e quem quer o estado lê `GET /dca/resumo`.

Anexo sem serviço declarado SHALL ser reportado como `nao_implementado` e NÃO DEVE gerar entrada de
cache, erro ou job.

#### Scenario: um job para todos os anexos

- **GIVEN** um ente e exercício autorizados, com `BO` e `BF` implementados no registry
- **WHEN** o processamento completo é solicitado
- **THEN** a resposta é `202` com um único identificador de percurso, `poll_url` e `sse_url`
- **AND** a lista devolvida traz `BO` e `BF` como anexos do percurso
- **AND** os anexos sem serviço aparecem como `nao_implementado`

#### Scenario: nenhum anexo implementado

- **GIVEN** um registry sem nenhum anexo com serviço declarado
- **WHEN** o processamento completo é solicitado
- **THEN** a resposta é `422` com a lista vazia declarada
- **AND** nenhum job é enfileirado

#### Scenario: exercício ausente ou inválido

- **WHEN** o processamento completo é solicitado sem exercício, ou com exercício fora da faixa
- **THEN** a resposta é `422`, sem criar job e sem tocar o cache

### Requirement: Cache válido é respeitado; reprocessar ignora

No processamento completo, anexo com resultado em cache **servível** — `ok`, com as versões de API
e de regras conferindo — NÃO DEVE ser reapurado. O reprocessamento completo SHALL ignorar o cache
válido de **todos** os anexos do percurso, registrando o solicitante, e o resultado anterior de
cada anexo SHALL permanecer legível até o novo substituí-lo.

#### Scenario: anexo já apurado não é reapurado

- **GIVEN** `BO` em cache válido e `BF` ausente
- **WHEN** o processamento completo é solicitado
- **THEN** apenas o `BF` é apurado
- **AND** o `BO` é reportado como `em_cache`, com o `calculado_em` que já tinha

#### Scenario: reprocessamento completo reapura tudo

- **GIVEN** `BO` e `BF` em cache válido
- **WHEN** o reprocessamento completo é solicitado
- **THEN** os dois são reapurados
- **AND** o solicitante fica registrado em cada anexo
- **AND** o resultado anterior permanece legível enquanto a reapuração corre

### Requirement: Falha de um anexo não interrompe o percurso

Falha na apuração de um anexo SHALL ser registrada naquele anexo — cache `erro` com o detalhe — e
o percurso SHALL continuar nos demais. O job completo SHALL terminar em estado **terminal conhecido do
consumidor**: `done` quando o percurso chegou ao fim, com a contagem de falhas e o desfecho por
anexo no corpo, e `error` apenas quando nenhum anexo concluiu. Estado terminal fora do conjunto que
o consumidor reconhece (`done`, `error`, `cancelled`, `interrupted`) NÃO DEVE ser publicado — quem
acompanha o percurso ficaria esperando para sempre um job que já acabou. O desfecho SHALL nomear
cada anexo e o que aconteceu com ele. Em nenhuma hipótese um anexo NÃO DEVE
ficar preso em `processando` por falha de outro.

#### Scenario: um anexo falha e os demais concluem

- **GIVEN** um percurso com `BO` e `BF`, e a apuração do `BF` falhando
- **WHEN** o job completo executa
- **THEN** o `BO` fica `ok` e o `BF` fica `erro` com o detalhe da falha
- **AND** o job termina `done`, com contagem de falhas igual a 1 e o `BF` nomeado no desfecho
- **AND** nenhum lock permanece retido

#### Scenario: todos os anexos falham

- **GIVEN** um percurso em que toda apuração falha
- **WHEN** o job completo executa
- **THEN** o job termina `error`, com o detalhe por anexo
- **AND** nenhum anexo fica com cache `ok`

### Requirement: Anexo com job em voo não é apurado duas vezes

Quando já existe job em execução para a identidade de um anexo do percurso, o processamento
completo NÃO DEVE criar um segundo job para ele: SHALL reportá-lo como `already_queued` com o
`job_id` em voo e seguir para o próximo. O lock por identidade continua sendo o mecanismo, o mesmo
das rotas por anexo.

#### Scenario: anexo já em andamento é pulado

- **GIVEN** um job individual do `BF` em execução
- **WHEN** o processamento completo é solicitado para o mesmo ente e exercício
- **THEN** o `BF` é reportado como `already_queued`, com o `job_id` do job em voo
- **AND** o `BO` é apurado normalmente
- **AND** nenhuma segunda apuração do `BF` é enfileirada

### Requirement: Leitura da MSC é paga uma vez por percurso

Dentro de um percurso completo, o mesmo recorte da MSC — ente, exercício, competência, classe,
matriz e tipo de saldo — SHALL ser consultado na fonte **uma única vez**, ainda que mais de um
anexo o utilize. A memória dessa leitura SHALL morrer com o job, como já vale para o job por anexo:
o ente retifica declaração já publicada, e nada do que foi lido pode ser servido a um job seguinte.

#### Scenario: anexos que leem a mesma classe consultam a fonte uma vez

- **GIVEN** um percurso com `BO` e `BF`, que leem as classes 5 e 6 da mesma matriz
- **WHEN** o job completo executa
- **THEN** a fonte recebe 18 consultas, contra 20 quando os dois anexos rodam em jobs separados
- **AND** nenhuma leitura é reaproveitada por um job posterior

### Requirement: Progresso do percurso é acompanhável

O estado do job completo SHALL trazer, além do status, o progresso (`concluidos` de `total`) e o
desfecho por anexo — anexo, status e detalhe de erro quando houver. O stream SHALL emitir um evento
a cada anexo concluído e um evento final de desfecho, no mesmo vocabulário que o front já consome
para o job por anexo.

No canal de operação, o percurso SHALL notificar como o pipeline do RGF: **uma mensagem por anexo**,
quando ele termina (`Concluído ✅`, `Falhou ❌`) ou quando vem do cache (`Cache ✅`, cinza, `Dados já
em cache`), e **um resumo** ao fim. O resumo SHALL ter o título `✅ <Cidade - UF>  <exercício>
[Anual] — <e-mail>` (`⚠️` com falha), o corpo `<n> anexo(s) concluído(s) com sucesso.` ou `Fila
concluída com <n> falha(s).`, e os campos `Fonte MSC`, `Tempo total`, `Detalhamento` (uma linha por
anexo implementado, na ordem do registry) e, havendo falha, `Erros`. A cor SHALL ser roxa sem falha e
laranja com falha. Anexo pulado por já estar em voo NÃO DEVE gerar mensagem própria.

#### Scenario: progresso é legível durante a execução

- **GIVEN** um percurso de dois anexos com o primeiro já concluído
- **WHEN** o estado do job é consultado
- **THEN** o progresso indica 1 de 2
- **AND** o desfecho do anexo concluído já aparece, com seu status

#### Scenario: conclusão do percurso é notificada uma vez

- **GIVEN** um percurso concluído, com ou sem erros
- **WHEN** o canal de operação está configurado
- **THEN** sai **um** resumo, com uma linha de detalhamento por anexo e a duração total
- **AND** nenhum campo do resumo sai como `None`

#### Scenario: cada anexo do percurso também notifica

- **GIVEN** um percurso de BO, BF e BP, com o BF em cache
- **WHEN** o percurso termina
- **THEN** saem `DCA BO — Concluído ✅`, `DCA BF — Cache ✅` e `DCA BP — Concluído ✅`, nesta ordem
- **AND** depois deles, o resumo, com `BF — cache ✅` no detalhamento

#### Scenario: percurso com falha

- **GIVEN** um percurso em que o BF falhou com `fonte fora do ar`
- **WHEN** o resumo é enviado
- **THEN** o título começa com `⚠️`, o corpo é `Fila concluída com 1 falha(s).` e a cor é laranja
- **AND** o campo `Erros` traz `**BF:** fonte fora do ar`

