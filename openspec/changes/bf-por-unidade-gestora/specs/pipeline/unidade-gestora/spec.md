# pipeline/unidade-gestora — Delta spec

Delta sobre a capability definida em `pipeline-dca-por-unidade-gestora`. Mesclar depois dela.

## ADDED Requirements

### Requirement: Aviso de recorte por PO em ente com SIAFIC

Quando a leitura de BO, BP ou BF for pela fonte SICONFI (`use_siconfi=true`), o hub resolver o
`token_ps` do ente (ente com SIAFIC) e o resultado servido tiver recortes `po:`, a resposta SHALL
trazer `avisoRecorte` = "Recorte por poder/órgão: o
SICONFI não informa a unidade gestora. Para emitir por unidade gestora, processe com SIAFIC.". Os
recortes `po:` SHALL ser emitidos normalmente.

`avisoRecorte` NÃO DEVE aparecer nestes casos:
- ente sem token (CSV ou hub sem resposta);
- leitura pela fonte SIAFIC.

#### Scenario: ente com SIAFIC pela MSC
- **GIVEN** Cuitegi 2025 com `token_ps` no hub, BO processado com `use_siconfi=true`
- **WHEN** `GET /dca/BO`
- **THEN** `recortesDisponiveis` traz `po:10131` e `po:20231`, e a resposta traz `avisoRecorte`

#### Scenario: ente CSV pela MSC
- **GIVEN** um ente sem SIAFIC (o hub não resolve o token), processado com `use_siconfi=true`
- **THEN** recortes `po:`, sem `avisoRecorte`

## MODIFIED Requirements

### Requirement: Recortes apurados no mesmo job

O job do BO, do BP e do **BF** SHALL apurar, com as mesmas regras e a mesma vigência, um resultado
completo para cada recorte:

| Chave | Registros que entram |
|---|---|
| `consolidado` | todos (a apuração de hoje, inalterada) |
| `poder:executivo` | unidades com `poder_orgao` `10131` ou `10132` |
| `poder:legislativo` | unidades com `poder_orgao` `20231` |
| `poder:executivo+legislativo` | a união dos dois |
| `ug:<id>` | os registros da UG, quando a fonte informa a UG |
| `po:<código>` | os registros do PO, quando a fonte não informa a UG |

O tipo de unidade SHALL ser:

- `UG` quando algum registro **do exercício atual** trouxer a unidade gestora. É o caso da fonte
  PublicSoft com a base por UG.
- `PO` nos demais casos: SICONFI, ou PublicSoft cuja base por UG responde `422` (MSC importada por
  CSV).

Num job por UG, os registros de N−1 sem UG NÃO DEVEM virar unidade. A coluna anterior da UG fica,
então, em zero com `sem_dados_exercicio_anterior`.

A unidade cujos registros têm mais de um `poder_orgao`, ou nenhum, não entra em grupo de poder.
Grupo de poder sem nenhuma unidade NÃO é apurado: não há peça a emitir, e pedi-lo responde `404`.

A fonte SHALL ser consultada uma vez por exercício, classe e tipo de saldo, porque os recortes
filtram os registros já lidos no job. O dado da MSC NÃO DEVE ser persistido; só os resultados
apurados.

#### Scenario: ente com UG
- **GIVEN** Cuitegi 2025 com 4 UGs na base de demonstrativos
- **WHEN** o BP é processado com a fonte PublicSoft
- **THEN** o cache guarda `consolidado`, os 3 grupos de poder e 4 recortes `ug:<id>`
- **AND** a fonte é consultada o mesmo número de vezes que antes da change, mais a leitura do ano
  anterior quando a origem do BP é `publicado_siconfi`

#### Scenario: BF com UG
- **GIVEN** Cuitegi 2025 com 4 UGs
- **WHEN** o BF é processado com a fonte PublicSoft
- **THEN** o cache guarda `consolidado`, os grupos de poder e 4 recortes `ug:<id>`

#### Scenario: ente sem UG
- **WHEN** o BO de Cuitegi 2025 é processado com `use_siconfi=true`
- **THEN** o cache guarda `consolidado`, os grupos de poder e um recorte `po:<código>` por `poder_orgao` presente

#### Scenario: N−1 sem UG num job por UG
- **GIVEN** 2025 lido com UG e 2024 lido pela base oficial (`422`, CSV)
- **THEN** só existem recortes `ug:`; nenhum `po:` aparece por causa de 2024
- **AND** a coluna anterior de cada UG sai em zero com `sem_dados_exercicio_anterior`

#### Scenario: grupo sem unidade
- **GIVEN** um ente sem nenhum registro com `poder_orgao` `20231`
- **THEN** o cache não traz `poder:legislativo`, e `GET /dca/BO?recorte=poder:legislativo` responde `404`

#### Scenario: Déficit e Superávit por recorte
- **GIVEN** a Prefeitura superavitária e a Câmara deficitária
- **THEN** cada recorte apura o seu próprio Déficit e Superávit, como uma apuração independente

#### Scenario: consolidado inalterado
- **WHEN** BO, BP e BF de Cuitegi 2025 são lidos no recorte `consolidado`, pelas duas fontes
- **THEN** `matriz`, `diagnostico` e `procedencia` são iguais aos do resultado anterior à change

### Requirement: Coluna anterior do BP por recorte vem da MSC do exercício anterior

Fora do `consolidado`, a coluna do exercício anterior do BP **e do BF** SHALL ser apurada da MSC do
exercício anterior com os mesmos registros do recorte, qualquer que seja a
`origem_exercicio_anterior` do consolidado. Os motivos:
- a DCA publicada só existe consolidada;
- o anterior manual do BF foi digitado para o ente.

A unidade sem registro em N−1 SHALL sair com a coluna anterior em zero e com
`sem_dados_exercicio_anterior = true`. `diagnostico.conferencia_publicado` SHALL existir só no
`consolidado`.

#### Scenario: consolidado pelo publicado, UG pela MSC
- **GIVEN** BP processado com `origem_exercicio_anterior=publicado_siconfi`
- **WHEN** o recorte `ug:1` é lido
- **THEN** a coluna anterior é a da MSCE do exercício anterior da UG 1, sem `conferencia_publicado`

#### Scenario: BF consolidado manual, UG pela MSC
- **GIVEN** BF processado com `origem_exercicio_anterior=manual`
- **WHEN** o recorte `ug:1` é lido
- **THEN** a coluna anterior é a da MSC de N−1 da UG 1

### Requirement: Leitura de um recorte sem reprocessar

`GET /dca/BO`, `GET /dca/BP` e **`GET /dca/BF`** SHALL aceitar `recorte` (uma chave da tabela de
recortes) e servir o resultado desse recorte do cache, sem enfileirar job. Sem `recorte`, SHALL
servir o padrão do poder do usuário. Toda resposta desses anexos apurada com recortes SHALL trazer:

- `recorte`: a chave servida;
- `recortesDisponiveis: [{chave, tipo, rotulo, poderOrgao?}]`, com os recortes visíveis ao usuário.
  `tipo` é `consolidado`, `poder`, `ug` ou `po`. O rótulo de `ug` é o nome da UG; o de `po` vem da
  tabela da STN (`docs/contas-stn/poder-orgao.md`).

`reprocessar`, `/batch-jobs` e o percurso NÃO recebem `recorte`.

#### Scenario: uma UG
- **GIVEN** BP de Cuitegi 2025 em cache `ok` com recortes
- **WHEN** `GET /dca/BP?recorte=ug:3`
- **THEN** `200` com o resultado da UG 3 e `recorte: "ug:3"`, sem job

#### Scenario: BF por UG
- **GIVEN** o BF de Cuitegi 2025 em cache `ok` com recortes
- **WHEN** `GET /dca/BF?recorte=ug:3`
- **THEN** `200` com o resultado da UG 3, sem job

#### Scenario: grupo de poder
- **WHEN** `GET /dca/BO?recorte=poder:executivo`
- **THEN** `200` com o resultado apurado sobre os registros de `10131` e `10132`

#### Scenario: recorte inexistente
- **WHEN** `GET /dca/BP?recorte=ug:99`, sem a UG 99 no cache
- **THEN** `404`

#### Scenario: recorte malformado
- **WHEN** `GET /dca/BP?recorte=99`
- **THEN** `422`

#### Scenario: anexo sem recorte
- **WHEN** `GET /dca/I-C?recorte=ug:1`
- **THEN** `422`

#### Scenario: cache anterior à change
- **GIVEN** BF em cache gravado antes desta change
- **WHEN** a leitura pede um recorte diferente de `consolidado`, ou o usuário não tem `consolidado`
- **THEN** `409` pedindo reprocessar o anexo

### Requirement: Recortes visíveis pelo poder autorizado no hub

A leitura de BO, BP e **BF** SHALL restringir os recortes ao poder do usuário. O poder é consultado
no hub a cada requisição pelo campo `poderes` de `POST /internal/authorize` (`regras-rgf-api`
CH-46). Nada é lido de claim do JWT.

| Poder no hub | Recortes visíveis | Padrão sem `recorte` |
|---|---|---|
| `consolidado` | todos | `consolidado` |
| `executivo` | `poder:executivo` e as unidades `10131`/`10132` | `poder:executivo` |
| `legislativo` | `poder:legislativo` e as unidades `20231` | `poder:legislativo` |
| `executivo` + `legislativo` | os dos dois, mais `poder:executivo+legislativo` | `poder:executivo+legislativo` |
| `judiciario`, ou nenhum | nenhum | `403` |

Unidade fora dos grupos de poder (mais de um PO, nenhum PO, ou PO fora da tabela) SHALL ser visível
só para `consolidado`. Recorte não visível pedido explicitamente SHALL dar `403`, sem nenhum valor
dele no corpo. Hub indisponível SHALL dar `503` (fail closed). `reprocessar`, `/batch-jobs` e o
percurso continuam exigindo só a unidade, porque processar não expõe dado.

#### Scenario: usuário do Legislativo no BF
- **GIVEN** usuário só `legislativo`
- **WHEN** `GET /dca/BF` sem `recorte`
- **THEN** `200` com `recorte: "poder:legislativo"`, e `recortesDisponiveis` só com o grupo Legislativo e a Câmara

#### Scenario: Executivo pede a Câmara
- **GIVEN** usuário só `executivo`
- **WHEN** `GET /dca/BF?recorte=ug:<id da Câmara>`, ou `recorte=consolidado`
- **THEN** `403`, sem valor no corpo

#### Scenario: consolidado sem mudança
- **GIVEN** usuário com `consolidado`
- **WHEN** `GET /dca/BP` sem `recorte`
- **THEN** a resposta é a consolidada do ente, igual à anterior à change, mais `recorte` e `recortesDisponiveis`

#### Scenario: registro sem PO
- **GIVEN** um ente sem UG com 1.000,00 em registros sem `poder_orgao`
- **THEN** o recorte `po:` desses registros é visível só para `consolidado`, e os 1.000,00 não entram em `poder:executivo`

#### Scenario: hub fora do ar
- **WHEN** o hub não responde à consulta de poderes
- **THEN** `503`, sem dado
