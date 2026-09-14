# Proposal — Fonte MSC por demonstrativo e competência mensal

**Status:** aprovada pelo PO
**Repositório:** `ps-dca`
**Capability:** `dca/fonte-msc` (**nova**) · `dca/balanco-orcamentario` (existente, `MODIFIED`)
**Anexo DCA:** todos
**Base normativa:** decisão do PO de 2026-09-14, sustentada por
`docs/evidencia-matriz-mscc-vs-msce.md`
**Fonte da verdade externa:** API `tt/msc_*` do SICONFI

## Why

O PO decidiu em 2026-09-14 que **todos** os demonstrativos da DCA são apurados sobre a **matriz de
encerramento (`MSCE`)**, com o tipo de saldo definido por demonstrativo. O Balanço Orçamentário,
único já implementado, lê hoje `MSCC` com saldo de encerramento — e a spec vigente **exige** isso
por escrito ("Leitura da MSC fixa em ending_balance, MSCC, classes 5 e 6"). Enquanto esse requisito
não for corrigido, o código certo passa a violar a spec, e o BF nasceria lendo de uma fonte
diferente da do BO sem razão técnica.

A troca é neutra em valor — medida, não presumida —, mas é mudança de comportamento numa capability
entregue: entra por change, não por edição.

Junto vem a **periodicidade mensal**, decidida pelo PO na mesma data: há entes que prestam contas
mensalmente, e hoje o repositório só sabe apurar o exercício fechado — `MES_DA_DCA = 12` é constante
no serviço. E a medição trouxe uma restrição que amarra as duas coisas: **a `MSCE` só existe na
competência 12**. Sondados João Pessoa e Cuitegi nos meses 1, 3, 6, 9 e 11 de 2025, a matriz de
encerramento não responde em nenhum; a consolidada responde em todos. O par (matriz, tipo de saldo)
passa a depender do demonstrativo **e** da competência — não há escolha a fazer para os meses 1 a 11.

## What Changes

- Capability nova `dca/fonte-msc`: **um** lugar declara, por demonstrativo, o par
  (matriz, tipo de saldo) e as classes contábeis lidas.
- O par passa a ser **propriedade do demonstrativo**, não parâmetro livre do adapter — a combinação
  errada (`MSCE` com saldo de encerramento fora do BP) fica inexprimível.
- `MODIFIED` no requisito de leitura da MSC da capability `dca/balanco-orcamentario`.
- Porta `FonteSaldos` passa a receber matriz e tipo de saldo; adapters SICONFI e PublicSoft
  traduzem para o vocabulário de cada API (`co_tipo_matriz`, `id_tv`).
- Procedência do resultado passa a declarar matriz, tipo de saldo, competência e classes lidas.
- Retry com backoff nos adapters — 2 de ~40 chamadas caíram por reset na medição.
- **Competência mensal**: o mês passa a ser parâmetro do serviço ao CLI, padrão 12, e integra a
  identidade do resultado. Fora de dezembro, a leitura é `MSCC` pelo saldo de encerramento —
  posição acumulada até o mês.

**Fora de escopo:** apuração do BF (change `bf-apuracao-f1`); chave de cache, job e rota mensais
(`P9` de `plataforma-pipeline-dca`); implementação de BP, DVP e DFC — aqui só a tabela que eles vão
consumir.

## Entradas e saídas

| Interface | Entrada | Saída |
|---|---|---|
| `fonte_de(demonstrativo, competencia)` | `"BO"` \| `"BF"` \| `"BP"` \| `"DVP"` \| `"DFC"` + mês | par (matriz, tipo de saldo) + classes |
| `FonteSaldos.registros(ente, ano, mes, classe, matriz, tipo_saldo)` | idem + par | `Sequence[Registro]` |
| `apurar(ente, exercicio, fonte, competencia=12)` | + mês | `Resultado` com a competência na procedência |
| `Procedencia` | — | acrescenta `matriz`, `tipo_saldo`, `competencia`, `classes` |

## A tabela decidida

**Competência 12 — exercício fechado:**

| Demonstrativo | Matriz | Tipo de saldo |
|---|---|---|
| Balanço Orçamentário (IPC 07) | `MSCE` | **abertura** |
| Balanço Financeiro (IPC 06) | `MSCE` | **abertura** |
| Balanço Patrimonial (IPC 04) | `MSCE` | **encerramento** |
| Demonstração das Variações Patrimoniais (IPC 05) | `MSCE` | **abertura** |
| Demonstração dos Fluxos de Caixa (IPC 08) | `MSCE` | **abertura** |

**Competências 1 a 11 — prestação de contas mensal:** `MSCC` pelo saldo de **encerramento**, para
todos os demonstrativos. Não é escolha: a `MSCE` não existe nesses meses. A leitura é a posição
acumulada até o mês, o que o piloto confirma em Cuitegi — receitas realizadas de 10.942.851,04 em
março, 22.477.392,39 em junho, 34.047.498,07 em setembro e 50.723.704,91 em dezembro.

O BP é a exceção porque o encerramento é o que incorpora o resultado do exercício ao patrimônio
líquido — medido em João Pessoa, conta `2.3`: 3.543.761.526,91 na abertura contra
3.815.939.008,42 no encerramento, diferença de 272.177.481,51. Os demais demonstrativos descrevem
o fluxo do exercício e precisam da posição anterior a esse lançamento.

## Exemplo concreto

| Ente | Exercício | Anexo | Célula | Valor esperado |
|---|---|---|---|---|
| 2505204 — Cuitegi/PB | 2025 | `RREO-Anexo 01` | `TotalDespesas` EMPENHADAS (f) | 44.557.533,10 — **igual** antes e depois da troca |
| 2507507 — João Pessoa/PB | 2025 | `RREO-Anexo 01` | os 11 valores de `docs/validacao-bo-jp-2025.md` | **inalterados**, em centavos |

## Critérios de aceite

- [ ] Regressão do BO **célula a célula**: 337 células em Cuitegi e 337 em João Pessoa, **zero**
      divergências entre `MSCC`/encerramento (hoje) e `MSCE`/abertura (depois).
- [ ] O BO apura as competências 1 a 11 sobre `MSCC`/encerramento, com valores acumulados
      crescentes, e a competência 12 sobre `MSCE`/abertura.
- [ ] Competência sem dados devolve `sem_dados`, sem cair para dezembro.
- [ ] Os 11 valores de `docs/validacao-bo-jp-2025.md` seguem batendo com o publicado, em centavos.
- [ ] A procedência de todo resultado declara matriz, tipo de saldo, competência e classes.
- [ ] Nenhuma chamada de apuração consegue pedir `MSCE` com saldo de encerramento fora do BP.
- [ ] `python -m pytest` e `python -m ruff check .` sem falha nova.

## Casos de erro

| Situação | Comportamento esperado |
|---|---|
| Demonstrativo desconhecido em `fonte_de` | erro explícito nomeando os demonstrativos conhecidos |
| Par (matriz, tipo de saldo) pedido fora da tabela | recusa, sem cair para um padrão |
| Fonte responde vazio para o par correto | `sem_dados: true`, sem tentar outro par por omissão |
| `MSCE` pedida fora da competência 12 | recusa explícita — a matriz de encerramento não existe nesses meses |
| Competência fora de 1–12 | erro de entrada, sem apurar |
| Reset de conexão da API | retry com backoff; esgotado, erro explícito com a classe e o offset |

## Restrições e riscos

- A decisão **C1** do PO (mês 12, `MSCC`) fica **revogada**: a matriz muda na competência 12, e o
  mês deixa de ser constante.
- O resultado mensal e o anual **não podem compartilhar entrada de cache**. Enquanto `P9` de
  `plataforma-pipeline-dca` não entrar, nenhum resultado mensal deve ser cacheado.
- Nos meses 1 a 11 o demonstrativo sai da matriz **consolidada**, enquanto em dezembro sai da de
  **encerramento**. Duas competências do mesmo exercício têm origens diferentes por construção — daí
  a procedência ser obrigatória, não ornamental.
- `MSCE` lida pelo saldo de **encerramento** zera as classes 3 e 4 e erra 47 das 337 células do BO.
  É o erro que esta change torna inexprimível; se o par virar parâmetro livre depois, volta.
- A evidência de equivalência é de **dois entes** (6.890 e 889.618 habitantes). Ampla, mas não é
  prova universal: a regressão roda nos dois, e divergência em outro ente é achado a registrar.

## Aprovação do PO

- [x] PO decidiu o par por demonstrativo em 2026-09-14
- [x] PO determinou a inclusão do processamento mensal em 2026-09-14 (entes com prestação de contas
      mensal)
- [x] PO aprovou esta proposta em 2026-09-14 — **gate para a fase PLAN/ARCH**
