# pipeline/plataforma — Delta spec

## Purpose

Servir o Balanço Financeiro pelo mesmo pipeline do Balanço Orçamentário — rota, cache, job e
resumo — sem que a plataforma aprenda regra contábil nenhuma. O que esta capability ganha é a
capacidade de transportar um demonstrativo que lê **mais de uma origem de saldo** e apresenta
**mais de uma coluna** por linha.

## ADDED Requirements

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

A identidade do resultado cacheado SHALL incluir a **origem da coluna do exercício anterior** e,
quando ela for o preenchimento manual, a identidade do conjunto informado. Dois pedidos que
diferem nisso SHALL ser resultados distintos e NÃO DEVEM compartilhar entrada de cache.

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
