# Proposal — BP: coluna do exercício anterior pela DCA publicada no SICONFI

**Status:** arquivada (2026-10-07)
**Repositório:** `ps-dca`
**Capability:** `dca/balanco-patrimonial` (existente) · `pipeline/plataforma` (identidade do pedido)
**Anexo DCA:** `DCA-Anexo I-AB` do exercício anterior, lido do `tt/dca`
**Base normativa:** IPC 04, ed. 2020-01 — as mesmas regras de `knowledge/rules/bp/`
**Front:** `front-declaracoes`, change `dca-balanco-patrimonial` (estendida com a escolha da origem)

## Why

No BF, a coluna do exercício anterior tem duas origens à escolha do usuário: a MSC do ano anterior ou
valores informados à mão. O PO quer o mesmo no BP, com outras duas origens: **a MSC** (como hoje) e
**o publicado**, isto é, o `DCA-Anexo I-AB` que o ente declarou ao SICONFI no exercício anterior.

A razão é a do BF: o ente pode ter declarado o exercício anterior com números que a MSC daquele ano
não reproduz. Em Cuitegi 2024, a MSC classifica a dívida ativa não tributária como intra
(`112629900`, 4.826.139,61), e o BP publicado a apresenta como consolidação. O usuário precisa poder
partir do que foi declarado.

**Medido em 2026-10-07** (`tt/dca`, `an_exercicio=2024`, `no_anexo=DCA-Anexo I-AB`):

| Ente | Registros | O que vem |
|---|---|---|
| Cuitegi (`2505204`) | 97 | contas `P1.*` e `P2.*` em hierarquia até o 5º/6º nível (consolidação, intra, inter), `P6.*` (2), `AtivoFinanceiro`, `AtivoPermanente`, `PassivoFinanceiro`, `PassivoPermanente`, `SaldoPatrimonial`, 2 itens de compensação |
| João Pessoa (`2507507`) | 136 | idem, sem itens de compensação |

Coluna única `31/12/2024`, valores com sinal (o PL deficitário vem negativo).

## What Changes

- Parâmetro `origem_exercicio_anterior` no BP: `publicado_siconfi` (**padrão**, decisão do PO) ou
  `msce_exercicio_anterior`. Entra na identidade do pedido (cache).
- **Publicado:** a coluna `exercicio_anterior` é apurada pelas **mesmas regras do IPC 04** sobre as
  contas **folha** publicadas no `I-AB` do ano anterior (conta publicada sem filha publicada), com
  as exclusões intra-OFSS. A coluna anterior fica comparável à atual (decisão do PO).
- **Quadro F/P no publicado:** `L2`, `L3`, `L5` e `L6` recebem `AtivoFinanceiro`,
  `AtivoPermanente`, `PassivoFinanceiro` e `PassivoPermanente` do `I-AB`; o atributo F/P não é
  publicado por conta. `L1`, `L4` e `L7` saem da `calculation`, e `L7` é conferido contra o
  `SaldoPatrimonial` publicado.
- Contas de Compensação e Superávit/Déficit seguem não apurados nas duas origens (P5).
- Procedência declara a origem. Diagnóstico `sem_publicacao_exercicio_anterior` quando o ente não
  publicou o `I-AB` do ano anterior.

**Fora de escopo:** o exercício atual, que continua só da MSC; os itens de compensação que alguns
entes publicam no `I-AB`; mudar o BF.

## Entradas e saídas

| Interface | Entrada | Saída |
|---|---|---|
| `GET /dca/BP` · `POST /dca/BP/reprocessar` | `origem_exercicio_anterior=publicado_siconfi\|msce_exercicio_anterior` (omitido → `publicado_siconfi`) | `procedencia.origem_exercicio_anterior`; `diagnostico.sem_publicacao_exercicio_anterior`; `diagnostico.conferencia_publicado` (`L7` × `SaldoPatrimonial`) |
| `apurar(..., anterior=Anterior.PUBLICADO)` | idem | idem |
| Percurso (`POST /batch-jobs`) | — | BP pela origem padrão (`publicado_siconfi`) |

## Exemplo concreto

Cuitegi/PB (`2505204`), 2025, origem publicado. Coluna 2024 a partir do `I-AB` de 2024:

| Linha | Publicado no I-AB (conta) | Coluna 2024 pelo IPC 04 |
|---|---|---|
| `L3` Caixa | `P1.1.1` = 19.812.433,77 | 19.812.433,77 (sem intra `1.1.1.1.2`) |
| `L10` Realizável LP | `P1.2.1` = 19.307.890,92 | sem `1.2.1.1.2` intra: valor a medir na fase TEST |
| F/P `L2` Ativo Financeiro | `AtivoFinanceiro` | o valor publicado |
| F/P `L7` Saldo Patrimonial | `SaldoPatrimonial` = −57.992.944,30 (PDF) | `L1 − L4`, conferido contra o publicado |

## Critérios de aceite

- [ ] Sem o parâmetro, o BP apura a coluna anterior pelo publicado; com `msce_exercicio_anterior`,
      sai bit a bit igual ao de hoje.
- [ ] Nenhuma conta publicada é contada duas vezes: soma das folhas = valor do grupo publicado, medido
      em Cuitegi e JP 2024 para `P1` e `P2`.
- [ ] Quadro F/P no publicado igual ao `I-AB` em centavos (`L2`, `L3`, `L5`, `L6`), e `L7` conferido.
- [ ] `I-AB` não publicado: coluna anterior `None` + `sem_publicacao_exercicio_anterior: true`. NÃO
      DEVE cair para a MSC por omissão.
- [ ] As duas origens não se misturam no cache.
- [ ] `python -m pytest` e `python -m ruff check .` sem falha nova.

## Casos de erro

| Situação | Comportamento |
|---|---|
| Ente sem `I-AB` publicado no ano anterior | coluna anterior `None` + `sem_publicacao_exercicio_anterior`; coluna atual íntegra |
| `tt/dca` fora do ar | job em erro explícito (retry dos adapters), nunca a MSC no lugar |
| Origem inválida na query | `422` |
| Conta publicada fora do PCASP | entra pela regra por prefixo; sem direção conhecida, a célula fica não apurada (regra vigente) |

## Restrições e riscos

- **Folha publicada:** se o ente publica um grupo e só parte das filhas, a soma das folhas fica menor
  que o grupo. A medição da fase TEST confere isso; havendo diferença, o resíduo vai ao diagnóstico.
- O `I-AB` é a declaração do ente, sem exclusões. Aplicar as exclusões do IPC 04 nele é decisão do PO
  (comparabilidade com a coluna atual), e a coluna anterior não vai bater com o PDF publicado onde
  houver intra.

## Aprovação do PO

- [x] PO pediu em 2026-10-07: duas origens no BP (MSC e publicado), publicado como padrão, regras do
      IPC 04 sobre as contas publicadas
- [x] PO aprovou a proposal em 2026-10-07
