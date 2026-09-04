# ps-dca — Contexto do projeto

## Visão geral

Processamento da **DCA** (Declaração de Contas Anuais — SICONFI/STN): cálculo dos anexos a
partir da MSC/dados do ente, cache por anexo e espelho conferível contra a API oficial `tt/dca`.

Terceiro projeto da mesma família, depois de `regras-rreo-api` (RREO) e `regras-rgf-api` (RGF).
O modelo operacional é o mesmo: rota HTTP enfileira job → worker calcula → cache em PostgreSQL →
leitura por polling/SSE. **Nada disso está implementado ainda** — o repositório está na fase de
spec (ver `AGENTS.md` na raiz).

### Escopo da DCA

| Dimensão | Valor |
|---|---|
| Periodicidade | Anual (`periodicidade=A`, `periodo=1`) |
| Poder | `-` (consolidado do ente) |
| Abrangência inicial | Municipal |
| Anexos | `DCA-Anexo I-AB`, `I-C`, `I-D`, `I-E`, `I-F`, `I-G`, `I-HI` |

O conteúdo de cada anexo (demonstrativo, colunas, regra de composição) é o que será fechado
com o PO nas changes de spec — **não presumir** a partir do RREO/RGF.

Referência normativa disponível no repo: `docs/referencia/ipc/` (IPC 04 BP, IPC 05 DVP,
IPC 06 Balanço Financeiro, IPC 07 BO, IPC 08 DFC).

## Stack alvo (a confirmar na fase PLAN/ARCH)

| Camada | Tecnologia |
|---|---|
| API | FastAPI, Uvicorn, Pydantic v2 |
| Worker | arq (Redis) |
| Cache / estado | PostgreSQL (`dca_*_cache`) |
| ORM / migrations | SQLModel/SQLAlchemy 2.x, Alembic |
| Auth | JWT Bearer + `X-Unidade-Id` (`cod_ibge`) |
| Fontes de dados | SICONFI (`tt/dca`), PublicSoft/MSC, XBRL importado (`instancias_import`) |
| Testes / lint | pytest, ruff |

## Convenções herdadas de RREO/RGF

- Identificador canônico de unidade: `cod_ibge` (7 dígitos).
- Front envia `Authorization: Bearer <jwt>` e `X-Unidade-Id: <cod_ibge>`; browser **nunca**
  envia `x-authorization` nem `token_ps`.
- Respostas JSON em **camelCase** (`model_dump(by_alias=True)`).
- Um pacote por anexo consolidando cálculo + orquestração + cache; sem pacotes-irmãos.
- Rotas direto sob `app/routes/<anexo>/` — sem subpasta redundante de namespace.
- Type hints explícitos; sem lógica de negócio em rota.
- **De-para = falha ruidosa:** concept/eixo sem mapeamento 1:1 vira `NULL` e não é servido —
  nunca chute.
- **Aceite = espelho 1:1 medido** contra `tt/dca` (contagem + valores). O espelho omite
  `valor = 0`, como o STN.

## Estrutura

```text
AGENTS.md                      # contrato de processo (autoritativo)
CLAUDE.md                      # redireciona para AGENTS.md
docs/referencia/ipc/           # IPCs (BP, DVP, BF, BO, DFC)
openspec/
├── project.md                 # este arquivo
├── AGENTS.md                  # fluxo OpenSpec + changes ativas
├── config.yaml                # contexto e regras para agentes
├── templates/                 # modelos de proposal/design/tasks/spec
├── specs/                     # fonte de verdade (comportamento acordado)
└── changes/
    ├── <change-ativa>/
    └── archive/AAAA-MM-DD-<slug>/
```

## Comandos de validação

Disponíveis desde 2026-09-04 (`pyproject.toml`):

```bash
python -m pytest                              # 89 testes
python -m ruff check .
python -m scripts.validate_rules knowledge    # gate da base canônica
python -m scripts.check_sources knowledge     # integridade do PDF e das tabelas da STN
python -m scripts.build_index knowledge       # regenera o índice de regras
```

`alembic upgrade head` só existirá na fase F3 (change `plataforma-pipeline-dca`), quando houver
tabela. Não inventar comando que não esteja no repositório.

## Projetos irmãos

| Projeto | Caminho | Uso |
|---|---|---|
| RREO | `C:\Projetos\regras-rreo-api` | Padrão de pipeline, cache, jobs, mapeamentos Tesouro |
| RGF | `C:\Projetos\regras-rgf-api` | Padrão de organização por anexo, cache ciente de vigência, conferência SICONFI |
| Importação XBRL | `C:\Projetos\prd-audite` | **Fonte da verdade** do modelo canônico e da ingestão |
