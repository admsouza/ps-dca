# Tasks — L51 Reserva do RPPS apurada como L39

**Repo:** `ps-dca` · **Aprovada pelo PO em:** 2026-09-10
Fatia vertical: Quadro Principal L51, mapeamento `*id003`, fora do XV.

## 1. TEST (antes do código)
- [x] 1.1 `test_l51_tem_as_seis_colunas_da_l39` — colunas, filtros, fora do L50
- [x] 1.2 `test_reserva_do_rpps_apura_como_l39` — MSC 99.997 vs 99.999
- [x] 1.3 Rodar e confirmar vermelho pelo `columns: {}`

## 2. IMPLEMENT
- [x] 2.1 `L51` com `columns: *id003` e nota de proveniência 2026-09-10
- [x] 2.2 Adendo B6 em `docs/source-analysis-ipc07.md`
- [x] 2.3 Comentários que citavam L51 sem coluna

## 3. REVIEW
- [x] 3.1 Diff só no escopo
- [x] 3.2 Testes só os cenários da change

## 4. VERIFY
- [x] 4.1 `python -m pytest` — 200 passed / 1 failed (pré-existente: docstring sem Scenario:/Requisito: em dois testes fora desta change)
- [x] 4.2 `python -m ruff check` nos arquivos tocados — limpo
- [x] 4.3 Reconferência: cada cenário do delta coberto

## 5. Arquivamento
- [x] 5.1 Mesclar deltas em `openspec/specs/`
- [x] 5.2 Mover para `openspec/changes/archive/2026-09-10-ipc07-l51-reserva-rpps/`
- [x] 5.3 Atualizar `openspec/AGENTS.md`
