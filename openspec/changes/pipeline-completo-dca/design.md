# Design — Processar e reprocessar a DCA inteira numa chamada

**Change:** `openspec/changes/pipeline-completo-dca/` · **Proposal aprovada pelo PO em:** 2026-09-23

## Contexto

A plataforma já tem tudo que o percurso precisa, e nada que o faça: registry com a ordem canônica e
o serviço de cada anexo, job único parametrizado (`apurar_anexo`), decisão de servir/enfileirar
(`services/pipeline/cache.ler_ou_enfileirar`), execução com desfecho garantido
(`services/pipeline/job.executar`), lock por identidade com recuperação de órfão, e a memória de
execução da MSC aberta pelo worker. O que falta é um orquestrador que percorra o registry — e a
restrição é não duplicar nenhuma dessas peças, porque cada duplicata é um caminho a mais para o
resultado divergir do que a rota por anexo produz.

## Componentes afetados

| Componente | Papel na change |
|---|---|
| `app/routes/anexos.py` | uma rota nova: `POST /batch-jobs`, declarada antes de `GET /dca/{anexo}` para manter a leitura do arquivo na ordem de escopo — coletivo, depois individual |
| `app/routes/jobs.py` | `GET /batch-jobs/{id}` e `GET /sse/batch-jobs/{id}`, no contrato de batch job do RREO; o SSE emite um evento a cada anexo concluído |
| `app/services/pipeline/completo.py` (novo) | decide o percurso: quais anexos entram, quais já estão em cache, quais estão em voo; devolve a lista e enfileira um job. Nenhuma apuração |
| `app/services/pipeline/job.py` | **sem mudança** (D8): o desfecho é lido do registro que ele mesmo grava |
| `app/services/pipeline/registry.py` | sem mudança: `REGISTRY` já é a ordem de execução e `implementado()` já é o filtro |
| `worker.py` | job novo `apurar_completo`, wrapper fino: abre uma memória de execução e delega ao orquestrador |
| `app/infra/fila/job_manager.py` | progresso do job pai: `concluidos`, `total` e desfecho por anexo |

## Fluxo da informação

```text
POST /batch-jobs?anReferencia=2025&forcar=false
  -> autorizacao por unidade + exercicio valido
  -> completo.montar_percurso(registry, repo, lock)   # em cache | em voo | a apurar | nao implementado
  -> 202 { batch_job_id, anexos[] }      e enfileira apurar_completo
                                             |
                                             v  worker
                                      escopo MSC aberto UMA vez
                                             |
                        para cada anexo a apurar, na ordem canonica:
                          lock por identidade -> job.executar(anexo) -> desfecho
                                             |
                      job_manager: progresso e desfecho por anexo (SSE + polling)
                                             |
                            uma notificacao consolidada ao fim
```

## Contratos / interfaces

```python
# app/services/pipeline/completo.py
@dataclass(frozen=True)
class NoPercurso:
    anexo: str
    estado: str                    # "a_apurar" | "em_cache" | "already_queued" | "nao_implementado"
    job_id: str | None = None      # preenchido em already_queued


def montar_percurso(*, ente, exercicio, repo, lock, jobs, versao_api,
                    versoes_regras, forcar=False) -> list[NoPercurso]: ...


def executar_percurso(*, ente, exercicio, percurso, repo, lock, jobs, job_id,
                      apurador_de, notificador=None, solicitado_por=None) -> dict: ...
```

Estado do job completo, sob a mesma chave `dca:job:<id>` de hoje:

```jsonc
{
  "status": "processing | done | error",     // terminais que o front ja encerra
  "progresso": { "concluidos": 2, "total": 2 },
  "falhas": 1,
  "anexos": [
    { "anexo": "BO", "status": "ok",   "duracao_ms": 4210, "erro_detalhe": null },
    { "anexo": "BF", "status": "erro", "duracao_ms": 900,  "erro_detalhe": "..." }
  ]
}
```

## Impacto

| Eixo | Impacto |
|---|---|
| Banco / migration | nenhuma — o resultado continua em `dca_anexo_cache`, uma linha por anexo, gravada pelo mesmo `job.executar` |
| Cache | nenhuma chave nova de resultado; a identidade por anexo é a de hoje, com os mesmos parâmetros do pedido |
| Filas / worker | job novo `apurar_completo` na mesma fila `arq:queue:dca`; locks continuam por anexo; `max_jobs` inalterado |
| APIs externas | menos consultas à MSC (18 contra 20 em João Pessoa/2025); nenhum endpoint novo da fonte |
| Regressão | `GET /dca/{anexo}` e `POST /dca/{anexo}/reprocessar` saem bit a bit iguais; `job.executar` muda o retorno, não o efeito |

## Decisões

### D1 — Um job em série, não fan-out de N jobs

**Escolhido:** job único percorrendo os anexos em série · **Descartado:** o completo enfileira um
job por anexo e agrega · **Porquê:** o custo da apuração é a leitura da MSC, e é justamente ela que
o percurso em série compartilha — em fan-out cada job abriria sua própria memória de execução e as
20 consultas voltariam. O fan-out só passa a valer quando o tempo total estourar o timeout, e o
número que decide isso (`diagnostico.duracao_ms` por anexo) já é gravado hoje.

### D2 — Reusar `job.executar` por anexo, sem atalho

**Escolhido:** o orquestrador chama a mesma função que o job por anexo chama · **Descartado:**
apurar direto pelo serviço do anexo e gravar o cache no orquestrador · **Porquê:** as cinco
garantias do caminho de erro (cache `erro` com detalhe, estado do job, lock liberado, notificação,
falha de notificação ignorada) vivem lá. Duplicá-las é convidar o percurso completo a divergir do
individual exatamente quando algo falha.

### D3 — Lock por anexo, não lock do percurso

**Escolhido:** o percurso adquire o lock de cada anexo na vez dele · **Descartado:** um lock
`COMPLETO` por ente/exercício · **Porquê:** um lock de percurso não impediria um
`POST /dca/BF/reprocessar` simultâneo — e é o lock por identidade que já impede apuração dupla.
Anexo com lock ocupado vira `already_queued` no resumo, com o `job_id` alheio, como a rota
individual já faz.

### D4 — Falha isolada por anexo

**Escolhido:** o percurso segue e o desfecho nomeia quem falhou · **Descartado:** abortar no
primeiro erro · **Porquê:** os anexos são independentes entre si; abortar transformaria uma falha
de fonte num anexo em nenhum demonstrativo apurado. Para que "terminou" não signifique "está tudo
certo", o desfecho carrega a contagem de falhas (D7).

### D5 — Uma notificação consolidada

**Escolhido:** o orquestrador silencia a notificação por anexo e emite uma ao fim · **Descartado:**
manter a notificação por anexo · **Porquê:** oito notificações por percurso tornam o canal de
operação inútil justamente quando ele precisa ser lido. A consolidada traz o desfecho por anexo e a
duração total — mais informação, uma mensagem.

### D6 — Uma rota, no contrato de batch job dos irmãos

**Escolhido:** `POST /batch-jobs` com `forcar` em query · **Descartado:** o par
`POST /dca/processar` + `POST /dca/reprocessar` · **Porquê:** duas rotas que diferem num booleano
são um handler a mais para manter, e a autorização separada é necessidade que ninguém pediu. Pesou
mais o consumidor: `regras-rreo-api/app/routes/jobs_rreo_completo.py` já publica
`POST /batch-jobs`, `GET /batch-jobs/{id}` e `/sse/batch-jobs/{id}`, e o front tem o cliente pronto
(`front-declaracoes/src/utils/rreoBatchJobStatus.ts`, `rreoBatchJobSse.ts`, com `sanitizePollUrl`).
Replicar o contrato é o que AGENTS.md §4 pede e o que faz o front custar quase nada — e "replicar"
inclui o **path**: aquele cliente monta `${base}/batch-jobs/{id}` e `${base}/sse/batch-jobs/{id}`
a partir da base do serviço (`/dca-api`), então as rotas ficam sem prefixo de anexo, como o
`/jobs/{id}` individual já é. Publicá-las sob `/dca/batch-jobs` anularia o reuso que motivou D6.

### D8 — Desfecho lido do cache, sem mexer em `job.executar`

**Escolhido:** depois de cada anexo, o percurso lê `repo.obter(...)` — status, `erro_detalhe` e
`duracao_ms` já estão lá · **Descartado:** mudar `executar` para devolver desfecho estruturado,
como o design previa · **Porquê:** o registro é gravado pelo próprio `executar` no mesmo instante;
lê-lo custa uma consulta ao repositório que já está aberto e deixa o caminho do job individual
**intocado** — zero risco de regressão na rota por anexo, que é o que mais roda hoje.

### D7 — Desfecho terminal em `done`, com contagem de falhas

**Escolhido:** `done` quando o percurso terminou, `falhas: n` e desfecho por anexo no corpo;
`error` só quando nenhum anexo concluiu · **Descartado:** um status `concluido_com_erros` ·
**Porquê:** medido no consumidor. `front-declaracoes/src/utils/rreoBatchJobStatus.ts:35` fecha os
terminais em `done | error | cancelled | interrupted`; status fora desse conjunto não é terminal
para o parser, e o diálogo giraria para sempre num job que já acabou. A informação que o
`concluido_com_erros` carregaria fica onde é legível sem varrer lista: um número.

## Arquivos criados / alterados

| Arquivo | Ação |
|---|---|
| `app/services/pipeline/completo.py` | criar — percurso e execução |
| `app/services/pipeline/notificacao.py` | alterar — notificação consolidada do percurso |
| `app/infra/fila/job_manager.py` | alterar — progresso e desfecho por anexo |
| `app/routes/anexos.py` | alterar — `POST /batch-jobs` |
| `app/routes/jobs.py` | alterar — polling e SSE do percurso, evento por anexo concluído |
| `worker.py` | alterar — job `apurar_completo` |
| `app/routes/anexos.py` (envelope do percurso) | alterar — `batch_job_id`, `anexos[]`, `progresso`, `falhas` |
| `tests/pipeline/test_pipeline_completo.py` | criar — um teste por `#### Scenario:` do delta |

## Pendências conhecidas

- **Teto de tempo com oito anexos.** Com `BO` e `BF` o job cabe folgado em
  `DCA_JOB_TIMEOUT_SECONDS` (3600s). A partir do quarto anexo, medir a duração acumulada antes de
  decidir entre manter a série e migrar para fan-out (D1).
- **Parâmetros por anexo.** Hoje só o BF aceita parâmetros próprios (competência, origem da coluna
  do exercício anterior); o percurso os repassa a quem a assinatura aceitar, como `_aceitos_por` já
  faz. Quando dois anexos quiserem parâmetros conflitantes, o payload do percurso precisa virar um
  mapa por anexo — não antes.
- **Reprocessamento multi-ente**, para quando a retificação for detectável: fora desta change.
