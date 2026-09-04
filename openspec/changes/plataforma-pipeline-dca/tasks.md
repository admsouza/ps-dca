# Tasks — Plataforma de pipeline da DCA

**Não implementar sem aprovação explícita do PO.** Esta change define **fluxo, infra e organização
da arquitetura**; nenhuma regra de anexo pertence a ela.

Relação com a change do BO: a F1 (núcleo) do `bo-quadro-principal-processamento` não depende desta e
segue em frente; as fases **F2 (transporte)** e **F3 (pipeline)** implementam o que está aqui.

## 0. SPEC

- [x] 0.1 Levantar o fluxo real dos dois pipelines em produção — `regras-rreo-api/ARCHITECTURE.md`
      §3, §5, §8, §12; `regras-rgf-api` (`job_manager.py`, `lock_anexo.py`,
      `services/anexo_01/cache/service.py`, `models/rgf_anexo01_cache.py`, `docker-compose.yml`).
- [x] 0.2 Levantar a infra compartilhada: Redis de `ps-infra` (rede externa, container
      `redis_cache`), Postgres em `host.docker.internal`, deploy CapRover com duas imagens.
- [x] 0.3 Registrar as diferenças deliberadas em relação a RREO/RGF (`proposal.md` › tabela) e as
      decisões P-D1 a P-D5 (`design.md` §7).
- [x] 0.4 Escrever `proposal.md` e `design.md`.
- [x] 0.5 Escrever o delta `specs/pipeline/plataforma/spec.md`.
- [x] 0.6 P4, P5 e P6 decididos pelo PO em 2026-09-04: job por anexo na primeira entrega
      (pipeline completo é change posterior); Postgres e Redis compartilhados, separação por prefixo;
      notificação Discord ao fim do job.
- [x] 0.7 Lacunas da auditoria decididas pelo PO em 2026-09-04: **L1** (reprocessamento forçado)
      entra nesta change (P7); de **L2**, a *porta* de seleção por exercício entra na F1 e o acervo
      de edições coexistindo vira change própria (P8); procedência do valor apurado entra (P9).
- [x] 0.8 PO aprovou `proposal.md`, `design.md` e o delta spec em 2026-09-04 (Jackson S. da Silva (PO)). **Fase SPEC
      fechada** — PLAN/ARCH liberada.

## 1. PLAN/ARCH

- [ ] 1.1 Registry e resumo agregado no formato "job por anexo" (P4), já com a ordem canônica dos
      7 anexos — o pipeline completo consome o mesmo registry, sem redesenho.
- [ ] 1.2 Fixar as dependências da F2/F3: `fastapi`, `uvicorn`, `gunicorn`, `pydantic`, `arq`,
      `redis`, `sqlalchemy`, `alembic`, `psycopg2-binary`, `python-jose`, `cryptography`. Nenhuma
      delas alcançável a partir de `domain/`.
- [ ] 1.3.0 Fechar o shape de `linhas` (JSONB) de `dca_regra_mapeamento` a partir do contrato de
      cálculo do BO — é o que o carregador de banco devolve e o que o seed produz.
- [ ] 1.3 Implementar `versao_regras` como **hash canônico** (P-D7): SHA-256 sobre as regras
      efetivamente carregadas para o exercício + as tabelas STN usadas, serializadas de forma
      estável (chaves ordenadas, UTF-8, LF) — nunca sobre bytes crus de arquivo. A edição declarada
      (`IPC07 2020-01`) acompanha na procedência, sem participar da invalidação.
- [ ] 1.4 Confirmar com a infra o acesso ao Postgres e ao Redis compartilhados. **Não** criar
      schema: a DCA usa o `public`, com prefixo `dca_*` e `alembic_version_dca` (P5).
- [x] 1.5 Nomes de variáveis levantados dos `.env` reais de RREO e RGF em 2026-09-04 e
      consolidados em `design.md` §5. Dois achados: o banco já é `db-ps-rreo-rgf-dca`, e
      `REDIS_PREFIX=msc_cache:` é comum aos dois — nomeia o cache de MSC, que deve continuar
      compartilhado; o isolamento é só do estado de execução (`dca:`).
- [ ] 1.6 Confirmar com a infra qual `POSTGRES_DB`/host a DCA usa por ambiente, e obter
      `TOKEN_ENCRYPTION_KEY` e `S2S_API_SECRET` próprios — nunca reaproveitar os dos irmãos.

## 2. TEST — antes do código

- [ ] 2.1 Traduzir cada cenário do delta spec em teste de comportamento.
- [ ] 2.2 Teste de ciclo completo com fila e banco de teste: miss → `202 + job_id` → worker →
      `200`, sem apurar no processo da API.
- [ ] 2.3 Teste que falha se `versao_regras` divergente servir cache.
- [ ] 2.4 Teste de lock: segunda requisição não enfileira segundo job; lock órfão é liberado.
- [ ] 2.5 Teste de fronteira de camada: `domain/` sem import de `requests`, `pandas`, `yaml`,
      `sqlalchemy`, `redis` ou `fastapi` — falha o build se alguém cruzar.
- [ ] 2.6 Testes de auth: `401` sem JWT, `403` para ente não autorizado, recusa de credencial de
      fonte vinda de browser.
- [ ] 2.7 Teste de vigência: a carga recebe o exercício e resolve a maior vigência `<=` a pedida;
      exercício anterior a toda vigência falha nomeando as disponíveis, sem aproximar.
- [ ] 2.7.1 Teste INSERT-only: publicar correção acrescenta vigência e a anterior continua legível;
      tentativa de alterar ou remover é recusada.
- [ ] 2.7.2 Teste de seed: a partir dos YAMLs, o banco passa a ter vigência utilizável marcada como
      `seed-yaml`, e a apuração passa a ler do banco.
- [ ] 2.8 Teste de procedência e diagnóstico: o resultado gravado identifica regras, edição
      normativa e versão das tabelas STN, e lista células não apuradas — tudo sem reapurar.
- [ ] 2.8.1 Teste de estabilidade do hash: reescrever os YAMLs com CRLF, reordenar chaves e
      reindentar **não** muda `versao_regras`; alterar uma conta **muda**.
- [ ] 2.9 Teste de reprocessamento: com cache `ok` cria job; não escapa do lock; resultado anterior
      permanece legível durante a reapuração; `403` sem autorização.
- [ ] 2.10 Rodar e confirmar que falham pelo motivo esperado.

## 3. IMPLEMENT — F2 (transporte)

- [ ] 3.1 `main.py` — app FastAPI, lifespan com pool `arq`, agregador único de routers.
- [ ] 3.2 `app/core/` — config por ambiente, engine e sessão, logging.
- [ ] 3.3 `app/auth/` — JWT + `X-Unidade-Id`; recusa de `x-authorization`/`token_ps` de browser.
- [ ] 3.4 Rota de leitura do anexo — fina: valida, lê cache, enfileira, responde.
- [ ] 3.5 Rota de reprocessamento (P7) — mesma autorização da leitura e mesmo lock; registra o
      solicitante; não apaga o resultado anterior antes de o novo existir.

## 4. IMPLEMENT — F3 (pipeline)

- [ ] 4.1 `infra/cache/` — model `dca_anexo_cache` e repository; `alembic/env.py` com
      `version_table="alembic_version_dca"` (offline e online), guarda contra marcador em
      `alembic_version` órfão e advisory lock `43812/1001` com `ALEMBIC_LOCK_TIMEOUT_SECONDS`;
      migration inicial. Histórico próprio — sem encadear no stub do RREO.
- [ ] 4.1.1 `infra/regras/banco.py` — model `dca_regra_mapeamento` (INSERT-only, PK
      `(anexo, ano_vigencia, mes_vigencia)`), resolução pela maior vigência `<=` a pedida, e
      comando de seed a partir dos YAMLs (`origem: seed-yaml`).
- [ ] 4.1.2 Rota administrativa de publicação de vigência (`origem: api-admin`), registrando o
      autor. Recusa alteração e remoção de vigência existente.
- [ ] 4.2 `services/pipeline/cache.py` — **um** service parametrizado por anexo, com a regra de
      invalidação por `versao_api` e `versao_regras`, e a gravação do solicitante do
      reprocessamento.
- [ ] 4.3 `infra/fila/` — `job_manager` (JSON, token cifrado, TTL) e **um** lock com recuperação de
      órfão.
- [ ] 4.4 `worker.py` — `WorkerSettings`, fila `arq:queue:dca`, limpeza de locks no startup,
      diagnóstico de Redis/Postgres.
- [ ] 4.5 `services/pipeline/registry.py` e resumo agregado — ordem canônica dos anexos,
      `sem_cache` para o que ainda não existe.
- [ ] 4.6 Polling de job e stream SSE.
- [ ] 4.7 Notificação Discord ao fim do job, disparada pelo worker, reusando
      `discord_notifier.py` do RGF. Falha de webhook não altera o desfecho do job.
- [ ] 4.8 Infra de execução: `docker-compose.yml` (`api` + `worker` na rede externa `ps-infra`),
      `Dockerfile.api`, `Dockerfile.worker`, `captain-definition-*`, `.env.example`.

## 5. REVIEW

- [ ] 5.1 Nenhum import de infraestrutura em `domain/`.
- [ ] 5.2 Nenhuma regra de cálculo em `routes/` ou em `worker.py`.
- [ ] 5.3 Uma tabela de cache, um service de cache, um lock — nenhuma cópia por anexo.
- [ ] 5.4 Nenhum `pickle` em job; nenhum token de fonte em texto claro no Redis.
- [ ] 5.5 Fila própria e prefixo `dca:` em toda chave de job, lock e resultado. Cache de MSC
      permanece no espaço comum (`msc_cache:`) — não isolar o que é reuso legítimo.
- [ ] 5.5.1 Nenhum segredo em arquivo versionado; `.env.example` só com nomes e valores neutros.
- [ ] 5.6 Toda tabela da DCA com prefixo `dca_*`; histórico em `alembic_version_dca`; nenhuma
      migration tocando objeto de RREO ou RGF.
- [ ] 5.7 Rota de anexo faz **só** validar, ler cache, enfileirar e responder. Nenhuma conta,
      filtro, consulta a fonte ou composição de demonstrativo no arquivo de rota — o erro medido
      em `regras-rreo-api/app/routes/anexo_08/rota_anexo_08.py` (114 KB).
- [ ] 5.8 Cada função registrada no worker é um wrapper fino que delega ao service. Nenhuma regra
      em `worker.py` — o erro medido em `regras-rgf-api/worker.py` (68 KB).
- [ ] 5.9 Identificador de anexo é conjunto fechado, validado na borda e restringido no banco.
- [ ] 5.10 Nenhum ponto do código escolhe regra sem receber o exercício.
- [ ] 5.10.1 Nenhum `UPDATE` ou `DELETE` sobre `dca_regra_mapeamento` em código de produção.
- [ ] 5.10.2 A apuração lê o mapeamento do banco; leitura direta de YAML só no seed e em teste.
- [ ] 5.11 Todo resultado persistido carrega procedência e diagnóstico — nenhum grava só valores.
- [ ] 5.12 `versao_regras` não é calculada sobre bytes de arquivo, e nenhuma versão de regra é
      declarada à mão como critério de invalidação.

## 6. VERIFY

- [ ] 6.1 `python -m pytest` — reportar `N passed / M failed`.
- [ ] 6.2 `python -m ruff check .` — reportar resultado real.
- [ ] 6.3 `alembic upgrade head` em banco limpo — reportar resultado real, e confirmar que o
      marcador ficou em `alembic_version_dca` e que nenhuma tabela sem prefixo `dca_*` foi criada.
- [ ] 6.3.1 Rodar o upgrade contra um banco que já contenha as tabelas de RREO/RGF e confirmar que
      nada dos irmãos foi alterado.
- [ ] 6.4 Subir `api` + `worker` com o Redis de `ps-infra` e apurar o quadro principal do BO pelo
      ciclo completo: miss → job → cache → `200`, com os 11 valores de
      `docs/validacao-bo-jp-2025.md` conferidos na resposta HTTP.
- [ ] 6.5 Reiniciar a API com job em voo e confirmar que o resultado é gravado mesmo assim.

## 7. Arquivamento

- [ ] 7.1 `tasks.md` 100% atualizado.
- [ ] 7.2 Mesclar o delta em `openspec/specs/pipeline/plataforma/spec.md`.
- [ ] 7.3 Mover para `openspec/changes/archive/AAAA-MM-DD-plataforma-pipeline-dca/`.
- [ ] 7.4 Atualizar a tabela "Change ativa" em `openspec/AGENTS.md`.
