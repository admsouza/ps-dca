# Proposal — Processar e reprocessar a DCA inteira numa chamada

**Status:** aprovada pelo PO em 2026-09-23 · em implementação
**Repositório:** `ps-dca`
**Capability:** `pipeline/processamento-completo` (nova)
**Anexo DCA:** todos os implementados — hoje `BO` e `BF`
**Base normativa:** n/a (orquestração; a regra de cada anexo é a da sua própria capability)
**Fonte da verdade externa:** `regras-rreo-api/app/routes/jobs_rreo_completo.py` — padrão de
pipeline completo já em produção nos irmãos

## Why

A DCA só é apurável **um anexo por chamada** (`GET /dca/{anexo}`, `POST /dca/{anexo}/reprocessar`).
Foi decisão consciente enquanto existia um anexo só (P4 e P-D6 de `plataforma-pipeline-dca`:
"quando o segundo anexo existir, o pipeline completo é uma change pequena"). O segundo existe desde
2026-09-18, e o custo de não ter a orquestração aparece em três lugares:

1. **Quem consome decide a ordem.** O front (`front-declaracoes`) precisa disparar N chamadas,
   acompanhar N streams e decidir o que fazer quando a terceira falha. É orquestração no cliente —
   exatamente o que RREO e RGF deixaram de fazer.
2. **Retificação obriga a reapurar tudo.** Quando o ente retifica a MSC, todo demonstrativo daquele
   exercício está velho ao mesmo tempo. Hoje isso são N `POST /reprocessar` disparados à mão, sem
   nada que diga quando o conjunto ficou consistente.
3. **A leitura da MSC é paga duas vezes.** BO e BF leem da mesma matriz: as classes 5 e 6 do BO são
   subconjunto exato do que o BF já lê. Em jobs separados são **20** consultas à fonte (2 do BO +
   18 do BF); num job único, com a memória de execução que o worker já abre, são **18** — as duas
   do BO saem de graça. O ganho cresce a cada anexo novo, que lê as mesmas seis classes.

## What Changes

- `POST /batch-jobs` — enfileira **um** job que percorre os anexos implementados na ordem do
  registry, servindo do cache o que já estiver válido; `forcar: true` no corpo reapura todos,
  equivalente ao `POST /dca/{anexo}/reprocessar` de hoje aplicado ao conjunto.
- `GET /batch-jobs/{id}` e `GET /sse/batch-jobs/{id}` — progresso e desfecho por anexo, no
  **mesmo contrato de batch job** que RREO e RGF publicam e o front já consome.
- Job novo `apurar_completo`, que reusa `services/pipeline/job.executar` anexo a anexo dentro de
  **uma** memória de execução da MSC — nenhuma regra de cálculo muda.
- Acompanhamento por `job_id` único: polling e SSE já existentes, com progresso
  (`anexos_concluidos` / `total`) e um desfecho por anexo.
- Anexo sem serviço no registry (`I-AB`…`I-HI`) é reportado como `nao_implementado`, não como erro.

**Fora de escopo:** cancelamento cooperativo (`/cancelar`, `cancel_requested`) — o front suporta,
mas ninguém pediu para a DCA e o percurso de dois anexos dura menos que a decisão de cancelar;
paralelismo entre anexos (a leitura da MSC é o custo, e ela já é compartilhada
em série); reprocessamento em lote de vários entes; agendamento automático por retificação
detectada; qualquer mudança em regra de apuração do BO ou do BF.

## Entradas e saídas

| Interface | Entrada | Saída |
|---|---|---|
| `POST /batch-jobs` | `anReferencia` e `forcar` em query — as mesmas dependências das rotas por anexo; ente pela autorização da unidade; solicitante registrado | `202` + `{batch_job_id, status, poll_url, sse_url, anexos: [{anexo, estado, job_id, calculado_em}]}` |
| `GET /batch-jobs/{id}` | `batch_job_id` | `{status, progresso: {concluidos, total}, falhas, anexos: [{anexo, status, job_id, duracao_ms, erro_detalhe}]}` |
| `GET /sse/batch-jobs/{id}` | idem | um evento por anexo concluído e um terminal `done`/`error` |

## Exemplo concreto

| Ente | Exercício | Anexos | Medida esperada |
|---|---|---|---|
| 2507507 — João Pessoa | 2025 | `BO`, `BF` | um `job_id`; ao fim, `GET /dca/resumo` traz `BO` e `BF` com `status: ok` e `calculado_em` do mesmo job |
| 2507507 — João Pessoa | 2025 | `BO`, `BF` | **18** consultas à fonte MSC no job completo, contra **20** somando os dois jobs isolados |

## Critérios de aceite

- [ ] `POST /dca/processar` para João Pessoa/2025 conclui com `BO` e `BF` em `ok` no resumo,
      valores **bit a bit iguais** aos dos jobs individuais de hoje (as 337 células do BO e as
      66 × 2 do BF).
- [ ] O job completo faz **18** consultas à fonte MSC (contra 20 em jobs separados), contadas por
      dublê de fonte no teste.
- [ ] Falha em um anexo não impede os demais: com o BF forçado a falhar, o BO sai `ok`, o job
      termina `done` com `falhas: 1` e o `BF` nomeado no desfecho.
- [ ] Nenhum anexo é apurado duas vezes quando já há job em voo para ele: o completo reporta o
      `job_id` alheio e segue.
- [ ] Suíte verde e `ruff` limpo; nenhum arquivo de `app/domain/`, `app/services/bo/` ou
      `app/services/bf/` alterado.

## Casos de erro

| Situação | Comportamento esperado |
|---|---|
| `exercicio` ausente ou fora da faixa | `422`, sem criar job |
| Unidade não autorizada para o ente | `403`, sem criar job |
| Nenhum anexo implementado no registry | `422` com a lista vazia declarada — nunca `202` de job que não faria nada |
| Fila indisponível no enfileiramento | `503`; nenhuma identidade fica presa em `processando` |
| Um anexo falha na apuração | os demais seguem; cache daquele anexo fica `erro` com o detalhe; job termina `done` com `falhas > 0` |
| Todos os anexos falham | job termina `error`, com o detalhe por anexo |
| Job completo excede `DCA_JOB_TIMEOUT_SECONDS` | os anexos já gravados permanecem `ok`; o job é marcado `error` e os locks pendentes são liberados no startup seguinte |

## Restrições e riscos

- **Teto de tempo.** Dois anexos cabem folgados no timeout atual (3600s). Com os oito, a medição
  de duração por anexo (já gravada em `diagnostico.duracao_ms`) é o que dirá se o job único ainda
  cabe ou se vira fan-out — decisão adiada de propósito, com o número na mão.
- **Concorrência com o job por anexo.** As rotas por anexo continuam existindo; o lock por
  identidade é o mesmo, e é ele que impede apuração dupla.
- **Notificação.** Uma notificação por anexo em um job de oito vira ruído no canal de operação;
  a proposta é uma notificação consolidada ao fim (D5 do design).

## Aprovação do PO

- [x] PO aprovou esta proposta em 2026-09-23 — **gate para a fase PLAN/ARCH**
- [x] PO confirmou a rota única `POST /batch-jobs` no contrato de batch job dos irmãos
- [x] PO confirmou a notificação consolidada no lugar de uma por anexo
