# Design — Contas específicas para L28/L61 por crédito e débito mensal

**Change:** `openspec/changes/bf-l28-l61-contas-especificas/` · **Proposal aprovada pelo PO em:** *(pendente)*

## Contexto

O motor do BF lê hoje **um único snapshot** MSC por exercício: matriz de encerramento, saldo de
abertura, competência 12, classes 1–6 (`app/infra/msc/fonte.py:52-58`). Sobre esse snapshot,
`saldo_da_celula_por_conta` (`app/domain/bo/saldo.py:145-180`) soma cada conta **na direção dela
própria no PCASP** (`Σ C − Σ D` se credora, `Σ D − Σ C` se devedora) — nunca "só os créditos" ou
"só os débitos" isolados.

O pedido para L28/L61 é outra semântica: somar apenas os lançamentos a **crédito** (L28) ou apenas
a **débito** (L61), mês a mês, sem subtrair o lado oposto. Isso não é um ajuste de parâmetro em
`saldo_da_conta` — é uma regra de agregação diferente, e a fonte de dados também muda (12
competências em `period_change`, não 1 snapshot de encerramento).

## Componentes afetados

| Componente | Papel na change |
|---|---|
| `knowledge/rules/bf/quadro_principal.yaml` (L28 ~l.1752, L61 ~l.3755) | `accounts` + discriminador de natureza; `status: extracted` |
| `app/domain/bo/saldo.py` | nova função de agregação "só um lado" (crédito ou débito), sem subtração |
| `app/infra/msc/fonte.py` | nova leitura: 12 `Fonte(Matriz.CONSOLIDADA, TipoSaldo.PERIODO, classes)`, uma por competência 1–12, só para as contas de L28/L61 |
| `app/infra/regras/carregador.py` | ler o discriminador novo do YAML (ou passar a consumir `movimento`, hoje ignorado) |
| `app/services/bf/informados.py:24` | `CODIGOS_SEM_MAPEAMENTO` perde `"L28"`, `"L61"` |

## Fluxo da informação

```text
MSC (12 chamadas period_change, competências 1–12, só contas de L28/L61)
  → Registro[] concatenados dos 12 meses
  → nova função em saldo.py: soma apenas registros.natureza == "C" (L28) ou == "D" (L61)
  → total da célula (sem subtração do lado oposto)
  → matriz.valores["L28"/"L61"]["exercicio_atual"]
  → cache → GET /dca/BF
```

As outras 64 linhas do BF continuam no fluxo atual (1 snapshot, `saldo_da_celula_por_conta`) — este
fluxo novo é **aditivo**, isolado a estas 2 linhas.

## Contratos / interfaces

A decidir na fase PLAN/ARCH com o PO (ver D1):
- Como o YAML expressa "só crédito" / "só débito" por linha: reaproveitar o campo `movimento`
  (hoje decorativo) passando a implementá-lo no carregador, ou introduzir um campo novo
  (ex: `apenas_natureza: credito|debito`) para não sobrecarregar um campo que já existe com outro
  sentido em L27/L60 (lá, direção da coluna/conta; aqui, filtro de lançamento).

## Impacto

| Eixo | Impacto |
|---|---|
| Banco / migration | nenhuma |
| Cache | avaliar se a chave de cache do BF precisa registrar que L28/L61 vieram de fonte `period_change`, para invalidação correta |
| Filas / worker | job do BF soma até 12 chamadas MSC extras, só para estas 2 linhas — medir latência antes de produção |
| APIs externas | MSC: confirmar paginação/limite por competência nos adapters SICONFI e PublicSoft |
| Regressão | as outras 64 linhas do BF não podem mudar de valor; rodar suíte completa + auditoria dos 5 entes de homologação |

## Decisões

### D1 — Função de agregação nova, não parametrizar `saldo_da_conta`
**Escolhido:** função nova em `saldo.py` que soma só um lado (sem subtração) · **Descartado:**
adicionar um modo a `saldo_da_conta` · **Porquê:** misturaria duas semânticas (saldo líquido vs.
soma de um lado) na mesma função testada e documentada como "a regra do BO/BF".

### D2 — 12 leituras MSC só para L28/L61, não mudar a fonte do demonstrativo inteiro
**Escolhido:** `Fonte(Matriz.CONSOLIDADA, TipoSaldo.PERIODO, ...)` por competência, isolado a estas
2 linhas · **Descartado:** mudar `ENCERRAMENTO_DO_EXERCICIO["BF"]` inteiro para `period_change` ·
**Porquê:** regrediria as outras 64 linhas, já validadas contra 5 entes de homologação — fora de
escopo e alto risco.

### D3 — `status: extracted` só após medir contra um ente real
**Escolhido:** manter `review_required` até o PO validar o resultado contra o BF publicado de pelo
menos 1 ente · **Porquê:** padrão do repo (ver `ipc06-bf-regras-canonicas` arquivada) — nenhuma
regra vira `extracted` sem evidência medida.

## Arquivos criados / alterados

| Arquivo | Ação |
|---|---|
| `knowledge/rules/bf/quadro_principal.yaml` | alterar (L28, L61) |
| `app/domain/bo/saldo.py` | alterar (nova função) |
| `app/infra/msc/fonte.py` | alterar (nova leitura por competência) |
| `app/infra/regras/carregador.py` | alterar (ler discriminador novo) |
| `knowledge/schemas/rule.json` | alterar (propriedade `apenas_natureza`, `enum: credito\|debito`) |
| `app/services/bf/informados.py` | alterar (linha 24) |
| `tests/bf/test_l28_l61_contas_especificas.py` | criar |

## Pendências conhecidas

- Exemplo concreto (ente/exercício/valor medido) ainda não existe — bloqueia `status: extracted`.
- Contagem de contas: o pedido fala em "16 contas" mas a lista trazida tem 15 linhas distintas —
  confirmar com quem definiu a regra antes de fechar o YAML.
- Formato do discriminador crédito/débito no YAML (D1 em aberto) — decidir na fase PLAN/ARCH.
- Performance das 12 chamadas MSC extras — medir.
