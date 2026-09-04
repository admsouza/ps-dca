> **ARQUIVADA EM 2026-09-04 — SUCEDIDA, NAO IMPLEMENTADA.**
>
> Esta change foi substituida por changes separadas por documento, comecando pela
> `ipc07-bo-regras-canonicas` (SPEC aprovada pelo PO em 2026-09-04). O motivo: as 309 linhas dos 5
> IPCs num unico escopo tornavam o gate de aprovacao grande demais para ser decidido de uma vez, e
> as ambiguidades de cada documento so aparecem quando ele e transcrito.
>
> **Destino dos artefatos compartilhados** (decisao do PO, 2026-09-04): `knowledge/schemas/*.json`,
> `knowledge/sources/<ipc>/metadata.yaml`, `knowledge/sources/stn/metadata.yaml` e
> `scripts/check_sources.py` sao criados pela `ipc07-bo-regras-canonicas` (tasks 3.1 e 3.2), que e a
> primeira a precisar deles. As changes dos IPC 04, 05, 06 e 08 os estendem, nao os recriam.
>
> O conteudo abaixo permanece como registro da analise de descoberta que originou as changes por
> IPC. Nada aqui e escopo ativo.

# Tasks — Base canônica de regras contábeis a partir dos IPC 04–08

**Repo:** `ps-dca` · **Não implementar sem aprovação explícita do PO.**
Fatia vertical: **IPC07, Quadro Principal, linhas `L1` e `L2`** — as duas construções que cobrem
todo o modelo (linha com contas/filtros/colunas e linha composta por referências) validadas
ponta-a-ponta antes de qualquer extração em massa.

Gate por fase em [`../../../AGENTS.md` §2](../../../AGENTS.md).
Fase 1 (descoberta) concluída: [`docs/source-analysis.md`](../../../docs/source-analysis.md) e
[`docs/source-analysis-ipc07.md`](../../../docs/source-analysis-ipc07.md).

**Ordem de implementação:** IPC07 (BO) primeiro. A matriz do IPC07 está reconstruída por
geometria; as 11 ambiguidades internas estão resolvidas por evidência do próprio documento (R1–R11)
e os 6 bloqueios estão isolados em 19 das 69 linhas. As outras **50** não dependem de decisão.

## 0. Fundação
- [x] 0.1 PO decidiu os 4 itens abertos (2026-08-27) — registrado em `proposal.md` e em `docs/source-analysis.md` §11
- [ ] 0.2 PO aprovar formalmente a proposal (checkbox de "Aprovação do PO") — **gate para PLAN/ARCH**
- [ ] 0.3 `pyproject.toml`: runtime `pyyaml`, `jsonschema`, `pydantic`; dev `pytest`, `ruff`, `pymupdf`
- [ ] 0.4 `knowledge/sources/ipc0{4,5,6,7,8}/metadata.yaml` com nome do arquivo, páginas, edição e SHA-256 medidos
- [ ] 0.5 `knowledge/sources/stn/metadata.yaml` com SHA-256 e contagem de registros das 7 tabelas de `docs/contas-stn/`
- [ ] 0.6 `scripts/check_sources.py` + confirmar os 5 PDFs e as 7 tabelas
- [ ] 0.7 `scripts/extract_ipc.py` gerando `knowledge/sources/<ipc>/extracted.md` para os 5 documentos
- [ ] 0.8 `scripts/load_stn_tables.py` devolvendo os conjuntos de códigos válidos (6.119 contas, 4.506 naturezas de receita, 174 NDs, 119 pares função/subfunção, 98 fontes)
- [ ] 0.9 `knowledge/bindings/field_bindings.yaml` com o campo `financeiro_permanente` (chaves SICONFI e PublicSoft, domínio de validação pelo PCASP)
- [ ] 0.10 `knowledge/schemas/{source,filter,rule,policy,document}.schema.json` (Draft 2020-12), com os enums fechados de `design.md`

## 1. TEST (antes do código)
- [ ] 1.1 `tests/test_validate_rules.py`: um teste por `#### Scenario:` do delta spec, usando fixtures em `tests/fixtures/` — regra sem `source`, `rule_id` duplicado, referência órfã, ciclo `A→B→A`, página fora do documento, operador inválido, campo de filtro inválido, `unresolved` com `status: validated`, índice dessincronizado, hash de PDF divergente, hash de tabela STN divergente, código inexistente na tabela oficial, `financeiro_permanente` incompatível com o indicador da conta
- [ ] 1.2 `tests/test_rules_normativas.py`: cenários normativos de `bo.quadro_principal.receitas.l1` e `.l2` — filtros de natureza, 4 colunas, contas por coluna com sinal, `saldo = c - b`, composição de `L1` por 8 referências
- [ ] 1.3 Rodar e **confirmar que falha** pelo motivo esperado (schemas ainda sem validador; regras ainda inexistentes)

## 2. IMPLEMENT
- [ ] 2.1 `scripts/validate_rules.py`: carga YAML + validação de schema (cenários "regra sem source", "operador inválido", "campo inválido")
- [ ] 2.2 `validate_rules.py`: unicidade de `rule_id` reportando os dois caminhos
- [ ] 2.3 `validate_rules.py`: resolução de `calculation.references` e detecção de ciclo com impressão do caminho
- [ ] 2.4 `validate_rules.py`: `source.page` dentro do intervalo de `metadata.yaml`
- [ ] 2.5 `validate_rules.py`: invariante `unresolved` não vazio ⇒ `status != validated`
- [ ] 2.6 `validate_rules.py`: conferência de que `prefix` é derivação legítima de `literal` (D5); `prefix: null` ⇒ `review_required`
- [ ] 2.7 `validate_rules.py`: conferência de cada `literal` contra as tabelas da STN (D13); código ausente ⇒ `review_required` com candidato **anotado, não aplicado**
- [ ] 2.8 `validate_rules.py`: domínio de `financeiro_permanente` contra `INDICADOR DO SUPERÁVIT FINANCEIRO` do PCASP (D7)
- [ ] 2.9 `scripts/build_index.py` + checagem de índice sincronizado em `validate_rules.py`
- [ ] 2.10 `validate_rules.py`: relatório final com contagem por demonstrativo e por status
- [ ] 2.11 **Fatia vertical:** `knowledge/rules/bo/quadro_principal.yaml` com `L1` e `L2` apenas; suíte verde
- [ ] 2.12 **Gate de revisão do modelo (Fase 4):** transcrever uma linha de cada construção difícil e confirmar que o schema as representa **sem alteração** — IPC04 `L2` do quadro 2 (`financeiro_permanente`), IPC04 quadro 4 (paramétrica por fonte), IPC06 `L4` (faixa de fonte derivada), IPC06 `L27` (movimento credor), IPC06 `L30` (saldo inicial com subtração), IPC07 `L25` (guarda condicional), IPC07 `L38` (ND + função concatenada), IPC08 `L13` (lista longa de ND), IPC08 quadro c `L1` (mesma ND replicada em 29 linhas por função). **Se alguma não couber, ajustar o schema aqui — não depois.**
- [ ] 2.13 `knowledge/policies/ipc0{4,5,6,7,8}.yaml` e ligação `policies:` nas regras da fatia
- [ ] 2.14 Extração completa BO — 69 regras (principal 51, RPNP 9, RPP 9), aplicando R1–R11 de `source-analysis-ipc07.md` §4 com o `literal` original em `evidence`; as 19 linhas de B1/B3/B5/B6 nascem `review_required` (`L11`,`L19`,`L20`,`L22`,`L23`,`L27`,`L28`,`L29`,`L30`,`L51` + as 9 do quadro de RPNP)
- [ ] 2.14.1 `scripts/extract_ipc.py`: reconstrução por geometria para páginas rotacionadas (linha = banda em `x`, coluna = banda em `y`) — sem isso a associação célula→coluna do IPC07 não fecha
- [ ] 2.15 Extração completa BP — 57 regras + 1 paramétrica
- [ ] 2.16 Extração completa DVP — 19 regras; P1 resolvido (parênteses equivalentes), com a decisão registrada em `provenance` e a grafia original em `evidence`
- [ ] 2.17 Extração completa BF — 80 regras; 9 das 11 linhas de vinculação resolvidas por faixa de fonte (`extraction_method: derived`); só `L7`/`L40` (R1) e `L10`/`L43` (R2) nascem `review_required`
- [ ] 2.18 Extração completa DFC — 84 regras; conferência **visual** obrigatória das 14 linhas de risco de `source-analysis.md` §7
- [ ] 2.19 Marcar `review_required` + `unresolved` + `evidence` literal nas regras tocadas por §11.5 (P2, P5, P6, R1, R2) e por §6.2 (N5)
- [ ] 2.20 `docs/rule-model.md`, `docs/architecture.md`, `docs/contribution-guide.md`, `knowledge/README.md`
- [ ] 2.21 `AGENTS.md` (raiz): **adicionar** seção "Regras contábeis canônicas" — localizar `rule_id` → ler YAML → conferir `source` → consultar o PDF se ambíguo → implementar → testar → registrar o `rule_id` no código; nunca inferir regra ausente; nunca codificar regra sem base canônica
- [ ] 2.22 `README.md`: seção apontando para `knowledge/` e para os comandos de validação
- [ ] 2.23 Migration: **não há** — YAML + Git é a fonte canônica (D3)

## 3. REVIEW
- [ ] 3.1 `git diff` completo: sem arquivo fora do escopo, sem código morto, sem abstração de uso único, sem `print`/segredo/`TODO` órfão
- [ ] 3.2 `git diff tests/` contém apenas testes novos e mudanças justificáveis
- [ ] 3.3 Confirmar que nenhuma linha do contrato existente do `AGENTS.md` foi alterada — só adição (D10)
- [ ] 3.4 Confirmar que nada em `docs/referencia/ipc/` nem em `docs/contas-stn/` foi tocado (`git diff --stat` vazio para os dois diretórios)
- [ ] 3.5 Amostra cega de 10 regras sorteadas: cada uma implementável a partir do YAML, sem abrir o PDF

## 4. VERIFY
- [ ] 4.1 `python -m pytest` — reportar `N passed / M failed`
- [ ] 4.2 `python -m ruff check .` — limpo
- [ ] 4.3 `python scripts/validate_rules.py` — exit `0`; relatório com **309** regras e `BP 57 · DVP 19 · BF 80 · BO 69 · DFC 84`
- [ ] 4.4 `python scripts/check_sources.py` — exit `0`, 12 hashes conferidos (5 PDFs + 7 tabelas STN)
- [ ] 4.5 `alembic upgrade head` — **não se aplica** (sem schema nesta change)
- [ ] 4.6 Espelho 1:1 contra `tt/dca` — **não se aplica** (nada é calculado nesta change); declarar como pendência da change que consumir as regras
- [ ] 4.7 Reconferência da spec: percorrer cada `#### Scenario:` do delta e apontar o teste ou a medição que o cobre; cenário sem cobertura fica declarado como pendência
- [ ] 4.8 Relatório final: estrutura criada, modelo adotado com exemplo real, documentos processados, regras por demonstrativo (contado dos arquivos, não estimado), pendências, resultado da validação

## 5. Arquivamento
- [ ] 5.1 `tasks.md` 100% marcado
- [ ] 5.2 Mesclar `specs/dca/base-canonica-regras/spec.md` em `openspec/specs/dca/base-canonica-regras/spec.md`
- [ ] 5.3 Mover para `openspec/changes/archive/AAAA-MM-DD-knowledge-base-ipc/`
- [ ] 5.4 Atualizar a tabela "Change ativa" em `openspec/AGENTS.md`
