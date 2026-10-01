# Proposal — Plataforma de pipeline da DCA (infra e arquitetura)

**Status:** proposta
**Capability:** `pipeline/plataforma` (nova)
**Bloqueia:** as fases F2 e F3 de `bo-quadro-principal-processamento` e todo anexo futuro
**Repositórios analisados:** `regras-rreo-api` (`ARCHITECTURE.md`, `main.py`, `worker.py`),
`regras-rgf-api` (job/cache/lock por anexo), `ps-infra` (Redis compartilhado)

## Why

A DCA é o **terceiro pipeline** da casa. RREO e RGF já rodam a mesma forma em produção — rota
enfileira job, worker apura, resultado em cache no Postgres, cliente acompanha por polling ou SSE —
e o PO determinou que a DCA funcione nesse mesmo fluxo.

Hoje esse fluxo está descrito em três lugares e em nenhum como requisito: o `ARCHITECTURE.md` do
RREO documenta o que **já foi feito lá**, o `project.md` da DCA cita a forma em duas linhas, e a
change do Balanço Orçamentário a menciona numa decisão de design (D6). Nada disso é verificável.

A consequência prática é conhecida, porque já aconteceu duas vezes: sem contrato de plataforma, cada
anexo reimplanta o seu. No RGF há **quatro cópias** da mesma mecânica de lock órfão — o próprio
código admite isso em `app/services/rgf/lock_anexo.py` — e seis services de cache quase idênticos,
que `services/cache_rgf/resumo.py` precisa importar um a um. Repetir isso na DCA seria escolher a
dívida sabendo o preço.

Esta change especifica a plataforma **antes** do primeiro anexo, para que o quadro principal do BO
nasça dentro do fluxo em vez de ser encaixado nele depois.

## What Changes

- Passa a existir `pipeline/plataforma`: o contrato observável do ciclo
  **requisição → cache → job → worker → cache → leitura**, igual para todo anexo da DCA.
- Fica definida a **organização em camadas** e a regra de dependência: domínio puro no núcleo,
  fontes e persistência na borda, entrando por `Protocol`.
- Fica definida a **infra**: dois processos (API e worker), Redis compartilhado da rede `ps-infra`,
  Postgres, Alembic, imagens e deploy CapRover, variáveis de ambiente.
- Fica definida **uma** tabela de cache parametrizada por anexo, **um** service de cache e **um**
  registry — não um conjunto por anexo, como em RREO e RGF.
- Fica definida a chave de identidade do resultado, incluindo a **versão das regras** como critério
  de invalidação.

**Fora de escopo:** a regra de qualquer anexo (isso é das changes de `dca/`); a importação XBRL
(`import/`); a emissão de token, que continua na API de autenticação externa; o front.

## Diferenças deliberadas em relação a RREO e RGF

| Ponto | RREO / RGF | DCA | Porquê |
|---|---|---|---|
| Tabela de cache | uma por anexo (`rreo_anexoNN_cache`, `rgf_anexoNN_cache`) | **uma**, com coluna `anexo` | payload é JSONB nos dois casos; 7 models idênticos não pagam o próprio custo |
| Service de cache | um por anexo | **um**, parametrizado | `services/cache_rgf/resumo.py` importa seis services só para perguntar o mesmo |
| Lock de job | copiado em cada anexo | **um**, no núcleo de pipeline | o RGF já tentou consertar isso a meio caminho (`lock_anexo.py`) |
| Cálculo | `pandas` no service, `requests` alcançável do domínio | núcleo **puro**, fontes por `Protocol` | testar o núcleo sem subir container |
| Invalidação de cache | versão da API, string no service | versão da API **e** versão das regras | na DCA a regra é dado versionado (`knowledge/rules/`), não código |

O que **não** muda, e é reuso direto: a separação API/worker, `arq` sobre Redis, o padrão
`202 + job_id` com polling e SSE, o estado `ok | processando | erro | sem_cache`, o resumo agregado
para o bootstrap do front e o deploy CapRover com duas imagens.

## Restrições

- Contrato de auth herdado, sem exceção: front envia `Authorization: Bearer <jwt>` e
  `X-Unidade-Id: <cod_ibge>`; `x-authorization` e `token_ps` vindos de browser SHALL ser rejeitados.
- Respostas JSON em camelCase (`model_dump(by_alias=True)`).
- Nenhuma lógica de cálculo em rota ou em worker — ambos só orquestram.
- Redis é o da rede `ps-infra`; esta change não sobe outro.

## Decisões

| # | Assunto | Decisão |
|---|---|---|
| **P1** | a DCA usa o mesmo fluxo de RREO/RGF | sim — decisão do PO em 2026-09-04, registrada aqui como requisito, não como semelhança |
| **P2** | granularidade do cache | uma tabela e um service, parametrizados por anexo |
| **P3** | ordem de construção | plataforma especificada agora; implementada na F2/F3 do BO, não antes (D6) |
| **P4** | granularidade do job | **job por anexo** na primeira entrega (PO, 2026-09-04). O pipeline completo — job único percorrendo os 7 anexos em série, como o RREO — é change posterior; o registry já nasce preparado para ele |
| **P5** | Postgres | **mesma instância e o mesmo schema `public` de RREO/RGF** (PO, 2026-09-04). É um monolito modular: hub, banco e Redis são compartilhados. A separação é por **prefixo de tabela** (`dca_*`) e por **tabela de migration própria** (`alembic_version_dca`), como os irmãos já fazem — não por schema |
| **P6** | notificação | **Discord ao fim do job**, como nos irmãos (PO, 2026-09-04) |
| **P7** | reprocessamento forçado (L1) | **entra nesta change** (PO, 2026-09-04) — mesma autorização da leitura, solicitante registrado, mesmo lock, resultado anterior legível até ser substituído |
| **P8** | seleção de regra por exercício (L2) | **a porta entra agora; o acervo de edições, depois** (PO, 2026-09-04). O STN muda regra **anualmente** e a DCA é anual: a apuração pede a regra vigente **para o exercício**, ainda que hoje só a edição `2020-01` responda. Gerir várias edições coexistindo é change própria, disparada pela primeira edição nova |
| **P10** | onde vive o mapeamento vigente | **banco, INSERT-only, vigência por competência** (PO, 2026-09-04), no padrão de `rgf_anexo02_mapeamento`: PO corrige sem deploy e o histórico fica. A **transcrição normativa do IPC** continua em YAML no repositório, e serve de seed (`origem: seed-yaml`). Uma tabela para todos os anexos, não uma por anexo |
| **P9** | procedência do valor apurado | toda apuração carrega as regras aplicadas, a edição normativa e a versão das tabelas STN que a produziram (PO, 2026-09-04) — é o que permite explicar divergência contra o STN sem investigação manual |

## Onde vive a regra: transcrição em YAML, mapeamento vigente em banco

O STN muda regra de mapeamento **anualmente**, e o PO precisa corrigir mapeamento sem esperar
release. São duas naturezas de conteúdo, e cada uma tem o seu lugar:

| Conteúdo | Onde | Porquê |
|---|---|---|
| **Transcrição normativa** — as 69 linhas do IPC 07 com `source.page`, `evidence.text` e hash do PDF | YAML no repositório | é documento, não configuração. Editável por admin, perde a rastreabilidade até a página do PDF — que é a entrega inteira de `ipc07-bo-regras-canonicas` |
| **Mapeamento vigente** — o que de fato entra em cada linha e coluna ao apurar | **banco**, INSERT-only, vigência por competência | é o que muda quando o STN republica, e o que o PO corrige sem deploy |

O YAML é o **seed** do banco (`origem: seed-yaml`), como já acontece em `rgf_anexo02_mapeamento`. A
apuração lê sempre do banco; o YAML é a origem versionada e o registro documental dela.

Padrão adotado de `regras-rgf-api/app/models/rgf_anexo02_mapeamento.py`, com duas correções:

1. **Uma tabela para todos os anexos**, com coluna de anexo — não uma por anexo. O próprio RGF marca
   isso como dívida no docstring do A03 (*"a unificação com o A02 segue em aberto na CH-05 (P2)"*).
   É a mesma decisão P2/P-D1 já tomada para o cache.
2. **`versao_regras` é hash do conteúdo carregado do banco**, não de arquivo — o que também elimina
   a armadilha de CRLF descrita em P-D7.

### Vigência: a porta agora, o acervo depois

- **Agora, na F1:** a carga de regras recebe o **exercício** e resolve a vigência — hoje há uma só,
  e o resultado é idêntico ao de fixar a edição no código. A diferença aparece depois.
- **Depois, em change própria:** interface de administração para publicar nova vigência, e
  reapuração de exercícios antigos pela regra da época.

Por que a porta não pode esperar: quando a primeira vigência nova for publicada, retrofitar a
seleção atravessa carregador, service, chave de cache e todo resultado já apurado.

## Aprovação do PO

- [x] PO aprovou esta proposta em **2026-09-04** — Jackson S. da Silva (PO). Gate da fase SPEC fechado; PLAN/ARCH liberada.
      Aprovação cobre a proposta, o `design.md` e o delta `specs/pipeline/plataforma/spec.md`,
      incluindo as decisões P1–P10 e P-D1 a P-D8.
