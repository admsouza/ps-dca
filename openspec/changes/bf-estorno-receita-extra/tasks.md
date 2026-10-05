# Tasks — Estorno de receita extra no BF

**Repo:** `ps-dca` · **PO aprovou em 2026-10-05.**

## 0. Fundação
- [x] 0.1 PO aprovou: líquido só na PublicSoft; SICONFI permanece o movimento da MSC

## 1. PLAN/ARCH
- [x] 1.1 `design.md` com D1–D3

## 2. TEST
- [x] 2.1 Cenários do delta em teste
- [x] 2.2 Suíte nova falha antes do código

## 3. IMPLEMENT
- [x] 3.1 Consulta do relatório na PublicSoft
- [x] 3.2 Abatimento de `L27`/`L60` e das somas
- [x] 3.3 SICONFI sem chamada e sem mudança de valor

## 4. REVIEW
- [x] 4.1 Diff só no escopo

## 5. VERIFY
- [x] 5.1 `python -m pytest` — 474 passed / 1 failed (`test_dois_documentos_integros`, pré-existente: ipc04 é o terceiro documento)
- [x] 5.2 `python -m ruff check` nos arquivos da change — limpo. `ruff check .` segue com 5 erros pré-existentes fora desta change
