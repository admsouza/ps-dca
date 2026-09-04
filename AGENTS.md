# AGENTS.md — Instruções para qualquer agente de IA neste repositório

Fonte **autoritativa** de processo para qualquer agente (Claude Code, Cursor, Codex, etc.).
Camada de detalhe: `openspec/AGENTS.md` (fluxo OpenSpec + tabela de changes ativas) e
`openspec/project.md` (escopo DCA, stack alvo, convenções).

> **Estado do repositório: FASE DE SPEC.**
> Não há código, arquitetura nem migrations — e **não haverá** enquanto as specs não
> forem fechadas com o PO. Agente que "adiantar" implementação está fora do processo.

---

## 0. Quando estas regras valem

Valem quando o trabalho for **especificação**, **implementação** (feature/bugfix/mudança de
comportamento), **refatoração** ou **teste de validação**.

**Isento (não precisa abrir change):** pergunta read-only, localizar arquivo, explicar
código/normativo, status, ler docs, discutir desenho sem alterar o repo.

## 1. Regra dura — OpenSpec antes de codar

> Toda **capability nova** ou **refatoração** DEVE ter uma change OpenSpec
> (`proposal` + `specs/` delta + `design` + `tasks`) **antes de qualquer código**.

Antes de agir no escopo da §0, o agente **DEVE**:

1. Perguntar se devemos **criar** uma change nova **ou usar** uma change ativa existente.
2. Aguardar resposta explícita (`sim` / `aprovado` / change nomeada).
3. Só então criar/usar a change e seguir o fluxo do `openspec/AGENTS.md`.

Ordem de leitura antes de qualquer ação: `openspec/project.md` → `openspec/AGENTS.md` →
`proposal.md` → `specs/**/spec.md` → `design.md` → `tasks.md`.

## 2. Ciclo de trabalho

```text
SPEC → PLAN/ARCH → TEST → IMPLEMENT → REVIEW → VERIFY
```

| Fase | Artefato | Gate para avançar |
|---|---|---|
| **SPEC** | `proposal.md` + `specs/<domínio>/<capability>/spec.md` (delta) | **Aprovação explícita do PO** |
| **PLAN/ARCH** | `design.md` + `tasks.md` | Decisões `D1..Dn` numeradas; lista de arquivos a criar/alterar |
| **TEST** | `tests/test_*.py` traduzindo cada `#### Scenario:` | Teste roda e **falha pelo motivo esperado** |
| **IMPLEMENT** | código mínimo | Suíte verde; `tasks.md` marcado no momento em que cada item fecha |
| **REVIEW** | `git diff` completo | Sem arquivo fora do escopo, sem código morto, sem abstração de uso único, sem `print`/segredo/`TODO` órfão |
| **VERIFY** | validação real (§5) | Resultado reportado como `N passed / M failed`, distinguindo falha nova de pré-existente |

Nenhuma fase começa antes do gate da anterior. Pular fase é erro de processo.

### 2.1 Conteúdo mínimo da fase SPEC

`proposal.md` + delta `specs/` **DEVEM** deixar explícito: objetivo, requisitos funcionais
(`SHALL`/`MUST`), **entradas e saídas** (payload/resposta/campos), critérios de aceite,
**casos de erro**, restrições e ao menos um **exemplo concreto** (ente/exercício/valor real,
com o anexo DCA correspondente). Critério de aceite sem número medível não é critério.

`design.md` **DEVE** cobrir: componentes afetados, fluxo da informação, contratos/interfaces,
impacto em banco/cache/filas/APIs externas, **lista dos arquivos criados ou alterados** e as
decisões arquiteturais (`D1..Dn`, com a alternativa descartada).

### 2.2 TDD — teste antes do código

Ordem obrigatória por tarefa de comportamento: **teste → falha → implementação**.
Teste que passa antes da implementação não testa nada — corrigir o teste, não seguir.
Comportamento observável primeiro (entrada → saída, aviso, erro), não estrutura interna.

## 3. Ao finalizar a change (só no fim, nunca no meio)

1. Garantir `tasks.md` 100% atualizado.
2. Mesclar os deltas de `openspec/changes/<change>/specs/` em `openspec/specs/`.
3. Mover a pasta para `openspec/changes/archive/AAAA-MM-DD-<slug>/`.
4. Atualizar a tabela "Change ativa" em `openspec/AGENTS.md`.

Durante a change, editar **apenas** os deltas em `openspec/changes/<change>/specs/` —
nunca `openspec/specs/`.

## 4. Fontes da verdade externas

| Assunto | Fonte | Regra |
|---|---|---|
| Importação/ingestão XML/XBRL e modelo canônico `instancias_import` | `C:\Projetos\prd-audite` | Consultar PRD, Tabela de Fatos e `docs/decisions/` (esp. `0007`, `0012`) antes de planejar. Não contrariar. |
| Padrões de pipeline, cache por anexo, jobs e auth | `C:\Projetos\regras-rreo-api`, `C:\Projetos\regras-rgf-api` | Replicar o padrão existente antes de inventar um novo. |
| Regra contábil da DCA | MCASP + IPCs em `docs/referencia/ipc/` + layout SICONFI | Divergência código × normativo se registra, não se silencia. |
| Espelho oficial | API `tt/dca` do SICONFI | Aceite = **1:1 medido** (chave + valor), não "parece certo". |

### 4.1 Ordem obrigatória quando uma decisão confronta a fonte da verdade

**doc (`prd-audite`) → spec (OpenSpec) → código.** A fonte da verdade nunca fica atrás do código.

## 5. Validação (a partir da fase IMPLEMENT)

Rodar **tudo**, na ordem, e reportar o resultado real:

```bash
python -m pytest                  # suíte inteira
python -m ruff check .            # lint (deve sair limpo)
alembic upgrade head              # migrations; rename/drop-column: upgrade → downgrade → upgrade
```

Além dos comandos:

- **Reconferência da spec:** percorrer os cenários do delta spec um a um e apontar onde cada
  um é coberto por teste ou por medição. Cenário sem cobertura fica declarado como pendência.
- **Regressão:** comportamento que já funcionava sai **bit a bit igual**.
- Não inventar comando que não existe no repo.

## 6. Segurança

- Segredos só por variável de ambiente; `.env` nunca versionado, `.env.example` sempre atualizado.
- Não logar JWT, `token_ps`, `DATABASE_URL` nem dado de ente identificável em log de erro.
- Toda chamada HTTP externa com timeout explícito.
- Query parametrizada sempre; nunca concatenar input em SQL.

## Resumo em uma frase

SPEC aprovada pelo PO → design e tasks completos → **teste falhando antes do código** →
código mínimo → review do diff → validação medida → tasks atualizadas e change arquivada.
Enquanto a spec não fechar, **não se escreve código**.
