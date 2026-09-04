# Proposal — remover o termo `5.3.1.3.0.00.00` da coluna (a) do quadro de RP Não Processados

**Status:** proposta
**Repositório:** `ps-dca`
**Capability:** `dca/base-canonica-regras` (existente)
**Anexo DCA:** `n/a` — Balanço Orçamentário do IPC 07, publicado como `RREO-Anexo 01`
**Base normativa:** IPC 07 edição 2020-01, p. 12 · PCASP (`docs/contas-stn/PCASP.md`)
**Fonte da verdade externa:** n/a

## Why

O IPC 07 p. 12 define a coluna "Inscritos — Em Exercícios Anteriores (a)" do quadro de RP Não
Processados como `5.3.1.2.0.00.00 + 5.3.1.3.0.00.00 + 5.3.1.6.0.00.00 (-) 6.3.1.6.0.00.00`.

`5.3.1.3.0.00.00` **não existe no PCASP atual**. A decisão B1 do PO (2026-08-27) mandou preservar o
termo como exceção histórica do PCASP 2019. Isso deixou uma pendência aberta — **C6** — porque uma
conta ausente da tabela não tem direção de saldo, e declará-la na regra exige um campo
(`natureza_saldo`) que o schema `knowledge/schemas/rule.json` não tem. Enquanto C6 está aberta, um
ente que escriturasse `5.3.1.3` produziria célula `None` nas 9 linhas do quadro.

**O PO decidiu em 2026-09-04 que `5.3.1.3` foi descontinuada e o que ela guardava está em
`5.3.1.2`** — que já é o primeiro termo da mesma fórmula. O termo, portanto, é redundante e sai.

Medições que sustentam a decisão (`docs/evidencia-c6-c7.md`):

- `5313` e `5323` aparecem em **zero** de ~185.000 registros de classe 5 (`MSCC`,
  `ending_balance`, 12/2025) em 9 entes grandes — SP, MG, RJ, BA, PR, RS, CE, PE e João Pessoa.
- O quadro **simétrico** de RP Processados tem 3 termos (`5.3.2.2 + 5.3.2.6 (-) 6.3.2.6`), e o
  grupo `5.3.2` não tem `5.3.2.3`. A fórmula de 3 termos torna os dois quadros simétricos.
- O grupo `5.3.1` é **Devedora em 4 de 4** e `5.3.2` em 4 de 4; `6.3.1`/`6.3.2` são Credora em
  16 de 16. Nenhuma redutora, nenhuma direção mista.

**Custo de não resolver:** C6 fica aberta indefinidamente à espera de um artefato (PCASP 2019) que
não está na API do STN, e o schema da base canônica ganha um campo que serve a um único caso que
nenhum ente escritura.

## What Changes

- A coluna `inscritos_exerc_anteriores` do quadro de RP Não Processados passa a declarar **3**
  contas: `5.3.1.2` e `5.3.1.6` com sinal `+`, e `6.3.1.6` com sinal `-`.
- A exceção histórica **B1 deixa de existir**. Todas as contas declaradas nessa coluna passam a
  estar no PCASP atual, com direção de saldo conhecida pela tabela.
- **A pendência C6 é encerrada sem alteração de schema.** `natureza_saldo` não é mais necessário:
  não há mais conta ausente da tabela em coluna de valor.

**Fora de escopo:**

- **A pendência C5** (`L25`, `L26`, `L49`, `L50`) — precisa de coluna em `RefLinha`, que é outra
  mudança de schema, com sua própria change. Esta proposta **não** a resolve.
- A decisão **B3** (padrões `2111/8111`, `2118/8118`, `2121/8121`, `2128/8128`) segue valendo: são
  usados como `field: conta_contabil` em filtro, não como conta de coluna, e portanto nunca
  precisaram de direção de saldo.
- As tabelas de `docs/contas-stn/` não são alteradas.
- O literal do IPC 07 não é apagado: a fórmula original de 4 termos permanece registrada em
  `source`/`evidence` da regra e em `docs/source-analysis-ipc07.md`.

## Entradas e saídas

| Interface | Entrada | Saída |
|---|---|---|
| `carregar(exercicio)` → `MapaBO` | exercício | as 9 linhas do quadro de RPNP com `inscritos_exerc_anteriores` declarando **3** contas |
| `apurar(ente, exercicio, fonte)` | ente, exercício | coluna (a) apurada; nunca `None` por direção desconhecida nessa coluna |

## Exemplo concreto

| Ente | Exercício | Anexo | Célula | Valor esperado |
|---|---|---|---|---|
| 2507507 — João Pessoa | 2025 | RPNP `L9` TOTAL | `inscritos_exerc_anteriores` | **R$ 67.299.876,72** |
| 2507507 — João Pessoa | 2025 | RPNP `L2` Pessoal | `inscritos_exerc_anteriores` | **R$ 6.520,06** |

**O valor apurado não muda.** `5.3.1.3` não tem escrituração em JP 2025, e conta declarada sem
movimento contribui zero — a apuração atual já vale `5.3.1.2 + 5.3.1.6 (-) 6.3.1.6`. É regressão
bit a bit, e é o critério de aceite principal.

O que muda é o **comportamento na presença** de escrituração em `5.3.1.3`: hoje a célula inteira
das 9 linhas sai `None`; depois, o registro é ignorado e as 9 seguem apuradas — sem aviso, porque
`residuos` classifica por natureza de receita/despesa e não por conta contábil. É perda de
sinal aceita em troca de não perder as 9 linhas, sobre um caso que nenhum ente medido produz.

## Critérios de aceite

- [ ] A coluna `inscritos_exerc_anteriores` declara exatamente 3 contas nas 9 linhas do quadro.
- [ ] `python -m app.cli.bo 2507507 2025` devolve `67.299.876,72` em `rp_nao_processados.l9` e
      `6.520,06` em `l2` — **idênticos aos atuais**, em centavos.
- [ ] `python -m pytest` sai com **3 failed** em vez de 4: `test_saldo.py::test_excecao_historica_usa_a_natureza_declarada` deixa de existir junto com a sua premissa.
- [ ] `python -m ruff check .` limpo e `python -m scripts.validate_rules knowledge` exit 0, com
      `review_required` em 0 e a contagem de regras inalterada (69).
- [ ] Nenhuma ocorrência de `5313` em `knowledge/rules/` fora de `source`/`evidence`/nota
      histórica.
- [ ] `python -m scripts.check_sources knowledge` continua íntegro — nenhuma tabela STN muda.

## Casos de erro

| Situação | Comportamento esperado |
|---|---|
| Ente escritura `5.3.1.3` (nenhum medido) | o registro não casa com conta declarada e é ignorado na coluna (a), **sem aviso** — `residuos` classifica por natureza de receita/despesa, não por conta contábil. Hoje esse registro apaga a célula das 9 linhas (`None`); depois é ignorado e as 9 seguem apuradas. Troca deliberada |
| Regra ainda declarando `5313` após a change | `validate_rules` acusa conta fora do PCASP e a regra vai a `review_required` |

## Restrições e riscos

- **Reverte a decisão B1 de 2026-08-27.** A decisão nova é de 2026-09-04 e prevalece; o histórico
  das duas fica registrado em `docs/source-analysis-ipc07.md`, sem apagar a anterior.
- **Mexe em spec mesclada.** `openspec/specs/dca/base-canonica-regras/spec.md` é da change
  arquivada `ipc07-bo-regras-canonicas`. O delta desta change altera 1 cenário e remove 1; a
  contagem de `dca/base-canonica-regras` em `tests/test_cobertura_spec.py` cai de **49 para 48**,
  e só no momento do arquivamento.
- **Impacto na change ativa `bo-quadro-principal-processamento`:** o requisito do delta spec que
  manda consultar `natureza_saldo` "somente quando a conta estiver ausente da tabela (exceções
  históricas B1/B3)" fica sem caso de uso. Removê-lo é tarefa **daquela** change, não desta — o
  delta dela ainda não foi mesclado.
- **Risco baixo, medido:** a mudança é inerte para todo ente medido. Se algum ente fora da amostra
  escriturar `5.3.1.3`, o valor dele deixa de entrar na coluna (a) — hoje ele já não entra, porque
  a célula sai `None`.

## Aprovação do PO

- [ ] PO aprovou esta proposta em ______ — **gate para a fase PLAN/ARCH**
