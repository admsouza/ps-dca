# Proposal — Contas específicas para L28/L61 por crédito e débito mensal

**Status:** proposta
**Repositório:** `ps-dca`
**Capability:** `dca/balanco-financeiro` (existente)
**Anexo DCA:** Balanço Financeiro (IPC 06), Quadro Principal
**Base normativa:** IPC 06 ed. 2024-06, item 29 p. 9 ("contas sob demanda — cabe a cada ente
adaptá-las"); layout SICONFI
**Change relacionada:** `bf-completar-nao-apuradas-g8` — **já arquivada e implementada**
(`openspec/changes/archive/2026-10-01-bf-completar-nao-apuradas-g8/`); esta proposal reduz seu
escopo em produção, de código e de spec mesclada, não apenas de um rascunho

## Why

`L28` (Outros Recebimentos Extraorçamentários) e `L61` (Outros Pagamentos Extraorçamentários) são
2 das 6 linhas `review_required` do IPC 06 sem conta declarada na base canônica. Hoje elas só saem
do `None` por `valores_sem_mapeamento` (`bf-completar-nao-apuradas-g8`): o operador digita o valor
à mão, todo exercício, sem o sistema calcular nada.

A operação definiu as contas e a regra de cálculo para este ente: soma dos lançamentos a CRÉDITO
(L28) e a DÉBITO (L61) das mesmas 16 contas, mês a mês (`period_change`, competências 1 a 12).
Mapeando a regra, as duas linhas passam a ser apuradas automaticamente, como as outras 64 linhas do
BF, e saem da lista de override manual.

## What Changes

- Mapear `L28` (ingressos): soma dos valores a **crédito** dos meses 1 a 12 (`period_change`) das
  16 contas listadas abaixo.
- Mapear `L61` (dispêndios): soma dos valores a **débito** dos meses 1 a 12 (`period_change`) das
  mesmas 16 contas.
- `status` das regras `bf.quadro_principal.ingressos.l28` e `bf.quadro_principal.dispendios.l61`
  passa de `review_required` para `extracted`.
- Remover `L28` e `L61` da whitelist `CODIGOS_SEM_MAPEAMENTO` de `bf-completar-nao-apuradas-g8`
  (G8 cai de 6 para 4 linhas: `L22`, `L23`, `L55`, `L56`).
- Novo modo de leitura da MSC para estas 2 linhas: somar `period_change` (`TipoSaldo.PERIODO`) de
  cada uma das 12 competências do exercício, por conta — distinto do padrão atual do BF (1 leitura
  de snapshot na competência de encerramento, ver `app/infra/msc/fonte.py:52-58`).

**Contas (L28 e L61 — mesma lista, direção pela natureza do lançamento, não pela conta):**

```
1.1.3.5.2.00.00  1.1.3.5.3.00.00  1.1.3.5.4.00.00  1.1.3.5.5.00.00
1.1.3.8.1.06.00  1.1.3.8.1.08.00  1.1.3.8.1.09.00  1.1.3.8.1.10.00
1.1.3.8.1.11.00  1.1.3.8.1.17.00  1.1.3.8.1.99.00  1.1.3.8.2.17.00
1.1.3.8.2.99.00  1.1.3.8.3.00.00  1.1.3.8.4.00.00
```
(15 contas distintas na lista recebida — o enunciado original cita "16"; conferir com o PO se falta
uma conta antes de fechar a regra.)

**Fora de escopo:** recalcular `exercicio_anterior` com `period_change` (mantém o snapshot de
abertura, como hoje); as outras 4 linhas do G8 (`L22`, `L23`, `L55`, `L56`); mudar o par
matriz/tipo-saldo do BF para as demais 64 linhas.

## Entradas e saídas

| Interface | Entrada | Saída |
|---|---|---|
| `GET /dca/BF` | sem mudança de payload | `L28.exercicio_atual` e `L61.exercicio_atual` calculados (antes: `None` ou valor de override G8) |
| `POST /dca/BF/reprocessar` com `valores_sem_mapeamento` contendo `L28` ou `L61` | — | `422` — código fora das 4 linhas G8 restantes |

## Exemplo concreto

| Ente | Exercício | Célula | Valor esperado |
|---|---|---|---|
| *(pendente — a definir com o PO: ente e exercício de homologação)* | | `L28` / `exercicio_atual` | *(medir contra BF publicado antes de fechar `status: extracted`)* |

## Critérios de aceite

- [ ] No ente de homologação escolhido, `L28` = soma a crédito das contas listadas, meses 1–12.
- [ ] `L61` = soma a débito das mesmas contas, mesmo critério.
- [ ] `diagnostico.nao_apuradas` deixa de listar `L28`/`L61` quando as 16(?) contas têm escrituração.
- [ ] `POST /dca/BF/reprocessar` com `L28` ou `L61` em `valores_sem_mapeamento` → `422`.
- [ ] Suíte completa (`python -m pytest`) e auditoria dos entes de homologação sem regressão nas
      outras 64 linhas do BF.

## Casos de erro

| Situação | Comportamento esperado |
|---|---|
| Conta sem natureza de saldo no PCASP | célula `None`, listada em `nao_apuradas` (padrão já existente) |
| `L28`/`L61` em `valores_sem_mapeamento` | `422` — linha fora da whitelist G8 reduzida |

## Restrições e riscos

- O campo `movimento: credor|devedor` já usado no YAML de L27/L60 **não é lido pelo motor hoje**
  (confirmado: nenhuma referência em `app/infra/regras/carregador.py`) — é só anotação transcrita
  do IPC 06. A regra de "somar só crédito" / "somar só débito" por lançamento precisa de uma função
  nova no motor (`app/domain/bo/saldo.py`), não existe hoje: `saldo_da_conta` sempre faz a
  subtração líquida pela direção da conta no PCASP, nunca "soma só um lado".
- Ler `period_change` mês a mês é uso novo no BF: até 12 chamadas à MSC só para estas 2 linhas —
  impacto de latência/limite de API a medir antes de ativar em produção.
- `bf-completar-nao-apuradas-g8` está **arquivada e implementada em produção** (código em
  `app/services/bf/informados.py:24`, spec mesclada em `openspec/specs/dca/balanco-financeiro/spec.md:162-231`)
  com as 6 linhas, aprovada pelo PO em 2026-09-24 — reduzir para 4 linhas altera comportamento já
  entregue e exige confirmação explícita do PO, não é unilateral.

## Aprovação do PO

- [x] PO aprovou esta proposta em `2026-10-01` — **gate para a fase PLAN/ARCH**
- [x] PO confirmou a redução de escopo de `bf-completar-nao-apuradas-g8` (6 → 4 linhas G8)
- [x] PO confirmou a lista de 15 contas (não são 16)

## Medição (4.3 de tasks.md)

**Reprovada.** João Pessoa/2025, API SICONFI real, 2026-10-01:

| Linha | Apurado (15 contas, classe 1) | Publicado | Diferença |
|---|---|---|---|
| `L28` | R$ 15.251,40 | R$ 13.227.595.529,71 | ~6 ordens de grandeza |
| `L61` | R$ 15.005,24 | R$ 12.295.961.584,22 | ~6 ordens de grandeza |

As 15 contas de classe 1 (ativo) informadas não são a fonte real de L28/L61 neste ente — motor,
YAML e whitelist G8 estão implementados e testados (ver `tasks.md`), mas `status` permanece
`review_required` até o PO revisar a lista de contas. Pista não testada, já registrada no YAML
antes desta change: `classes 7/8` (controle devedor/credor do PCASP, IPC 06 item 20 (e)).
