# dca/balanco-orcamentario

> Comportamento acordado e em vigor. Consolidado da change
> `bo-quadro-principal-processamento`, aprovada pelo PO em 2026-09-04 e arquivada em
> `openspec/changes/archive/`. Inclui as alterações das changes
> `ipc07-b1-remocao-termo-5313`, `ipc07-c5-c7-linhas-cruzadas`, `ipc07-l51-reserva-rpps` e
> `bo-template-no-resultado`.
> Alterações entram por nova change, nunca por edição direta deste arquivo.

## Purpose

Garantir que o **quadro principal** do Balanço Orçamentário (51 linhas — 4 colunas de receita e 6 de
despesa) seja apurado a partir da Matriz de Saldos Contábeis do ente, aplicando as regras canônicas
entregues por `ipc07-bo-regras-canonicas` sem reinterpretá-las, com direção de saldo lida da tabela
oficial e sem nenhuma inferência de sinal.

Esta capability **apura**; não publica anexo nem expõe rota HTTP. O demonstrativo pertence a este
repositório (decisão C4 do PO, 2026-09-04); o `RREO-Anexo 01` é do `regras-rreo-api` e aqui entra
apenas como gabarito de conferência.

Primeira entrega da capability. Os quadros de RP Processados e Não Processados, a ligação com o
anexo DCA e o transporte HTTP são changes posteriores.


### Requirement: Direção do saldo resolvida por conta folha na tabela PCASP

A direção do saldo de uma conta SHALL ser lida da coluna `NATUREZA DO SALDO` de
`docs/contas-stn/PCASP.md`, pela **conta folha de 9 dígitos do registro**. A apuração NÃO DEVE
inferir a direção da classe contábil, do prefixo declarado na regra, nem do campo `natureza_conta`
do registro — esse campo descreve o lançamento, não a conta.

Conta ausente da tabela SHALL tornar a célula não apurada, com aviso — nunca zero. Não há
mecanismo de direção declarada na regra: a decisão B1, único caso que o exigiria, foi revogada em
2026-09-04 (change `ipc07-b1-remocao-termo-5313`), e B3 usa os padrões em filtro, não em coluna.

#### Scenario: conta devedora de classe 6

- **GIVEN** a conta `621310100` (Deduções — FUNDEB), registrada como **Devedora** no `PCASP.md`
- **WHEN** seu saldo é apurado na MSC de João Pessoa (`2507507`) 12/2025
- **THEN** o resultado é `Σ D − Σ C` = `332.643.194,90`, positivo
- **AND** o mesmo vale para `621390000`, que devolve `44.846.513,57`

#### Scenario: heurística de classe é rejeitada

- **GIVEN** que `621310100` e `621390000` são de classe 6 e devedoras
- **WHEN** a apuração usa a direção lida da tabela
- **THEN** nenhuma das duas sai negativa
- **AND** a apuração NÃO consulta nenhum conjunto de classes credoras

#### Scenario: contas de mesmo prefixo com direções opostas

- **GIVEN** o prefixo `6.2.1.3`, que no `PCASP.md` tem 1 conta credora e 5 devedoras
- **WHEN** as contas desse prefixo entram numa célula
- **THEN** cada uma é resolvida pela sua própria linha na tabela
- **AND** a direção declarada no prefixo da regra NÃO é aplicada a nenhuma delas

#### Scenario: natureza do lançamento não determina a direção

- **GIVEN** registros da mesma conta credora, uns com `natureza_conta: C` e outros com `D`
- **WHEN** o saldo é apurado
- **THEN** o resultado é `Σ C − Σ D`
- **AND** o sinal NÃO muda em função de qual natureza predomina nos registros

### Requirement: Saldo da célula por soma de saldos de conta com a operação da regra

O saldo de uma conta SHALL ser `Σ C − Σ D` se credora e `Σ D − Σ C` se devedora. O valor da célula
SHALL ser `Σ operacao × saldo(conta)`, sobre as contas declaradas na coluna, restrito aos registros
que satisfazem os `filters` da linha. Todos os valores SHALL ser `Decimal`; `float` NÃO DEVE ser
usado em nenhum ponto do cálculo.

#### Scenario: coluna com uma conta

- **GIVEN** a coluna Despesas Pagas, conta `622130400`, em JP 12/2025
- **WHEN** a célula é apurada
- **THEN** o valor é `4.529.794.533,11`, idêntico em centavos ao `DCA-Anexo I-D`

#### Scenario: coluna com várias contas somadas

- **GIVEN** a coluna Despesas Empenhadas, contas `622130400 + 622130500 + 622130700`
- **WHEN** a célula é apurada
- **THEN** o valor é `4.850.356.845,30`, idêntico em centavos ao gabarito

#### Scenario: conta com sinal negativo na fórmula

- **GIVEN** a Dotação Atualizada, `522110100 + 522120100 + 522120201 − 522130900`
- **WHEN** a célula é apurada
- **THEN** o valor é `6.043.181.131,90`
- **AND** `522130900` (cancelamento) entra subtraindo, conforme a `operacao` da regra

### Requirement: Casamento de conta por conta folha declarada, nunca por prefixo solto

Uma conta do registro SHALL entrar numa célula apenas quando corresponder às contas **declaradas**
pela regra. O casamento NÃO DEVE ser feito por `startswith` sobre o prefixo do IPC 07 quando isso
capturar contas irmãs não declaradas.

#### Scenario: conta irmã de controle paralelo não entra

- **GIVEN** que `L29` declara `522130100` (Superávit Financeiro) e que `522139900` (Valor Global da
  Dotação Adicional por Fonte) é sua irmã sob o prefixo `5.2.2.1.3`
- **WHEN** a coluna de `L29` é apurada em JP 12/2025
- **THEN** `522139900` NÃO compõe o valor
- **AND** a célula não é inflada em `R$ 729.036.483,90`

#### Scenario: contas bifront ficam fora das colunas

- **GIVEN** que `621100000` e `522139900` têm movimento em JP 12/2025 e nenhuma compõe as colunas
  do quadro
- **WHEN** a Dotação Atualizada é apurada
- **THEN** ela fecha em `6.043.181.131,90`, igual a `522310000` e a `622310000`
- **AND** nenhuma das duas contas bifront compõe esse valor

### Requirement: Célula sem direção conhecida não é apurada

Quando a conta não tiver natureza na tabela PCASP nem `natureza_saldo` declarado na regra, a célula
SHALL ser `None` e SHALL gerar aviso nomeando a conta, a linha e a coluna. A apuração NÃO DEVE
emitir `0`, NÃO DEVE presumir direção e NÃO DEVE abortar as demais células.

#### Scenario: conta sem natureza conhecida

- **WHEN** uma conta com movimento não está no `PCASP.md` e sua regra não declara `natureza_saldo`
- **THEN** a célula que a contém sai `None`
- **AND** o aviso nomeia conta, `rule_id` e coluna
- **AND** as demais células do quadro continuam apuradas

#### Scenario: zero legítimo é distinguido de não apurado

- **GIVEN** uma conta presente no PCASP, com direção conhecida e sem escrituração no período
- **WHEN** a célula é apurada
- **THEN** o valor é `Decimal("0.00")`, não `None`
- **AND** nenhum aviso é emitido

#### Scenario: escrituração em conta descontinuada não apaga a célula

- **GIVEN** um ente que escriture saldo em `5.3.1.3.0.00.00`, conta descontinuada e não declarada
  em nenhuma coluna
- **WHEN** o quadro de RP Não Processados é apurado
- **THEN** a coluna (a) é apurada a partir das 3 contas declaradas, com valor, **não** `None`
- **AND** o registro não é somado a essa coluna e não gera aviso: `residuos` classifica por
  natureza de receita e de despesa, não por conta contábil

### Requirement: Leitura da MSC fixa em ending_balance, MSCC, classes 5 e 6

A apuração SHALL consultar `id_tv = ending_balance`, `co_tipo_matriz = MSCC`, mês **12**, classes
**5** e **6**, na matriz orçamentária. `period_change` NÃO DEVE ser consultado. O mês de
encerramento NÃO DEVE ser usado, porque nele as contas de controle das classes 5 e 6 estão zeradas.

#### Scenario: duas consultas por apuração

- **WHEN** o quadro principal de um ente é apurado
- **THEN** são feitas exatamente duas leituras de saldos, classe `5` e classe `6`, mesmo mês e
  mesmo `id_tv`
- **AND** ambas usam a matriz orçamentária

#### Scenario: paginação completa da fonte SICONFI

- **GIVEN** um ente cujo retorno excede 5.000 registros numa classe
- **WHEN** os saldos são lidos
- **THEN** o adapter segue `hasMore`/`offset` até o fim
- **AND** o total de registros entregue ao apurador é o total da fonte, não a primeira página

#### Scenario: volume do caso real

- **WHEN** JP `2507507` 12/2025 é lido
- **THEN** chegam `4.600` registros de classe 5 e `4.320` de classe 6

### Requirement: Fontes MSC intercambiáveis atrás do mesmo contrato

Os adapters SICONFI e PublicSoft SHALL entregar registros com o mesmo conjunto de campos em
snake_case — `conta_contabil`, `natureza_conta`, `valor`, `natureza_receita`, `natureza_despesa`,
`fonte_recursos`, `poder_orgao`, `complemento_fonte`. O núcleo de apuração NÃO DEVE conter
referência a HTTP, a nome de endpoint ou a formato de resposta de qualquer fonte.

#### Scenario: mesma matriz por fontes diferentes

- **GIVEN** o mesmo ente, ano e mês disponíveis nas duas fontes com os mesmos saldos
- **WHEN** o quadro é apurado com cada uma
- **THEN** as duas matrizes são iguais célula a célula

#### Scenario: gate de auditoria da PublicSoft reprovado

- **GIVEN** que a auditoria do exercício/mês não devolve `status == "validado"` **e**
  `podeGerar == true`
- **WHEN** os saldos são solicitados à PublicSoft
- **THEN** o adapter devolve conjunto vazio de registros, sem levantar erro de transporte
- **AND** a apuração reporta ausência de dados, não zeros

#### Scenario: normalização de camelCase

- **GIVEN** uma resposta da PublicSoft com `codConta`, `naturezaConta`, `naturezaReceita` e
  `poderOrgao`, em `data[]` ou `items[]`
- **WHEN** o adapter normaliza
- **THEN** os campos chegam ao núcleo como `conta_contabil`, `natureza_conta`, `natureza_receita` e
  `poder_orgao`

### Requirement: Ordem de apuração — células, agregações e derivadas

A matriz SHALL ser apurada em três passos, nesta ordem: (a) células por conta e filtro; (b) linhas
de agregação (`soma_filhas`), coluna a coluna, em ordem topológica; (c) colunas derivadas por
linha. Uma derivada NÃO DEVE ser calculada antes da agregação da sua linha.

#### Scenario: derivada verdadeira também nos totais

- **GIVEN** a coluna `saldo = receitas_realizadas − previsao_atualizada` e uma linha de total
- **WHEN** a matriz é apurada
- **THEN** o `saldo` do total é igual à diferença das colunas do próprio total
- **AND** isso vale por construção, sem passo de conferência posterior

#### Scenario: agregação propaga não apurado

- **GIVEN** uma linha de agregação cuja filha tem uma célula `None`
- **WHEN** a soma é feita
- **THEN** a célula da linha de agregação também é `None`, com aviso encadeado
- **AND** o `None` NÃO é tratado como `0` na soma

#### Scenario: ciclo entre referências é rejeitado

- **WHEN** o mapa carregado contém dependência circular entre linhas
- **THEN** a apuração falha nomeando o caminho do ciclo, sem produzir matriz parcial

### Requirement: Override de conta na linha em L29 e L30

Quando a regra declarar `line_account_override`, as contas da **linha** SHALL substituir as contas
padrão da coluna. O override SHALL ser aceito somente em `bo.quadro_principal.receitas.l29` e
`.l30`; declarado em qualquer outro `rule_id`, a apuração SHALL falhar nomeando o `rule_id`.

#### Scenario: superávit financeiro pela conta da linha

- **GIVEN** `L29` com override e conta `522130100`
- **WHEN** a previsão atualizada de `L29` é apurada em JP 12/2025
- **THEN** o valor é `470.338.332,64`, igual ao `SuperavitFinanceiro` publicado

#### Scenario: composição da linha 27

- **GIVEN** `L27 = L28 + L29 + L30`
- **WHEN** a previsão atualizada é apurada
- **THEN** `12.000.000,00 + 470.338.332,64` fecha `482.338.332,64`

### Requirement: Reserva do RPPS é apurada com o mapeamento de despesa

`bo.quadro_principal.despesas.l51` SHALL ser apurada com as mesmas colunas e contas da
`bo.quadro_principal.despesas.l39`. Os filtros da linha SHALL restringir a MSC a
`natureza_despesa` `9.9.00.00.00`, função `99` e subfunção `997`. A linha NÃO DEVE ser agregada
por `L40` nem por `L50`. Escrituração ausente nessa classificação SHALL produzir `0.00`, não
célula vazia nem aviso de não apurada.

#### Scenario: reserva do RPPS

- **GIVEN** um registro `622130400` com ND `9.9.00.00.00`, função `99`, subfunção `997` e saldo
  `100,00`, e outro idêntico com subfunção `999` e saldo `50,00`
- **WHEN** o quadro principal é apurado
- **THEN** `L51.pagas` é `100,00` e `L39.pagas` é `50,00`
- **AND** nenhum aviso de célula não apurada cita `l51`

#### Scenario: L51 fica fora do TOTAL (XV)

- **WHEN** `L50` é lida
- **THEN** suas referências são só `L48` e `L49`

### Requirement: Linha condicional só é apresentada quando a condição vale

Linha com `calculation.condition` SHALL ter valor apresentado apenas quando a condição for
satisfeita; caso contrário a célula SHALL ficar sem valor, distinta de `0` e de não apurada.
As linhas de déficit e superávit NÃO DEVEM aparecer simultaneamente com valor.

A condição SHALL ser aplicada **antes** de a linha ser agregada por seus dependentes, e a célula
suprimida SHALL contribuir **zero** para o total que a agrega — o total tem valor mesmo quando a
linha de ajuste não se aplica. Medido: em ente deficitário o STN deixa `Superavit` em branco e
publica `TotalDespesasComSuperavit` igual a `TotalDespesas` (SP e GO, exatos em centavos);
simétrico em ente superavitário com `Deficit` e `TotalReceitasComDeficit`.

A célula suprimida NÃO DEVE gerar aviso de não apurada: "não se aplica" e "não sei" são estados
distintos, e só o segundo é defeito de apuração.

#### Scenario: exercício superavitário

- **GIVEN** `L25 Déficit = L48 − L24` com resultado negativo
- **WHEN** a matriz é apurada
- **THEN** `L25` fica sem valor, e sem aviso de célula não apurada
- **AND** `L49 Superávit` é apresentada com valor positivo em `empenhadas`, `liquidadas` e `pagas`
- **AND** `L26 TOTAL (VII)` tem valor, com a parcela de `L25` valendo zero
- **AND** em João Pessoa 2025 `L49.empenhadas` = 267.518.451,03 e `L50.empenhadas` =
  5.117.875.296,33, a receita realizada

#### Scenario: exercício deficitário

- **GIVEN** um ente cuja despesa empenhada supera a receita realizada — medido em São Paulo (`35`)
  2025, `L48.empenhadas` = 385.042.592.630,74 contra `L24.receitas_realizadas` = 372.818.667.132,35
- **WHEN** a matriz é apurada
- **THEN** `L25.receitas_realizadas` = 12.223.925.498,39, a única coluna que a linha tem
- **AND** `L49` fica sem valor nas três colunas, e sem aviso
- **AND** `L50` tem valor igual a `L48` em cada uma das suas cinco colunas

### Requirement: Resíduo de classificação é medido e reportado

Registros cuja natureza de receita ou de despesa não seja classificada por nenhuma linha do total
SHALL ser reportados como **resíduo**, com o valor agregado e a natureza. O resíduo NÃO DEVE ser
somado ao total nem descartado em silêncio.

#### Scenario: recursos arrecadados em exercícios anteriores

- **GIVEN** três registros de `521110000` com natureza de receita `9.9.9.0.00.0.0`, somando
  `12.000.000,00` em JP 12/2025
- **WHEN** o quadro é apurado
- **THEN** esses `12.000.000,00` NÃO entram no total das receitas
- **AND** a previsão inicial do total sai `5.301.644.648,00`, igual ao publicado
- **AND** o relatório de apuração nomeia a natureza e o valor do resíduo

### Requirement: Matriz apurada reproduz o gabarito oficial em centavos

A apuração do caso de referência SHALL reproduzir, sem diferença em centavos, os 11 valores
conferidos em `docs/validacao-bo-jp-2025.md`. A comparação SHALL ser feita em `Decimal` e sobre a
saída do código, não sobre script de análise.

#### Scenario: conferência do caso de referência

- **WHEN** o quadro principal de JP `2507507` 12/2025 é apurado pelo código
- **THEN** as 5 colunas de despesa executada, as 3 de receita realizada, a dotação inicial, a
  dotação atualizada e a previsão atualizada batem em centavos com `DCA-Anexo I-C`, `I-D` e
  `RREO-Anexo 01`
- **AND** o relatório informa quantas células saíram `None` e o motivo de cada uma

#### Scenario: rótulos em latin-1

- **GIVEN** que os nomes de conta do `tt/dca` e da MSC vêm em latin-1
- **WHEN** rótulos são comparados
- **THEN** a decodificação ocorre antes da comparação
- **AND** nenhuma divergência é reportada por diferença de codificação

### Requirement: Regra carregada pela vigência do exercício apurado

A carga do mapa de regras SHALL receber o **exercício apurado** e devolver a regra vigente para ele.
A apuração NÃO DEVE fixar a edição do IPC no código nem presumir que exista uma única edição
publicada.

#### Scenario: exercício determina a edição

- **WHEN** o quadro principal é apurado para um exercício
- **THEN** o mapa carregado é o vigente para aquele exercício
- **AND** a edição usada aparece na procedência do resultado

#### Scenario: exercício descoberto

- **WHEN** o exercício apurado não é coberto por nenhuma vigência declarada
- **THEN** a apuração falha nomeando o exercício e as vigências disponíveis
- **AND** nenhuma regra é aplicada por aproximação

### Requirement: Matriz acompanhada de procedência e diagnóstico

A matriz apurada SHALL vir acompanhada da procedência — regras aplicadas, edição do IPC e versão das
tabelas de `docs/contas-stn/` — e do diagnóstico: células não apuradas com motivo, resíduos de
classificação e duração. Esses dados SHALL fazer parte do resultado, não apenas do log.

#### Scenario: divergência explicável pelo resultado

- **GIVEN** uma matriz apurada que diverge do publicado pelo STN
- **WHEN** o resultado é inspecionado
- **THEN** ficam determinadas as regras aplicadas, a edição do IPC e a versão das tabelas STN
- **AND** as células não apuradas e os resíduos estão listados com seus motivos

#### Scenario: apuração sem pendência

- **WHEN** todas as células são apuradas e não há resíduo
- **THEN** o diagnóstico vem vazio, e não omitido

### Requirement: Nenhuma regra fora da base canônica

A apuração SHALL usar exclusivamente as regras carregadas de `knowledge/rules/bo/`. Conta, filtro,
coluna ou cálculo NÃO DEVEM ser codificados no apurador.

#### Scenario: mapa é a única fonte de regra

- **WHEN** o código do apurador é inspecionado
- **THEN** nenhum código de conta contábil, natureza ou função aparece literal fora de teste
- **AND** trocar uma conta no YAML muda a matriz sem alterar código

### Requirement: O resultado publica o template de apresentação

Todo resultado apurado SHALL trazer, além dos valores, o **template do demonstrativo**: uma
sequência ordenada de linhas com `rule_id`, `codigo`, `rotulo`, `quadro`, `grupo`, `nivel`, `ordem`
e `totalizadora`. Quem renderiza NÃO DEVE precisar declarar rótulo, nível ou ordem por fora.

`nivel` e `ordem` SHALL ser os declarados na transcrição normativa versionada, e NÃO DEVEM ser
derivados da árvore de composição — as duas coisas divergem, e a norma é a que vale.

#### Scenario: template acompanha os valores

- **WHEN** um anexo é apurado
- **THEN** o resultado traz `linhas` com uma entrada por linha do demonstrativo
- **AND** todo `rule_id` de `linhas` existe em `matriz`, e todo `rule_id` de `matriz` existe em
  `linhas`

#### Scenario: nível e ordem são os da norma

- **GIVEN** a transcrição declara `nivel` e `ordem` para cada linha
- **WHEN** o template é publicado
- **THEN** os valores publicados são os declarados na transcrição
- **AND** `Reserva do RPPS` sai com `nivel: 2`, e não com o nível que a composição sugeriria

#### Scenario: linhas saem na ordem de apresentação da norma

- **WHEN** o template é publicado
- **THEN** os quadros aparecem na ordem `QUADRO_PRINCIPAL`, `RP_NAO_PROCESSADOS`,
  `RP_PROCESSADOS`
- **AND** dentro do quadro principal, o grupo `RECEITAS` precede `DESPESAS`
- **AND** dentro de cada grupo, as linhas seguem `ordem` crescente

#### Scenario: ordem é relativa ao grupo

- **GIVEN** que a norma numera receitas de 1 a 30 e despesas de 1 a 21
- **WHEN** o template é publicado
- **THEN** existem duas linhas com `ordem: 1` no quadro principal, distinguidas por `grupo`
- **AND** `grupo` é publicado em cada linha, de modo que a intercalação seja resolúvel

#### Scenario: linha totalizadora é identificável sem reimplementar a regra

- **GIVEN** uma linha composta de outras
- **WHEN** o template é publicado
- **THEN** ela sai com `totalizadora: true`
- **AND** linha de folha e linha de rótulo saem com `totalizadora: false`

#### Scenario: adição não quebra consumidor existente

- **WHEN** o resultado é publicado
- **THEN** `matriz`, `procedencia` e `diagnostico` permanecem com a mesma forma
- **AND** nenhum campo é removido ou renomeado

### Requirement: Vigência publicada sem os metadados de apresentação é completada

Vigência de mapeamento publicada antes desta change NÃO DEVE quebrar a apuração nem publicar
template incompleto. O carregador SHALL completar `nivel` e `ordem` ausentes a partir da
transcrição versionada, registrando o evento em log.

#### Scenario: vigência antiga não tem nível nem ordem

- **GIVEN** uma vigência publicada cujo shape não traz `nivel` e `ordem`
- **WHEN** o mapa é carregado do banco
- **THEN** os dois campos são completados pela transcrição versionada
- **AND** o evento é registrado em log, sem falhar a apuração

#### Scenario: linha do banco sem correspondente na transcrição

- **GIVEN** uma vigência com linha que a transcrição versionada não contém
- **WHEN** o mapa é carregado
- **THEN** a linha permanece no template com a ordem em que aparece na vigência
- **AND** a apuração não falha
