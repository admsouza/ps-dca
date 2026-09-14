# Design — Base canônica de regras do Balanço Financeiro (IPC 06)

**Change:** `openspec/changes/ipc06-bf-regras-canonicas/` · **Proposal aprovada pelo PO em:** 2026-09-14

## Contexto

A base canônica existe e está fechada para o IPC 07 (69 regras do BO). Os artefatos compartilhados
— `knowledge/schemas/`, `knowledge/sources/`, `scripts/validate_rules.py`, `scripts/build_index.py`,
`scripts/check_sources.py` — foram escritos com o BO em mente: o `rule_id` começa por `bo.`, o
enum de `field` é o do IPC 07 e a coluna só conhece `accounts` e `calculation`.

O IPC 06 traz três coisas que o BO não tem e que forçam o desenho:

1. **Fonte ou destinação de recursos** como dimensão de corte (itens 21–24). É o que diferencia
   `L2`, `L4`–`L10` e `L12`–`L14`, que compartilham o mesmo par de contas.
2. **Saldo de conta patrimonial em data** (`saldo inicial` / `saldo final`) nas linhas `L29`–`L32`
   e `L62`–`L65` — agregação por saldo, não por movimento do período.
3. **Sentido do movimento** (credor/devedor) em `L27` e `L60`, únicas linhas do BF em que duas
   linhas de sentidos opostos compartilham contas.

O IPC 06 **não** traz classificação funcional, natureza de receita/despesa nem coluna de
exclusões — nada de `exclusion_groups` no BF.

## Componentes afetados

| Componente | Papel na change |
|---|---|
| `knowledge/sources/ipc06/metadata.yaml` | fonte normativa: arquivo, 19 páginas, edição 2024-06, SHA-256 |
| `knowledge/sources/ipc06/extracted.md` | insumo de transcrição gerado do PDF |
| `knowledge/rules/bf/quadro_principal.yaml` | 66 regras (L1–L66), 2 colunas |
| `knowledge/rules/bf/quadro_anexo.yaml` | 14 regras (L1–L14), 6 colunas |
| `knowledge/policies/ipc06.yaml` | itens 27, 30, 33, 37 e 38 |
| `knowledge/schemas/rule.json` | `fonte_recurso`, `saldo`, `movimento`, decisões `F*` |
| `scripts/extract_ipc.py` | passa a receber o IPC como argumento, em vez do PDF fixo |
| `scripts/validate_rules.py` | conjunto de `field` e de colunas por documento; regras novas do BF |
| `scripts/build_index.py` | índice cobre `BO` e `BF` |

## Fluxo da informação

```text
PDF (docs/referencia/ipc) → check_sources (SHA-256) → extract_ipc → extracted.md
   → transcrição assistida → knowledge/rules/bf/*.yaml → validate_rules → build_index
```

Nada aqui executa apuração: a base é dado, o motor vem depois.

## Contratos / interfaces

Extensões no `rule.json` (aditivas — nenhuma regra do BO muda):

```yaml
# $defs.filtro.field
enum: [conta_contabil, natureza_receita, natureza_despesa, funcao, subfuncao, fonte_recurso]

# $defs.conta
saldo:      { enum: [inicial, final] }   # obrigatório em conta de classe 1/2 nas linhas de saldo

# $defs.coluna
movimento:  { enum: [credor, devedor] }  # só em L27 e L60 do BF
```

Validação por documento (`source.document`), não global:

| Documento | `field` permitido | Colunas permitidas |
|---|---|---|
| IPC07 | `conta_contabil`, `natureza_receita`, `natureza_despesa`, `funcao`, `subfuncao` | as 4/6/6/5 já vigentes |
| IPC06 | `conta_contabil`, `fonte_recurso` | Principal: `exercicio_atual`, `exercicio_anterior` · Anexo: `(a)`–`(f)` |

## Impacto

| Eixo | Impacto |
|---|---|
| Banco / migration | nenhum — a base é arquivo |
| Cache | nenhum |
| Filas / worker | nenhum |
| APIs externas | nenhum |
| Regressão | `rules_index.json` na parte `BO` sai **bit a bit igual**; as 69 regras do BO não mudam |

## Decisões

### D1 — `field: fonte_recurso` validado por documento, não por enum global
**Escolhido:** o validador deriva o conjunto de `field` de `source.document` ·
**Descartado:** enum global com todos os campos · **Porquê:** um enum único aceitaria
`natureza_despesa` numa regra do BF e `fonte_recurso` numa do BO — a spec do IPC 07 exige a
rejeição desse segundo caso, e um enum global a tornaria impossível.

### D2 — `saldo` na conta, não na coluna
**Escolhido:** `saldo: inicial|final` em cada conta · **Descartado:** atributo da linha ·
**Porquê:** `L30` mistura três contas que **todas** são saldo inicial, mas o campo por conta é o
que permite a regra `L63` reusar o mesmo bloco trocando só o momento, e deixa o validador recusar
saldo em conta de execução orçamentária.

### D3 — `movimento` explícito em vez de sinal negativo
**Escolhido:** `movimento: credor|devedor` na coluna · **Descartado:** `sign: -` em `L60` ·
**Porquê:** `L60` soma **positivamente** no TOTAL (XII); usar o sinal para representar o sentido
do movimento faria o total subtrair o que deveria somar.

### D4 — dois arquivos de regra, um por quadro
**Escolhido:** `quadro_principal.yaml` + `quadro_anexo.yaml` · **Descartado:** arquivo único ·
**Porquê:** espelha `knowledge/rules/bo/`, e os dois quadros têm conjuntos de colunas disjuntos.

### D5 — `L33` permanece no grupo dos ingressos
**Escolhido:** `bf.quadro_principal.ingressos.l33`, com `ordem` ao fim dos ingressos ·
**Descartado:** seguir a ordem física da p. 12 · **Porquê:** `L33 = (L1 + L15 + L21 + L24 + L29)`
só referencia linhas de ingresso; a posição na p. 12 é diagramação, e fica registrada em
`evidence.text`.

### D6 — fonte declarada por faixa de código principal, sem prefixo de exercício
**Escolhido:** `fonte_recurso in (...)` com os códigos principais de 3 dígitos do bloco 500–999 ·
**Descartado:** enumerar as fontes com prefixo (`1540`, `2540`, `9540`, …) · **Porquê:** o prefixo
`1|2|9` marca exercício corrente / anteriores / condicionados e **não** separa subgrupo; incluí-lo
triplicaria cada lista sem mudar o recorte, e quebraria na criação de qualquer fonte nova do ente.
A faixa vem dos cabeçalhos de bloco de `docs/contas-stn/fontes-recursos-stn-2026.xlsx`, registrado
com SHA-256 em `knowledge/sources/stn/metadata.yaml`; os códigos já existem em
`fonte-recursos.md`, que segue sendo o domínio de validação.

### D7 — `extract_ipc.py` parametrizado pelo IPC
**Escolhido:** `python -m scripts.extract_ipc ipc06 [páginas]`, com PDF e páginas de tabela vindos
do `metadata.yaml` · **Descartado:** copiar o script para `extract_ipc06.py` · **Porquê:** o
terceiro IPC (04, 05, 08) chegaria como terceira cópia divergente.

## Arquivos criados / alterados

| Arquivo | Ação |
|---|---|
| `knowledge/sources/ipc06/metadata.yaml` | criar |
| `knowledge/sources/stn/metadata.yaml` | alterar (registrar o `.xlsx` do Anexo I) |
| `knowledge/sources/ipc06/extracted.md` | criar (gerado) |
| `knowledge/rules/bf/quadro_principal.yaml` | criar |
| `knowledge/rules/bf/quadro_anexo.yaml` | criar |
| `knowledge/policies/ipc06.yaml` | criar |
| `knowledge/schemas/rule.json` | alterar (aditivo) |
| `knowledge/indexes/rules_index.json` | regerar |
| `scripts/extract_ipc.py` | alterar (parametrizar o IPC) |
| `scripts/validate_rules.py` | alterar (regras por documento) |
| `scripts/build_index.py` | alterar (cobrir BF) |
| `tests/test_regras_bf.py` | criar |
| `docs/source-analysis-ipc06.md` | criar (ambiguidades e decisões F1–F5) |

## Pendências conhecidas

- **F1/F2** decididos: `L22`, `L23`, `L28`, `L55`, `L56` e `L61` nascem `review_required`, com o
  candidato registrado e não aplicado. Estado declarado, não bloqueio da entrega.
- A apuração do BF (motor, service, rota, cache) fica para a change seguinte, equivalente à F1 do
  BO.
