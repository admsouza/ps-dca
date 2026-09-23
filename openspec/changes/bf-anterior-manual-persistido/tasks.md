# Tasks — Exercício anterior manual persiste na unidade

**Repo:** `ps-dca` · **Não implementar sem aprovação explícita do PO.**
Fatia vertical: Recife (`2611606`), exercício 2025, `L17` = `628456869.17`.

## 0. Fundação
- [x] 0.1 PO pediu a implementação em 2026-09-23

## 1. TEST (antes do código)
- [x] 1.1 Um teste por `#### Scenario:` dos dois deltas — `tests/pipeline/test_anterior_manual.py`
- [x] 1.2 Rodou e falhou pelo motivo esperado; depois ficou verde

## 2. IMPLEMENT
- [x] 2.1 Mapa em `procedencia.valores_anteriores` na apuração manual
- [x] 2.2 Helper `parametros_efetivos`: omisso reaplica; MSC explícita não
- [x] 2.3 `POST` lê o corpo; `valores_anteriores` na query responde `400`
- [x] 2.4 Worker do percurso usa o helper
- [x] 2.5 Erro de job não apaga a procedência
- [x] 2.6 Sem migration

## 3. REVIEW
- [x] 3.1 Diff nos arquivos do design
- [x] 3.2 Nenhum log do mapa

## 4. VERIFY
- [x] 4.1 `tests/pipeline/test_anterior_manual.py` + rota BF — 11 passed
- [x] 4.2 `ruff check` limpo nos arquivos tocados
- [ ] 4.3 Recife/2025 ao vivo: gravar `L17`, ler de novo sem mapa, percurso, MSC explícita
- [x] 4.4 Cenários cobertos em `test_anterior_manual.py`

## 5. Arquivamento
- [ ] 5.1 `tasks.md` 100% marcado (falta 4.3)
- [ ] 5.2 Mesclar os deltas em `openspec/specs/`
- [ ] 5.3 Mover para `openspec/changes/archive/AAAA-MM-DD-bf-anterior-manual-persistido/`
- [ ] 5.4 Atualizar a seção "Change ativa" em `openspec/AGENTS.md`
