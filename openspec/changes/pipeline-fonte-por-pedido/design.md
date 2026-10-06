# Design — Fonte de dados escolhida por pedido (`use_siconfi`)

**Change:** `openspec/changes/pipeline-fonte-por-pedido/` · **Proposal aprovada pelo PO em:** 2026-10-06

## Contexto

`apuracao.fonte(nome, token)` já escolhe o adapter pelo nome e cai em `config().fonte_padrao`
(`DATA_SOURCE`) quando `nome` é `None`. O worker chama `apuracao.apurador(...)` sem `fonte_nome` e
lê a credencial do cofre (`credencial.ler`), mas nenhuma rota chama `credencial.guardar`. Os
parâmetros que mudam o valor (competência, origem do anterior, G8) já passam por um único caminho:
rota → `parametros_efetivos` → `identidade_do_pedido` (sufixo de `versao_regras`) → payload do job
→ `versao_do_pedido` no worker. A fonte entra nesse mesmo caminho.

O desenho segue o já implementado em `regras-rgf-api` (`app/auth/rgf_dependencies.py::
resolve_publicsoft_auth`) e `regras-rreo-api` (`get_publicsoft_token`): `use_siconfi: bool =
Query(False)`, `token_ps` resolvido no hub (`/internal/resolve-tenant`), cifrado no Redis por job e
enviado à PublicSoft em `x-authorization`; `use_siconfi` no payload do job.

## Componentes afetados

| Componente | Papel na change |
|---|---|
| `app/routes/anexos.py` | lê `use_siconfi`; vira `parametros["fonte"]`; resolve o token quando PublicSoft |
| `app/auth/hub.py` | `resolver_token(sub, cod_ibge)` → `POST /internal/resolve-tenant` |
| `app/services/pipeline/cache.py` | `parametros_efetivos` preserva `fonte`; `identidade_do_pedido` a inclui; `ler_ou_enfileirar` guarda a credencial com o `job_id` antes de enfileirar |
| `worker.py` | `apuracao.apurador(..., fonte_nome=parametros.get("fonte"))` |
| `app/services/pipeline/apuracao.py` | sem mudança: `_aceitos_por` já descarta `fonte` antes do serviço |

## Fluxo da informação

```text
GET /dca/BF?use_siconfi=false
  → unidade_autorizada (JWT + hub /internal/authorize)          (inalterado)
  → fonte = "publicsoft" → hub /internal/resolve-tenant → token_ps
  → parametros_efetivos(+fonte) → versao_regras|...:f=publicsoft
  → cache servível? 200
  → senão: credencial.guardar(cofre, job_id, token_ps) → fila.enfileirar(..., fonte="publicsoft")
worker: credencial.ler(job_id) → apurador(fonte_nome="publicsoft", token=token_ps) → cache
```

## Contratos / interfaces

- Query: `use_siconfi: bool = Query(False)`, como RREO e RGF.
- `parametros["fonte"]`: `"siconfi"` | `"publicsoft"`. Vai no payload do job (não é segredo).
- `identidade_do_pedido`: acrescenta `f=<fonte>` quando a chave existe.
- `ler_ou_enfileirar(..., guardar_credencial: Callable[[str], None] | None = None)`: chamado com o
  `job_id` depois do lock e antes de `fila.enfileirar`.
- Hub: `POST {AUTH_API_URL}/internal/resolve-tenant`, `{sub, cod_ibge}`, `X-Internal-Secret`.
  `200` → `token_ps`; `403` → `403`; `404` → `404`; `409` → `409`; rede/401/5xx → `503`. Mesmo
  mapeamento de `HttpDemonstrativosClient.resolve_tenant` do RGF.
- Hub não configurado: só em `development`/`test`/`local` segue sem token, como
  `_autorizar_pelo_token`; nos demais ambientes, `503`.

## Impacto

| Eixo | Impacto |
|---|---|
| Banco / migration | nenhum |
| Cache | identidade ganha `f=<fonte>`; o hash de `versao_api` já muda com esta change, então cada anexo reapura uma vez de qualquer forma |
| Filas / worker | payload ganha `fonte`; credencial cifrada no cofre (`dca:job:<id>:credencial`, TTL do job) |
| APIs externas | 1 chamada a `/internal/resolve-tenant` por pedido PublicSoft, como no RGF |
| Regressão | `apurar_completo` (batch) sem `fonte`: continua no `DATA_SOURCE` |

## Decisões

### D1 — Ausência do parâmetro
**Escolhido:** `Query(False)` → PublicSoft, como RREO e RGF (PO, 2026-10-06) · **Descartado:**
ausência = `DATA_SOURCE` · **Porquê:** mesmo contrato nos três pipelines; o front já envia sempre.

### D2 — Fonte na identidade do cache
**Escolhido:** sufixo `f=<fonte>` em `versao_regras` · **Descartado:** fonte fora da chave
(RREO) e coluna nova na chave primária · **Porquê:** é o defeito relatado — o usuário marca SIAFIC
e recebe SICONFI. O RGF já tratou fonte que muda valor como dimensão do cache (CH-07,
`fontePeriodoAnterior`, cache miss por fonte). O sufixo faz o mesmo sem migration; trocar de fonte
reapura e a última apuração ocupa a linha.

### D3 — Quando resolver o token
**Escolhido:** na rota, sempre que a fonte é PublicSoft, como `resolve_publicsoft_auth` do RGF ·
**Descartado:** só ao enfileirar · **Porquê:** mesmo contrato do RGF; `ler_ou_enfileirar` é
síncrono e o hub é async.

## Arquivos criados / alterados

| Arquivo | Ação |
|---|---|
| `app/routes/anexos.py` | alterar |
| `app/auth/hub.py` | alterar |
| `app/services/pipeline/cache.py` | alterar |
| `worker.py` | alterar |
| `tests/pipeline/test_fonte_por_pedido.py` | criar |

## Pendências conhecidas

- `POST /batch-jobs` continua na fonte padrão; entra quando o front passar a usá-lo na DCA.
