# Proposal — Revisar linhas extraorçamentárias do Balanço Financeiro

**Status:** proposta
**Repositório:** `ps-dca`
**Capability:** `dca/balanco-financeiro` (existente)
**Anexo DCA:** Balanço Financeiro (IPC 06), Quadro Principal
**Base normativa:** IPC 06 ed. 2024-06 · layout SICONFI
**Origem:** [SPEC-0001](https://github.com/admsouza/workflow-changes-tasks/blob/main/projetos/ps-dca/specs/dca/SPEC-0001-revisao-linhas-extraorcamentarias-balanco-financeiro.md)

## Why

`L27`, `L28`, `L60` e `L61` são as linhas extraorçamentárias do quadro principal cujo valor a
operação quer rever. `L28` e `L61` continuam `review_required`. A change
`bf-l28-l61-contas-especificas` mediu 15 contas de classe 1 em João Pessoa/2025 e reprovou
(apurado na casa dos R$ 15 mil contra publicado na casa dos R$ 12–13 bilhões). Esse resultado não
serve de regra.

O caso novo é PM Cuitegi, outubro/2025. Os totais esperados são os da SPEC-0001. Sem essa revisão,
Recebimentos Extraorçamentários (IV) e Pagamentos Extraorçamentários (X) seguem sem gabarito neste
ente.

## What Changes

- Revisar a apuração de:
  - `L27` — Depósitos Restituíveis e Valores Vinculados
  - `L28` — Outros Recebimentos Extraorçamentários
  - `L60` — Depósitos Restituíveis e Valores Vinculados
  - `L61` — Outros Pagamentos Extraorçamentários
- Validar o total `L24` Recebimentos Extraorçamentários (IV) = `L25 + L26 + L27 + L28`.
- Validar o total `L57` Pagamentos Extraorçamentários (X) = `L58 + L59 + L60 + L61`.
- A procedência SHALL identificar a origem do valor de `L27`, `L28`, `L60` e `L61`.
- Regra das demais linhas do BF permanece a que já está em `openspec/specs/`. Totalizadora que
  soma uma destas quatro linhas reflete a parcela nova; o restante da fórmula não muda.

**Fora de escopo:** as outras linhas do quadro e do anexo; adotar as 15 contas de classe 1 da
change `bf-l28-l61-contas-especificas`; arquivar ou reabrir aquela change; trocar matriz ou tipo
de saldo do BF inteiro.

## Entradas e saídas

| Interface | Entrada | Saída |
|---|---|---|
| Apuração do BF | ente Cuitegi (`2504801`), caso da SPEC-0001 | `L24` e `L57` do exercício nos totais abaixo; origem de `L27`, `L28`, `L60` e `L61` na procedência |

A competência que corresponde a "outubro/2025" não está fechada (ver design, D1). O contrato HTTP
do `GET /dca/BF` não muda.

## Exemplo concreto

Ente: PM Cuitegi/PB (`2504801`). Caso: outubro/2025, como nomeado na SPEC-0001.

| Grupo | Composição informada | Total esperado |
|---|---|---|
| Receita extraorçamentária → `L24` (IV) | ativo R$ 0,00; passivo R$ 394.823,97 − R$ 7.158,64 | **R$ 387.665,33** |
| Despesa extraorçamentária → `L57` (X) | ativo R$ 1.583,00; passivo R$ 526.127,10 − R$ 7.158,64 = R$ 518.968,46 | **R$ 520.551,46** |

A SPEC-0001 não reparte R$ 387.665,33 entre `L25`, `L26`, `L27` e `L28`, nem R$ 520.551,46 entre
`L58`, `L59`, `L60` e `L61`. Também não diz a que contas "ativo" e "passivo" correspondem.

## Critérios de aceite

- [ ] `L27`, `L28`, `L60` e `L61` revisadas, com a origem de cada valor identificável na procedência.
- [ ] `L24` Recebimentos Extraorçamentários (IV) = R$ 387.665,33 no caso Cuitegi da SPEC-0001.
- [ ] `L57` Pagamentos Extraorçamentários (X) = R$ 520.551,46 no mesmo caso.
- [ ] Nenhuma linha cuja fórmula não dependa destas quatro muda de valor.
- [ ] A lista de contas e a competência só entram depois do PO fechar D1, D2 e D3.

## Casos de erro

| Situação | Comportamento esperado |
|---|---|
| Origem de `L27`, `L28`, `L60` ou `L61` não identificável | a linha não é dada como revisada |
| Valor de `L24` ou `L57` diferente do gabarito, em centavos | aceite reprovado |

## Restrições e riscos

- "Outubro/2025" pode ser a competência 10 ou o exercício 2025. Travar um dos dois sem o PO mede o
  caso errado.
- A change `bf-l28-l61-contas-especificas` permanece bloqueada na medição de João Pessoa/2025.
  As contas dela não são premissa desta proposal.
- `L25`, `L26`, `L58` e `L59` entram nos totais (IV) e (X). Mexer na fórmula delas está fora de
  escopo; o total só fecha se a parcela revisada, somada ao que essas linhas já apuram, bater o
  gabarito.

## Aprovação do PO

- [ ] PO aprovou esta proposta — **gate para a fase PLAN/ARCH**
- [ ] PO fechou D1 (competência), D2 (valor por linha) e D3 (contas)
