# Proposal — Apuração da Demonstração dos Fluxos de Caixa (F1)

**Status:** implementada e arquivada em 2026-10-27.
**Repositório:** `ps-dca`
**Capability:** `dca/demonstracao-fluxos-caixa` (existente, criada por `ipc08-dfc-regras-canonicas`)
**Anexo DCA:** nenhum — a DFC não é publicada pelo `tt/dca`, como o BO e o BF
**Base normativa:** IPC 08 ed. 2020-01, já transcrita em `knowledge/rules/dfc/` (84 regras)
**Fonte da verdade externa:** não existe espelho. A conferência é a **identidade de caixa** da
própria MSC e o demonstrativo publicado por Porto Alegre.

## Why

As 84 regras existem e estão validadas; nada as executa. A DFC é o quinto demonstrativo e entra
pelo motor que já serve BO, BF, BP e DVP — `MSCE`, saldo de abertura, classes 1 a 6, duas colunas,
`saldo_da_celula` na direção da coluna. O que a DFC traz de novo não é o motor: são três pontos que
**já foram medidos** e que esta change existe para resolver.

## O que a medição de 2026-10-26 encontrou

Mapa das 84 regras aplicado à MSC consolidada de Porto Alegre/RS 2025 (24.214 registros), com o
motor atual e sem escrever serviço nenhum:

| Achado | Medido | Consequência |
|---|---|---|
| **8 linhas não apuram** | `L1`, `L12`, `L17`, `L18`, `L26`, `L27`, `L34`, `L36` saem `não apurada` | a agregadora que referencia uma linha **sem `columns`** (`L16`, `L21`, `L30`) morre inteira: "referências sem coluna em comum" |
| **`L35` lê o exercício errado** | saiu 2.854.802.415,12, que é o caixa **final** de 2025 | o caixa inicial é o `1.1.1` da MSC de **N−1**: 2.785.855.199,20 |
| **`L9` sai zerada** | 0,00 contra 301.239.717,16 publicados | a investigar: filtro de natureza de receita da remuneração das disponibilidades |

A identidade que fecha a DFC existe e é medível **sem o ente**: `1.1.1` em 2025 (2.854.802.415,12)
menos `1.1.1` em 2024 (2.785.855.199,20) = **68.947.215,92**. É o valor que `L34` tem de produzir.
Hoje `L34` nem apura.

## What Changes

- `app/services/dfc/quadro_principal.py` — apuração das 84 linhas, quatro quadros, duas colunas.
- `app/services/dfc/informados.py` — `CODIGOS_SEM_MAPEAMENTO = {"L16", "L21", "L30"}` (D10 da
  change anterior), no padrão de `bf/informados.py`.
- `app/cli/dfc.py` — a DFC verificável sem rota, sem banco e sem container, como os quatro CLIs.
- Totalização das agregadoras no serviço, com as linhas informadas já postas, em vez de deixar o
  motor devolver `não apurada` (D2 abaixo).
- `L35` lendo a MSC de N−1, pelo mecanismo de origem por linha que o BF já usa (D3).

**Fora de escopo:** o transporte HTTP (`dfc-no-pipeline`, espelho de `dvp-no-pipeline`) e o recorte
por unidade gestora com escolha da origem do exercício anterior (`dfc-por-unidade-gestora`). O
motor compartilhado (`app/domain/`) não é alterado. Nenhuma regra YAML muda.

## Entradas e saídas

| Interface | Entrada | Saída |
|---|---|---|
| `apurar(ente, exercicio, fonte, ...)` | MSC `MSCE`/abertura, classes 1–6, exercícios N e N−1 | 84 linhas × 2 colunas |
| `python -m app.cli.dfc <ibge> <exercicio>` | a mesma | matriz impressa, ou `--json` |
| `valores_informados={"L16": "..."}` | digitação do contador | as três linhas sem conta |

## Exemplo concreto

Porto Alegre/RS (`4314902`), 2025, MSC consolidada, com o motor atual:

| Linha | Apurado hoje | Publicado (adm. direta) |
|---|---:|---:|
| L3 Impostos, Taxas e Contribuições | 4.068.529.090,17 | 3.740.394.788,89 |
| L10 Transferências recebidas | 4.888.923.505,51 | 4.180.157.906,76 |
| L14 Juros e encargos | 115.727.775,84 | 115.201.049,07 |
| L35 Caixa inicial | 2.854.802.415,12 **(errado: é o final)** | 1.492.410.149,01 |
| L34 Geração líquida | **não apurada** | 261.360.251,01 |

O publicado é de recorte menor (administração direta × MSC consolidada), como já registrado no BF
do mesmo ente. Por isso o aceite primário é a identidade de caixa, não o PDF.

## Critérios de aceite

- [x] Porto Alegre 2025: `L34` apurado = `68.947.215,92` (variação de `1.1.1` entre as duas MSC),
      com `L16` informado no valor que o fechamento exigir — **a medição que decide a change**.
- [x] `L35` = 2.785.855.199,20 e `L36` = 2.854.802.415,12 (caixa inicial e final da MSC).
- [x] Nenhuma das 84 linhas sai `não apurada` por "referências sem coluna em comum".
- [x] `L14` = 115.727.775,84 e `L32` = 4.278.384,37 (regressão dos valores já medidos em D4).
- [x] As identidades estruturais fecham sobre o apurado, nas duas colunas: `L2 = L3+…+L11`,
      `L12 = L13+…+L16`, `L1 = L2−L12`, `L34 = L1+L17+L26`, `L36 = L34+L35`, `L29` do quadro de
      função, `L4` do de juros, `L7`/`L15` do de transferências.
- [x] As quatro amarrações entre quadros: `P.L10 = T.L7`, `P.L13 = F.L29`, `P.L14 = J.L4`,
      `P.L15 = T.L15`.
- [x] `L9` explicada: ou apura a remuneração das disponibilidades, ou o motivo de 0,00 está medido
      e registrado.
- [x] BO, BF, BP e DVP bit a bit iguais — nenhum arquivo de `app/domain/` alterado.
- [x] `python -m pytest` verde; `python -m ruff check .` limpo.

## Casos de erro

| Situação | Comportamento esperado |
|---|---|
| `L16`/`L21`/`L30` não informadas | `0,00` na agregadora e a célula marcada como informável — nunca contaminar a linha-total |
| Exercício anterior sem MSC | `L35` não apurada, no contrato de BP/BF/DVP; `L36` idem |
| Conta sem direção no PCASP | célula inteira não apurada (`None`), nunca zero |
| Fonte sem nenhum registro | coluna não apurada e `sem_dados` no diagnóstico |

## Restrições e riscos

- **`L34` pode não fechar.** `L11` e `L16` são 58,4% e 62,6% do movimento em Porto Alegre e não
  têm mapa fechado: `L11` tem duas naturezas ausentes da tabela STN e `L16` não tem conta. Se a
  diferença não couber em `L16`, o mapa de `L11` é o próximo suspeito, e a decisão volta ao PO.
- A DFC publicada tem ingressos de 20,3 bi contra receita orçamentária de 8,7 bi no BF do mesmo
  ente: há movimento extraorçamentário que nenhuma natureza orçamentária alcança.
- Comparar com o PDF de Porto Alegre mistura recortes. Vale como ordem de grandeza, não como
  aceite.

## Gates

| Gate | Artefato |
|---|---|
| SPEC | este arquivo e `specs/dca/demonstracao-fluxos-caixa/spec.md` |
| PLAN/ARCH | `design.md` (D1–D6) e `tasks.md` |
| TEST | teste do cenário antes do código — `tasks.md` §1 |
| IMPLEMENT | `tasks.md` §2, só depois do teste falhar pelo motivo esperado |
| REVIEW | `git diff` — `tasks.md` §3 |
| VERIFY | pytest, ruff, cenários medidos — `tasks.md` §4 |

## Aprovação do PO

- [x] PO aprovou em 2026-10-27 — "vamos concluir o backend do DFC"
