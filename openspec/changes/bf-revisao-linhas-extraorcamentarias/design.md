# Design — Revisar linhas extraorçamentárias do Balanço Financeiro

**Change:** `openspec/changes/bf-revisao-linhas-extraorcamentarias/` · **Proposal aprovada pelo PO em:** pendente

## Contexto

A SPEC-0001 pede a revisão de `L27`, `L28`, `L60` e `L61` e o fechamento dos totais (IV) e (X)
em PM Cuitegi, outubro/2025. Ela traz a composição ativo/passivo e os dois totais. Não traz
conta, valor por linha nem o que "outubro" significa num demonstrativo anual.

No código atual, `L24` é `L25 + L26 + L27 + L28` e `L57` é `L58 + L59 + L60 + L61`
(`knowledge/rules/bf/quadro_principal.yaml`). `L28` e `L61` seguem `review_required`. A change
`bf-l28-l61-contas-especificas` já implementou uma lista de 15 contas de classe 1 e a medição
contra João Pessoa/2025 reprovou. Essa lista não entra aqui.

## Componentes afetados

A definir depois que D1, D2 e D3 fecharem. Candidatos, sem decisão:

| Componente | Papel possível |
|---|---|
| `knowledge/rules/bf/quadro_principal.yaml` | contas e status de `L27`, `L28`, `L60`, `L61` |
| `app/services/bf/quadro_principal.py` | apuração das quatro linhas e dos totais `L24` e `L57` |
| procedência do BF | origem identificável de cada uma das quatro linhas |

Nenhum destes arquivos é alterado nesta fase.

## Fluxo da informação

```text
caso Cuitegi / outubro-2025 (competência = D1)
  → apuração de L27, L28, L60, L61 (contas = D3, fatia = D2)
  → L24 = L25 + L26 + L27 + L28  →  387.665,33
  → L57 = L58 + L59 + L60 + L61  →  520.551,46
  → procedência nomeia a origem das quatro linhas
```

## Contratos / interfaces

Sem mudança de rota, payload ou cache nesta fase. O aceite é valor de `L24` e `L57` mais a
origem das quatro linhas na procedência.

## Impacto

| Eixo | Impacto |
|---|---|
| Banco / migration | nenhum previsto |
| Cache | invalidar o BF do ente/exercício quando a regra das quatro linhas mudar |
| Filas / worker | nenhum até o desenho da leitura existir |
| APIs externas | a leitura MSC depende de D1 e D3 |
| Regressão | linha que não depende das quatro permanece bit a bit igual |

## Decisões

### D1 — Competência de "outubro/2025"
**Escolhido:** nada ainda. **Alternativas em aberto:** competência 10 de 2025, ou o exercício
2025 (competência 12, ou soma das competências 1 a 12, como o BF já faz em `L27`/`L60`).
**Porquê de esperar:** a SPEC-0001 nomeia o mês e o demonstrativo é anual. Escolher agora mede
outro caso.

### D2 — Valor de cada linha
**Escolhido:** nada ainda. O gabarito é o total `L24` = R$ 387.665,33 e `L57` = R$ 520.551,46,
com a composição ativo/passivo da proposal. **Em aberto:** quanto cabe a `L27` e a `L28`, quanto
cabe a `L60` e a `L61`, e a que contas "ativo" e "passivo" se referem. O subtotal de passivo da
despesa (R$ 518.968,46) e o ativo (R$ 1.583,00) estão registrados; a soma deles é o total de
`L57`.

### D3 — Contas
**Escolhido:** não usar as 15 contas de classe 1 de `bf-l28-l61-contas-especificas`.
**Descartado:** copiar aquela lista para esta change. **Porquê:** a medição em João Pessoa/2025
reprovou por seis ordens de grandeza. A lista desta change só existe quando o PO a entregar.

### D4 — Change nova
**Escolhido:** `bf-revisao-linhas-extraorcamentarias`. **Descartado:** continuar dentro de
`bf-l28-l61-contas-especificas`. **Porquê:** o caso, o ente e o escopo são outros (`L27`/`L60` e
os totais IV/X). A change bloqueada permanece como está.

## Arquivos criados / alterados

| Arquivo | Ação |
|---|---|
| `openspec/changes/bf-revisao-linhas-extraorcamentarias/proposal.md` | criar |
| `openspec/changes/bf-revisao-linhas-extraorcamentarias/specs/dca/balanco-financeiro/spec.md` | criar |
| `openspec/changes/bf-revisao-linhas-extraorcamentarias/design.md` | criar |
| `openspec/changes/bf-revisao-linhas-extraorcamentarias/tasks.md` | criar |
| `openspec/AGENTS.md` | alterar (registrar a change) |

Código, YAML e teste ficam para depois da aprovação do PO e do fechamento de D1–D3.

## Pendências conhecidas

- D1, D2 e D3 abertas. Sem elas não há teste nem implementação.
- A SPEC-0001 não cita o código IBGE. Esta change usa `2505204` (IBGE confirmado pelo PO em 2026-10-06), em
  Cuitegi/PB em `docs/entes-homologacao/cuitegi/`.
