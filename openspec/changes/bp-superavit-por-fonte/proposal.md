# Proposal — Superávit / Déficit Financeiro por fonte

**Status:** em implementação (PO aprovou em 2026-10-08)
**Repositório:** `ps-dca`
**Capability:** `dca/balanco-patrimonial` (existente)
**Anexo DCA:** `DCA-Anexo I-AB` — Quadro do Superávit / Déficit Financeiro
**Base normativa:** MCASP · IPC 04 ed. 2020-01, p. 13 (`docs/referencia/ipc/IPC04 - BP atualizacao - 20200117.pdf`) · PCASP `8.2.1.1.1` · `docs/contas-stn/fonte-recursos.md` · `docs/contas-stn/complemento-fonte.md`

## Why

O quadro sai inteiro não apurado. A regra publicada é só o total, com blocker: a cardinalidade depende do ente. O relatório do ente é uma linha por fonte e complemento, com o saldo da conta `8.2.1.1.1`. Sem isso o BP não reproduz o quadro da Lei 4.320/64.

## What Changes

- O quadro deixa de devolver `None`. Cada fonte com saldo em `8.2.1.1.1` vira uma linha.
- O código da linha tem 8 dígitos: fonte da MSC (4) + complemento (4). Complemento ausente vale `0000`.
- O saldo da linha é `C − D` das folhas `821110100` e `821110200`. Superávit positivo, déficit negativo.
- A coluna do exercício é o saldo de encerramento desse ano. A coluna anterior é o mesmo saldo no exercício anterior.
- Fonte que começa com `2` entra (`25000000` e as demais). O PO corrigiu em 2026-10-08: a exclusão anterior foi engano.
- O total é a soma das linhas que entraram.
- As duas visões (`isolado` e `consolidado`) trazem o mesmo quadro.
- Contas de Compensação continuam não apuradas.

**Fora de escopo:** BO, BF e os outros quadros do BP; uma regra YAML por fonte.

## Entradas e saídas

| Interface | Entrada | Saída |
|---|---|---|
| Apuração do BP (job e `python -m app.cli.bp`) | MSC de encerramento, classe 8, exercícios N e N−1; `fonte_recursos` e `complemento_fonte` | Matriz do quadro `SUPERAVIT_DEFICIT`: uma linha por fonte+complemento com saldo, mais `Total` |
| `GET /dca/BP` | cache do BP, `visao` | O mesmo quadro nas duas visões |

## Exemplo concreto

Ente Cuitegi/PB (`2505204`), exercício 2025, SICONFI, matriz de encerramento, saldo final. O total de 2024 (`13.279.106,25`) é o do relatório PublicSoft impresso em 07/10/2026 e só fecha com as fontes `2…` incluídas.

| Ente | Exercício | Célula | Valor esperado |
|---|---|---|---|
| 2505204 | 2025 | `17500000` exercício atual | 12.879,61 |
| 2505204 | 2025 | `17500000` exercício anterior | 835,46 |
| 2505204 | 2025 | `18020000` exercício atual | 61.862,85 |
| 2505204 | 2025 | `18020000` exercício anterior | (212.922,03) |
| 2505204 | 2025 | `15010000` exercício anterior | 715.372,64 |
| 2505204 | 2025 | `25000000` exercício atual | (15.855,84) |
| 2505204 | 2025 | `25000000` exercício anterior | (1.984.731,88) |
| 2505204 | 2025 | `Total` exercício atual | 48.827.308,73 |
| 2505204 | 2025 | `Total` exercício anterior | 13.279.106,25 |

## Critérios de aceite

- [ ] Cuitegi 2025: `17500000`, `18020000` e `25000000` batem os valores da tabela, em centavos.
- [ ] `Total` = 48.827.308,73 no exercício e 13.279.106,25 no anterior.
- [ ] Linha com as duas colunas zeradas não aparece.
- [ ] Isolado e consolidado devolvem o mesmo quadro.
- [ ] Compensação permanece `None`.

## Casos de erro

| Situação | Comportamento esperado |
|---|---|
| Classe 8 sem saldo em `82111` | Nenhuma linha de fonte; `Total` = 0,00 nas duas colunas |
| Fonte vazia com saldo | Linha `00000000` entra; o saldo não é descartado |
| Complemento ausente | Tratado como `0000` |
| Leitura da MSC do ano anterior vazia | Coluna anterior 0,00 nas linhas que só têm saldo no exercício; diagnóstico de exercício anterior segue o do BP |

## Restrições e riscos

- A leitura atual do BP não pede a classe 8 e descarta `complemento_fonte`. Sem os dois, o quadro não fecha.
- A origem `publicado_siconfi` da coluna anterior do Quadro Principal não substitui este quadro: o `I-AB` não abre por fonte.
- Em 2025, Cuitegi tem 3.840.319,73 na conta sem fonte (`00000000`). Entra no total. O impresso não mostra essa linha no trecho conferido.

## Aprovação do PO

- [x] PO aprovou esta proposta em 2026-10-08 — **gate para a fase PLAN/ARCH**
