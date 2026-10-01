# Tasks — Anexo Manual alimenta (I) e totalizadoras

**Repo:** `ps-dca` · Fatia: Recife 2025.

## 0. Fundação
- [x] 0.1 PO aprovou escopo ampliado (2026-09-23)

## 1. TEST
- [x] 1.1 Cenários do delta em `tests/bf/test_apuracao.py`
- [x] 1.2 Confirmados com a implementação

## 2. IMPLEMENT
- [x] 2.1 De-para anexo → `(I)` + D2/D4
- [x] 2.2 Compostas Manual (D6) incl. TOTAL VI/XII
- [x] 2.3 Conferência anterior (D5)
- [x] 2.4 Sem migration

## 3. REVIEW
- [x] 3.1 Diff só no escopo (`quadro_principal` + testes + OpenSpec)

## 4. VERIFY
- [x] 4.1 `tests/bf/test_apuracao.py` + `test_anterior_manual.py` — 36 passed
- [x] 4.2 ruff nos arquivos tocados

## 5. Arquivamento
- [x] 5.1 Mesclar delta em `openspec/specs/dca/balanco-financeiro/spec.md` (2026-10-01)
- [x] 5.2 Mover para `archive/2026-10-01-bf-manual-anexo-alimenta-receita-i/`
- [x] 5.3 Atualizar `openspec/AGENTS.md`
- [x] 5.4 Front: pode parar de injetar `(I)`; o preview de totais pode espelhar a API. Registrado no índice do OpenSpec.
