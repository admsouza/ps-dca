# Tasks — Percurso completo respeita a origem da coluna anterior do BP

**Repo:** `ps-dca` · **Não implementar sem aprovação explícita do PO.**

## 0. Fundação
- [x] 0.1 Causas localizadas: `/batch-jobs` sem o parâmetro; `pedido_do_percurso` sobrescreve a
      origem com o padrão no worker
- [x] 0.2 PO aprova a proposal — 2026-10-07

## 1. TEST
- [x] 1.1 Cenários do delta em `tests/pipeline/test_percurso_origem_bp.py` (7 testes)
- [x] 1.2 Rodar e confirmar que falha pelo motivo esperado — **não comprovado**: o agente foi
      interrompido antes de registrar a execução prévia ao código

## 2. IMPLEMENT
- [x] 2.1 `pedido_do_percurso` com `origem_bp`
- [x] 2.2 Rota `/batch-jobs`: parâmetro, validação, `versao_de` e payload
- [x] 2.3 Worker: `origem_bp` no `pedido_de` (sem o dict que sobrescrevia a origem)

## 3. VERIFY
- [x] 3.1 `python -m pytest` — **590 passed / 0 failed** (base 583); ruff: 5 achados pré-existentes.
      Revisão: o teste de integração lia o BP sem `use_siconfi=true` (503 do hub no teste); corrigido

## 4. Arquivamento
- [x] 4.1 Mesclar delta em `openspec/specs/pipeline/processamento-completo/spec.md` (+4 em
      `CENARIOS_ESPERADOS`), arquivar e atualizar `openspec/AGENTS.md`
