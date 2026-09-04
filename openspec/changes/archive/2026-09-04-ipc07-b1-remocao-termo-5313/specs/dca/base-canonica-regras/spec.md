# dca/base-canonica-regras — Delta spec

Remoção do termo `5.3.1.3.0.00.00` da coluna "Inscritos — Em Exercícios Anteriores (a)" do quadro
de RP Não Processados, por decisão do PO de 2026-09-04: a conta foi descontinuada e o que ela
guardava está em `5.3.1.2.0.00.00`, que já é o primeiro termo da mesma fórmula.

Dois requisitos existentes são alterados. **Nenhum requisito é removido e a contagem de cenários
não muda (49):** o cenário `conta 531 histórica é preservada` é substituído por
`a fórmula fica simétrica à do quadro de RP Processados`.

## MODIFIED Requirements

### Requirement: Regra por linha, com o mapa de colunas do quadro

Cada linha de quadro SHALL ser uma regra própria, identificada por `rule_id`, declarando o mapa de
colunas do quadro com as contas do PCASP que compõem cada coluna e o sinal de cada conta na fórmula
do IPC 07 — `+` para termo somado, `-` para termo marcado `(-)`.

A coluna NÃO DEVE declarar conta ausente do PCASP vigente para o exercício. A coluna NÃO DEVE
declarar a mesma conta duas vezes: a apuração soma por conta declarada, sem deduplicar, e a
repetição dobraria o valor. Conta declarada sem escrituração no período SHALL contribuir zero, e
NÃO DEVE tornar a célula não apurada.

Quando um termo do literal do IPC 07 é descontinuado do PCASP e seu conteúdo passa a estar em outra
conta **já declarada na mesma coluna**, o termo SHALL ser removido da regra, e o literal original
SHALL permanecer legível na nota de proveniência.

#### Scenario: coluna com contas de sinal negativo

- **GIVEN** o IPC07 p. 12, quadro de RP Não Processados, coluna
  "Inscritos — Em Exercícios Anteriores (a)", cujo literal é
  `5.3.1.2.0.00.00 + 5.3.1.3.0.00.00 + 5.3.1.6.0.00.00 (-) 6.3.1.6.0.00.00`
- **WHEN** a regra de qualquer linha de filtro desse quadro é lida
- **THEN** a coluna declara **exatamente 3** contas: `5.3.1.2` e `5.3.1.6` com sinal `+`, e
  `6.3.1.6` com sinal `-`
- **AND** `5.3.1.3` NÃO é declarada, por estar descontinuada e ter o conteúdo em `5.3.1.2`
- **AND** o literal de 4 termos permanece legível na nota de proveniência da regra

#### Scenario: a fórmula fica simétrica à do quadro de RP Processados

- **GIVEN** que o quadro de RP Processados declara `5.3.2.2 + 5.3.2.6 (-) 6.3.2.6` na coluna
  homóloga, e que o grupo `5.3.2` não tem `5.3.2.3`
- **WHEN** as colunas "Inscritos — Em Exercícios Anteriores (a)" dos dois quadros são comparadas
- **THEN** ambas declaram 3 contas, nas mesmas posições de família
- **AND** nenhuma regra de `rp_nao_processados` declara `decision: B1`, nem fica
  `review_required`

### Requirement: Decisões do PO são aplicadas com escopo fechado e auditável

Cada decisão do PO SHALL ser aplicada apenas às regras em seu escopo declarado, registrada na
proveniência da regra, e NÃO DEVE deixar a regra em `review_required`. Decisão revogada por decisão
posterior SHALL ter a revogação registrada, e a decisão anterior NÃO DEVE ser apagada do histórico
em `docs/source-analysis-ipc07.md`.

A decisão **B1** de 2026-08-27 — preservar `5.3.1.3.0.00.00` como exceção histórica do PCASP 2019 —
foi **revogada em 2026-09-04**: a conta foi descontinuada e seu conteúdo está em `5.3.1.2.0.00.00`,
já declarada na mesma coluna. Nenhuma regra invoca mais a exceção B1.

A decisão **B3** (`2111/8111`, `2118/8118`, `2121/8121`, `2128/8128`) SEGUE valendo: esses padrões
são usados como `field: conta_contabil` em filtro, não como conta de coluna, e nunca dependeram de
direção de saldo.

#### Scenario: refinanciamento usa padrões de conta PCASP

- **GIVEN** os pares `2111/8111`, `2118/8118`, `2121/8121` e `2128/8128` das exclusões de `L11` e
  dos critérios de `L19`, `L20`, `L22` e `L23`
- **WHEN** essas cinco regras são lidas
- **THEN** os oito códigos são declarados como `field: conta_contabil`
- **AND** as grafias de `L11` e `L19`–`L23` normalizam para os mesmos oito padrões PCASP
- **AND** nenhum candidato de `natureza-receita.md` é aplicado
- **AND** a ausência desses padrões no PCASP atual é registrada como exceção histórica do PCASP
  2019 decidida pelo PO, sem `review_required` por B3
