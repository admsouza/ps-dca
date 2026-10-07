# OpenSpec — Instruções para agentes de IA

> Ver também [`AGENTS.md`](../AGENTS.md) na raiz (regras autoritativas): perguntar OpenSpec antes
> de especificar/implementar/refatorar; ao concluir a change, atualizar `tasks.md` e mover para
> `openspec/changes/archive/`.

## Fluxo de trabalho

1. Leia `openspec/project.md` para contexto do repositório.
2. Para trabalhar numa change ativa, leia **nesta ordem**:
   - `openspec/changes/<change>/proposal.md` — por quê e o quê
   - `openspec/changes/<change>/specs/**/spec.md` — requisitos (delta)
   - `openspec/changes/<change>/design.md` — como
   - `openspec/changes/<change>/tasks.md` — checklist (`- [ ]`)
3. A fonte de verdade do comportamento acordado está em `openspec/specs/`.
4. Durante uma change, edite apenas os deltas em `openspec/changes/<change>/specs/`.
5. Ao concluir e arquivar, os deltas são mesclados em `openspec/specs/`.

## Criar uma change

```bash
mkdir -p openspec/changes/<slug>/specs/<domínio>/<capability>
cp openspec/templates/proposal.md openspec/changes/<slug>/proposal.md
cp openspec/templates/spec.md     openspec/changes/<slug>/specs/<domínio>/<capability>/spec.md
cp openspec/templates/design.md   openspec/changes/<slug>/design.md
cp openspec/templates/tasks.md    openspec/changes/<slug>/tasks.md
```

Slug em kebab-case, prefixado pelo anexo quando aplicável: `dca-anexo-i-c-receitas`.

Domínios previstos: `dca/` (regra de anexo), `import/` (ingestão XBRL), `pipeline/`
(orquestração, cache, jobs), `auth/`, `front/` (consumo UI, implementado em outro repo).

## Regras de especificação

- Requisitos usam **SHALL/MUST**; cenários usam `#### Scenario:` (4 hashtags).
- Delta specs usam `## ADDED Requirements`, `## MODIFIED Requirements`, `## REMOVED Requirements`.
- Capability nova exige `## Purpose` no delta spec.
- Specs descrevem **comportamento observável** — não nomes de classes nem passos de implementação.
- Detalhes de implementação ficam em `design.md` e `tasks.md`.
- Toda spec de anexo cita a **base normativa** (MCASP/IPC/layout SICONFI) e ao menos um
  **exemplo real** (ente, exercício, valor esperado).

## Fases e gates

`SPEC → PLAN/ARCH → TEST → IMPLEMENT → REVIEW → VERIFY` — definição e gates de cada fase em
[`../AGENTS.md` §2](../AGENTS.md). A fase SPEC só fecha com **aprovação explícita do PO**.

## Change ativa

Em **2026-10-01** as seis changes já implementadas foram conferidas contra o código e arquivadas.
Specs em vigor: `dca/base-canonica-regras`, `dca/balanco-orcamentario`,
`dca/balanco-financeiro` (64 cenários), `dca/balanco-patrimonial` (16, desde 2026-10-07), `dca/fonte-msc`, `pipeline/plataforma` (80) e
`pipeline/processamento-completo` (11).

**Change ativa, em implementação:** `dca-regra-na-celula` — `GET /dca/{anexo}/regra` e diálogo no BF.
Anexo sem projeção registrada responde 404. Não arquivada.

**Change ativa, fase VERIFY, bloqueada:** `bf-l28-l61-contas-especificas` — motor, YAML e whitelist
G8 (6→4 linhas) implementados e com suíte 100% verde, mas a medição contra o BF publicado de João
Pessoa/2025 (2026-10-01) reprovou: `L28`/`L61` apurados com as 15 contas de classe 1 (ativo) da
proposal saem seis ordens de grandeza abaixo do publicado. `status` continua `review_required` no
YAML — pendência do PO: revisar a lista de contas (candidato não testado: classes 7/8, controle
devedor/credor do PCASP) antes de qualquer novo teste.

**Change ativa, fase SPEC:** `bf-revisao-linhas-extraorcamentarias` — revisão de `L27`, `L28`,
`L60` e `L61` a partir da SPEC-0001. Gabarito: PM Cuitegi (`2505204`), outubro/2025, `L24` (IV) =
R$ 387.665,33 e `L57` (X) = R$ 520.551,46. Não reutiliza as 15 contas da change bloqueada.
Aguardando aprovação do PO e o fechamento de D1 (competência), D2 (valor por linha) e D3 (contas).

**Change ativa, em implementação:** `bf-estorno-receita-extra` — na PublicSoft, `L27` e `L60`
saem líquidas (movimento MSC − `totalGeral` do estorno de receita extra do exercício da coluna).
SICONFI permanece o movimento da MSC. PO aprovou em 2026-10-05.

**Change ativa, em implementação:** `pipeline-fonte-por-pedido` — `use_siconfi` do front escolhe a fonte
por pedido (hoje ignorado: vale o `DATA_SOURCE` do worker) e o `token_ps` passa a ser resolvido no
hub e guardado cifrado para o job, como no RGF/RREO. PO aprovou em 2026-10-06.

**Change ativa, em implementação — aguardando PO:** `bf-estorno-siconfi` — o SICONFI com
`token_ps` também abate o estorno extra em `L27`/`L60`. O DCA não faz pré-check em
`/auditorias` (exige JWT; o `409` do `base-demonstrativos` vira sem dados). **A auditoria do
exercício anterior está desligada temporariamente, aguardando o PO:** o `409` do anterior não
bloqueia o BF e não abate o estorno sobre o zero.

| Change arquivada em 2026-10-01 | O que o código já fazia |
|---|---|
| `plataforma-pipeline-dca` | ciclo único: rota, cache, job, worker, SSE, lock, vigência publicada |
| `vigencia-por-anexo` | semente de boot publica BO e BF, cada um na transcrição do próprio anexo |
| `pipeline-completo-dca` | `POST /batch-jobs`: um percurso pelos anexos implementados |
| `bf-anterior-manual-persistido` | mapa manual do exercício anterior na procedência; pedido sem origem reaplica |
| `bf-manual-anexo-alimenta-receita-i` | no Manual, o anexo alimenta `(I)` e as totalizadoras saem da calculation |
| `bf-completar-nao-apuradas-g8` | `valores_sem_mapeamento` no corpo completa as seis linhas sem conta no exercício atual |

O front pode deixar de injetar `(I)` e de repetir o mapa manual: a API deriva `(I)` e reaplica o
mapa salvo.

Não reexecutado nesta revisão (os cenários seguem cobertos por teste):

- Recife/2025 ao vivo do mapa manual (`L17`) e do G8 (`L22`);
- subir API+worker e reiniciar com job em voo (itens 6.4 e 6.5 de `plataforma-pipeline-dca`).

Pendências que **não** voltaram a ser change:

- as 10 decisões de `docs/decisoes-bf-para-po-2026-09-18.md`;
- as divergências contra o BF publicado pelos entes;
- o critério de identificação da MSC de encerramento na periodicidade mensal
  (`docs/pendencias-periodicidade-mensal.md`).

Handoff do BF: **`docs/PONTO-DE-PARADA-BF.md`**. O quadro principal, o anexo, a competência de
encerramento e a entrada do BF no pipeline continuam em `openspec/changes/archive/2026-09-18-*`.

## Changes arquivadas (recentes)

| Data | Change |
|---|---|
| 2026-10-07 | `bp-apuracao-f1` — **Balanço Patrimonial (IPC 04) no mesmo fluxo do BF.** Capability nova `dca/balanco-patrimonial` (16 cenários): Quadro Principal e quadro F/P apurados de `MSCE`/encerramento, classes 1, 2 e 6; compensação e superávit por fonte declarados não apuráveis (P5). Atributo F/P lido do fato e declarado por termo de conta (`ContaCC.financeiro_permanente`); contas mistas do PCASP (`2.3.4`/`2.3.7`) pela direção da classe. Espelho `I-AB` de JP: quadro F/P 5/5 em centavos. Exclusões intra-OFSS mantidas (P8-a): `L1 − L15` declarado, JP +5,95 bi e Cuitegi −2,0 mi. Suíte **verde**. Evidência: `docs/evidencia-bp-fp-2025.md`, `docs/depara-bp-iab-ipc04.md`. |
| 2026-10-01 | `plataforma-pipeline-dca`, `vigencia-por-anexo`, `pipeline-completo-dca`, `bf-anterior-manual-persistido`, `bf-manual-anexo-alimenta-receita-i`, `bf-completar-nao-apuradas-g8` — conferidas contra o código e mescladas. Ver a seção "Change ativa". |
| 2026-09-14 | `msc-fonte-e-competencia` — **fonte MSC por demonstrativo e apuração mensal.** Decisão do PO: todos os demonstrativos sobre a matriz de **encerramento**, saldo de **abertura** no BO, BF, DVP e DFC, e de **encerramento** no BP. O par vira propriedade do demonstrativo, e a combinação errada deixa de ser exprimível. Competência passa a parâmetro (padrão 12), para entes que prestam contas mensalmente — nos meses 1–11 a leitura é a consolidada, porque a **`MSCE` só existe em dezembro** (medido). Regressão do BO: **337 células × 2 entes, zero divergências**. Retry com backoff nos adapters. Revoga a decisão C1. Capability nova `dca/fonte-msc` (12 cenários); BO passa a 46. Suíte **312 passed**. |
| 2026-09-14 | `ipc06-bf-regras-canonicas` — **base canônica do Balanço Financeiro (IPC 06, ed. 2024-06).** 80 regras em `knowledge/rules/bf/` (Quadro Principal 66 + Quadro Anexo 14), 5 policies e 3 enums novos: `fonte_recurso`, `saldo` (inicial/final) e `movimento` (credor/devedor). Campos e colunas passam a ser validados **por documento**. Fontes por subgrupo vindas do Anexo I da Portaria STN 710/2021 (`fontes-recursos-stn-2026.xlsx`, decisão F3). `review_required 6` — L22, L23, L28, L55, L56 e L61, sem mapeamento no IPC 06 (F1/F2). Suíte **287 passed**; parte `BO` do índice bit a bit igual. Spec: 27 requisitos / 83 cenários. Análise da fonte: `docs/source-analysis-ipc06.md`. |
| 2026-09-10 | `bo-template-no-resultado` — **template de apresentação no resultado.** `linhas` com `rule_id`, `codigo`, `rotulo`, `quadro`, `grupo`, `nivel`, `ordem` e `totalizadora`; `nivel`/`ordem` vindos da transcrição normativa, nunca derivados da composição; vigência antiga completada pela transcrição no carregamento. Aditiva: `matriz`, `procedencia` e `diagnostico` inalterados. 2 requisitos / 8 cenários mesclados na spec do BO (35 → 43). |
| 2026-09-10 | `ipc07-l51-reserva-rpps` — **L51 Reserva do RPPS apurada como L39.** Mesmo mapeamento `*id003`, filtros ND `9.9` + função `99` + subfunção `997`, fora do TOTAL (XV). Revoga a parte de B6 que deixava L51 sem coluna. |
| 2026-09-04 | `bo-quadro-principal-processamento` — **F1 do BO entregue e verificada.** Núcleo puro (`domain/` + adapters + carregador YAML + service + CLI), sem Postgres nem Redis. Aceite 1:1 em centavos contra JP 12/2025 e conferência linha a linha contra o `RREO-Anexo 01`. Spec em `openspec/specs/dca/balanco-orcamentario/spec.md` — 17 requisitos / 43 cenários. F2 e F3 são trabalho de `plataforma-pipeline-dca`. |
| 2026-09-04 | `ipc07-c5-c7-linhas-cruzadas` — **C5 e C7 fechadas.** `L25`, `L26`, `L49` e `L50` passam a ser apuradas, com colunas medidas no publicado do STN e referência que nomeia a coluna lida; `L29` perde `previsao_inicial` (B6 restringida). Motor: 3 casos distintos na parcela agregada e condição decidida por linha. **Suíte 153 passed / 0 failed** — verde pela primeira vez. Aceite: JP 13/13 em centavos, SP e GO conferidos. Evidência: `docs/evidencia-c5-deficit-superavit.md`. |
| 2026-09-04 | `ipc07-b1-remocao-termo-5313` — `5.3.1.3.0.00.00` removida da coluna (a) do quadro de RP Não Processados: descontinuada, com o conteúdo em `5.3.1.2`, já primeiro termo da fórmula. Revoga a decisão B1 de 2026-08-27. **Encerra a pendência C6 sem alteração de schema.** Regressão bit a bit: 0 células divergentes em 69 linhas. Removido de passagem o código morto de `natureza_saldo` e a função `_direcao_da_conta`, nunca chamada. Evidência: `docs/evidencia-c6-c7.md`. |
| 2026-09-04 | `ipc07-bo-regras-canonicas` — base canônica do IPC 07 entregue: 69 regras em `knowledge/rules/bo/`, 2 policies, schemas, validador e índice. 89 testes verdes; `review_required` 0. Spec em `openspec/specs/dca/base-canonica-regras/spec.md`. |
| 2026-09-04 | `knowledge-base-ipc` — sucedida por changes separadas por IPC; nunca implementada. Artefatos compartilhados (`knowledge/schemas/`, `knowledge/sources/`, `scripts/check_sources.py`) passaram para `ipc07-bo-regras-canonicas`. |

## Antes de codar (regras do projeto)

- A implementação segue o ciclo SPEC → PLAN → TEST → IMPLEMENT. Change nova continua exigindo spec aprovada pelo PO antes do código.
- Respeitar contrato de auth: JWT + `X-Unidade-Id`; rejeitar `x-authorization`.
- Importação XBRL: `C:\Projetos\prd-audite` manda (ver `../AGENTS.md` §4).
- Replicar o padrão de RREO/RGF antes de inventar abstração nova (YAGNI).
- Marcar tarefas concluídas em `tasks.md` no momento em que fecham (`- [x]`).

## Validação

A adotar na fase IMPLEMENT:

```bash
python -m pytest
python -m ruff check .
alembic upgrade head
```
