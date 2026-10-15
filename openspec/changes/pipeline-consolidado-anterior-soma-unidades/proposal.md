# Proposal — Consolidado anterior como soma das unidades

**Status:** proposta criada por decisão funcional de 2026-10-15; aprovação formal do texto pendente
**Repositório:** `ps-dca`
**Capability:** `pipeline/anterior-por-recorte` (existente)
**Anexo DCA:** Balanço Financeiro (BF) e Balanço Patrimonial (BP)
**Base normativa:** IPC 04 e IPC 06, colunas do exercício anterior; não altera o mapeamento contábil
**Depende de:** `pipeline-anterior-por-recorte` e `bf-por-unidade-gestora`

## Why

O consolidado aparece hoje como uma origem própria da coluna anterior, independente das escolhas das
UGs ou POs. Isso permite que a tela mostre unidades em `processado`, `msce` ou `manual`, enquanto o
consolidado usa outra origem e deixa de representar a soma do que foi configurado e conferido por
unidade.

A decisão funcional é que o consolidado não seja configurável: ele é o resultado da soma das colunas
anteriores resolvidas das unidades do job, sejam elas `ug:` ou `po:`.

## What Changes

- No BF e no BP, a coluna anterior do consolidado passa a ser derivada, célula a célula, das unidades.
- Cada unidade continua resolvendo sua própria origem (`processado`, `msce` ou `manual`) antes da soma.
- O consolidado deixa de aceitar origem e mapa manual próprios.
- A procedência do consolidado declara `origem_exercicio_anterior=soma_das_unidades`.
- Grupos de poder continuam usando a mesma regra de soma das unidades que os compõem.
- Nenhuma parcela pode existir somente no consolidado: dado que afete a coluna anterior e não pertença
  a uma UG/PO impede a publicação do resultado como `ok` e produz diagnóstico explícito.

**Fora de escopo:**
- coluna do exercício atual;
- `valores_sem_mapeamento` (G8) do BF, que completa somente o exercício atual;
- mudar a apuração contábil de cada unidade;
- converter automaticamente preferências antigas do consolidado em preferências de unidades;
- frontend, coberto pela change `front-declaracoes/dca-consolidado-anterior-soma-unidades`.

## Entradas e saídas

| Interface | Entrada | Saída |
|---|---|---|
| `POST /dca/{BF\|BP}/reprocessar` | `anterior_por_recorte` somente com `ug:`/`po:` | `202`; consolidado derivado no resultado |
| `GET /dca/{BF\|BP}` | sem origem própria do consolidado | resultado com `procedencia.origem_exercicio_anterior=soma_das_unidades` |
| `POST /batch-jobs` | sem `origem_exercicio_anterior` para BF/BP | percurso usa as escolhas gravadas por unidade ou o padrão de cada unidade |
| Campos legados do consolidado | `origem_exercicio_anterior` ou `valores_anteriores` no corpo | `422`, sem job |
| Campo legado na query | `origem_exercicio_anterior` em BF/BP | `400`, sem job |

## Exemplo concreto

Cuitegi/PB (`2505204`), BP 2025: a auditoria por recorte mediu `L1 = 76.314.331,92` e a soma dos
três POs também em `76.314.331,92`, diferença `0,00`. Quando esse resultado alimentar a coluna
anterior do BP 2026, o `L1` consolidado anterior SHALL ser `76.314.331,92`, obtido exclusivamente da
soma dos POs resolvidos, sem ler uma origem própria do consolidado.

## Critérios de aceite

- [ ] BF e BP: 100% das células anteriores do consolidado são iguais à soma das unidades, com diferença `0,00`.
- [ ] Origens mistas por unidade (`processado`, `msce`, `manual`) são refletidas na soma do consolidado.
- [ ] Superávit/Déficit do BP usa a união das fontes; fonte ausente numa unidade conta `0,00`.
- [ ] Célula não apurada em qualquer unidade deixa a célula consolidada não apurada, sem virar zero.
- [ ] Nenhuma rota oferece ou reaplica origem própria do consolidado.
- [ ] Pedido legado com origem ou manual do consolidado é recusado antes de enfileirar job.
- [ ] Contribuição sem UG/PO produz erro explícito; nenhum resultado parcial é gravado como `ok`.
- [ ] Coluna atual e `valores_sem_mapeamento` permanecem bit a bit iguais.

## Casos de erro

| Situação | Comportamento esperado |
|---|---|
| `origem_exercicio_anterior` ou `valores_anteriores` próprios do consolidado | `422` no corpo ou `400` na query, sem job |
| `consolidado` ou `poder:*` dentro de `anterior_por_recorte` | `422`, como hoje |
| Unidade manual sem valores válidos | `422`, sem job |
| Parcela da coluna anterior fora de todos os recortes `ug:`/`po:` | job em `erro`, diagnóstico sem dado sensível e sem cache `ok` parcial |
| Job sem nenhuma unidade emitida | job em `erro`; consolidado vazio não é publicado |

## Restrições e riscos

- É uma alteração incompatível para clientes que ainda enviam origem própria do consolidado.
- Cache antigo continua com a regra anterior até ser reprocessado; a versão de regras deve invalidá-lo.
- A implementação deve provar que cada parcela da coluna anterior pertence a exatamente uma unidade,
  evitando perda e dupla contagem.
- O erro não deve registrar valores contábeis identificáveis nem payload manual em log.

## Aprovação do PO

- [ ] PO aprovou esta proposta em <data> — **gate para a fase PLAN/ARCH**
