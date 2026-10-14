# pipeline/anterior-por-recorte — Delta spec

## Purpose
Garante que a coluna do exercício anterior de cada recorte do BF e do BP seja da própria unidade. Ela
vem de uma de três origens, escolhida por unidade: o resultado de N−1 já processado, a MSC de N−1 ou
valores digitados. O grupo de poder soma as suas unidades.

## ADDED Requirements

### Requirement: Origem da coluna anterior escolhida por unidade

O job do BF e do BP SHALL apurar a coluna do exercício anterior de cada unidade (`ug:<id>` ou
`po:<código>`) pela origem dela:

| Origem | Valor |
|---|---|
| `processado_exercicio_anterior` | coluna atual da mesma linha (`codigo`), mesmo anexo e mesmo recorte, no resultado `ok` de N−1 em cache |
| `msce_exercicio_anterior` | apuração de N−1 sobre os registros da unidade, na fonte do pedido |
| `manual` | `valores` informados para a unidade |

A origem de cada unidade SHALL ser, nesta ordem:
1. a pedida em `anterior_por_recorte`. `{"origem": "padrao"}` limpa a escolha gravada e devolve
   a unidade ao padrão;
2. a escolha explícita gravada no processamento anterior do mesmo anexo e exercício
   (`procedencia.escolha_anterior` do recorte), com os valores, no `manual`. A escolha gravada de uma
   unidade que não existe no job SHALL ser descartada, sem aviso e sem voltar a ser gravada. Uma
   escolha `processado` gravada cujo N−1 não está `ok` SHALL cair em `msce`, com o motivo em
   `diagnostico`;
3. o padrão: `processado_exercicio_anterior` quando o cache de N−1 do anexo estiver `ok` e tiver o
   recorte, e `msce_exercicio_anterior` quando não tiver, ou quando N−1 estiver `processando` ou em
   `erro`. Nesse último caso, com o motivo em `diagnostico`.

A unidade NÃO DEVE usar a DCA publicada (`publicado_siconfi`) na coluna anterior. Na `msce`, a
leitura de N−1 SHALL ser a MSC da fonte do pedido: base PublicSoft por UG no `ug:`, e SICONFI ou a
base da fonte no `po:`. A unidade sem registro na MSC de N−1 SHALL sair com a coluna anterior em
zero e com `diagnostico.sem_dados_exercicio_anterior = true`.

No `processado`:
- a transposição SHALL levar, por `codigo`, `exercicio_atual → exercicio_anterior`;
- no Quadro Anexo do BF, SHALL levar `*_atual → *_anterior`;
- no BP, SHALL transpor também cada visão de `visoes` e o `fonte_vazia` da coluna atual;
- no Superávit/Déficit do BP, as linhas SHALL ser a união das fontes de N e de N−1, com a fonte
  ausente em 0,00.

A procedência SHALL declarar
`anterior_processado: {exercicio, calculado_em, versao_regras, fonte, estorno_receita_extra?, estorno_despesa_extra?}`.
`fonte` sai da identidade gravada em N−1 (`f=`) e é `null` quando ela não existe. Os estornos são os
da procedência do recorte em N−1, relativos ao ano N−1. Um N−1 processado por outra fonte SHALL ser
aceito quando o recorte existe nele.

#### Scenario: padrão com N−1 processado
- **GIVEN** o BF de Cuitegi 2024 em cache `ok` com o recorte `ug:3`
- **WHEN** o BF de 2025 é processado sem `anterior_por_recorte` e sem escolha gravada
- **THEN** a coluna `exercicio_anterior` de `ug:3` em 2025 é igual, em centavos, à coluna `exercicio_atual` de `ug:3` em 2024
- **AND** o serviço não apura 2024 para `ug:3`
- **AND** a procedência de `ug:3` traz `origem_exercicio_anterior = processado_exercicio_anterior` e `anterior_processado.exercicio = 2024`

#### Scenario: padrão sem N−1 processado
- **GIVEN** nenhum cache do BP de Cuitegi 2024, ou um cache gravado antes dos recortes
- **WHEN** o BP de 2025 é processado sem `anterior_por_recorte`
- **THEN** cada UG usa `msce_exercicio_anterior`, com resultado bit a bit igual ao da change `pipeline-dca-por-unidade-gestora`

#### Scenario: N−1 em processamento
- **GIVEN** o BF de 2024 com `status = processando` no momento do job de 2025
- **THEN** as unidades sem escolha usam `msce` e `diagnostico` registra "exercício anterior em processamento"

#### Scenario: Superávit por fonte no processado
- **GIVEN** `ug:1` com a fonte `1500` só em 2024 e a fonte `1700` só em 2025
- **THEN** o BP de 2025 de `ug:1` traz as duas linhas: `1500` com atual 0,00 e anterior = atual de 2024; `1700` com anterior 0,00

#### Scenario: PO pela MSC do SICONFI
- **GIVEN** Cuitegi 2025 processado com `use_siconfi=true` e sem cache de 2024 com `po:20231`
- **WHEN** o BF de 2025 é processado
- **THEN** a coluna anterior de `po:20231` é a MSC de 2024 do SICONFI filtrada por `20231`, e não a DCA publicada

#### Scenario: N−1 processado por outra fonte
- **GIVEN** o BP de 2024 processado com SIAFIC (recortes `ug:`) e o de 2025 com `use_siconfi=true` (recortes `po:`)
- **THEN** os `po:` de 2025 caem em `msce`, porque não existem em 2024
- **AND** o `consolidado`, se pedido `processado`, usa o de 2024 e declara `anterior_processado.fonte = "publicsoft"`

#### Scenario: origens diferentes no mesmo job
- **WHEN** o BF de 2025 é reprocessado com `{"ug:3": {"origem": "manual", "valores": {...}}, "ug:5": {"origem": "msce_exercicio_anterior"}}`
- **THEN** `ug:3` traz os valores digitados, `ug:5` traz a MSC de 2024 e as demais UGs usam a escolha gravada ou o padrão

#### Scenario: escolha gravada é reaplicada
- **GIVEN** um processamento anterior com `ug:3` em `manual` e `ug:5` em `msce` explícito
- **WHEN** o anexo é reprocessado com `{"ug:1": {"origem": "manual", ...}}`, ou pelo percurso
- **THEN** `ug:3` reaplica os valores salvos, `ug:5` continua em `msce`, e `ug:1` passa a ser manual

#### Scenario: processado explícito sem N−1
- **GIVEN** o BF de 2024 sem cache `ok`
- **WHEN** chega `POST /dca/BF/reprocessar` de 2025 com `{"ug:3": {"origem": "processado_exercicio_anterior"}}`
- **THEN** `409` "processe 2024 antes", sem job

#### Scenario: processado do BP no percurso sem N−1
- **GIVEN** o BP de 2024 sem cache `ok`
- **WHEN** chega `POST /batch-jobs` com `origem_exercicio_anterior=processado_exercicio_anterior`
- **THEN** a resposta é `409` "processe 2024 antes", sem job, como na rota do anexo

#### Scenario: a origem do percurso não vaza para o BF
- **GIVEN** `POST /batch-jobs` com `origem_exercicio_anterior=processado_exercicio_anterior`
- **WHEN** o percurso apura o BF
- **THEN** o BF usa a sua própria origem (gravada ou padrão); a da query vale só para o BP

#### Scenario: processado gravado sem N−1
- **GIVEN** `ug:3` com `processado` gravado num processamento anterior, e o BF de 2024 sem cache `ok`
- **WHEN** o BF de 2025 é reprocessado para outra UG, ou pelo percurso
- **THEN** `ug:3` usa `msce`, `diagnostico` registra o motivo e o job conclui

#### Scenario: limpar a escolha
- **GIVEN** `ug:3` com `manual` gravado
- **WHEN** chega `{"ug:3": {"origem": "padrao"}}`
- **THEN** `ug:3` passa ao padrão, e a `escolha_anterior` dela fica `null`

#### Scenario: N−1 some entre a rota e o job
- **GIVEN** `processado` explícito aceito pela rota, e o BF de 2024 passou a `processando` antes do job
- **THEN** o job de 2025 termina em `erro` "processe 2024 antes", sem publicar outra origem

#### Scenario: linha sem par em N−1
- **GIVEN** uma linha de 2025 cujo `codigo` não existe no resultado de 2024
- **THEN** a célula anterior dessa linha fica não apurada, com o motivo "sem linha no exercício anterior"

#### Scenario: UG sem MSC no ano anterior
- **GIVEN** uma UG sem registros na MSC de 2024 e em `msce`
- **THEN** a coluna anterior dela sai em zero, com `sem_dados_exercicio_anterior = true`

### Requirement: Validação de `anterior_por_recorte`

`anterior_por_recorte` SHALL aceitar só chaves `ug:<id>` e `po:<código>` (inclusive `po:` sem código).
Cada valor SHALL ter `origem` entre as três da tabela, ou `padrao` (aceito pela API; o front não o oferece). No `manual`, SHALL ter `valores` validados
pelo anexo:

- **BF:** as chaves e a validação do manual do consolidado de hoje.
- **BP:** as chaves com prefixo de quadro (ver o requisito do manual do BP em
  `dca/balanco-patrimonial`).

Chave de grupo, `consolidado`, origem desconhecida, `manual` sem `valores`, chave de linha
inexistente ou linha totalizadora SHALL dar `422`, sem job. Chave de unidade **pedida agora** e ausente no
job SHALL ser ignorada, com aviso em `diagnostico`. O `409` do `processado` vale só para a escolha
pedida agora; a escolha gravada sem N−1 cai em `msce` com motivo. `anterior_por_recorte` NÃO DEVE ser aceito em
`/batch-jobs`.

#### Scenario: chave de grupo
- **WHEN** `anterior_por_recorte` traz `poder:executivo`
- **THEN** `422`

#### Scenario: totalizadora no manual
- **WHEN** o manual do BP traz `P:<codigo de uma totalizadora>`
- **THEN** `422`

#### Scenario: unidade inexistente
- **WHEN** `anterior_por_recorte` traz `ug:99`, que nenhum registro do job tem
- **THEN** o job conclui e `diagnostico` registra que `ug:99` foi ignorada

### Requirement: Identidade do pedido com as escolhas por unidade

A identidade do pedido SHALL incluir as escolhas explícitas por unidade (origem e, no manual, os
valores), reconstruídas da procedência gravada quando o pedido não as traz. O mapa de escolhas
explícitas SHALL ser gravado também na procedência de topo (`anterior_por_recorte`), para
sobreviver a job em erro. A origem resolvida pelo
padrão NÃO DEVE entrar na identidade. Ler o anexo ou reprocessá-lo sem mudar escolhas NÃO DEVE
produzir `pedido` em `motivos_desatualizado`.

#### Scenario: leitura depois de escolha manual
- **GIVEN** o BP de 2025 processado com `ug:3` em `manual`
- **WHEN** `GET /dca/BP?recorte=ug:3`
- **THEN** `desatualizado = false`

#### Scenario: escolha sobrevive a job em erro
- **GIVEN** o BP de 2025 processado com `ug:3` em `manual`, e um job seguinte que terminou em erro
- **WHEN** `reprocessar` sem corpo
- **THEN** `ug:3` é reapurada em `manual` com os mesmos valores e a identidade `ar-<hash>` não muda

### Requirement: Grupo de poder soma a coluna anterior das unidades

A coluna anterior de `poder:*` SHALL ser a soma, linha folha a linha folha, das colunas anteriores
das unidades do grupo, cada uma pela sua origem, e a procedência do grupo SHALL declarar
`origem_exercicio_anterior = soma_das_unidades`. As totalizadoras SHALL sair da calculation. No
Superávit por fonte do BP, entra a união das fontes, e a fonte ausente numa unidade conta 0,00. Uma
unidade com a célula não apurada SHALL deixar a célula do grupo não apurada.

#### Scenario: grupo com origens mistas
- **GIVEN** Prefeitura em `processado`, FMS em `manual` e Câmara em `msce`
- **THEN** a coluna anterior de `poder:executivo+legislativo` em cada linha folha é igual à soma das três, com diferença 0,00

#### Scenario: aditividade
- **GIVEN** todas as unidades em `msce`
- **THEN** o grupo somado é igual, célula a célula, ao grupo apurado sobre a MSC filtrada pelo grupo

### Requirement: Consolidado com origem processada

`origem_exercicio_anterior` do consolidado SHALL aceitar `processado_exercicio_anterior` no BF e no
BP, nos parâmetros onde ela já é aceita (corpo do `reprocessar`; query da leitura `GET /dca/{BF|BP}`,
que a usa para a identidade; query do percurso para o BP), com a
mesma regra aplicada ao recorte `consolidado` de N−1. O padrão do consolidado e as origens de hoje
NÃO DEVEM mudar.

#### Scenario: consolidado processado
- **GIVEN** o BP de Cuitegi 2024 em cache `ok`
- **WHEN** o BP de 2025 é processado com `origem_exercicio_anterior=processado_exercicio_anterior`
- **THEN** o `L1` anterior de 2025 é igual ao `L1` atual do consolidado de 2024, e não há `conferencia_publicado`

#### Scenario: consolidado sem mudança
- **WHEN** o BF e o BP de 2025 são processados com as origens de hoje
- **THEN** o consolidado sai bit a bit igual ao de antes da change
