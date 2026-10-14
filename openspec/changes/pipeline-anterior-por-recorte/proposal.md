# Proposal — Coluna do exercício anterior por unidade: processado, MSC ou manual (BF e BP)

**Status:** aprovada pelo PO em 2026-10-13 — em implementação
**Repositório:** `ps-dca` (front: `front-declaracoes` `dca-bf-e-anterior-por-recorte`)
**Capability:** `pipeline/anterior-por-recorte` (nova) · `pipeline/unidade-gestora` (MODIFIED: coluna anterior por recorte) · `dca/balanco-patrimonial` (ADDED: coluna anterior manual)
**Anexo DCA:** BP / `DCA-Anexo I-AB` e BF (IPC 06), colunas do exercício anterior
**Base normativa:** MCASP · IPC 04 · IPC 06 (coluna "Exercício Anterior" = valores do exercício anterior da mesma entidade)
**Depende de:** `pipeline-dca-por-unidade-gestora` e `bf-por-unidade-gestora` (o BF por recorte).
Esta change vem **depois** das duas.

## Why

A PCA é prestada por unidade gestora (UG), e a coluna "Exercício Anterior" de cada UG tem de ser da
**própria UG**. Depois das changes de UG e do BF, essa coluna tem uma única origem por unidade: a
MSC do ano anterior, relida e reapurada a cada job. Isso não atende três situações reais:

- **A UG mudou ou é nova.** Não há MSC por UG no ano anterior: era um CSV sem UG, ou o
  `ID_INSTITUICAO` era outro. A coluna sai em zero, e o ente precisa **digitar** o anterior. Hoje só
  o BF consolidado aceita digitação; o BP não aceita em nenhum recorte.
- **O ano anterior já foi apurado e publicado na PCA.** A coluna anterior de 2025 deveria ser
  **exatamente** a coluna atual de 2024 daquela UG, com o estorno, o G8 e o manual aplicados naquele
  momento. Reapurar a MSC de 2024 depois de uma retificação muda, sem aviso, a peça de 2025.
- **Consistência entre as peças.** O que o ente apresentou em 2024 por UG é o ponto de partida de
  2025. Um retrato gravado garante isso. Uma nova apuração não garante.

A regra é a mesma no BF e no BP, por isso fica no pipeline e não em cada anexo.

## What Changes

- **Três origens para a coluna anterior** de cada unidade (`ug:<id>` ou `po:<código>`):

  | Origem | Valor da coluna anterior em N |
  |---|---|
  | `processado_exercicio_anterior` | a coluna **atual** do mesmo anexo, mesmo recorte, no resultado `ok` de N−1 já gravado no cache |
  | `msce_exercicio_anterior` | a MSC de N−1 da fonte do pedido, com os registros da unidade: `ug:` pela PublicSoft por UG, `po:` pelo SICONFI ou pela base da fonte. **Nunca a DCA publicada** |
  | `manual` | os valores digitados para a unidade, no BF **e no BP** |

- **A origem é escolhida por unidade.** Uma UG pode vir de `processado` e outra de `manual` no mesmo
  job.
- **Padrão por unidade sem escolha:** `processado_exercicio_anterior` se o cache de N−1 do anexo
  estiver `ok` e tiver aquele recorte; `msce_exercicio_anterior` se não tiver. Um cache gravado antes
  dos recortes cai sozinho em `msce`.
- **Toda escolha explícita fica gravada**, seja `processado`, `msce` ou `manual` com os valores. Um
  pedido que não menciona a unidade reaplica a escolha gravada. Só a unidade sem nenhuma escolha usa
  o padrão. `{"origem": "padrao"}` limpa a escolha. Um `processado` gravado cujo N−1 sumiu cai
  em `msce`, com o motivo registrado, sem travar o job.
- **O consolidado ganha a opção `processado_exercicio_anterior`**, nos mesmos parâmetros que aceitam
  `origem_exercicio_anterior` hoje: o corpo do `reprocessar` do BF e do BP, a query da leitura e a
  query do percurso para o BP. As origens de hoje continuam valendo (BF: `msce` e `manual`; BP: `publicado_siconfi` e
  `msce`), e o padrão do consolidado não muda.
- **Manual do BP** (novo). O usuário digita as linhas folha da coluna anterior:
  - do Quadro Principal, do quadro de ativos e passivos financeiros e permanentes e das contas de
    compensação;
  - do Superávit/Déficit, uma linha por fonte (4 dígitos), que o usuário pode acrescentar.

  As totalizadoras saem da calculation. Vale para as unidades; no consolidado do BP, o manual fica
  fora (ver Fora de escopo).
- **O grupo de poder não tem origem própria.** A coluna anterior dele é a **soma das colunas
  anteriores das unidades** que o compõem: linhas folha somadas, totalizadoras pela calculation. No
  Superávit por fonte, entra a união das fontes, e a fonte ausente numa unidade conta 0,00.
- **A procedência declara a origem de cada recorte.** No `processado`, ela traz
  `anterior_processado: {exercicio, calculado_em, versao_regras, fonte, estorno_receita_extra?, estorno_despesa_extra?}`
  do resultado de N−1. Um N−1 processado por outra fonte é aceito.
- **A UG sem MSC em N−1 (`msce`) sai com zero e com o aviso `sem_dados_exercicio_anterior`**, como na
  change de UG (PO 2026-10-13).

**Fora de escopo:**
- Origem por grupo de poder: o grupo deriva das unidades.
- `anterior_por_recorte` no percurso (`/batch-jobs`), que não tem corpo e roda BF e BP juntos. No
  percurso, cada unidade usa a escolha gravada ou o padrão.
- Manual no consolidado do BP. O consolidado tem o publicado e o processado. Se o PO pedir, entra
  numa change própria.
- Recalcular automaticamente a peça de N quando N−1 é reprocessado (ver Restrições).
- BO, que não tem coluna do exercício anterior.

## Entradas e saídas

| Interface | Entrada | Saída |
|---|---|---|
| `POST /dca/{BF\|BP}/reprocessar` | atual + `anterior_por_recorte?: {"ug:3": {"origem": "manual", "valores": {...}}, "ug:5": {"origem": "msce_exercicio_anterior"}}`; `origem_exercicio_anterior` do consolidado aceita `processado_exercicio_anterior` | `202`; `409`/`422` |
| Valores do manual — BF | as chaves de hoje (`L2`, `A:L1:receita`, `A:L1:deducoes`) | — |
| Valores do manual — BP | `P:<codigo>` (Quadro Principal), `FP:<codigo>` (ativos e passivos financeiros e permanentes), `C:<codigo>` (compensação), `S:<fonte 4 dígitos>` (Superávit/Déficit) | — |
| `POST /batch-jobs` | `origem_exercicio_anterior` do BP aceita `processado_exercicio_anterior` | — |
| Job | cache de N−1 do mesmo anexo (`dca_anexo_cache`), sem nova chamada externa | em cada recorte, coluna anterior + `procedencia.origem_exercicio_anterior` + `procedencia.escolha_anterior` (a escolha explícita, ou `null`) + `anterior_processado?` + `valores_anteriores?` |
| `GET /dca/{BF\|BP}?recorte=` | sem mudança | a procedência do recorte servido traz a origem dele |

## Exemplo concreto

Cuitegi/PB (`2505204`), BF e BP com fonte PublicSoft. UGs: Prefeitura, FMAS, FMS e Câmara.

1. Processar o BF e o BP de **2024**. O cache de 2024 guarda o consolidado e os recortes.
2. Processar o BF e o BP de **2025** sem `anterior_por_recorte`.
3. Em cada `ug:<id>`, a coluna anterior de 2025 é igual, **em centavos**, à coluna atual do mesmo
   `ug:<id>` em 2024. A procedência registra `processado_exercicio_anterior` e
   `anterior_processado.exercicio = 2024`.
4. Reprocessar o BP de 2025 com `{"ug:<Câmara>": {"origem": "manual", "valores": {"P:L3": "1500000.00", "S:1500": "20000.00", ...}}}`
   muda só a Câmara. No `poder:legislativo`, a coluna anterior passa a ser a digitada, e no
   `poder:executivo+legislativo` passa a ser a soma.
5. Reprocessar o BP sem `anterior_por_recorte` mantém a Câmara no manual.

## Critérios de aceite

- [ ] Cuitegi BF e BP 2025, todas as UGs em `processado`: diferença 0,00 contra a coluna atual de 2024, célula a célula, incluindo as fontes do Superávit.
- [ ] Sem o cache de 2024 com recortes: todas as UGs em `msce`, bit a bit iguais ao resultado de `bf-por-unidade-gestora` (BF) e de `pipeline-dca-por-unidade-gestora` (BP).
- [ ] Unidade em `processado`: o serviço não apura N−1 para ela (zero chamadas do serviço com `anterior=msce` para a unidade, medido no teste).
- [ ] Grupo de poder: a coluna anterior de cada linha folha é igual à soma das unidades do grupo, com diferença 0,00.
- [ ] Consolidado com as origens de hoje: bit a bit igual, nas duas fontes.
- [ ] Escolha explícita (`processado`, `msce` ou `manual`) gravada e reaplicada num pedido que não menciona a unidade, e no percurso.
- [ ] Ler o anexo depois de reprocessar sem mudança de escolha **não** marca `pedido` em `motivos_desatualizado`.

## Casos de erro

| Situação | Comportamento esperado |
|---|---|
| `processado_exercicio_anterior` **explícito** e N−1 sem cache `ok` (ou sem o recorte pedido) | `409` "processe {N−1} antes", sem job |
| N−1 deixou de estar `ok` entre a rota e o job (escolha explícita) | o job termina em `erro` com o mesmo motivo, sem cair em outra origem |
| N−1 em `processando` ou `erro` na hora do job (padrão) | a unidade usa `msce`, e o `diagnostico` registra o motivo |
| `manual` sem `valores`, chave de linha inexistente, linha totalizadora ou fonte que não tem 4 dígitos | `422` |
| Chave de grupo (`poder:*`) ou `consolidado` em `anterior_por_recorte` | `422` |
| Chave de unidade que não existe no job (inclusive `po:` vazio inexistente) | não aplica; aviso em `diagnostico` |
| Linha de N sem par por `codigo` em N−1 (mudança de layout) | célula não apurada, motivo "sem linha no exercício anterior" |
| Unidade (`ug:`/`po:`) | nunca usa a DCA publicada na coluna anterior |

## Restrições e riscos

- **O `processado` é um retrato.** Reprocessar 2024 não muda a peça de 2025 já gravada. A
  procedência mostra de qual `calculado_em` veio o anterior. Marcar N como desatualizado quando N−1
  mudar fica como pendência.
- **O cache guarda só o último processamento.** A chave é `(ente, exercício, anexo)`, sem a fonte.
  Reprocessar N−1 com outra fonte troca os recortes `ug:` por `po:`, ou o contrário, e o padrão de N
  cai em `msce` para as unidades que não casam mais.
- **A identidade da UG** é o `ID_INSTITUICAO`, que precisa ser estável entre os exercícios. É
  pendência herdada da change de UG. A UG nova usa o `manual`.
- **A soma no grupo exige linhas aditivas.** BF e BP não têm linha condicional (`condition` só no
  YAML do BO), e o teste confere isso.

## Aprovação do PO

- [x] A coluna anterior da unidade vem da própria unidade e sempre da MSC, nunca da DCA publicada. "Não pelo SICONFI" = não pela DCA publicada (PO 2026-10-13)
- [x] Três origens: processado, MSC e manual (PO 2026-10-13)
- [x] Origem escolhida por UG (PO 2026-10-13)
- [x] Padrão `processado` se houver cache de N−1 com o recorte, senão `msce` (PO 2026-10-13)
- [x] O consolidado também ganha `processado` (PO 2026-10-13)
- [x] A regra fica no pipeline e é usada pelo BF e pelo BP (PO 2026-10-13)
- [x] Na MSC, o `po:` lê a MSC da fonte do pedido, inclusive o SICONFI (PO 2026-10-13)
- [x] Processado de outra fonte em N−1 é aceito, com `anterior_processado.fonte` (PO 2026-10-13)
- [x] O cache continua guardando só o último processamento, sem chave por fonte (PO 2026-10-13)
- [x] O BP ganha manual por unidade nesta change (PO 2026-10-13)
- [x] UG sem MSC em N−1: zero com aviso (PO 2026-10-13)
- [x] PO aprovou esta proposta em 2026-10-13 — **gate para a fase PLAN/ARCH**
