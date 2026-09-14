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

### Requirement: Sentido do movimento separado por natureza do lançamento

As colunas que declaram `movimento` SHALL somar apenas os lançamentos daquele sentido:
`credor` soma os registros de natureza `C`, `devedor` os de natureza `D`. A leitura SHALL usar a
variação do período, não o saldo acumulado — o saldo líquido não distingue os dois sentidos, e
usá-lo faria `L27` e `L60` devolverem o mesmo número com sinais trocados.

#### Scenario: depósitos restituíveis nos dois sentidos

- **GIVEN** registros da conta `2.1.8.8.0.00.00` com `C` = 300,00 e `D` = 120,00 no período
- **WHEN** `bf.quadro_principal.ingressos.l27` e `bf.quadro_principal.dispendios.l60` são apuradas
- **THEN** `L27` vale 300,00 e `L60` vale 120,00
- **AND** as duas somam **positivamente** em `L24` e `L57`, respectivamente

#### Scenario: nenhuma outra linha usa o sentido do movimento

- **WHEN** a base do BF é carregada
- **THEN** apenas `L27` e `L60` declaram `movimento`
- **AND** as demais linhas somam o saldo da conta na direção do PCASP, como no BO

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

### Requirement: Classes da MSC lidas pelo Balanço Financeiro

A apuração do BF SHALL ler as classes **1, 2, 3, 4, 5 e 6** da MSC, matriz `MSCC`. As classes 7 e 8
NÃO DEVEM ser lidas enquanto as contas de controle de `L22`, `L23`, `L55` e `L56` não tiverem
mapeamento decidido (F1 do IPC 06). O conjunto de classes SHALL ser declarado na procedência do
resultado.

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

#### Scenario: transferências financeiras existem na matriz consolidada

- **GIVEN** a competência 12 do exercício apurado
- **WHEN** `L15 Transferências Financeiras Recebidas` e `L48 Concedidas` são apuradas sobre `MSCC`
- **THEN** as duas trazem valor, vindo das classes 4 e 3
- **AND** a procedência declara `MSCC`

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

### Requirement: Quadro Anexo apurado nas seis colunas

O Quadro Anexo SHALL ser apurado com as seis colunas do IPC 06: `(a)`/`(d)` a receita
orçamentária, `(b)`/`(e)` as deduções e `(c)`/`(f)` calculadas como `(a) − (b)` e `(d) − (e)`.
`L14 TOTAL` SHALL fechar `L1 + L2 + L10` em cada uma das seis.

#### Scenario: saldo do anexo é derivado, não somado

- **GIVEN** `bf.quadro_anexo.l1` com `(a)` = 1.000,00 e `(b)` = 150,00
- **WHEN** a matriz é apurada
- **THEN** `(c)` vale 850,00, calculada da própria linha
- **AND** `L14 (c)` é a soma de `L1 (c)`, `L2 (c)` e `L10 (c)`

#### Scenario: o anexo detalha o que o principal traz líquido

- **GIVEN** o caso de referência
- **WHEN** `bf.quadro_anexo.l14` coluna `(c)` e `bf.quadro_principal.ingressos.l1`
  `exercicio_atual` são comparadas
- **THEN** a diferença entre as duas é registrada no diagnóstico, com o valor medido
- **AND** a comparação não altera nenhum dos dois

### Requirement: Matriz apurada reproduz o publicado do anexo I-D

A matriz do BF SHALL reproduzir, em centavos, os valores publicados do `DCA-Anexo I-D` para o ente
e exercício de referência. Divergência SHALL ser registrada em `docs/validacao-bf-jp-2025.md`, com
a célula, o valor apurado, o publicado e a hipótese — nunca corrigida por constante no código.

#### Scenario: aceite do caso de referência

- **GIVEN** João Pessoa/PB (2507507), exercício 2025
- **WHEN** a apuração do BF é executada contra a MSC
- **THEN** cada célula apurada é igual à publicada no `tt/dca`, anexo I-D, em centavos
- **AND** `L33` é igual a `L66`

#### Scenario: divergência é registrada, não escondida

- **WHEN** uma célula diverge do publicado
- **THEN** a divergência entra no documento de validação, com célula, apurado, publicado e hipótese
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
