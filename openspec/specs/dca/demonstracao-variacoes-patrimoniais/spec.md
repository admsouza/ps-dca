# dca/demonstracao-variacoes-patrimoniais

> Comportamento acordado e em vigor. Mesclado da change `dvp-quadro-principal`, arquivada em
> 2026-10-23. O transporte HTTP e o recorte por unidade gestora têm changes próprias
> (`dvp-no-pipeline`, `dvp-por-unidade-gestora`).
> Alterações entram por nova change, nunca por edição direta deste arquivo.

## Purpose

Apurar o Quadro Principal da Demonstração das Variações Patrimoniais (IPC 05, ed. 2020-01) no mesmo contrato de BO, BP e BF, conferível em centavos contra o `DCA-Anexo I-HI`.

### Requirement: Quadro Principal com dezenove linhas

O sistema SHALL apurar as linhas L1–L19 do Quadro Principal da DVP. L2–L8 e L10–L18 SHALL somar o prefixo de 2º nível declarado na regra. L1, L9 e L19 SHALL ser só `calculation.references`. Nenhuma dessas dezenove regras SHALL declarar `filters` nem `exclusion_groups`.

A coluna Exclusões do IPC 05 (item 22) e o 5º nível = 2 do item 16 NÃO DEVEM reduzir o valor. Motivo medido em 2026-10-23: o `I-HI` de João Pessoa (`2507507`) 2025 traz L6 `4.5` = 11.722.481.279,59 e L14 `3.5` = 9.199.369.111,48; a MSC menos a lista do IPC 05 devolve 3.151.851.371,43 e 628.739.203,32.

#### Scenario: dezenove regras sem exclusão

- **WHEN** `knowledge/rules/dvp/quadro_principal.yaml` é carregado
- **THEN** existem 19 `rule_id` únicos `dvp.quadro_principal.*`
- **AND** nenhuma regra contém `filters` nem `exclusion_groups`

#### Scenario: transferência intra permanece na linha

- **GIVEN** a MSC de João Pessoa (`2507507`), 2025, classe 4, conta em `4.5.1`
- **WHEN** L6 é apurada
- **THEN** o valor inclui essa conta
- **AND** L6 na coluna `exercicio_atual` é 11.722.481.279,59

### Requirement: Mesmo motor e mesma direção de coluna

A DVP SHALL usar o motor de saldo já usado por BO, BP e BF. O saldo de cada conta SHALL ser tomado na direção da coluna. Classe 4 é credora e classe 3 é devedora. Conta de natureza oposta à coluna SHALL reduzir a linha. Conta sem folha no PCASP SHALL herdar a direção do prefixo. Sem direção no prefixo, a célula SHALL ficar não apurada.

#### Scenario: dedução de imposto reduz L2

- **GIVEN** João Pessoa (`2507507`), 2025, `4.1.1.2.1.97` com saldo 1.052.431,74 na direção devedora
- **WHEN** L2 é apurada na direção credora da classe 4
- **THEN** essa conta reduz L2
- **AND** L2 é 397.963.739,37

#### Scenario: conta sintética usa o prefixo

- **GIVEN** Porto Alegre (`4314902`), 2025, movimento em `4.4.2.5.1.00.00`, ausente como folha no `PCASP.md`
- **WHEN** L5 é apurada
- **THEN** a conta entra pela direção do prefixo `4.4`
- **AND** L5 fecha com o `I-HI` em centavos

### Requirement: Duas colunas, matriz de encerramento, saldo de abertura

A coluna `exercicio_atual` SHALL ler o exercício apurado. A coluna `exercicio_anterior` SHALL ler o exercício imediatamente anterior com o mesmo mapa de contas. As duas SHALL usar a matriz de encerramento e o saldo de abertura, classes 3 e 4.

#### Scenario: João Pessoa 2025 fecha o quadro

- **GIVEN** a MSC de encerramento de João Pessoa (`2507507`), 2025, saldo de abertura, classes 3 e 4
- **WHEN** a DVP é apurada
- **THEN** L1 é 17.319.103.824,61
- **AND** L9 é 17.046.926.343,10
- **AND** L19 é 272.177.481,51
- **AND** cada linha-base é igual ao grupo de 2º nível do `DCA-Anexo I-HI` de 2025

#### Scenario: Porto Alegre 2025 fecha os totais

- **GIVEN** a MSC de encerramento de Porto Alegre (`4314902`), 2025
- **WHEN** a DVP é apurada
- **THEN** L1 é 53.603.764.288,49
- **AND** L9 é 54.984.708.163,98
- **AND** L19 é −1.380.943.875,49

#### Scenario: coluna anterior é o I-HI do ano anterior

- **WHEN** a DVP de 2025 de João Pessoa e a de Porto Alegre são apuradas
- **THEN** a coluna `exercicio_anterior` de cada linha-base é igual ao `I-HI` de 2024 do mesmo ente

#### Scenario: linha sem movimento é zero

- **GIVEN** que o `I-HI` de João Pessoa 2025 não publica `3.8` e a MSC de `3.8` é zero
- **WHEN** L17 é apurada
- **THEN** L17 é 0,00

### Requirement: Regressão de BO, BP e BF

A entrada da DVP NÃO DEVE alterar valor de BO, BP nem BF.

#### Scenario: anexos já apurados permanecem iguais

- **WHEN** a suíte de BO, BP e BF roda depois desta change
- **THEN** os cenários que já passavam continuam passando, com os mesmos valores
