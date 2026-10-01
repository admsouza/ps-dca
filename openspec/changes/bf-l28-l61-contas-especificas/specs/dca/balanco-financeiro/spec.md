# dca/balanco-financeiro — Delta spec

## ADDED Requirements

### Requirement: `L28` apurada por soma de lançamentos a crédito

`L28` (Outros Recebimentos Extraorçamentários) SHALL ser apurada somando, mês a mês (competências
1 a 12, `period_change`), apenas os lançamentos de **natureza crédito** das contas:

```
1.1.3.5.2.00.00  1.1.3.5.3.00.00  1.1.3.5.4.00.00  1.1.3.5.5.00.00
1.1.3.8.1.06.00  1.1.3.8.1.08.00  1.1.3.8.1.09.00  1.1.3.8.1.10.00
1.1.3.8.1.11.00  1.1.3.8.1.17.00  1.1.3.8.1.99.00  1.1.3.8.2.17.00
1.1.3.8.2.99.00  1.1.3.8.3.00.00  1.1.3.8.4.00.00
```

O lado devedor desses lançamentos NÃO DEVE ser subtraído — a regra é soma de um lado, não saldo
líquido. Entra só fonte extraorçamentária `860`, `861`, `862`, `863` ou `869` (os 3 dígitos do IPC,
depois de descartar o 1º dígito da MSC). Conta sem escrituração no exercício contribui zero; conta
sem natureza de saldo conhecida no PCASP torna a célula inteira `None`, listada em
`diagnostico.nao_apuradas`.

#### Scenario: L28 soma os créditos de todos os meses

- **GIVEN** lançamentos a crédito nas contas listadas distribuídos entre as competências 1 e 12
- **WHEN** a matriz do BF é apurada
- **THEN** `L28.exercicio_atual` é a soma de todos os lançamentos a crédito dessas contas, nas 12
  competências
- **AND** lançamentos a débito nessas mesmas contas NÃO são subtraídos do total

#### Scenario: L28 ignora fonte fora das extraorçamentárias

- **GIVEN** crédito na conta `1.1.3.5.2` com fonte `1860` e outro com fonte `1500`, no mesmo mês
- **WHEN** `L28` é apurada
- **THEN** só o crédito da fonte `860` entra
- **AND** a fonte `500` não reduz nem aumenta o total

#### Scenario: conta sem escrituração contribui zero

- **GIVEN** uma das contas listadas sem nenhum lançamento no exercício
- **WHEN** `L28` é apurada
- **THEN** essa conta contribui `0,00`, sem tornar a célula `None`

### Requirement: `L61` apurada por soma de lançamentos a débito

`L61` (Outros Pagamentos Extraorçamentários) SHALL ser apurada somando, mês a mês (competências 1 a
12, `period_change`), apenas os lançamentos de **natureza débito** das mesmas 15 contas de `L28`,
nos dois exercícios. O lado credor NÃO DEVE ser subtraído. Entra só fonte extraorçamentária `860`,
`861`, `862`, `863` ou `869`.

`L60` SHALL ser a soma dos débitos de `period_change` das competências 1 a 12, nos dois exercícios,
nas contas `2.1.8.8` e `2.2.8.8`, com o mesmo filtro de fonte. Crédito NÃO entra.

#### Scenario: L61 soma os débitos de todos os meses

- **GIVEN** lançamentos a débito nas contas listadas distribuídos entre as competências 1 e 12
- **WHEN** a matriz do BF é apurada
- **THEN** `L61.exercicio_atual` é a soma de todos os lançamentos a débito dessas contas, nas 12
  competências
- **AND** lançamentos a crédito nessas mesmas contas NÃO são subtraídos do total

#### Scenario: L61 ignora fonte fora das extraorçamentárias

- **GIVEN** débito na conta `1.1.3.8.1.06` com fonte `1860` e outro com fonte `1500`, no mesmo mês
- **WHEN** `L61` é apurada
- **THEN** só o débito da fonte `860` entra
- **AND** a fonte `500` não reduz nem aumenta o total

## MODIFIED Requirements

### Requirement: Linha sem conta declarada no IPC 06 não é apurada

Quatro linhas do quadro principal — `L22`, `L23`, `L55`, `L56` — não têm conta declarada na base
canônica. Por padrão elas SHALL sair **não apuradas** (`None`), com motivo no diagnóstico, e NÃO
DEVEM sair como zero.

`L28` e `L61` deixam de pertencer a este grupo: passam a ter conta declarada e regra de cálculo
própria (ver "L28 apurada por soma de lançamentos a crédito" e "L61 apurada por soma de lançamentos
a débito", acima).

No total que as agrega, a linha não apurada SHALL contribuir como **parcela inexistente** — o total
soma as demais e declara o bloqueio. Propagar `None` até o total deixaria o demonstrativo inteiro em
branco por causa de quatro linhas.

Quem apura MAY completar a coluna **`exercicio_atual`** dessas quatro linhas informando
`valores_sem_mapeamento` no corpo de `POST /dca/BF/reprocessar`. Esse override NÃO É o modo Manual
do exercício anterior e NÃO DEVE exigir `origem_exercicio_anterior: manual`. `L28` e `L61` em
`valores_sem_mapeamento` SHALL ser recusados com `422` — passaram a ter cálculo automático.

#### Scenario: L28/L61 fora da whitelist de override manual

- **GIVEN** corpo com `valores_sem_mapeamento.L28` ou `valores_sem_mapeamento.L61`
- **WHEN** a request é validada
- **THEN** a API responde `422`
- **AND** o mapa G8 (agora com 4 códigos) já salvo NÃO é substituído

## REMOVED Requirements

### Requirement: Linha sem mapeamento não apura, e o total declara o efeito

**Motivo:** este requisito cobria 6 linhas (`L22`, `L23`, `L28`, `L55`, `L56`, `L61`) como
igualmente bloqueadas por falta de conta. `L28`/`L61` saem desse grupo por terem conta e regra
próprias. **Migração:** o comportamento para as 4 linhas restantes (`L22`, `L23`, `L55`, `L56`)
continua coberto pelo requisito "Linha sem conta declarada no IPC 06 não é apurada", acima,
atualizado para 4 linhas; os cenários de total com parcela bloqueada (`L21 = L22 + L23`, `L24 = ...
+ L28`) são re-expressos nesse mesmo requisito, trocando `L28` por uma das 4 linhas remanescentes
onde a composição citava `L28` como exemplo.
