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

- [x] 1.1 Fechado em `design.md` § 4bis, "O registry e o resumo agregado". Ordem canônica
      `("BO", "I-AB", "I-C", "I-D", "I-E", "I-F", "I-G", "I-HI")` — o `BO` à frente por ser o
      derivado da MSC, os 7 da DCA na ordem do SICONFI. Um job parametrizado por anexo (P4);
      anexo sem implementação entra com `servico: null` e o resumo o reporta `sem_cache`. O
      pipeline completo consome a mesma tupla como ordem de execução.
- [x] 1.2 As 11 fixadas em `pyproject.toml`, extra `plataforma` — extra, e não `dependencies`,
      enquanto nada em `app/` as importa; migram quando a F2 entrar. A garantia de não serem
      alcançáveis a partir de `domain/` é executável: `tests/test_fronteira_camadas.py` (task 2.5).
- [x] 1.3.0 Fechado em `design.md` § 4bis, "O shape de `linhas`". Array 1:1 com `Linha`, `Coluna`,
      `ContaCC`, `Filtro`, `RefColuna` e `RefLinha` de `app/domain/bo/modelo.py`, sem a transcrição
      normativa (que não é lida ao apurar). Três pontos que o seed herda: `exclusoes` é array **de
      arrays** (D2), `natureza_saldo` fica reservado na conta para quando C6 fechar, e nenhum
      `Decimal` atravessa o shape.
- [x] 1.3 Implementado em `app/infra/regras/carregador.py::_hash_canonico`. **Lacuna corrigida
      nesta sessão:** o hash cobria só as regras — os hashes das tabelas STN iam para a procedência
      mas **não entravam na invalidação**, então uma tabela de natureza de receita corrigida
      serviria cache velho. Agora o payload canônico é
      `{"regras": [...], "tabelas_stn": {...}}`, com `sort_keys=True`, UTF-8 e sobre o conteúdo
      **parseado** (imune a CRLF). A edição (`IPC07 2020-01`) segue só na procedência.
- [x] 1.4 Acesso confirmado e schema levantado em 2026-09-04, por inspeção read-only do banco
      real `db-ps-rreo-rgf-dca` (PostgreSQL 18.0, `localhost:5432`). **44 tabelas, todas em
      `public`.** Três achados que confirmam P5:
      - **`dca_*`: zero tabelas.** O espaço de nomes da DCA está livre — nenhuma colisão.
      - **Não existe `alembic_version` órfão**: só `alembic_version_rgf` (`060_token_ps_validacao_status`)
        e `alembic_version_rreo` (`032`). `alembic_version_dca` é livre, e a guarda da task 4.1
        continua valendo como defesa, sem caso hoje.
      - O RGF tem **uma tabela de cache por anexo** (`rgf_anexo01..06_cache`) e **uma de mapeamento
        por anexo** (`rgf_anexo02..05_mapeamento`) — o acúmulo que P-D1 evita com tabela única.
- [x] 1.5 Nomes de variáveis levantados dos `.env` reais de RREO e RGF em 2026-09-04 e
      consolidados em `design.md` §5. Dois achados: o banco já é `db-ps-rreo-rgf-dca`, e
      `REDIS_PREFIX=msc_cache:` é comum aos dois — nomeia o cache de MSC, que deve continuar
      compartilhado; o isolamento é só do estado de execução (`dca:`).
- [x] 1.6 Resolvido em 2026-09-04. `.env` criado (fora do git, `.gitignore` linha 10) e
      `.env.example` atualizado com os mesmos nomes e **placeholders vazios**:
      - **Herdado do `regras-rgf-api`**, compartilhado de propósito: `POSTGRES_HOST/PORT/USER/
        PASSWORD/DB` (banco `db-ps-rreo-rgf-dca`) e as 7 variáveis de Redis, incluindo
        `REDIS_PREFIX=msc_cache:`.
      - **Gerado próprio da DCA**, nunca copiado: `SECRET_KEY`, `S2S_API_SECRET` e
        `TOKEN_ENCRYPTION_KEY` (Fernet, 32 bytes urlsafe base64). Vazamento em um irmão não
        compromete a DCA.
      Ambiente de produção ainda não confirmado — o `.env` atual é `development`.

## 2. TEST — antes do código

**Concluída: 63 dos 63 cenários cobertos.** Fundação pronta em `tests/pipeline/conftest.py` —
fakes em memória de repositório, fila e lock, implementando as mesmas portas que os adapters de
`infra/` vão implementar. Estado: **66 testes vermelhos**, e o resto da suíte segue verde (155).

- [x] 2.1 Traduzir cada cenário do delta spec em teste de comportamento. **63 de 63.** `tests/pipeline/test_ciclo.py` e `test_invalidacao.py`: `Ciclo único`,
      `Identidade e invalidação`, `Cache único`, `Anexo é conjunto fechado`.
      `tests/pipeline/test_execucao.py` (bloco 1 — contrato de execução): `Rota e worker apenas
      orquestram`, `Lock por identidade com recuperação de órfão`, `Apuração não roda no processo
      da API`, `Serviço chamável por rota, worker e CLI`, `Estado de execução isolado`, `Estado do
      job é serializado sem execução de código`.
      `tests/pipeline/test_mapeamento.py` (bloco 2 — mapeamento e regras): `Regra vigente é
      resolvida pelo exercício apurado`, `Mapeamento vigente é publicado sem sobrescrever o
      anterior`, `Procedência do valor apurado`.
      `tests/pipeline/test_transporte.py` (bloco 3 — API e observabilidade): `Acompanhamento por
      polling e por stream`, `Resumo agregado responde sempre`, `Diagnóstico da apuração acompanha
      o resultado`, `Conclusão de job é notificada`, `Autorização por unidade em toda rota de
      anexo`.
      `tests/pipeline/test_reprocessamento.py` (4) e `test_infra.py` (bloco 4 — banco
      compartilhado, núcleo isolado e falha de infraestrutura, 8).
      `pipeline/plataforma` entrou em `COM_TESTES` (`tests/test_cobertura_spec.py`): daqui para a
      frente, cenário sem teste quebra o build.
- [ ] 2.2 Teste de ciclo completo com fila e banco de teste: miss → `202 + job_id` → worker →
      `200`, sem apurar no processo da API. **Coberto com fakes** em
      `test_redeploy_da_api_nao_interrompe_job` e `test_cache_miss_nao_bloqueia_a_resposta`
      (a apuração é monkeypatchada para explodir se a rota a chamar). Falta a versão com fila e
      Postgres reais, que entra na F3.
- [x] 2.3 `test_versao_de_regras_divergente_nao_serve` e `test_alteracao_real_de_regra_invalida`.
      Cobre também o inverso — `test_regra_de_outro_anexo_nao_invalida` —, que é o que impede um
      hash global de reapurar os sete anexos de todos os entes por uma linha do BO.
- [x] 2.4 `tests/pipeline/test_execucao.py` — `test_segundo_job_para_a_mesma_identidade`,
      `test_worker_reiniciado_deixa_lock_orfao` e `test_limpeza_no_startup_do_worker`.
      **Tensão de spec, fechada em 2026-09-08 por medição do front** (ver §3): o requisito do lock
      mandava devolver "o `job_id` existente" e o `Scenario: processamento já em voo` mandava `202`
      **sem** `job_id`. Vale o contrato dos irmãos — `job_id` do job em voo com
      `status: already_queued` —, e o delta spec foi corrigido nos dois lados.
      A limpeza de órfãos no startup ficou em `app.services.pipeline.startup.preparar(lock)`, e
      não em `worker.py`: mantém o worker como wrapper fino e o startup testável sem `arq`.
- [x] 2.5 `tests/test_fronteira_camadas.py`. Percorre o **fecho transitivo** dos imports `app.*`
      a partir de `app/domain/**` via `ast` — um domínio limpo que importe módulo de `infra/` que
      importe `sqlalchemy` está igualmente contaminado, e o teste pega. Cobre as 14 proibidas
      (as 6 da task + `arq`, `alembic`, `psycopg2`, `uvicorn`, `gunicorn`, `pydantic`, `jose`,
      `cryptography`). Verificado por injeção: `import sqlalchemy` em `domain/bo/saldo.py` derruba
      o teste nomeando o módulo.
- [x] 2.6 `tests/pipeline/test_transporte.py` — `test_token_ausente_ou_invalido`,
      `test_ente_diferente_do_autorizado`, `test_credencial_de_fonte_vinda_do_browser` e
      `test_token_de_fonte_no_armazenamento_do_job`.
      `autorizar(token, unidade, ente, verificar=None)` recebe a verificação de JWT por parâmetro:
      o teste roda sem `jose` e sem `SECRET_KEY`, e a unidade é confrontada **com o token**, não
      aceita do cabeçalho cru. O teste da credencial procura o segredo em claro no armazenamento —
      é o que um `dump` do Redis mostraria (OWASP A02).
- [x] 2.7 `tests/pipeline/test_mapeamento.py` — `test_exercicio_e_parametro_da_carga_de_regras`
      (duas edições publicadas, 2020 e 2027; cada exercício recebe a sua) e
      `test_exercicio_sem_regra_vigente`. `SemVigencia` é a **mesma** exceção do carregador de
      YAML: a regra "não aproxima a mais próxima" não muda porque a fonte passou a ser o banco, e
      duplicar a exceção deixaria uma das duas metades sem teste.
- [x] 2.7.1 `test_correcao_publica_nova_vigencia`, `test_alteracao_destrutiva_e_recusada`,
      `test_origem_e_autoria_registradas`, `test_um_repositorio_para_todos_os_anexos` e
      `test_publicar_mapeamento_de_um_anexo_nao_afeta_outro`. `RepoVigenciasFake`
      (`tests/pipeline/conftest.py`) recusa insert sobre `(anexo, ano, mes)` como o `PRIMARY KEY`
      recusa no banco, e o teste ainda verifica que o módulo **não expõe** `atualizar`/`remover`.
- [x] 2.7.2 `test_semente_a_partir_da_transcricao_normativa`. Não basta "existe vigência": o teste
      compara os `rule_id` e a **matriz apurada** pelo mapa do banco contra a do YAML — semente que
      perde conteúdo no caminho passaria por um assert de contagem.
- [x] 2.8 Procedência e diagnóstico. `test_divergencia_e_explicavel_pelo_resultado_gravado`
      lê a procedência do registro com `qp.apurar` monkeypatchado para falhar — se explicar a
      divergência exigisse reapurar, o teste quebra. `test_mudanca_de_tabela_de_referencia_e_distinguivel`
      apura duas vezes com o sha256 de uma tabela STN trocado: mesma matriz, `tabelas_stn` e
      `versao_regras` distintos (premissa conferida contra o carregador da F1).
      Diagnóstico em `test_transporte.py`: `test_celula_nao_apurada_e_visivel_ao_consumidor`
      (conta fora do PCASP → 266 células declaradas com motivo, nunca `0`) e
      `test_apuracao_integra_tambem_declara_diagnostico` (vazio **declarado**, não omitido).
      As duas premissas foram medidas contra a F1 antes de escrever o assert.
- [x] 2.8.1 `test_identificador_de_regra_e_estavel_a_formatacao` e
      `test_alteracao_de_conta_muda_o_identificador` — **passam contra a F1**, sem precisar de
      F2/F3: o hash canônico já existe. Confere as duas direções de fim de linha (LF e CRLF),
      reindentação e reordenação de chaves.

      **Achado do próprio teste:** na primeira versão ele acusava instabilidade a CRLF, e eu
      cheguei a "corrigir" o `_hash_canonico` por isso. O diagnóstico estava errado — os YAMLs do
      repositório **já estão em CRLF**, e o `replace(b"\n", b"\r\n")` da fixture produzia
      `\r\r\n`, mudando a estrutura de linhas e, por dobra de escalar do YAML, o valor
      parseado. O teste media o seu próprio defeito. A alteração no produto foi **revertida**: ela
      resolvia problema inexistente e, pior, mascararia um `\r` legítimo dentro de escalar
      citado. A fixture passou a normalizar antes de gerar a variante.
- [x] 2.9 `tests/pipeline/test_reprocessamento.py` — os quatro cenários. Reprocessar é o **mesmo**
      `ler_ou_enfileirar`, com `forcar=True` e `solicitado_por`: caminho próprio duplicaria lock,
      cache e enfileiramento, que é a dívida dos irmãos. O teste do resultado anterior verifica o
      registro **durante** a reapuração — apagar antes de reapurar abriria janela de minutos com o
      anexo vazio.
- [x] 2.10 Rodar e confirmar que falham pelo motivo esperado.
      **66 vermelhos**, todos por `ModuleNotFoundError` dos módulos da F2/F3 ou por asserção de
      comportamento; 158 verdes.
      **Três testes passam antes da F2/F3, e é correto**: os dois do hash canônico (2.8.1) e
      `test_apuracao_testavel_sem_infraestrutura` / `test_troca_de_fonte_nao_altera_o_dominio` —
      propriedades que a F1 já tem e que o teste passa a travar. Os dois últimos foram
      **verificados por injeção**: `import requests` em `domain/bo/saldo.py` e um
      `socket.create_connection` dentro de `domain/bo/matriz.py::apurar` derrubam cada um deles.
      As migrations são verificadas sem Postgres — o que erra na prática é o alvo de um `op.*` e a
      tabela de versão, e as duas coisas estão no código; um teste que exigisse banco de produção
      para provar que a migration não toca `rreo_*` não rodaria em CI. **Dois testes tiveram de ser reescritos por
      passarem antes da implementação** — afirmavam a validação do próprio dublê, não a
      persistência real; agora apontam para `app.infra.cache.modelo` e ficam vermelhos. E as
      exceções foram nomeadas (`AnexoDesconhecido`, `StatusInvalido`) em vez de `Exception` cega,
      que deixaria o teste verde por acidente de import.

**Gate da fase TEST: fechado.** 63/63 cenários com teste, 66 vermelhos pelo motivo esperado.
**F2 e F3 implementadas em 2026-09-08: os 66 ficaram verdes, 224 passed, `ruff` limpo.**

**Tensão lock × ciclo: fechada em 2026-09-08, por medição do consumidor.**

O requisito do lock mandava devolver "o `job_id` existente"; o `Scenario: processamento já em voo`
mandava `202` **sem** `job_id`. A primeira implementação tentou os dois em campos separados
(`job_id: null` + `job_id_em_voo`) — e foi **descartada** ao medir `C:/Projetos/front-declaracoes`:

| Onde | O que o front faz com `202` sem `job_id` |
|---|---|
| `src/utils/rgfAnexoJob.ts:170` — utilitário **compartilhado** pelos anexos RGF 02–06 | **lança erro**: "job iniciado sem ID de rastreamento" |
| `src/hooks/useRGFAnexo1.ts:782` | cai em `pollSemJobId` — polling cego, sem SSE |
| `useRREOAnexo4/6/12` | desiste (`setSemCache`) |

E o discriminador de "este job não é seu" já existe no ecossistema, e **não** é a ausência do
`job_id`: é `status: "already_queued"`, que o RGF publica (`_responder_job_existente`) e a UI já
renderiza em seis componentes (`RGFDialog.tsx:1144` → "Já existe um cálculo em andamento.
Acompanhe o progresso.").

`job_id_em_voo` era campo que **nenhum** consumidor lia. O delta spec foi corrigido nos dois lados
(`Ciclo único` e `Lock por identidade`), e a resposta passou a ser a dos irmãos: `202` com o
`job_id` em voo, `status: already_queued`, `poll_url` e `sse_url`. Verificado com concorrência real
no container — dois clientes, um único `job_id`, nenhum segundo job enfileirado.
2. ~~Host/banco de produção~~ — **resolvido em 2026-09-08**: `.env` alinhado a
   `regras-rreo-api/.env` e `regras-rgf-api/.env`. Banco `db-ps-rreo-rgf-dca` em
   `host.docker.internal:5432`, Redis `redis_cache`, `SECRET_KEY`/`S2S_API_SECRET` **do hub** — a
   nota anterior de gerar segredos próprios foi revogada (JWT `HS256` local com chave própria não
   valida token do hub). Senha do Postgres na forma **crua**: o RREO a publica percent-encoded só
   porque a embute em `DATABASE_URL`.

## 3. IMPLEMENT — F2 (transporte) — **CONCLUÍDA em 2026-09-08**

Entregue: `main.py`, `app/routes/{anexos,jobs,mapeamentos,dependencias}.py`, `app/auth/`,
`app/core/{config,database,migrations}.py`.

    GET  /dca/{anexo}?anReferencia=&id_ente=      200 | 202 processing | 202 already_queued
    POST /dca/{anexo}/reprocessar                 202 — forcar=True, registra o solicitante
    GET  /dca/resumo                              200 sempre, só metadados, oito anexos
    GET  /jobs/{job_id} · /sse/jobs/{job_id}      polling e stream
    GET  /dca/{anexo}/mapeamentos[/vigente]       vigências publicadas
    POST /dca/{anexo}/mapeamentos                 publica vigência (409 se já existe)
    GET  /health · /ready                         liveness e readiness

**O contrato de entrada é o dos irmãos**, de propósito: `id_ente` em query, `Authorization: Bearer`,
`X-Unidade-Id` conferido contra `id_ente` — um frontend que já fala com RREO/RGF não muda nada.

**Achado que mudou o desenho da auth:** o RGF **não** lê a unidade de um claim. O token dá o `sub`,
e a autorização é confirmada no hub (`POST {AUTH_API_URL}/internal/authorize`, `X-Internal-Secret`),
porque quem pode ler qual ente é dado de banco — um usuário ganha ou perde unidade sem reemitir JWT.
A DCA seguiu isso (`app/auth/hub.py`), com **fail closed**: hub fora do ar responde `503`, nunca
libera. Sem hub configurado e em `ENVIRONMENT=development`, cai para o claim e loga aviso a cada
requisição; fora de development, recusa com `503`.

## 4. IMPLEMENT — F3 (pipeline) — **CONCLUÍDA em 2026-09-08**

Entregue: `worker.py` (uma função de job para os oito anexos), `app/infra/fila/`
(chaves · serializacao · job_manager · lock · credencial · redis_adapters), `app/infra/cache/`
(modelo · repositorio · vigencias_repo), `app/infra/msc/cache.py`, `app/infra/regras/vigencias.py`,
`app/infra/notificacao/discord.py`, `app/services/pipeline/` (registry · cache · job · resultado ·
resumo · notificacao · startup · apuracao), `alembic/` e Docker.

**Migration aplicada em 2026-09-08** no `db-ps-rreo-rgf-dca`: `dca_anexo_cache` e
`dca_regra_mapeamento` + `alembic_version_dca` em `001_dca_cache`. 44 tabelas viraram 47, e
`alembic_version_rreo` (032) e `alembic_version_rgf` (060) ficaram intactas.

**Quatro achados de execução, cada um com o seu conserto:**

1. **`tabelas_stn` vinha vazia ao carregar do banco** — a procedência perdia a versão das tabelas
   da STN, que o requisito exige. Conserto: as tabelas **não** vêm do banco; são versionadas em
   `knowledge/sources/stn/` e lidas de lá, e entram em `versao_regras` (uma tabela corrigida
   invalida o cache sem nenhuma regra mudar).
2. **O cache de MSC devolvia dado cru onde o domínio espera `Registro`.** Conserto: reidratar pelo
   **mesmo** normalizador dos adapters (`normalizacao.normalizar`), que já cobre snake_case do
   SICONFI e camelCase da PublicSoft — e payload não reconhecível vira miss, nunca exceção.
3. **`docs/contas-stn/` estava fora da imagem** por causa do `.dockerignore`. É **dado de
   produção**: a direção do saldo sai do `PCASP.md`. Sem ele o job morria com `FileNotFoundError`.
4. **Porta 8002 já é do `audite_ps-api-1`** — a DCA foi para a **8003** (8000 é RREO, 8001 RGF).

**Cache de MSC compartilhado, com uma restrição de segurança.** O RREO grava sob `msc_cache:` com um
byte de formato: `` parquet+lz4 e `` **pickle**+lz4. A DCA lê o parquet e trata o pickle
como *miss*, reconsultando a fonte — `pickle.loads` de dado escrito por outro processo executa
código, e é o mesmo risco que a spec proíbe para payload de job. A chave é o MD5 dos mesmos
parâmetros, com os mesmos nomes, para que o reuso realmente aconteça.

## 4bis. IMPLEMENT — notas antigas da F2/F3

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
