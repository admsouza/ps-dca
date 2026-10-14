# Proposal — Balanço Financeiro emitido por unidade gestora (estorno de GRE/GDE por UG)

**Status:** aprovada pelo PO em 2026-10-13 — em implementação
**Repositório:** `ps-dca` (fonte: `ps-erp` change `relatorio-estorno-poder-orgao`; front: `front-declaracoes` `dca-bf-e-anterior-por-recorte`)
**Capability:** `dca/balanco-financeiro` (existente) · `pipeline/unidade-gestora` (da change `pipeline-dca-por-unidade-gestora`)
**Anexo DCA:** Balanço Financeiro (IPC 06), Quadro Principal e Quadro Anexo
**Base normativa:** MCASP · IPC 06 · IPC 04 item 8 (levantamento de unidade específica)
**Depende de:** `pipeline-dca-por-unidade-gestora` e `bf-estorno-receita-extra`. **Vem antes de**
`pipeline-anterior-por-recorte`, que acrescenta as origens Processado e Manual por unidade.

## Why

O BO e o BP já saem por UG. O BF ficou em standby porque se supunha que o estorno de receita e
despesa extra (guias GRE e GDE), abatido de `L27` e `L60`, era do ente e não tinha UG.

**A premissa é falsa** (medido no código em 2026-10-13). As consultas de
`relatorios-gerenciais/estorno-{receita,despesa}-extra` do `ps-erp` agrupam por
`GUIA_*.ID_INSTITUICAO`, e a resposta já traz `totaisPorUnidadeGestora: [{idInstituicao, valor}]`.
`ID_INSTITUICAO` é a mesma chave da UG na base `unidades-gestoras`. O DCA é que lia só o
`totalGeral`.

Sem o BF por UG, a PCA por unidade fica incompleta, e o usuário do Legislativo não emite o BF da
Câmara.

## What Changes

- **O BF entra nos anexos com recorte.** O job apura o consolidado, os grupos de poder e cada
  unidade. `GET /dca/BF?recorte=` lê do cache sem job, com as mesmas regras de visibilidade do BO e
  do BP.
- **Estorno por unidade.** O BF de um recorte abate de `L27` e `L60` a **soma dos estornos das
  unidades** que ele contém:
  - `ug:<id>`: o `totaisPorUnidadeGestora` da instituição `id`;
  - `po:<código>`: os estornos das instituições cujo `poderOrgao` é o código (o `ps-erp` passa a
    expor esse campo);
  - grupo de poder: a soma das unidades dele;
  - consolidado: o `totalGeral`, como hoje.

  A propagação para `L24`, `L33`, `L57` e `L66` segue a D3 de `bf-estorno-receita-extra`.
- **Uma chamada por exercício e tipo de estorno no job**, memorizada no escopo como a MSC. Os
  recortes não chamam o relatório de novo.
- **Estorno sem unidade.** É estorno que entra no `totalGeral` do consolidado mas não cai em
  nenhuma unidade. O consolidado registra esse estorno em
  `diagnostico.estorno_sem_unidade: [{exercicio, tipo, unidade, valor}]`, e o job não falha. Os
  casos são:
  - por UG: instituição com estorno e sem nenhum registro na MSC do exercício;
  - por PO: instituição com `poderOrgao` nulo, ou com um PO que não aparece na MSC do exercício.
- **Coluna do exercício anterior das unidades e dos grupos:** a MSC de N−1 dos registros do recorte,
  como o BP faz na change de UG. O estorno de N−1 também é o das unidades. A UG sem MSC em N−1 sai
  com a coluna anterior em **zero** e com o aviso `sem_dados_exercicio_anterior`. Essa é a regra
  atual da change de UG, confirmada pelo PO em 2026-10-13. As origens Processado e Manual por
  unidade vêm na change `pipeline-anterior-por-recorte`.
- **O anterior manual (`valores_anteriores`) e o G8 (`valores_sem_mapeamento`) valem só no
  consolidado.** Os dois foram digitados para o ente. Fora do consolidado:
  - a coluna anterior é a MSC;
  - as linhas do G8 ficam não apuradas, com o motivo "informado só no consolidado".

  Hoje o G8 vaza para os recortes (`apuracao.py:186`, que só remove `dca`). Esta change corrige.
- A regra de hoje vale por recorte: num exercício sem nenhuma leitura, o estorno não é abatido.
- **SICONFI sem `token_ps`:** nenhum recorte abate, como o consolidado de hoje. É o caso do ente
  CSV: sem ERP PublicSoft não há GRE/GDE.
- **Ente com SIAFIC processado com a fonte MSC (`use_siconfi=true`):** emite por **PO**, porque o
  SICONFI não informa a UG. A resposta de BO, BP e BF traz o aviso `avisoRecorte` = "Recorte por
  poder/órgão: o SICONFI não informa a unidade gestora. Para emitir por unidade gestora, processe
  com SIAFIC." O ente com SIAFIC é o que tem o `token_ps` resolvido pelo hub no pedido. O aviso é
  calculado na leitura, que já resolve o token na fonte SICONFI, sem estado novo no cache.

**Fora de escopo:**
- G8 digitado por unidade.
- Ratear o estorno sem unidade.
- Processado e Manual por unidade (change `pipeline-anterior-por-recorte`).
- `anterior_por_recorte` no percurso (`/batch-jobs`).
- Pendências de `bf-estorno-siconfi`, que aguardam o PO. Esta change segue a decisão que o PO tomar
  lá para o consolidado.

## Entradas e saídas

| Interface | Entrada | Saída |
|---|---|---|
| Relatório `ps-erp` | `?exercicio={ano}&tipo=sintetico` (igual) | `data.totalGeral` + `data.totaisPorUnidadeGestora[].{idInstituicao, valor, poderOrgao}` |
| `GET /dca/BF` | params de hoje + `recorte?` | corpo do recorte + `recorte` + `recortesDisponiveis` (contrato do BO/BP) |
| Procedência do recorte | — | `estorno_receita_extra`/`estorno_despesa_extra` com o valor **abatido no recorte**, por exercício |
| Diagnóstico do consolidado | — | `estorno_sem_unidade` quando houver |
| Diagnóstico da unidade | — | `sem_dados_exercicio_anterior` quando a unidade não tem MSC em N−1 |
| `GET /dca/{BO\|BP\|BF}` | — | `avisoRecorte?: string` quando o ente tem SIAFIC e o resultado foi processado pelo SICONFI |

## Exemplo concreto

PM Cuitegi/PB (`2505204`), 2025, fonte PublicSoft. Estorno de receita extra: `totalGeral` =
115.679,40; estorno de despesa: 0,00.

| Recorte | Célula | Valor esperado |
|---|---|---|
| `consolidado` | `L27` atual | 4.486.188,21 (igual a hoje) |
| `consolidado` | `L60` atual | 4.479.755,61 (igual a hoje) |
| Σ `ug:<id>` das 4 UGs | `L27` atual | 4.486.188,21 se `estorno_sem_unidade` estiver vazio |
| cada `ug:<id>` | `L27` atual | bruto da UG − `totaisPorUnidadeGestora[id]` (a medir) |

## Critérios de aceite

- [ ] Cuitegi 2025 `consolidado` pelas duas fontes: BF bit a bit igual ao de antes da change.
- [ ] Cuitegi 2025: Σ `L27` e Σ `L60` das UGs = consolidado − Σ `estorno_sem_unidade`, com diferença 0,00.
- [ ] Σ do estorno abatido nas unidades + Σ `estorno_sem_unidade` = `totalGeral`, por exercício e tipo, por UG e por PO.
- [ ] O relatório de estorno é chamado no máximo 2 × 2 vezes por job (exercício × tipo), qualquer que seja o número de recortes.
- [ ] Equilíbrio do BF por UG em Cuitegi 2025 (`diagnostico.equilibrio`): diferença registrada em `docs/entes-homologacao/cuitegi/auditoria-recorte-2025.md`. Critério: a soma das diferenças de equilíbrio das UGs só pode divergir da diferença do consolidado pelo estorno de **despesa** sem unidade, em centavos. O estorno de receita sai de ingresso e de dispêndio e se anula.
- [ ] `GET /dca/BF?recorte=ug:3` → `200` sem `enqueue`.

## Casos de erro

| Situação | Comportamento esperado |
|---|---|
| Resposta sem `totaisPorUnidadeGestora` | a apuração falha (`EstornoIndisponivel`); nenhum recorte é publicado com o bruto |
| Recorte por PO e resposta **sem o campo** `poderOrgao` (`ps-erp` anterior à change) | `L27`/`L60` dos `po:` não apuradas, com o motivo "estorno sem poder/órgão"; o consolidado segue |
| `poderOrgao: null` numa instituição | o estorno dela vai para `estorno_sem_unidade`; os `po:` abatem o resto |
| Estorno de instituição sem registro na MSC | `diagnostico.estorno_sem_unidade` no consolidado; o job conclui |
| Exercício do recorte sem nenhuma leitura | não abate (`L27`/`L60` sem bruto) |
| `recorte` inexistente, malformado, sem acesso, cache antigo | `404`/`422`/`403`/`409`, como no BO e no BP |

## Restrições e riscos

- **A GRE/GDE tem de estar na mesma instituição do lançamento na MSC.** Isso é premissa do ERP.
  Uma divergência aparece como `L27` negativa na UG ou como estorno sem unidade. Medir em Cuitegi.
- **Usuário só `executivo` deixa de ver o BF consolidado**, a mesma mudança de comportamento do BO e
  do BP. Conceder `consolidado` no hub antes de liberar.
- Não sobe antes da `CH-46` do hub. O recorte `po:` com estorno depende da change do `ps-erp`.

## Aprovação do PO

- [x] Duas changes novas: pipeline (anterior por recorte) e BF por UG (PO 2026-10-13)
- [x] `po:` abate o estorno pelo `poderOrgao` exposto no `ps-erp` (PO 2026-10-13)
- [x] Estorno sem unidade: aviso no diagnóstico, sem falhar o job (PO 2026-10-13)
- [x] Ente com SIAFIC e fonte MSC: emite por PO, com aviso, sem bloquear (PO 2026-10-13)
- [x] UG sem MSC em N−1: coluna anterior zero, com aviso (PO 2026-10-13)
- [x] PO aprovou esta proposta em 2026-10-13 — **gate para a fase PLAN/ARCH**
