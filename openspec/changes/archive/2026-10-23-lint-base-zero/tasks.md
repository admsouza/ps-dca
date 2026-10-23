# Tasks — Lint na base zero

**Repo:** `ps-dca` · Fatia: `ruff check .` em 0 achados, sem tocar em comportamento.

## 0. Fundação
- [x] 0.1 Medido em 2026-10-23: 6 achados, todos presentes antes das changes da DVP
      (conferido com `git stash -u` na árvore limpa)
- [x] 0.2 PO aprovou

## 1. TEST
- [x] 1.1 Sem teste novo: a verificação é o próprio `ruff check .`, e a suíte existente é a rede de
      proteção contra alteração acidental de comportamento

## 2. IMPLEMENT
- [x] 2.1 `ruff check . --fix` nos três automáticos — `3 fixed`: linha em branco sobrando em
      `vigencias.py:121`, idem `tests/bo/test_template.py:206`, e `HTTPException` morto em
      `tests/pipeline/test_unidade_por_header.py:5`
- [x] 2.2 Três `E501` quebrados à mão: string de log partida em duas (`vigencias.py:188`),
      comentário de fim de linha movido para a linha de cima
      (`test_autorizacao_por_ug.py:314`) e docstring de módulo em duas linhas
      (`test_unidade_por_header.py:1`)

## 3. REVIEW
- [x] 3.1 `git diff`: 4 arquivos, 10 inserções e 7 remoções, só import, quebra de linha e
      import morto. Nenhuma linha de lógica

## 4. VERIFY
- [x] 4.1 `python -m ruff check .` — **All checks passed!** (0 achados)
- [x] 4.2 `python -m pytest` — **916 passed, 3 deselected**, o mesmo de antes

## 5. Arquivamento
- [x] 5.1 `tasks.md` marcado
- [x] 5.2 Sem delta de spec a mesclar
- [x] 5.3 Pasta movida para `openspec/changes/archive/2026-10-23-lint-base-zero/`
- [x] 5.4 `openspec/AGENTS.md` atualizado
