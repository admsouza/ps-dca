# Design — Plataforma de pipeline da DCA

**Change:** `openspec/changes/plataforma-pipeline-dca/` · **Aprovada pelo PO em:** 2026-09-04 (Jackson S. da Silva (PO))

## 1. Processos

Dois processos, mesmo código, comunicação só pelo Redis — igual a RREO e RGF.

```
┌─────────┐  HTTP   ┌──────────────┐ enfileira ┌─────────────┐
│  front  │ ──────► │  API         │ ────────► │   Redis     │
│         │ ◄────── │  (FastAPI)   │           │ fila+locks  │
└─────────┘ 202+job └──────┬───────┘           └──────┬──────┘
     ▲                     │ lê cache                 │ consome
     │ polling / SSE       ▼                          ▼
     │              ┌──────────────┐          ┌───────────────┐
     └───────────── │  PostgreSQL  │ ◄─────── │ worker (arq)  │
        resultado   │ dca_anexo_   │  grava   │ apura o anexo │
                    │ cache (JSONB)│          └───────┬───────┘
                    └──────────────┘                  │ MSC
                                                      ▼
                                            SICONFI · PublicSoft
```

**API** — valida auth e parâmetros, lê cache, enfileira quando falta. Nunca apura.
**Worker** — consome a fila, chama o service de apuração, grava cache. Dono do ciclo de vida dos
jobs e da limpeza de locks órfãos no startup.

Por que fila e não cálculo no request: a apuração lê a MSC inteira do ente e estoura o timeout de
gateway (~55s) muito antes de terminar; o desenho já está justificado em
`regras-rreo-api/ARCHITECTURE.md` §3 e não é reaberto aqui.

## 2. Camadas e regra de dependência

Dependências apontam **para dentro**. O núcleo não conhece HTTP, banco, fila, `pandas` nem YAML.

```text
app/
├─ domain/                   # NÚCLEO — puro, sem I/O, sem framework
│  ├─ bo/                    #   apuração do Balanço Orçamentário (change do BO)
│  └─ pipeline/              #   identidade do resultado, estados, versão de regras
├─ services/                 # ORQUESTRAÇÃO — síncrona, sem estado, sem Depends
│  ├─ bo/quadro_principal.py #   mapa + fonte + direção -> Matriz
│  └─ pipeline/              #   cache service (1), registry (1), resumo agregado (1)
├─ infra/                    # BORDA — implementa as portas do domínio
│  ├─ msc/                   #   adapters SICONFI e PublicSoft
│  ├─ pcasp/                 #   natureza do saldo por conta folha
│  ├─ regras/                #   carregador de knowledge/rules/**.yaml
│  ├─ cache/                 #   models SQLAlchemy + repository
│  └─ fila/                  #   job_manager e lock (Redis)
├─ routes/<anexo>/           # HTTP — rota fina; valida, lê cache, enfileira
├─ auth/                     # JWT + X-Unidade-Id
└─ core/                     # config, database, logging
main.py · worker.py · alembic/
```

**A regra em uma frase:** `services/` pode importar `domain/` e `infra/`; `domain/` não importa
ninguém; `routes/` e `worker.py` só importam `services/`. O teste 4.x da change do BO já verifica a
metade que lhe cabe (`domain/` sem `requests`, `pandas`, `yaml`).

O que torna isso diferente de RREO/RGF, concretamente: lá o cálculo importa `requests` e monta
DataFrame; aqui a fonte de dados entra por `Protocol` (`FonteSaldos`, `DirecaoSaldo`), e a mesma
função de apuração roda em teste com uma lista literal de registros, sem container.

## 3. O ciclo de uma requisição

Idêntico ao de RREO/RGF, com o estado explícito:

1. `GET /dca/<anexo>?anReferencia=2025` — valida JWT e `X-Unidade-Id`.
2. Lê `dca_anexo_cache` pela chave de identidade:
   - `ok` e versões conferem → **200** com o resultado;
   - `processando` → **202** sem `job_id` (já há job em voo);
   - ausente, `erro` ou versão divergente → cria job, adquire lock, enfileira, **202 + `job_id`**.
3. Worker consome → `services/bo/quadro_principal.apurar(...)` → grava `ok` ou `erro`, libera lock.
4. Cliente acompanha por `GET /jobs/{job_id}` ou pela stream SSE.

**Lock por identidade**, em uma implementação só — não uma cópia por anexo, como nos outros dois
repositórios. Lock cujo job não está mais `processing` é órfão: liberado e o processamento recomeça.

## 4. Identidade do resultado e invalidação

A DCA é anual e consolidada (`periodicidade=A`, `periodo=1`, poder `-`), o que simplifica a chave em
relação ao RGF, que carrega periodicidade, período e poder.

```
identidade = (id_ente, an_referencia, anexo)
invalida se: versao_api != atual   ou   versao_regras != atual
```

`versao_regras` é o que a DCA tem e os irmãos não: a regra vive em `knowledge/rules/**.yaml`,
versionada e com hash. Editar uma conta no YAML **tem** de invalidar o cache — se a invalidação
dependesse só de `versao_api`, uma correção de regra sem bump de código serviria resultado velho.

Tabela única:

```
dca_anexo_cache
  id_ente         varchar(7)   PK
  an_referencia   smallint     PK
  anexo           varchar(20)  PK        -- 'BO', 'I-C', 'I-D', …
  resultado       jsonb        not null
  status          varchar(20)  not null  -- ok | processando | erro
  versao_api      varchar(20)
  versao_regras   varchar(64)            -- hash/versão da base canônica
  calculado_em    timestamptz
  duracao_ms      integer
  erro_detalhe    text
  solicitado_por  integer                -- usuário do reprocessamento forçado (P7)
  procedencia     jsonb                  -- regras aplicadas, edição normativa, versão das tabelas STN (P9)
  diagnostico     jsonb                  -- células não apuradas com motivo, resíduos, duração
```

Uma tabela, não sete. O payload é JSONB nos dois pipelines existentes; sete models idênticos só
existem lá por acúmulo histórico, e são o que obriga `services/cache_rgf/resumo.py` a importar seis
services para fazer a mesma pergunta.

## 4bis. Onde vive a regra

Duas naturezas de conteúdo, dois lugares (P10):

- **Transcrição normativa** — as 69 linhas do IPC 07 com `source.page`, `evidence.text` e hash do
  PDF — fica em `knowledge/rules/**.yaml`, versionada em git e revisada por PR. É documento.
- **Mapeamento vigente** — o que de fato entra em cada linha ao apurar — fica em banco, e é de onde
  a apuração lê. É configuração operacional, e o PO publica correção sem deploy.

```
dca_regra_mapeamento
  anexo          varchar(20)  PK        -- mesma lista fechada do cache
  ano_vigencia   smallint     PK
  mes_vigencia   smallint     PK        -- 1..12; DCA publica com 1
  versao         varchar(40)  not null
  linhas         jsonb        not null  -- shape achatado do contrato de cálculo
  origem         varchar(20)  not null  -- seed-yaml | api-admin
  criado_em      timestamptz  not null
  criado_por_usuario_id integer
```

**INSERT-only.** Corrigir é publicar nova vigência; não há `UPDATE` nem `DELETE`. A resolução no
cálculo é a maior vigência `<=` a competência pedida — exatamente o padrão de
`regras-rgf-api/app/models/rgf_anexo02_mapeamento.py`, que já roda em produção.

Duas correções em relação a ele:

1. **Uma tabela, coluna `anexo`** — o RGF tem uma por anexo e registra a dívida no docstring do A03
   (*"a unificação com o A02 segue em aberto na CH-05 (P2)"*). Mesma decisão P-D1 do cache.
2. **`versao_regras` é hash do conteúdo carregado do banco**, canonicalizado — some a armadilha de
   CRLF que P-D7 descreve para arquivos.

O carregador (`infra/regras/`) implementa a porta do domínio e passa a ter duas implementações: a de
banco, usada em produção, e a de YAML, usada no seed e nos testes da F1 — que assim não precisam de
Postgres. O domínio não sabe de qual das duas veio.

## 5. Infra

### Local

Redis vem de `C:\Projetos\ps-infra` (rede externa `ps-infra`, container `redis_cache`) — esta change
**não** sobe outro Redis. O compose da DCA declara `api` e `worker`, ambos em `ps-infra`, com
Postgres em `host.docker.internal`, como o RGF já faz.

### Imagens e deploy

Duas imagens da mesma base Python 3.11-slim, usuário não-root: `Dockerfile.api`
(`gunicorn main:app` com `UvicornWorker`) e `Dockerfile.worker` (`arq worker.WorkerSettings`).
Deploy CapRover, um `captain-definition` por imagem.

### Variáveis de ambiente

Levantadas dos `.env` reais de `regras-rreo-api` e `regras-rgf-api` em 2026-09-04. Mesmos nomes
sempre que a variável significa a mesma coisa — num monolito modular, nome divergente para o mesmo
conceito transforma `.env` de produção em adivinhação.

Dois achados desse levantamento estão anotados logo abaixo da tabela, porque contrariam o que este
design dizia antes.

| Variável | Valor na DCA | Efeito |
|---|---|---|
| `POSTGRES_HOST` · `POSTGRES_PORT` · `POSTGRES_USER` · `POSTGRES_PASSWORD` | os do hub | conexão; padrão do RGF, sem URL-encoding manual de senha |
| `POSTGRES_DB` | `db-ps-rreo-rgf-dca` | **o banco já existe e já nomeia a DCA** |
| `DATABASE_URL` | — | forma usada pelo RREO; aceita como alternativa, resolvida depois de `POSTGRES_*` |
| `DB_POOL_SIZE` / `DB_MAX_OVERFLOW` | 5 / 10 | pool próprio; RREO usa 20/60 e RGF 5/10 na mesma instância |
| `DB_ECHO` · `DB_CONNECT_TIMEOUT` | false · 10 | idem RREO |
| `RUN_MIGRATIONS` | true | `alembic upgrade head` no boot |
| `ALEMBIC_LOCK_TIMEOUT_SECONDS` | 120 | advisory lock compartilhado `43812/1001` |
| `REDIS_HOST` · `REDIS_PORT` · `REDIS_DB` · `REDIS_PASSWORD` | os do hub | Redis compartilhado |
| `REDIS_PREFIX` | **`msc_cache:`** | prefixo do cache de MSC — **compartilhado de propósito** com os irmãos |
| `REDIS_SOCKET_TIMEOUT` · `REDIS_SOCKET_CONNECT_TIMEOUT` · `REDIS_MAX_CONNECTIONS` | 5 · 5 · — | idem irmãos |
| `DCA_ARQ_QUEUE_NAME` | `arq:queue:dca` | fila própria |
| `PIPELINE_MAX_CONCORRENTES` | 2–4 | `max_jobs` do worker (RREO usa 2) |
| `WEB_WORKERS` · `WEB_TIMEOUT` | 1 · 300 | gunicorn |
| `DCA_JOB_TIMEOUT_SECONDS` / `DCA_JOB_TTL_SECONDS` | 3600 | timeout e TTL de job |
| `SECRET_KEY` · `ALGORITHM` · `ACCESS_TOKEN_EXPIRE_MINUTES` | do hub · `HS256` · — | JWT verificado localmente |
| `TOKEN_ENCRYPTION_KEY` | própria | cifra do token de fonte no Redis — chave dedicada, não derivada do `SECRET_KEY` |
| `S2S_API_SECRET` | do hub | chamada service-to-service entre os módulos |
| `AUTH_API_URL` | do hub | confirmação de usuário ativo |
| `DATA_SOURCE` | `siconfi` | fonte padrão |
| `SICONFI_TIMEOUT` · `SICONFI_POOL_MAXSIZE` | 30 · 12 | fonte SICONFI |
| `PUBLICSOFT_API_URL` · `PUBLICSOFT_AUDIT_URL` · `PUBLICSOFT_TIMEOUT` · `PUBLICSOFT_POOL_MAXSIZE` · `PUBLICSOFT_SSL_VERIFY` | os do hub | fonte PublicSoft |
| `DISCORD_WEBHOOK_URL` | do hub | notificação de fim de job (P6) |
| `ENVIRONMENT` · `DEBUG` · `ENABLE_SWAGGER` · `ENABLE_SWAGGER_PUBLIC` · `CORS_ORIGINS` | — | ambiente e exposição |
| `LOG_LEVEL` · `APP_LOG_LEVEL` · `WORKER_LOG_LEVEL` · `ARQ_LOG_LEVEL` · `PIPELINE_LOG_LEVEL` · `NOTIFICATION_LOG_LEVEL` | `WARNING` no root, `INFO` nos operacionais | verbosidade por componente, padrão do RREO |
| `DIAGNOSTICO_INFRA` · `DIAGNOSTICO_INFRA_DB_MIN_MS` | false · 25 | logs `[DIAG]` de latência de query |

**Achado 1 — o banco já se chama `db-ps-rreo-rgf-dca`.** A DCA estava prevista na instância desde o
começo. Não há banco novo a criar, e isso confirma P5: compartilhado, separado por prefixo de tabela
e `alembic_version_dca`.

**Achado 2 — `REDIS_PREFIX=msc_cache:` é idêntico nos dois irmãos, e deve continuar assim.** Este
design dizia antes que o prefixo seria `dca`, para isolar. Errado: esse prefixo nomeia o **cache dos
dados da MSC**, que são os mesmos para os três pipelines — mesmo ente, ano, mês e classe. Compartilhar
é reuso real: a MSC de João Pessoa baixada pelo RREO serve à DCA sem nova consulta à fonte.

O isolamento que importa é o do **estado de execução**, e esse é outro conjunto de chaves: jobs,
locks e resultados. No RGF eles vivem sob o prefixo `rgf` fixado em `app/utils/job_manager.py`; na
DCA, sob `dca`. Portanto:

| Categoria de chave | Prefixo | Por quê |
|---|---|---|
| cache de dados MSC | `msc_cache:` — **comum** | mesmo dado, mesma fonte; baixar três vezes é desperdício |
| job, lock, resultado | `dca:` — **próprio** | estado de execução de um pipeline não é do outro |

### Banco e migrations

**Mesma instância e o mesmo schema `public` de RREO e RGF** (P5). O ambiente é um monolito modular:
hub, Postgres e Redis são compartilhados, e a separação entre projetos é por convenção de nome, como
os dois irmãos já praticam:

| Mecanismo | RREO | RGF | DCA |
|---|---|---|---|
| Prefixo de tabela | `rreo_*` | `rgf_*` | `dca_*` |
| Tabela de versão do Alembic | `alembic_version_rreo` | `alembic_version_rgf` | **`alembic_version_dca`** |
| Advisory lock de migration | `43812 / 1001` | `43812 / 1001` | **as mesmas** |

Três consequências operacionais, todas na F3:

1. **`version_table="alembic_version_dca"`** no `env.py`, offline e online. Com a mesma guarda que o
   RGF tem: se o marcador aparecer em `alembic_version` (sem sufixo), abortar — é sintoma de alguém
   ter rodado `alembic upgrade`/`stamp` com config sem `version_table`, e o histórico do projeto
   errado seria sobrescrito.
2. **Advisory lock com as mesmas chaves dos irmãos** (`43812`, `1001`), timeout em
   `ALEMBIC_LOCK_TIMEOUT_SECONDS`. Compartilhar a chave é deliberado: como os três dividem o schema,
   o lock serializa migrations **entre projetos**, não só entre réplicas do mesmo.
3. **Histórico de revisões independente.** O RGF encadeia sobre um stub do RREO
   (`021_rreo_head_stub`); a DCA **não** encadeia — nasce com histórico próprio. Encadear acopla o
   deploy dos projetos, e o advisory lock já resolve a concorrência que o encadeamento tentava
   endereçar.

`alembic upgrade head` roda no boot do container, atrás de `RUN_MIGRATIONS`, como no RGF.

### Notificação

Discord ao fim de cada job (P6), como nos irmãos: webhook em `DISCORD_WEBHOOK_URL`, disparado pelo
**worker**, com ente, exercício, anexo, duração e desfecho. Notificação NUNCA altera o desfecho do
job — falha de webhook é logada e ignorada. Reuso direto de `app/utils/discord_notifier.py` do RGF
(`notificar`, `fmt_duracao`, `label_ente`).

## 6. Segurança

Herdado sem exceção de RREO/RGF: JWT `HS256` verificado localmente, `X-Unidade-Id` (`cod_ibge`)
autorizando o ente, e recusa de `x-authorization`/`token_ps` vindos de browser. Token de fonte
guardado no Redis só pelo TTL do job e **cifrado** — o `job_manager` do RGF usa Fernet derivada de
`SECRET_KEY`, e o motivo está no próprio arquivo: acesso ao Redis não pode virar acesso ao token
(OWASP A02). Serialização de job em JSON, nunca `pickle`.

## 6bis. Anti-padrões medidos nos irmãos, e a barreira de cada um

Medição feita em 2026-09-04 sobre os dois repositórios. Não é crítica retrospectiva: cada linha é um
caminho que a DCA percorreria de novo se nada a impedisse.

| Medido | Onde | Barreira na DCA |
|---|---|---|
| rota de **114 KB** com cálculo dentro | `regras-rreo-api/app/routes/anexo_08/rota_anexo_08.py` | requisito "rota e worker apenas orquestram" + check 5.7 |
| orquestrador de **66–68 KB** | `regras-rreo-api/app/routes/jobs_rreo_completo.py`, `regras-rgf-api/worker.py` | função de job é wrapper fino que delega ao service — check 5.8 |
| **6** arquivos de lock órfão | `regras-rgf-api/app/services/anexo_0{2..5}/orfaos.py`, `utils/rgf_orfaos.py`, `services/rgf/lock_anexo.py` | um lock, no núcleo de pipeline — requisito e check 5.3 |
| **6** services de cache quase iguais | `regras-rgf-api/app/services/anexo_0{1..6}/cache*` | um service parametrizado — requisito e check 5.3 |
| identificador de anexo como string livre | ambos | conjunto fechado, validado na borda e no banco — requisito próprio |

O ponto que a medição deixa claro: o `ARCHITECTURE.md` do RREO **já dizia** "nunca lógica de cálculo
na rota" (§13), e a rota de 114 KB existe assim mesmo. Princípio sem verificação não segura nada —
por isso cada linha da tabela tem um item de REVIEW correspondente, não só uma frase de design.

## 7. Decisões

**P-D1 — Uma tabela e um service de cache, parametrizados por anexo.**
Descartado: um por anexo, como RREO e RGF.
Porquê: o payload é JSONB e o ciclo é idêntico; o que varia é o conteúdo, que já está no JSON. A
prova de que a replicação custa está nos irmãos — seis services de cache e quatro cópias de lock,
uma delas com comentário admitindo o débito.

**P-D2 — `versao_regras` na chave de invalidação.**
Descartado: só `versao_api`, como nos irmãos.
Porquê: na DCA a regra é dado versionado, fora do código. Sem isso, corrigir um YAML não invalida
nada e o cache serve número errado — falha silenciosa, a pior categoria num demonstrativo fiscal.

**P-D3 — Núcleo puro, fontes por `Protocol`.**
Descartado: o padrão atual, com `requests`/`pandas` alcançáveis do cálculo.
Porquê: é o que permite verificar os 11 valores do BO sem subir container, e o que impede que a
próxima fonte de dados obrigue a mexer em regra.

**P-D4 — Fila com nome próprio (`arq:queue:dca`).**
Porquê: mesmo Redis dos outros dois pipelines. Nome compartilhado faria worker do RGF consumir job
da DCA.

**P-D8 — Mapeamento vigente em banco, INSERT-only; transcrição normativa em YAML.**
Descartado: tudo em YAML com deploy a cada correção; e tudo em banco, inclusive a transcrição.
Porquê: são conteúdos de natureza diferente. A transcrição do IPC carrega página, literal e hash do
PDF — editável por admin, perde a rastreabilidade que é a entrega inteira da change
`ipc07-bo-regras-canonicas`. O mapeamento vigente muda quando o STN republica e precisa de correção
sem release. INSERT-only porque um demonstrativo já publicado precisa continuar explicável pela
regra da época — `UPDATE` apagaria a única prova de qual regra produziu o número.

**P-D7 — `versao_regras` é hash canônico; a edição declarada acompanha, não substitui.**
Descartado: versão declarada à mão como único identificador, no modelo `_VERSAO_API = "3.3.1"` do
`regras-rgf-api/app/services/anexo_01/cache/service.py`.
Porquê: versão manual depende de alguém lembrar de incrementar, e quem esquece não recebe erro — o
cache serve resultado apurado pela regra antiga e o número errado sai assinado. Falha silenciosa é
inaceitável num demonstrativo fiscal. O hash muda sozinho quando a regra muda.

As duas coexistem porque respondem perguntas diferentes: o hash responde *é o mesmo conteúdo?* e
invalida o cache; a edição declarada (`IPC07 2020-01`) responde *qual regra se quis aplicar?* e é o
que um auditor lê. Ambas entram na procedência (P9); só o hash entra na invalidação.

**Canonicalizar antes de hashear** — sobre o conteúdo parseado e reserializado de forma estável
(chaves ordenadas, UTF-8, LF), nunca sobre o arquivo bruto. Hash de bytes crus muda com um
`git checkout` que troque LF por CRLF no Windows, e invalidaria o cache inteiro sem regra nenhuma
ter mudado.

Escopo do hash: o mapeamento **efetivamente carregado** para o exercício apurado — a vigência
resolvida no banco — mais as tabelas de `docs/contas-stn/` usadas. Publicar vigência de outro anexo
não pode invalidar este.

**P-D6 — Job por anexo primeiro; pipeline completo depois.**
Descartado: já entregar o job único que percorre os 7 anexos, como o RREO.
Porquê: só um anexo existe. O pipeline completo é orquestração sobre jobs que ainda não foram
escritos, e o registry — que ele consome — já nasce pronto. Quando o segundo anexo existir, o
pipeline completo é uma change pequena; hoje seria código sem consumidor.

**P-D5 — Especificar agora, implementar na F2/F3.**
Porquê: o custo de encaixar um anexo pronto num fluxo inventado depois é maior que o de escrever o
contrato antes. Mas a F1 do BO não espera por isto — ela é verificável por CLI (D6 da change do BO).

## 8. Pendências

- P4, P5 e P6 **resolvidos** pelo PO em 2026-09-04 — ver `proposal.md` › Decisões.
- P7 (reprocessamento forçado) **entra** nesta change; P8 (seleção de regra por exercício)
  **adiada com gatilho** — decidir antes de apurar o segundo exercício ou de publicar edição nova
  de IPC. `versao_regras` invalida por versão, não por vigência: força reapuração, mas não escolhe
  a edição correta.
- Proposta, design e delta spec **aprovados pelo PO em 2026-09-04** (task 0.8). Fase SPEC fechada.
