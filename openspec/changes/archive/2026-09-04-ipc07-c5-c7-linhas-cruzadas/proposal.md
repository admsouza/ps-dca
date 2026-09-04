# Proposal — C5 (linhas cruzadas receita × despesa) e C7 (previsão inicial de `L29`)

**Status:** proposta
**Repositório:** `ps-dca`
**Capability:** `dca/base-canonica-regras` (existente) + delta em `dca/balanco-orcamentario` (change ativa)
**Anexo DCA:** `n/a` — Balanço Orçamentário do IPC 07, publicado como `RREO-Anexo 01`
**Base normativa:** IPC 07 edição 2020-01, p. 9–10 · `RREO-Anexo 01` de 2025, `nr_periodo=6`
**Fonte da verdade externa:** API `tt/rreo` do SICONFI

## Why

Duas pendências travam a change do BO: **C5** deixa 4 linhas sem apurar e 3 testes vermelhos;
**C7** é a última divergência de valor contra o STN. As duas nasceram como "o IPC 07 não diz", e
**as duas foram medidas** contra o publicado do STN — deixaram de ser interpretação.

- **C5** (`docs/evidencia-c5-deficit-superavit.md`): `L25`, `L26`, `L49` e `L50` cruzam os blocos de
  receita (4 colunas) e despesa (6), que não têm coluna em comum. O IPC 07 não diz em qual coluna
  são apresentadas. O STN publica, e a prática foi medida nas duas metades.
- **C7** (`docs/evidencia-c6-c7.md`): `L29` Superávit Financeiro sai com previsão inicial de
  R$ 470.338.332,64 e leva `L27` a 482.338.332,64 contra 12.000.000,00 do STN. **Zero de 25 entes**
  publicam `PREVISÃO INICIAL` para `SuperavitFinanceiro`.

**Custo de não resolver:** a change do BO não arquiva, a suíte nunca fica verde, e a F2 fica atrás
de uma decisão que a evidência já respondeu.

## What Changes

### C5 — as 4 linhas passam a ser apuradas

Medido, e **assimétrico** entre as metades:

| Linha | Colunas | Fórmula por célula |
|---|---|---|
| `L25` Déficit (VI) | `receitas_realizadas` (1) | `L48.empenhadas − L24.receitas_realizadas`, se positivo |
| `L26` TOTAL (VII) | `previsao_inicial`, `previsao_atualizada`, `receitas_realizadas` (3) | `L24.<coluna> + L25.<coluna>` |
| `L49` Superávit (XIV) | `empenhadas`, `liquidadas`, `pagas` (3) | `L24.receitas_realizadas − L48.<coluna>`, se positivo |
| `L50` TOTAL (XV) | `dotacao_inicial`, `dotacao_atualizada`, `empenhadas`, `liquidadas`, `pagas` (5) | `L48.<coluna> + L49.<coluna>` |

Nenhuma das quatro tem coluna de saldo — o STN não publica `SALDO (a-c)` em
`TotalReceitasComDeficit` nem `SALDO (g)`/`SALDO (i)` em `TotalDespesasComSuperavit`.

Isso exige **duas** capacidades novas:

1. **Referência cruzada em coluna.** `L49.empenhadas` lê `L24.receitas_realizadas` — coluna de nome
   diferente da que está sendo calculada. Hoje a agregação lê sempre a mesma coluna em todas as
   referências, então declarar as colunas não bastaria: buscaria `L24.empenhadas`, que não existe.
2. **Linha suprimida por condição contribui zero, e se apresenta em branco.** Medido: em ente
   deficitário o STN deixa `Superavit` em branco **e publica** `TotalDespesasComSuperavit` igual a
   `TotalDespesas` (SP e GO, exatos). Simétrico em ente superavitário. Hoje a condição grava `None`
   e a agregação propaga `None` como indeterminado — os totais sairiam em branco, contra o
   publicado. E a condição roda **depois** da agregação, então o total somaria o valor cru.

### C7 — `L29` perde a coluna de previsão inicial

`L29` deixa de declarar `previsao_inicial`. `L27 = L28 + L29 + L30` passa a valer 12.000.000,00
nessa coluna, batendo com o STN.

**Fora de escopo:**

- A coluna "NO BIMESTRE" e os percentuais `% (b/a)` / `% (c/a)` do `RREO-Anexo 01` — o BO do IPC 07
  não os tem, e a DCA é anual.
- Qualquer alteração nas tabelas de `docs/contas-stn/`.
- A ressalva de preenchimento do ente (PB não publicou `Deficit` tendo empenhada acima da receita):
  é dado do ente, não regra.

## Entradas e saídas

| Interface | Entrada | Saída |
|---|---|---|
| `carregar(exercicio)` → `MapaBO` | exercício | `L25`/`L26`/`L49`/`L50` com colunas declaradas e referências que podem nomear a coluna lida |
| `apurar(ente, exercicio, fonte)` | ente, exercício | as 4 linhas apuradas; célula suprimida por condição sai em branco, e os totais que a agregam saem com valor |

## Exemplo concreto

| Ente | Exercício | Célula | Valor esperado |
|---|---|---|---|
| 2507507 — João Pessoa (superavitário) | 2025 | `L49.empenhadas` | **R$ 267.518.451,03** |
| 2507507 — João Pessoa | 2025 | `L49.liquidadas` · `L49.pagas` | 548.825.560,55 · 588.080.763,22 |
| 2507507 — João Pessoa | 2025 | `L50.empenhadas` | **R$ 5.117.875.296,33** = receita realizada |
| 2507507 — João Pessoa | 2025 | `L25.receitas_realizadas` | **em branco** (superavitário) |
| 2507507 — João Pessoa | 2025 | `L26.receitas_realizadas` | **R$ 5.117.875.296,33** = `L24`, com `L25` valendo zero |
| 2507507 — João Pessoa | 2025 | `L27.previsao_inicial` | **R$ 12.000.000,00** (era 482.338.332,64) |
| 35 — São Paulo (deficitário) | 2025 | `L25.receitas_realizadas` | **R$ 12.223.925.498,39** |
| 35 — São Paulo | 2025 | `L49.*` | **em branco**; `L50.empenhadas` = 385.042.592.630,74 |

## Critérios de aceite

- [ ] As 4 linhas saem apuradas em JP 2025, e `diagnostico.nao_apuradas` fica **vazio**.
- [ ] `L49` bate em centavos com `Superavit` do `RREO-Anexo 01` nas 3 colunas; `L50` bate com
      `TotalDespesasComSuperavit` nas 5.
- [ ] `L27.previsao_inicial` = 12.000.000,00.
- [ ] Em **SP** e **GO** (deficitários): `L25` bate com `Deficit`, `L26` com
      `TotalReceitasComDeficit`, e `L49` sai em branco com `L50` = `L48`.
- [ ] `python -m pytest` — **0 failed**. Os 3 vermelhos de C5 fecham.
- [ ] Regressão: as 65 linhas que não são `L25`/`L26`/`L49`/`L50`/`L27` saem **bit a bit iguais**.
- [ ] `ruff` limpo · `validate_rules` exit 0 · 69 regras · `check_sources` íntegro.

## Casos de erro

| Situação | Comportamento esperado |
|---|---|
| Referência nomeia coluna que a linha referenciada não tem | célula `None` com aviso nomeando linha, coluna pedida e coluna ausente — nunca zero |
| Ente com receita realizada exatamente igual à empenhada | nem déficit nem superávit; ambas as linhas em branco e os totais iguais às linhas base |
| Ente que não publica a linha de ajuste (medido: PB) | a apuração produz o valor; a divergência contra o publicado é do ente e aparece na conferência, não como erro |

## Restrições e riscos

- **Mexe no motor, não só na base canônica.** `RefLinha` e `_agregar` mudam, e a ordem de aplicação
  da condição muda. É a primeira change desta série a alterar `app/domain/bo/matriz.py`.
- **`None` acumula dois sentidos hoje** — "não apurado" e "não se aplica". Esta change os separa:
  o segundo passa a ser registrado à parte, e só o primeiro gera aviso.
- **A metade do déficit foi medida em estados, não em municípios.** Os 12 deficitários de 2025 são
  todos estaduais; JP é superavitária. O aceite conferre as duas metades, cada uma no ente que a
  produz.
- **Estimativa revisada:** o achado da condição × agregação torna a change ~4–5× o diff da
  `ipc07-b1-remocao-termo-5313`, não 2–3× como estimado antes de medir.

## Aprovação do PO

- [x] PO aprovou o encaminhamento em 2026-09-04 — pedido de fechar C5 e C7 numa change só.
