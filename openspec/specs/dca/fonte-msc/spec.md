# dca/fonte-msc

> Comportamento acordado e em vigor. Consolidado da change `msc-fonte-e-competencia`,
> aprovada pelo PO em 2026-09-14 e arquivada em `openspec/changes/archive/`.
> Alterações entram por nova change, nunca por edição direta deste arquivo.

## Purpose

Declarar, num só lugar, **de onde** cada demonstrativo da DCA lê os saldos da Matriz de Saldos
Contábeis: qual matriz, qual tipo de saldo e quais classes contábeis. O par (matriz, tipo de saldo)
é norma contábil, não configuração de infraestrutura — e a combinação errada produz demonstrativo
errado sem erro, o que torna "declarar num só lugar" uma exigência de correção, não de estilo.

## Requirements

### Requirement: Par (matriz, tipo de saldo) declarado por demonstrativo e competência

A leitura da MSC SHALL ser determinada pelo **demonstrativo apurado** e pela **competência**.

Na competência 12, conforme a tabela decidida pelo PO em 2026-09-14:

| Demonstrativo | Matriz | Tipo de saldo |
|---|---|---|
| `BO` — Balanço Orçamentário | `MSCE` | abertura |
| `BF` — Balanço Financeiro | `MSCE` | abertura |
| `BP` — Balanço Patrimonial | `MSCE` | **encerramento** |
| `DVP` — Variações Patrimoniais | `MSCE` | abertura |
| `DFC` — Fluxos de Caixa | `MSCE` | abertura |

Nas competências **1 a 11**, todos os demonstrativos SHALL ler `MSCC` pelo saldo de
**encerramento** — a posição acumulada até o mês. A `MSCE` NÃO DEVE ser pedida nesses meses: ela não
existe. Medido em João Pessoa e Cuitegi, 2025, competências 1, 3, 6, 9 e 11 — a matriz de
encerramento não responde em nenhuma, e a consolidada responde em todas.

O par NÃO DEVE ser parâmetro livre de quem chama a apuração. Demonstrativo fora da tabela SHALL
levar a erro explícito, nomeando os conhecidos — NÃO DEVE haver par padrão para o desconhecido.
Competência fora de 1–12 SHALL ser recusada na entrada.

#### Scenario: o Balanço Patrimonial é a única exceção

- **WHEN** a tabela é consultada para `BP`
- **THEN** o tipo de saldo é o de **encerramento**
- **AND** para `BO`, `BF`, `DVP` e `DFC` é o de **abertura**
- **AND** a matriz é `MSCE` nos cinco

#### Scenario: combinação errada é inexprimível

- **WHEN** uma apuração de `BO`, `BF`, `DVP` ou `DFC` é executada
- **THEN** não existe caminho de chamada que leia `MSCE` pelo saldo de encerramento
- **AND** a tentativa de forçá-lo termina em erro explícito, não em leitura silenciosa

#### Scenario: competência mensal usa a matriz consolidada

- **WHEN** a tabela é consultada para `BO` na competência 6
- **THEN** o par é `MSCC` com saldo de **encerramento**
- **AND** para a competência 12 do mesmo demonstrativo o par é `MSCE` com saldo de abertura

#### Scenario: a matriz de encerramento não existe fora de dezembro

- **WHEN** a `MSCE` é pedida para uma competência diferente de 12
- **THEN** a leitura é recusada com erro explícito
- **AND** a apuração NÃO cai para a consolidada em silêncio nem para a competência 12

#### Scenario: valores mensais são acumulados até o mês

- **GIVEN** o BO de Cuitegi/PB 2025
- **WHEN** as competências 3, 6, 9 e 12 são apuradas
- **THEN** as receitas realizadas saem 10.942.851,04, 22.477.392,39, 34.047.498,07 e
  50.723.704,91 — monotônicas, porque cada competência é a posição acumulada
- **AND** a dotação atualizada acompanha as alterações do exercício: 47.880.373,00 em março e
  53.568.335,00 em dezembro

#### Scenario: demonstrativo desconhecido

- **WHEN** a tabela é consultada para um demonstrativo que ela não declara
- **THEN** o erro nomeia os demonstrativos conhecidos
- **AND** nenhum par é devolvido por omissão

### Requirement: Saldo de abertura do exercício vem do exercício anterior

Quando a regra pedir o saldo de **abertura do exercício**, a leitura SHALL ser feita na competência
12 do **exercício anterior**. A leitura na competência 12 do próprio exercício NÃO DEVE ser usada
para isso: na `MSCE` ela é a posição pré-encerramento do exercício corrente, e na `MSCC` é a
abertura de dezembro.

#### Scenario: abertura do exercício em João Pessoa 2025

- **WHEN** o saldo de abertura de `1.1.1` é lido para o exercício 2025
- **THEN** a consulta é `(2024, competência 12, MSCE, abertura)` e devolve 1.865.100.624,27
- **AND** a consulta `(2025, competência 12, MSCE, abertura)` devolveria 2.613.640.800,87, que é
  outra coisa — 748.540.176,60 a mais

### Requirement: Procedência declara de onde os números vieram

Todo resultado apurado SHALL declarar, na procedência: matriz, tipo de saldo, competência e classes
contábeis lidas. A competência é parte da **identidade** do resultado: duas competências do mesmo
exercício são resultados distintos e NÃO DEVEM compartilhar entrada de cache. Resultado sem essa declaração NÃO DEVE ser publicado nem cacheado — dois pares
diferentes produzem valores diferentes para os mesmos `rule_id`, e sem a declaração duas apurações
incomparáveis passam por iguais.

#### Scenario: procedência completa

- **WHEN** qualquer demonstrativo é apurado
- **THEN** a procedência traz matriz, tipo de saldo, competência e a lista de classes
- **AND** dois resultados de pares diferentes são distinguíveis sem reapurar
- **AND** o resultado da competência 6 declara `MSCC`, e o da 12 declara `MSCE`

#### Scenario: competência sem dados não cai para dezembro

- **GIVEN** uma competência em que a MSC do ente não tem registro
- **WHEN** a apuração é executada
- **THEN** o diagnóstico traz `sem_dados: true` para aquela competência
- **AND** nenhum valor de outra competência é devolvido no lugar

### Requirement: Adapters traduzem o par, o domínio não conhece a API

O vocabulário do domínio SHALL ser `matriz` (`consolidada` | `encerramento`) e `tipo_saldo`
(`abertura` | `encerramento` | `periodo`). Cada adapter SHALL traduzir para o que sua API usa —
`co_tipo_matriz` e `id_tv` no SICONFI. O núcleo NÃO DEVE conter os nomes da API.

#### Scenario: tradução no adapter

- **WHEN** o adapter SICONFI recebe `matriz=encerramento` e `tipo_saldo=abertura`
- **THEN** a chamada usa `co_tipo_matriz=MSCE` e `id_tv=beginning_balance`
- **AND** nenhum módulo de `app/domain/` menciona `id_tv` ou `MSCE`

### Requirement: Leitura resiliente a falha de conexão

Os adapters SHALL repetir a chamada com espera crescente quando a conexão cair, e SHALL falhar
explicitamente ao esgotar as tentativas, nomeando classe e offset. Falha de rede NÃO DEVE virar
página faltante — matriz incompleta sem erro é resultado errado que parece certo.

#### Scenario: reset de conexão no meio da paginação

- **GIVEN** uma leitura paginada em que uma das chamadas sofre reset
- **WHEN** o adapter repete com espera crescente e obtém resposta
- **THEN** a coleta continua do mesmo offset, sem pular registros

#### Scenario: tentativas esgotadas

- **WHEN** todas as tentativas falham
- **THEN** o erro nomeia a classe e o offset onde parou
- **AND** nenhuma matriz parcial é entregue ao apurador

## ADDED Requirements

### Requirement: A competência da matriz de encerramento é traduzida por adapter

O domínio SHALL expressar a leitura como **competência (1–12) mais matriz**. O número que cada API
usa para chegar à matriz de encerramento SHALL ser traduzido pelo adapter da fonte, nunca pelo
serviço.

| Fonte | Tradução |
|---|---|
| SICONFI | competência 12 com `co_tipo_matriz=MSCE` — medido: `me_referencia=13` devolve zero registros nos 4 entes de homologação |
| PublicSoft | competência especial **13** (`mesMsc=13` / `meReferencia=13`); 12 é dezembro |

O gate de auditoria da PublicSoft SHALL ser consultado na **mesma** competência que será lida.
Auditar dezembro e ler o encerramento liberaria uma competência com base na validação de outra.

#### Scenario: encerramento na PublicSoft

- **WHEN** a matriz de encerramento é pedida à PublicSoft para a competência 12 do domínio
- **THEN** a consulta de saldos usa `meReferencia=13`
- **AND** a auditoria é consultada com `mesMsc=13`

#### Scenario: consolidada mantém o mês pedido

- **WHEN** a matriz consolidada é pedida para as competências 1, 6 ou 12
- **THEN** a consulta usa o próprio mês
- **AND** 12 significa dezembro

#### Scenario: encerramento no SICONFI

- **WHEN** a matriz de encerramento é pedida ao SICONFI
- **THEN** a consulta usa `me_referencia=12` e `co_tipo_matriz=MSCE`
- **AND** a competência 13 NÃO é pedida a esta fonte
