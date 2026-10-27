# Proposal — `L25` é residual: não repete o que `L23` e `L24` já contaram

**Status:** proposta — aprovada pelo PO em 2026-10-27.
**Repositório:** `ps-dca`
**Capability:** `dca/demonstracao-fluxos-caixa`
**Base normativa:** IPC 08 ed. 2020-01, p. 10 (`L23`, `L24`, `L25`)

## Why

Medido contra Cuitegi/PB 2025 — ente **consolidado**, mesmo recorte da MSC
(`docs/entes-homologacao/cuitegi/auditoria-dfc-2025.md`, achado A1):

| Linha | Apurado | Publicado |
|---|---:|---:|
| `L23` Aquisição de ativo não circulante | 1.791.501,94 | 1.791.501,94 ✔ |
| `L25` Outros desembolsos de investimentos | **1.791.501,94** | **0,00** |
| `L22` Desembolsos (investimento) | **3.583.003,88** | **1.791.501,94** |

A mesma despesa entra nas duas linhas. `L23` filtra por **elemento** (`4.4.xx.51.xx`,
`4.4.xx.52.xx`, `4.4.xx.61.xx`…); `L25` filtra `4.4.xx.xx.xx` + `4.5.xx.xx.xx` e exclui por
**modalidade** (`4.4.36`, `4.4.40`, `4.4.41`…). A lista de exclusões de `L25` não cobre os
elementos de `L23`, e a despesa de Cuitegi é modalidade 90 — que nenhuma exclusão alcança.

**A transcrição está fiel ao PDF** (conferido em `knowledge/sources/ipc08/extracted.md`, p. 10): a
dupla contagem está no IPC 08 lido ao pé da letra. O ente a resolve publicando `L25` = 0,00.

## What Changes

- `L25` passa a ser apurada **sobre os registros que não entraram em `L23` nem em `L24`**, pelo
  mecanismo `registros_por_regra` que o serviço já usa para `L35`.
- Nenhuma regra YAML muda: os filtros do IPC 08 continuam como estão, e a exclusão mútua é
  decisão de apuração, registrada aqui.

**Fora de escopo:** os achados A2 (intragovernamentais), A3 (`L32`/`L33`) e A4 (`L13`/`L15`) da
mesma auditoria. `L11` e `L16` do Quadro Principal, que têm a mesma forma de "Outros", não mudam:
`L16` é campo informado (D10) e `L11` tem lista própria de naturezas, sem sobreposição medida.

## Por que não subtrair os totais

`L25 = L25_bruto − L23 − L24` **daria negativo**: `L23` captura o elemento 51 de **qualquer**
modalidade, inclusive `4.4.50.51`, cuja modalidade 50 está excluída de `L25`. Esse registro está
em `L23` e não em `L25_bruto` — subtrair o total de `L23` tiraria o que nunca entrou.

A exclusão tem de ser **por registro**: `L25` recebe o conjunto de registros menos os que atendem
aos filtros de `L23` ou de `L24`.

## Critérios de aceite

- [x] Cuitegi 2025: `L25` = 0,00 e `L22` = 1.791.501,94, iguais ao publicado.
- [x] `L23` e `L24` inalterados em todos os entes.
- [x] `L25` nunca negativa por construção.
- [x] Nenhum YAML de regra alterado.
- [x] BO, BF, BP e DVP bit a bit iguais; suíte verde; `ruff` limpo.

## Aprovação do PO

- [x] PO aprovou abrir em 2026-10-27, após a auditoria de Cuitegi
