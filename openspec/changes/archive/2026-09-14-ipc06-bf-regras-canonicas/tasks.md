# Tasks — Base canônica de regras do Balanço Financeiro (IPC 06)

**Repo:** `ps-dca` · **Concluída e arquivada em 2026-09-14.**
Fatia vertical: as 80 linhas dos 2 quadros do IPC 06 validadas e indexadas, sem apuração.

## 0. Fundação
- [x] 0.1 PO aprovou a proposal e decidiu F1–F5 em 2026-09-14
- [x] 0.1b Registrar `docs/contas-stn/fontes-recursos-stn-2026.xlsx` em
      `knowledge/sources/stn/metadata.yaml` (sha256
      `2996eb9890283aa6e5ae658bb92f9eb2eddd60a2209d59b7fbf80659ec9594cf`)
- [x] 0.2 `knowledge/sources/ipc06/metadata.yaml` (19 páginas, edição 2024-06, SHA-256
      `e663ffe5ee0376fd03e7cd340e79a9f6a4a8e265e9e4863098f7f1773dc1d097`)
- [x] 0.3 `scripts/extract_ipc.py` parametrizado (D6) e `extracted.md` do IPC 06 gerado
- [x] 0.4 `docs/source-analysis-ipc06.md` com as ambiguidades encontradas e as decisões F1–F5

## 1. TEST (antes do código)
- [x] 1.1 Traduzir cada `#### Scenario:` do delta spec em `tests/test_regras_bf.py`
- [x] 1.2 Rodar e **confirmar que falha** pelo motivo esperado (base do BF inexistente)

## 2. IMPLEMENT
- [x] 2.1 `knowledge/schemas/rule.json`: `fonte_recurso`, `saldo`, `movimento`, decisões `F*`
- [x] 2.2 `scripts/validate_rules.py`: `field` e colunas derivados de `source.document` (D1)
- [x] 2.3 `knowledge/policies/ipc06.yaml` — itens 27, 30, 33, 37 e 38
- [x] 2.4 `quadro_principal.yaml` ingressos `L1`–`L33` (pp. 10–12)
- [x] 2.5 `quadro_principal.yaml` dispêndios `L34`–`L66` (pp. 12–13)
- [x] 2.6 `quadro_anexo.yaml` `L1`–`L14` (pp. 14–15), com `(c)` e `(f)` calculadas
- [x] 2.7 `scripts/build_index.py` cobrindo `BF`; regerar `rules_index.json`
- [x] 2.8 Migration: n/a (a base é arquivo)

## 3. REVIEW
- [x] 3.1 `git diff` completo: sem arquivo fora do escopo, sem código morto, sem `print`/segredo/`TODO` órfão
- [x] 3.2 `git diff tests/` contém apenas testes novos e mudanças justificáveis
- [x] 3.3 Diff do `rules_index.json` na parte `BO`: **vazio**

## 4. VERIFY
- [x] 4.1 `python -m pytest` — **287 passed / 0 failed**
- [x] 4.2 `python -m ruff check .` — 5 erros, todos pré-existentes e fora do escopo (`app/infra/regras/vigencias.py`, `app/routes/jobs.py`, `tests/bo/test_template.py`, `tests/pipeline/test_unidade_por_header.py`); arquivos da change limpos
- [x] 4.3 `python -m scripts.check_sources` — `2 documento(s)` e 8 tabelas, exit `0`
- [x] 4.4 `python -m scripts.validate_rules` — `BF: quadro_anexo 14 · quadro_principal 66`,
      149 regras no total, `review_required 6` (L22, L23, L28, L55, L56, L61)
- [x] 4.5 Reconferência da spec: cada cenário → onde é coberto
- [x] 4.6 Leitura cega: dado só o `rule_id` de `L30`, `L27` e `bf.quadro_anexo.l14`, a regra é
      implementável sem abrir o PDF

## 5. Arquivamento
- [x] 5.1 `tasks.md` 100% marcado
- [x] 5.2 Mesclar deltas em `openspec/specs/dca/base-canonica-regras/spec.md` — 27 requisitos /
      83 cenários; `CENARIOS_ESPERADOS` atualizado em `tests/test_cobertura_spec.py`
- [x] 5.3 Mover para `openspec/changes/archive/2026-09-14-ipc06-bf-regras-canonicas/`
- [x] 5.4 Atualizar a tabela "Change ativa" em `openspec/AGENTS.md`
