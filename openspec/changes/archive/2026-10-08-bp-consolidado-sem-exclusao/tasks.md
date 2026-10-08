# Tasks — BP consolidado inclui todas as contas

**Repo:** `ps-dca` · **PO aprovou em 2026-10-08.**
Fatia vertical: BP de Cuitegi/PB (`2505204`), 2025, visão consolidado igual à I-AB.

## 0. Fundação
- [x] 0.1 Proposal, delta, design e tasks

## 1. TEST (antes do código)
- [x] 1.1 Cenários do delta em `tests/bp/test_visao.py`, `tests/bp/test_espelho_iab.py` e `tests/pipeline/test_bp_visao.py`
- [x] 1.2 Rodar e confirmar a falha pelo motivo esperado

## 2. IMPLEMENT
- [x] 2.1 `apurar` deixa de aplicar os filtros `visao: consolidado`

## 3. REVIEW
- [x] 3.1 Diff só nos arquivos do design

## 4. VERIFY
- [x] 4.1 `python -m pytest` — 606 passed após mesclar a spec (1 failed antes, só a cobertura dos cenários antigos)
- [x] 4.2 `python -m ruff check` nos arquivos desta change — limpo. O `ruff check .` segue com 5 erros pré-existentes fora do escopo
- [x] 4.3 Sem migration
- [x] 4.4 Espelho: consolidado de Cuitegi 2025 = isolado = 76.314.331,92 (sintético da planilha)
- [x] 4.5 Cada cenário do delta apontado no teste

## 5. Arquivamento
- [x] 5.1 `tasks.md` marcado
- [x] 5.2 Mesclar delta em `openspec/specs/`
- [x] 5.3 Mover para `openspec/changes/archive/2026-10-08-bp-consolidado-sem-exclusao/`
- [x] 5.4 Tabela de changes em `openspec/AGENTS.md`
