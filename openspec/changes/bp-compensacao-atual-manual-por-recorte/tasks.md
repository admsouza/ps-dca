# Tasks — BP · Compensação atual manual por recorte

**Repo:** `ps-dca` · **Não implementar sem aprovação explícita da proposal e do delta spec.**
Fatia vertical: Cuitegi/PB (`2505204`), 2025, `po:10131`/`po:10132`/`po:20231` → grupos → consolidado.

## 0. Fundação

- [x] 0.1 Change criada com autorização do PO em 2026-10-21
- [x] 0.2 PO aprovou `proposal.md` e o delta spec em 2026-10-21
- [ ] 0.3 Reconciliar o delta com `bp-superavit-por-fonte` se ela for arquivada antes desta change

## 1. TEST — antes do código

- [x] 1.1 Testar folhas/totalizadoras atuais da unidade, zero explícito e ausência `None`
- [x] 1.2 Testar soma de `ug:`/`po:` em grupo e consolidado, inclusive propagação de `None`
- [x] 1.3 Testar `422`, `403`, operação tudo ou nada e ausência de job
- [x] 1.4 Testar reaplicação por omissão, limpeza por mapa vazio e independência do anterior
- [x] 1.5 Rodar os testes novos e confirmar falha pelo motivo esperado (`12 failed`)

## 2. IMPLEMENT

- [x] 2.1 Validar e autorizar `valores_atuais_por_recorte` na rota
- [x] 2.2 Aplicar e totalizar Compensação atual no serviço BP
- [x] 2.3 Aplicar por individual e derivar grupos/consolidado no pipeline
- [x] 2.4 Persistir, reaplicar, limpar e identificar o mapa no cache/procedência
- [x] 2.5 Serializar a procedência manual necessária ao backend e ao frontend

## 3. REVIEW

- [x] 3.1 `git diff` completo: sem arquivo fora do escopo, código morto, `print`, segredo ou `TODO`
- [x] 3.2 Confirmar que BO, BF, outros quadros do BP e coluna anterior não mudaram
- [x] 3.3 Conferir autorização backend para todas as chaves antes de enfileirar

## 4. VERIFY

- [ ] 4.1 `python -m pytest` — `798 passed / 0 failed / 72 errors` de permissão em `tmp_path`
- [ ] 4.2 `python -m ruff check .` — 6 erros preexistentes fora da change; arquivos alterados limpos
- [x] 4.3 `python -m alembic upgrade head` — concluído; sem migration nova
- [ ] 4.4 Medir Cuitegi 2025: três POs, grupos e consolidado; diferença 0,00 nas somas
- [x] 4.5 Reconferir cada cenário do delta contra teste automatizado; medição viva segue em 4.4

## 5. Arquivamento

- [ ] 5.1 `tasks.md` 100% marcado
- [ ] 5.2 Mesclar o delta em `openspec/specs/dca/balanco-patrimonial/spec.md`
- [ ] 5.3 Mover para `openspec/changes/archive/AAAA-MM-DD-bp-compensacao-atual-manual-por-recorte/`
- [ ] 5.4 Atualizar a tabela “Change ativa” em `openspec/AGENTS.md`
