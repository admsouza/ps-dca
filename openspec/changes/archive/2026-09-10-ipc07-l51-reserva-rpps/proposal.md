# Proposal — L51 Reserva do RPPS apurada como L39

**Status:** aprovada pelo PO
**Repositório:** `ps-dca`
**Capability:** `dca/base-canonica-regras` + `dca/balanco-orcamentario` (existentes)
**Anexo DCA:** Balanço Orçamentário (IPC 07)
**Base normativa:** IPC 07 p. 11 REGRAS — `L51 Reserva do RPPS ND 9.9.00.00.00 Função 99.997`
**Fonte da verdade externa:** decisão do PO em 2026-09-10

## Why

A B6 (2026-09-03) deixou `L51` sem coluna de valor: a ESTRUTURA (p. 15) a põe depois de
`TOTAL (XV)` sem marcação. Os filtros da REGRAS (p. 11) ficaram no YAML e **nunca eram aplicados**.
O PO confirmou em 2026-09-10: **calcular L51 como a L39, respeitando o mapeamento**.

Custo de não resolver: Reserva do RPPS some do demonstrativo apurado, embora a MSC classifique
ND `9.9` + função `99` + subfunção `997`.

## What Changes

- `L51` passa a declarar as **6 colunas de despesa** da âncora `*id003` (as mesmas contas da `L39`).
- Filtros permanecem: `natureza_despesa 9.9.00.00.00`, função `99`, subfunção `997`.
- `L51` **não entra** em `L40` nem em `L50` — continua depois do XV.
- B6 fica **restrita a `L27`–`L30`**. A parte “L51 sem coluna” é revogada; o histórico em
  `docs/source-analysis-ipc07.md` permanece.

**Fora de escopo:** alterar `L39`, totais, schema, rota, cache (invalida só via `versao_regras`).

## Entradas e saídas

| Interface | Entrada | Saída |
|---|---|---|
| Apuração do BO | MSC com ND `9.9`, função `99`, subfunção `997` | `matriz[l51]` com as 6 colunas de despesa |
| `GET /dca/BO` | mesmo pedido | célula de `L51` preenchida (zero se sem escrituração) |

## Exemplo concreto

Registro `622130400`, ND `9.9.00.00.00`, função `99`, subfunção `997`, saldo `100,00` →
`L51.pagas = 100,00`. O mesmo valor com subfunção `999` vai para `L39`, não para `L51`.

## Critérios de aceite

- [ ] `L51.columns` idêntico ao de `L39` (âncora `*id003`).
- [ ] Filtros ND / 99 / 997 preservados.
- [ ] `L50` referencia só `L48 + L49`.
- [ ] Fixture com RPPS e contingência: cada valor cai na linha certa.
- [ ] Suíte `pytest` verde; `ruff check .` limpo.

## Casos de erro

| Situação | Comportamento esperado |
|---|---|
| Sem escrituração na classificação | células `0.00`, sem aviso de não apurada |
| Subfunção `999` | não entra em `L51` |

## Restrições

- Sem republicar vigência: `_completar_apresentacao` copia colunas do YAML para semente INSERT-only.
- Sem incluir `L51` no total.

## Decisões

| # | Assunto | Decisão |
|---|---|---|
| D1 | Mapeamento | `columns: *id003`, igual à L39 |
| D2 | Totais | L51 fora de L40 e L50 |
| D3 | B6 | revogada só para L51; L27–L30 intactos |
