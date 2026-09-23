# Proposal — Exercício anterior manual persiste na unidade

**Status:** em implementação
**Repositório:** `ps-dca`
**Capability:** `dca/balanco-financeiro` (existente) e `pipeline/plataforma` (existente)
**Anexo DCA:** Balanço Financeiro (IPC 06)
**Base normativa:** IPC 06, ed. 2024-06 — a coluna do exercício anterior não é calculável quando o publicado não sai da MSC
**Fonte da verdade externa:** n/a (persistência do que o usuário informou; a regra da coluna continua a da spec do BF)
**Change irmã:** `front-declaracoes` / `bf-anterior-manual-persistido`

## Why

Quem preenche a coluna do exercício anterior no modo manual perde o preenchimento no processamento seguinte. O mapa vive no `sessionStorage` da aba e viaja na query de `GET /dca/BF`. O cache tem uma linha por ente, exercício e anexo: um pedido sem o mapa (reprocessar no diálogo, leitura depois do job, `POST /batch-jobs`) não reconhece essa linha e grava por cima o resultado da MSC.

O custo é duplo. O ente redigita dezenas de células. Os valores ficam em log de acesso, histórico e `Referer`.

## What Changes

- Gravar o mapa informado em `procedencia.valores_anteriores` da linha de cache do BF que já existe.
- Pedido do BF **sem** origem reaplica esse mapa. A coluna do exercício anterior sai dele. O exercício corrente é recalculado na MSC.
- Só `origem_exercicio_anterior=msce_exercicio_anterior` explícito deixa de reaplicar e apaga o mapa.
- A gravação do mapa é `POST`, no corpo. `valores_anteriores` na query é recusado.

**Fora de escopo:** tabela nova; histórico de edições; preenchimento manual do exercício corrente; mudar a fórmula do IPC 06.

## Entradas e saídas

| Interface | Entrada | Saída |
|---|---|---|
| `POST /dca/BF/reprocessar` | query: `anReferencia`, `id_ente`; corpo JSON `{ "origem_exercicio_anterior": "manual", "valores_anteriores": { "<código>": "<decimal>" } }` | `202` com `job_id`. Ao fim, a linha de cache traz a coluna anterior com esses valores e `procedencia.valores_anteriores` igual ao corpo |
| `GET /dca/BF` | query: `anReferencia`, `id_ente`. Sem mapa | `200` com a coluna anterior igual à última gravação manual, quando houver mapa salvo |
| `POST /dca/BF/reprocessar` e `POST /batch-jobs` | sem origem e sem mapa | reapura o corrente na MSC e mantém a coluna anterior do mapa salvo |
| `POST /dca/BF/reprocessar` | query `origem_exercicio_anterior=msce_exercicio_anterior`, sem mapa | apaga o mapa; a coluna anterior volta a sair da MSC do exercício anterior |

Autorização das quatro chamadas: a mesma das rotas de anexo (`Authorization` e unidade do ente).

## Exemplo concreto

| Ente | Exercício | Célula | Valor esperado |
|---|---|---|---|
| 2611606 — Recife | 2025 | `L17` / `exercicio_anterior` | `628456869.17` informado no corpo. Depois de `GET /dca/BF` e de `POST /batch-jobs` sem mapa, a mesma célula continua `628456869.17` |

Esse é o valor publicado de Recife em 2024 que a MSC não reproduz (spec do BF: a MSC devolve 0,00).

## Critérios de aceite

- [ ] Recife/2025, `L17` informada como `628456869.17`: após o job, a célula é esse valor e `procedencia.origem_exercicio_anterior` é `manual`.
- [ ] `GET /dca/BF` seguinte, sem mapa na request, devolve a mesma célula.
- [ ] `POST /batch-jobs` sem mapa mantém a célula. O exercício corrente pode mudar; a coluna anterior não.
- [ ] MSC explícito: a célula deixa de ser `628456869.17` e a procedência passa a `msce_exercicio_anterior`.
- [ ] Código fora do IPC 06 responde `422` e a linha de cache anterior permanece.
- [ ] `valores_anteriores` na query responde `400` e não apura.

## Casos de erro

| Situação | Comportamento esperado |
|---|---|
| Código de linha fora do IPC 06 | `422`, nomeando o código; mapa já salvo permanece |
| Valor que não é decimal | `422`; mapa já salvo permanece |
| `valores_anteriores` na query | `400`; não apura e não grava |
| Job do BF falha depois de um mapa já salvo | a procedência com o mapa permanece; o próximo pedido sem origem ainda o reaplica |
| BF sem mapa salvo e sem origem | coluna anterior sai da MSC, como hoje |

## Restrições e riscos

- Sem migration. O mapa cabe no JSONB `procedencia` que a linha já tem.
- O front atual manda o mapa na query. Esta change quebra esse caminho de propósito; a change irmã no `front-declaracoes` passa a usar o `POST`.
- Falha de job não pode zerar `procedencia`: é onde o mapa mora.

## Aprovação do PO

- [ ] PO aprovou esta proposta em ______ — **gate para a fase PLAN/ARCH**
