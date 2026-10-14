## MODIFIED Requirements

### Requirement: Percurso respeita a origem da coluna anterior do BP

`POST /batch-jobs` SHALL aceitar `origem_exercicio_anterior` (`publicado_siconfi` |
`msce_exercicio_anterior` | `processado_exercicio_anterior`), aplicado **só** ao Balanço
Patrimonial; o BF e o BO NÃO DEVEM recebê-lo. Omitido, o BP reaplica o manual salvo do consolidado
ou vale `msce_exercicio_anterior`, como no BF (PO 2026-10-14). `processado_exercicio_anterior` sem o
BP de N−1 `ok` SHALL responder `409` "processe {N−1} antes", sem job. A decisão de cache do percurso
(rota) e a apuração e gravação do BP (worker) SHALL usar a mesma identidade de pedido, com essa
origem. Origem inválida SHALL responder `422` sem enfileirar job. BO e BF NÃO DEVEM mudar de
identidade nem de resultado.

#### Scenario: percurso grava o BP pela origem pedida

- **GIVEN** `POST /batch-jobs` com `origem_exercicio_anterior=msce_exercicio_anterior`
- **WHEN** o percurso conclui
- **THEN** o BP gravado declara `origem_exercicio_anterior: msce_exercicio_anterior`
- **AND** a leitura do BP com a mesma origem responde `desatualizado: false`, sem enfileirar job

#### Scenario: percurso sem origem mantém o padrão

- **WHEN** `POST /batch-jobs` chega sem `origem_exercicio_anterior`
- **THEN** o BP reaplica o manual salvo do consolidado ou, sem ele, é apurado pela MSC

#### Scenario: cache do BP em outra origem entra a apurar

- **GIVEN** o BP em cache válido pela origem publicado
- **WHEN** o percurso sem `forcar` é pedido com `msce_exercicio_anterior`
- **THEN** o BP aparece no percurso como `a_apurar`
- **AND** BO e BF com cache válido continuam `em_cache`

#### Scenario: origem inválida no percurso

- **WHEN** `POST /batch-jobs` chega com `origem_exercicio_anterior=manual`
- **THEN** a resposta é `422`
- **AND** nenhum job é enfileirado

#### Scenario: processado do BP no percurso sem N−1

- **GIVEN** o BP de 2024 sem cache `ok`
- **WHEN** chega `POST /batch-jobs` com `origem_exercicio_anterior=processado_exercicio_anterior`
- **THEN** a resposta é `409` "processe 2024 antes", sem job

#### Scenario: a origem do percurso não vaza para o BF

- **GIVEN** `POST /batch-jobs` com `origem_exercicio_anterior=processado_exercicio_anterior`
- **WHEN** o percurso apura o BF
- **THEN** o BF usa a sua própria origem (gravada ou padrão); a da query vale só para o BP

## ADDED Requirements

### Requirement: Percurso apura pela fonte do pedido

`POST /batch-jobs` SHALL aceitar `use_siconfi` como a leitura e o reprocessamento de cada anexo
(`true` = SICONFI; `false` = PublicSoft/SIAFIC, com o `token_ps` resolvido no hub e guardado cifrado
para o job, nunca no payload da fila). A identidade de pedido de cada anexo do percurso SHALL levar
essa fonte. Sem isso o percurso apurava sempre pela fonte padrão do servidor e a leitura pela fonte
escolhida via o resultado como desatualizado (Cuitegi, 2026-10-14).

#### Scenario: percurso usa a fonte escolhida no front

- **GIVEN** o dialog da DCA com a fonte SIAFIC
- **WHEN** o usuário clica em Processar ou Reprocessar
- **THEN** `POST /batch-jobs` leva `use_siconfi=false`, o job apura pela PublicSoft, com recortes por UG
- **AND** a leitura de cada anexo pela SIAFIC responde sem `desatualizado`
