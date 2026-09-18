# dca/balanco-financeiro — Delta spec

## Purpose

Apurar as 80 linhas do Balanço Financeiro (IPC 06, ed. 2024-06) a partir da base canônica em
`knowledge/rules/bf/` e dos registros da MSC, produzindo matriz, template de apresentação,
procedência e diagnóstico — verificável sem Postgres, Redis ou container, como a F1 do BO.

O motor de matriz, saldo e filtros é **o mesmo** do Balanço Orçamentário. Esta capability
acrescenta o que o IPC 06 exige e o IPC 07 não exigia: corte por fonte de recursos, saldo em data
e sentido do movimento. Nada aqui altera o comportamento do BO.

## ADDED Requirements

### Requirement: Fonte de recursos casada pelo código principal

O motor SHALL aceitar `fonte_recurso` como campo de filtro, resolvido contra
`Registro.fonte_recursos`. O valor escriturado na MSC SHALL ser normalizado antes da comparação:
o **primeiro dígito** é o prefixo de exercício (`1` corrente, `2` anteriores, `9` condicionados) e
NÃO participa do casamento; os **três dígitos seguintes** são o código principal e SHALL casar por
**igualdade**, não por prefixo. O detalhamento que o ente acrescenta após o código principal NÃO
DEVE impedir o casamento.

Fonte escriturada com menos de 4 dígitos, ou cujo código principal esteja fora do bloco 500–999,
SHALL ser tratada como não classificada: o registro NÃO DEVE entrar em nenhuma linha por fonte, e
SHALL aparecer em `diagnostico.residuos`.

#### Scenario: fonte do exercício corrente casa com o código principal

- **GIVEN** um registro com `fonte_recursos: "1500"` e a linha `bf.quadro_principal.ingressos.l2`,
  que declara `fonte_recurso in ("500", "501", "502", "503")`
- **WHEN** a matriz é apurada
- **THEN** o registro entra em `L2`

#### Scenario: o mesmo código principal em exercícios anteriores e condicionados

- **GIVEN** registros com `fonte_recursos` `"1500"`, `"2500"` e `"9500"`
- **WHEN** `L2` é apurada
- **THEN** os três entram na linha
- **AND** o prefixo não aparece em nenhum valor declarado na regra

#### Scenario: detalhamento do ente após o código principal

- **GIVEN** um registro com `fonte_recursos: "1540000123"`, detalhamento do ente sobre a fonte
  `540`
- **WHEN** `bf.quadro_principal.ingressos.l4` (Educação, `540`–`599`) é apurada
- **THEN** o registro entra em `L4`

#### Scenario: casamento por prefixo solto é rejeitado

- **GIVEN** um registro com `fonte_recursos: "1505"` e a linha `L2`, que declara `500`–`503`
- **WHEN** a matriz é apurada
- **THEN** o registro **não** entra em `L2` — `505` não é `500`
- **AND** aparece em `diagnostico.residuos` com `campo: fonte_recurso`

#### Scenario: campo singular não silencia o casamento

- **WHEN** uma linha do BF declara `field: fonte_recurso` e o registro traz `fonte_recursos`
- **THEN** o motor resolve os dois como o mesmo campo
- **AND** nenhuma linha por fonte é apurada como zero por incompatibilidade de nome

### Requirement: Saldo em data lido pelo tipo de valor da MSC

A porta `FonteSaldos` SHALL aceitar o tipo de valor da leitura. Conta declarada com
`saldo: inicial` SHALL ser lida do saldo de abertura **do exercício**; com `saldo: final`, do saldo
de encerramento da competência apurada. O tipo de valor SHALL ser explícito na chamada — a fonte
NÃO DEVE assumir o saldo de encerramento por omissão quando a regra pede saldo inicial.

O saldo de abertura do exercício SHALL vir da competência 12 do **exercício anterior**. A leitura
`(ano, competência 12, abertura)` NÃO DEVE ser usada para isso: na `MSCE` ela é a posição
pré-encerramento do próprio exercício, e na `MSCC` é a abertura de dezembro. Medido em João Pessoa
2025 — a leitura correta dá 1.865.100.624,27 e a incorreta 2.613.640.800,87, 748.540.176,60 a mais.

#### Scenario: L30 lê o saldo de abertura do exercício

- **GIVEN** `bf.quadro_principal.ingressos.l30`, cujas três contas declaram `saldo: inicial`
- **WHEN** a matriz é apurada para o exercício 2025 de João Pessoa
- **THEN** o valor é 1.865.100.624,27, a abertura do exercício
- **AND** NÃO é 2.613.640.800,87, que é a abertura da competência 12
- **AND** o valor de `L30` difere do de `L63`, que lê o encerramento das mesmas contas

#### Scenario: as duas pontas do exercício fecham entre si

- **GIVEN** o caso de referência
- **WHEN** `L29 Saldo do Exercício Anterior` e `L62 Saldo para o Exercício Seguinte` são apuradas
- **THEN** `L29` do exercício apurado é igual a `L62` do exercício imediatamente anterior, em
  centavos

#### Scenario: tipo de valor não suportado pela fonte

- **WHEN** a fonte é consultada com um tipo de valor que ela não oferece
- **THEN** ela falha explicitamente, nomeando o tipo pedido
- **AND** NÃO devolve o saldo de encerramento no lugar

### Requirement: Movimento bruto de depósitos restituíveis declarado como indisponível

`L27` e `L60` declaram as **mesmas contas** (`2.1.8.8` e `2.2.8.8`) e, no demonstrativo publicado,
representam fluxos brutos em sentidos opostos. A MSC **não expõe esse movimento bruto**: entrega
saldo e variação, e nenhum dos dois reproduz o publicado. Medido em Recife, 2026-09-18 — saldo de
`2.1.8.8`: 132.890.609,07 (2024) e 176.421.602,57 (2025), variação +43.530.993,50; `period_change`
da MSCC: líquido -6.107.254,33; o publicado implica +123.944.269,55. Três números, nenhum igual.

As duas linhas SHALL ser apuradas pelo saldo das contas declaradas, como as demais, e a diferença
contra o publicado SHALL ser registrada no relatório de auditoria do ente. A apuração NÃO DEVE
inventar um fluxo bruto que a fonte não tem.

#### Scenario: depósitos restituíveis apurados pelo saldo declarado

- **GIVEN** as contas `2.1.8.8` e `2.2.8.8` na matriz do exercício
- **WHEN** `L27` e `L60` são apuradas
- **THEN** ambas trazem o saldo das contas declaradas, na direção do PCASP
- **AND** a divergência contra o BF publicado aparece no relatório de auditoria do ente, com os
  dois valores

#### Scenario: nenhuma linha do BF depende de movimento bruto

- **WHEN** a base do BF é carregada
- **THEN** nenhuma coluna declara `movimento`
- **AND** todas as linhas somam o saldo das contas declaradas

### Requirement: Origem do saldo declarada por linha

A origem do saldo SHALL ser propriedade **da linha**, não do demonstrativo. Medido em 2026-09-18
nos entes de homologação, três origens cobrem o quadro principal:

| Origem | Linhas | Por quê |
|---|---|---|
| `MSCE`/abertura do exercício | as demais, inclusive `L62`-`L65` | é a posição final do exercício |
| `MSCE`/**encerramento** do exercício | `L25`, `L26` | `5.3.1.7` e `5.3.2.7` **não existem** na abertura: a inscrição de restos a pagar acontece no encerramento |
| `MSCE`/abertura do **exercício anterior** | `L29`-`L32` | o saldo do exercício anterior é o do ano anterior |

Ler tudo de uma origem só NÃO DEVE acontecer: `L25` e `L26` sairiam **zeradas sem erro**, e
`L29`-`L32` trariam a posição final em vez da inicial.

A procedência SHALL declarar a origem usada por cada linha.

#### Scenario: inscrição de restos a pagar vem do encerramento

- **GIVEN** a MSCE de Recife 2025, em que `5.3.1.7` e `5.3.2.7` não têm saldo na abertura
- **WHEN** `L25` e `L26` são apuradas
- **THEN** valem 74.205.408,29 e 106.062.740,96, lidas do saldo de encerramento
- **AND** os dois valores coincidem com o RREO Anexo 01 publicado pelo próprio ente

#### Scenario: saldo do exercício anterior lido do ano anterior

- **GIVEN** o exercício 2025 de Recife
- **WHEN** `L29`-`L32` são apuradas
- **THEN** leem a MSCE/abertura de **2024**: `1.1.1` = 802.570.332,31 e `1.1.3.5.1` = 717.721,98
- **AND** somam 803.288.054,29, o valor publicado em `L29`

#### Scenario: a procedência nomeia a origem de cada linha

- **WHEN** o resultado é publicado
- **THEN** `procedencia.origens_por_linha` traz, para cada código de linha, matriz, tipo de saldo e
  exercício lidos

### Requirement: Linha sem conta declarada no IPC 06 não é apurada

Seis linhas do quadro principal — `L22`, `L23`, `L28`, `L55`, `L56`, `L61` — não têm conta
declarada na base canônica. Elas SHALL sair **não apuradas**, com motivo no diagnóstico, e NÃO
DEVEM sair como zero: zero afirma que não houve movimento, e aqui não se sabe.

Medido em 2026-09-18: os valores que os entes publicam nessas linhas **não existem na MSC** — busca
em 7 combinações de matriz e tipo de saldo, em todos os prefixos de conta de 3 a 9 dígitos, como
saldo, como total de créditos e como total de débitos. A busca foi validada por controle, achando
`L16` e `L25`.

No total que as agrega, a linha não apurada SHALL contribuir como **parcela inexistente** — o total
soma as demais e declara o bloqueio. Propagar `None` até o total deixaria o demonstrativo inteiro em
branco por causa de seis linhas.

#### Scenario: linha sem conta sai não apurada

- **WHEN** `L22` é apurada
- **THEN** a célula é `None` nas duas colunas
- **AND** o diagnóstico nomeia a linha e o motivo

#### Scenario: o total soma as parcelas que existem

- **GIVEN** `L21` = `L22` + `L23`, ambas sem conta declarada
- **WHEN** a matriz é apurada
- **THEN** `L21` vale 0,00 e `L33` é apurada normalmente

### Requirement: Policy declarada e não aplicada é publicada como tal

A policy `ipc06.exclusao_de_intraorcamentarias` (item 38) declara o conceito **sem dizer quais
códigos** caracterizam a transferência intraorçamentária acompanhada de execução. A apuração NÃO
DEVE aplicá-la por interpretação: medido em 2026-09-18, excluir a receita das categorias 7 e 8 e a
despesa de modalidade 91 **quebra `L1` e `L34` em Belo Horizonte e João Pessoa**, que conferem em
centavos sem a exclusão.

A policy SHALL constar do diagnóstico como declarada e não aplicada, com o motivo.

#### Scenario: o item 38 não altera o valor apurado

- **GIVEN** registros de receita com natureza das categorias 7 e 8
- **WHEN** `L2` é apurada
- **THEN** o valor inclui os registros intraorçamentários
- **AND** `diagnostico.policies_nao_aplicadas` cita o item 38 e o motivo

### Requirement: Duas colunas por linha, apuradas no mesmo passe

Toda linha do Quadro Principal SHALL apresentar `exercicio_atual` e `exercicio_anterior`. A coluna
do exercício anterior SHALL ser apurada com o **mesmo mapa de regras** do exercício apurado, sobre
os registros do exercício imediatamente anterior. A coluna NÃO DEVE ser copiada do resultado
publicado nem estimada.

#### Scenario: as duas colunas saem da mesma regra

- **GIVEN** `bf.quadro_principal.ingressos.l2`, cujas duas colunas declaram as mesmas contas e os
  mesmos filtros
- **WHEN** a matriz é apurada para o exercício 2025
- **THEN** `exercicio_atual` vem dos registros de 2025 e `exercicio_anterior` dos de 2024
- **AND** as duas usam a edição do IPC 06 vigente para o exercício **apurado**

#### Scenario: exercício anterior sem dados na fonte

- **WHEN** a fonte não tem registros para `exercicio - 1`
- **THEN** `exercicio_anterior` sai não apurada, com o motivo no diagnóstico
- **AND** `exercicio_atual` é apurada normalmente

### Requirement: Coluna do exercício anterior com origem escolhida por quem apura

A coluna do exercício anterior SHALL aceitar duas origens:

1. **`MSCE` do exercício anterior** (padrão) — apurada pelas mesmas regras do IPC 06.
2. **Preenchimento manual**, linha a linha, informado por quem apura.

A segunda existe porque o ente pode ter publicado o exercício anterior com números que a matriz
daquele ano não reproduz: medido em Recife, `L17` e `L50` de 2024 saem 628.456.869,17 da MSC contra
**0,00** publicado.

A procedência SHALL declarar a origem usada. No modo manual, linha não informada SHALL ser `None`
com motivo — nunca zero. Linha informada que o IPC 06 não declara SHALL ser recusada antes de
apurar. A coluna do exercício **atual** NÃO DEVE aceitar preenchimento manual.

#### Scenario: coluna anterior apurada da MSCE do exercício anterior

- **WHEN** a apuração corre com a origem padrão
- **THEN** `exercicio_anterior` vem da matriz do exercício anterior, pelas mesmas regras
- **AND** a procedência declara `msce_exercicio_anterior`

#### Scenario: coluna anterior preenchida manualmente

- **GIVEN** valores informados para parte das linhas
- **WHEN** a apuração corre no modo manual
- **THEN** as linhas informadas trazem o valor informado
- **AND** as demais saem `None`, com `não informado` no diagnóstico
- **AND** a procedência declara `manual`

#### Scenario: linha informada fora do IPC 06

- **WHEN** o preenchimento manual traz um código que a base canônica não declara
- **THEN** a apuração é recusada, nomeando o código

### Requirement: Classes da MSC lidas pelo Balanço Financeiro

A apuração do BF SHALL ler as classes **1, 2, 3, 4, 5 e 6** da MSC, matriz `MSCE` — decisão G9 do
PO em 2026-09-14, confirmada pela medição de 2026-09-18. As classes 7 e 8 NÃO DEVEM ser lidas: o
mapeamento de `L22`, `L23`, `L55` e `L56` não existe no IPC 06, e a busca reversa mostrou que os
valores publicados nessas linhas não estão em conta nenhuma da MSC. O conjunto de classes SHALL ser
declarado na procedência do resultado.

#### Scenario: classes lidas

- **WHEN** a apuração do BF é executada
- **THEN** a fonte é consultada para as classes 1, 2, 3, 4, 5 e 6
- **AND** a procedência declara esse conjunto
- **AND** o BO segue lendo apenas as classes 5 e 6

### Requirement: Tipo de matriz e tipo de saldo declarados no resultado

A apuração SHALL declarar, na procedência, **qual matriz** (`MSCC` | `MSCE`), **qual tipo de saldo**
por linha e **qual competência** produziram os números. Resultado sem essa declaração NÃO DEVE ser
publicado: os mesmos `rule_id` produzem valores diferentes conforme a matriz, e sem a declaração
duas apurações incomparáveis pareceriam a mesma coisa.

O par (matriz, tipo de saldo) SHALL ser tratado como **uma** escolha, propriedade do
demonstrativo, nunca como dois parâmetros independentes. `MSCE` combinada com o saldo de
encerramento SHALL ser recusada no BF com erro explícito, citando que nela as classes 3 e 4 não têm
registro.

O saldo de **abertura do exercício**, que `L29`–`L32` exigem, SHALL vir de
`(ano-1, competência 12, MSCE, abertura)`. Medido em João Pessoa: 1.865.100.624,27, idêntico ao
`(ano-1, competência 12, MSCC, encerramento)` já usado como referência.

#### Scenario: transferências financeiras existem na matriz de encerramento lida pela abertura

- **GIVEN** a competência 12 do exercício apurado
- **WHEN** `L15 Transferências Financeiras Recebidas` e `L48 Concedidas` são apuradas sobre
  `MSCE`/abertura
- **THEN** as duas trazem valor, vindo das classes 4 e 3
- **AND** a procedência declara `MSCE`/abertura

#### Scenario: a matriz de encerramento lida pela abertura é equivalente

- **GIVEN** o BO apurado sobre `MSCC`/encerramento, em Cuitegi/PB e em João Pessoa/PB, 2025
- **WHEN** a mesma apuração é feita sobre `MSCE`/**abertura**
- **THEN** as 337 células saem idênticas nos dois entes, em centavos
- **AND** as classes 3 e 4 trazem os mesmos registros

#### Scenario: o saldo de abertura vem do exercício anterior

- **GIVEN** `L29`–`L32`, que pedem o saldo de abertura do exercício apurado
- **WHEN** o BF de 2025 é apurado
- **THEN** a fonte é consultada em `(2024, competência 12, MSCE, abertura)`
- **AND** o valor de `L30` é 1.865.100.624,27 em João Pessoa
- **AND** NÃO é 2.613.640.800,87, que é a posição pré-encerramento do próprio 2025

#### Scenario: a matriz de encerramento lida pelo encerramento zera as classes de resultado

- **GIVEN** que em Cuitegi/PB 2025 a `MSCE` devolve **0 registros** nas classes 3 e 4, contra 98 e
  40 na `MSCC`
- **WHEN** a mesma apuração é feita sobre `MSCE`
- **THEN** `L16`–`L20` e `L49`–`L53` saem todas zeradas
- **AND** é por isso que a matriz de encerramento é recusada, não escolhida por configuração

#### Scenario: o saldo de caixa não depende do tipo de matriz

- **GIVEN** que em Cuitegi/PB 2025 o caixa da classe 1 é 26.286.597,15 nas duas matrizes
- **WHEN** `L30` e `L63` são apuradas
- **THEN** o valor é o mesmo em `MSCC` e `MSCE`
- **AND** a escolha da matriz não altera as linhas de saldo

#### Scenario: a procedência diz sobre o que foi apurado

- **WHEN** qualquer resultado do BF é produzido
- **THEN** a procedência declara o tipo de matriz, a competência e o tipo de saldo usado por linha
- **AND** dois resultados de matrizes diferentes são distinguíveis sem reapurar

### Requirement: Competência é parâmetro, do mês ao exercício fechado

A apuração SHALL receber a **competência** (mês) como parâmetro, com 12 como padrão, para atender à
periodicidade mensal além da anual. O mês NÃO DEVE ser constante no serviço, na chave de cache nem
no job. Competência sem dados na MSC SHALL produzir `sem_dados` para aquele mês — a apuração NÃO
DEVE cair para dezembro por omissão.

A competência SHALL integrar a identidade do resultado: dois meses do mesmo exercício são
resultados distintos, e NÃO DEVEM compartilhar entrada de cache.

> **Pendente de decisão do PO (G10).** A periodicidade mensal vale para **todos os anexos**, não só
> o BF, e muda o significado do tipo de saldo: num mês qualquer, o saldo de encerramento é posição
> acumulada e a variação do período é o movimento daquele mês. Alcança o BO já entregue e a change
> `plataforma-pipeline-dca` (chave de cache, job, rota).

#### Scenario: apuração de um mês que não é dezembro

- **WHEN** o BF é apurado para a competência 6 de um exercício
- **THEN** a fonte é consultada com `me_referencia=6`
- **AND** a procedência declara a competência 6
- **AND** o resultado não é servido a partir do cache da competência 12

#### Scenario: competência sem dados não cai para dezembro

- **GIVEN** uma competência em que a MSC do ente não tem registro
- **WHEN** a apuração é executada
- **THEN** o diagnóstico traz `sem_dados: true` para aquela competência
- **AND** nenhum valor de outro mês é devolvido no lugar

### Requirement: Linha sem mapeamento não apura, e o total declara o efeito

As seis linhas `review_required` do IPC 06 — `L22`, `L23`, `L28`, `L55`, `L56` e `L61` — SHALL sair
não apuradas, com o motivo citando o bloqueio documental. O total que as agrega SHALL tratá-las
como **parcela inexistente**, somando as demais parcelas, e o diagnóstico SHALL nomear cada linha
bloqueada que participou daquele total. O total NÃO DEVE sair `None` por causa delas, e a linha
bloqueada NÃO DEVE ser apurada como zero.

#### Scenario: total de um grupo inteiramente bloqueado

- **GIVEN** `L21 Outras Movimentações Financeiras Recebidas (III) = (L22 + L23)`, com as duas
  parcelas bloqueadas
- **WHEN** a matriz é apurada
- **THEN** `L21` vale `0,00`, com as duas parcelas nomeadas no diagnóstico
- **AND** `L22` e `L23` permanecem `None`, distinguíveis de zero

#### Scenario: total com parcela bloqueada entre parcelas apuradas

- **GIVEN** `L24 = (L25 + L26 + L27 + L28)`, com `L28` bloqueada
- **WHEN** a matriz é apurada
- **THEN** `L24` é a soma de `L25`, `L26` e `L27`
- **AND** o diagnóstico registra que `L28` não entrou

#### Scenario: bloqueio não vira zero na própria linha

- **WHEN** qualquer das seis linhas bloqueadas é lida na matriz
- **THEN** o valor é `None`
- **AND** o diagnóstico traz o `rule_id`, a coluna e o item do IPC 06 que sustenta o bloqueio

### Requirement: Equilíbrio do Balanço Financeiro conferido e reportado

A apuração SHALL conferir `L33 TOTAL (VI)` contra `L66 TOTAL (XII)` em cada coluna e SHALL
reportar a diferença quando houver. A conferência NÃO DEVE ajustar valor nenhum para forçar o
equilíbrio.

#### Scenario: demonstrativo equilibrado

- **GIVEN** o caso de referência
- **WHEN** a matriz é apurada
- **THEN** `L33` e `L66` são iguais em centavos, nas duas colunas
- **AND** o diagnóstico não registra desequilíbrio

#### Scenario: desequilíbrio é medido, não corrigido

- **GIVEN** uma apuração em que `L33 − L66` é diferente de zero
- **WHEN** o resultado é produzido
- **THEN** o diagnóstico traz a diferença, por coluna, com sinal
- **AND** os dois totais mantêm os valores apurados

### Requirement: Aceite por homologação contra o BF do ente e o RREO

O `tt/dca` **não publica** o Balanço Financeiro — medido em 2026-09-14: 2.002 registros, 7 anexos,
nenhum deles é o BF. O aceite SHALL se apoiar, nesta ordem:

1. **Identidades do próprio demonstrativo** sobre a matriz apurada (`L1 = L2+L3+L11`,
   `L33 = L1+L15+L21+L24+L29`, e as demais): não dependem de ente nenhum e SHALL fechar sempre.
2. **RREO publicado pelo próprio ente** (Anexo 01 e Anexo 07), terceira fonte independente do PDF:
   cobre `L1`, `L34`, `L25`, `L26`, `L58` e `L59`.
3. **BF publicado pelo SIAFIC** dos entes de homologação, com a ressalva de que ele pode ter sido
   alterado na publicação e divergir da matriz que o próprio ente enviou.

Divergência SHALL ser registrada no relatório de auditoria do ente
(`docs/entes-homologacao/<ente>/auditoria-bf-2025.md`), nomeando **linha e coluna** do IPC 06, o
valor apurado e o publicado — nunca corrigida por constante no código nem por alteração de regra
canônica sem citação do IPC 06.

#### Scenario: aceite do caso de referência

- **GIVEN** Recife/PE (2611606), exercício 2025, cujo BF publicado traz as 66 linhas na ordem e na
  nomenclatura do IPC 06
- **WHEN** a apuração do BF é executada contra a MSC
- **THEN** as 24 identidades do demonstrativo fecham em centavos, nas duas colunas
- **AND** `L1`, `L34`, `L25`, `L26`, `L58` e `L59` conferem com o RREO publicado pelo ente
- **AND** cada célula que divergir do BF publicado está no relatório de auditoria

#### Scenario: divergência é registrada, não escondida

- **WHEN** uma célula diverge do publicado
- **THEN** a divergência entra no relatório de auditoria do ente, com linha, coluna, apurado,
  publicado e diferença
- **AND** nenhuma constante de ajuste é introduzida no código

### Requirement: Regra carregada pela vigência e pelo demonstrativo

O carregador SHALL receber o demonstrativo (`bo` | `bf`) além do exercício, e SHALL devolver
apenas as regras da edição vigente daquele demonstrativo. Exercício sem edição que o cubra SHALL
levantar `SemVigencia`, nomeando as edições disponíveis. O `versao_regras` SHALL ser o hash
canônico das regras **daquele** demonstrativo mais as tabelas STN usadas.

#### Scenario: carga do BF

- **WHEN** o mapa do BF é carregado para o exercício 2025
- **THEN** ele traz 80 linhas, todas da edição `2024-06` do IPC 06
- **AND** nenhuma regra do BO entra no mapa

#### Scenario: exercício anterior à edição do IPC 06

- **WHEN** o mapa do BF é pedido para o exercício 2023
- **THEN** `SemVigencia` é levantada, nomeando `2024-06 (desde 2024-06-30)`
- **AND** nenhuma matriz parcial é produzida

#### Scenario: versão de regras é própria de cada demonstrativo

- **WHEN** os mapas do BO e do BF são carregados para o mesmo exercício
- **THEN** os dois `versao_regras` são diferentes
- **AND** uma mudança nas regras do BF não altera o `versao_regras` do BO

### Requirement: Resultado com procedência, diagnóstico e template

O resultado do BF SHALL trazer, além da matriz: `procedencia` (documento, edição, exercício,
`versao_regras`, regras aplicadas, classes lidas e hashes das tabelas STN), `diagnostico`
(não apuradas, bloqueadas, resíduos, desequilíbrio, duração, `sem_dados`) e o template de
apresentação com `rule_id`, `codigo`, `rotulo`, `quadro`, `grupo`, `nivel`, `ordem` e
`totalizadora`, na ordem de publicação do IPC 06. `nivel` e `ordem` SHALL vir da transcrição
normativa, nunca derivados da composição.

#### Scenario: ordem de apresentação do BF

- **WHEN** o resultado é serializado
- **THEN** as linhas saem na ordem Quadro Principal (ingressos, depois dispêndios) e Quadro Anexo
- **AND** `L33` aparece ao fim dos ingressos, não após os dispêndios como no PDF

#### Scenario: diagnóstico vazio é declarado

- **WHEN** nada fica pendente numa apuração
- **THEN** o diagnóstico existe no resultado, com listas vazias
- **AND** não é omitido

### Requirement: Motor único entre Balanço Orçamentário e Balanço Financeiro

O núcleo de modelo, saldo e matriz SHALL ser um só, usado pelos dois demonstrativos. NÃO DEVE
existir cópia do motor por demonstrativo. A apuração do BO SHALL sair **bit a bit igual** à
anterior a esta change.

#### Scenario: regressão do BO

- **WHEN** o caso de referência do BO é reapurado após a unificação do motor
- **THEN** os 11 valores de `docs/validacao-bo-jp-2025.md` saem idênticos, em centavos
- **AND** a suíte inteira do BO passa sem alteração de asserção

#### Scenario: nenhum módulo duplicado

- **WHEN** a árvore `app/domain/` é lida
- **THEN** existe um único módulo de matriz, um de saldo e um de modelo
- **AND** nenhum deles carrega o nome de um demonstrativo específico

### Requirement: Resíduo de classificação medido e reportado no BF

Registro cuja fonte de recursos não caia em nenhuma linha por fonte SHALL ser somado por código e
reportado em `diagnostico.residuos`, com o campo `fonte_recurso`. O resíduo NÃO DEVE ser somado a
nenhuma linha nem descartado em silêncio.

#### Scenario: fonte fora dos subgrupos do IPC 06

- **GIVEN** registros com fonte cujo código principal não pertence a nenhum subgrupo declarado
- **WHEN** a matriz é apurada
- **THEN** eles aparecem em `diagnostico.residuos`, agregados por código
- **AND** `L1` continua sendo exatamente `L2 + L3 + L11`
