# Tasks — Balanço Financeiro por unidade gestora

**Repo:** `ps-dca` · **Não implementar sem aprovação explícita do PO.**
Fatia vertical: Cuitegi (`2505204`) 2025, BF por UG (PublicSoft) e por PO (SICONFI com token).
Ordem: depois de `pipeline-dca-por-unidade-gestora`, **antes** de `pipeline-anterior-por-recorte`.

## 0. Fundação
- [x] 0.1 Decisões do PO (2026-10-13): change própria, `po:` pelo `poderOrgao` do `ps-erp`, estorno sem unidade no diagnóstico, PO com aviso no ente SIAFIC pela MSC, UG nova com zero + aviso
- [x] 0.2 PO aprovou a proposal; design e tasks revisados depois do gate (2026-10-13)
- [ ] 0.3 `pipeline-dca-por-unidade-gestora` arquivada
- [ ] 0.4 `ps-erp` `relatorio-estorno-poder-orgao` em homologação (só o recorte `po:` com estorno depende disso)
- [ ] 0.5 Fixture: resposta sintética real de estorno de Cuitegi 2025 e 2024, sem token
- [ ] 0.6 Medir: Σ `totaisPorUnidadeGestora` = 115.679,40 e toda `idInstituicao` presente na base por UG

## 1. TEST (antes do código)
- [x] 1.1 `tests/msc/test_estorno_por_unidade.py`: parse de `Estorno`; falta de `totaisPorUnidadeGestora` → erro; `poderOrgao` ausente × `null`
- [x] 1.2 `tests/recorte/test_bf_estorno_por_unidade.py`: abatimento por UG, PO e grupo; partição por UG e por PO; uma chamada por exercício; estorno sem unidade (UG sem registro, PO nulo); anterior manual e G8 só no consolidado; UG nova com zero + aviso; consolidado bit a bit
- [x] 1.3 Rota: `GET /dca/BF?recorte=ug:3` `200` sem `enqueue`; visibilidade por poder no BF; `avisoRecorte` só com SIAFIC + `use_siconfi=true` (BO, BP e BF)
- [x] 1.4 Rodar e confirmar que falham pelo motivo esperado

## 2. IMPLEMENT
- [x] 2.1 `Estorno` no adapter
- [x] 2.2 Memória do estorno no escopo; `_Filtrada` (estorno por recorte) e `_Observada` (unidades por exercício)
- [x] 2.3 `_abater_estorno` com `Estorno.total`; `g8_so_no_consolidado`
- [x] 2.4 `com_recortes`: tirar `valores_anteriores`/`valores_sem_mapeamento` dos extras dos recortes; `"BF"` em `RECORTAVEIS`; `estorno_sem_unidade`
- [x] 2.5 `avisoRecorte` calculado na leitura (fonte SICONFI + token + recortes `po:`)

## 3. REVIEW
- [x] 3.1 `git diff` completo sem arquivo fora do escopo

## 4. VERIFY
- [x] 4.1 `python -m pytest` — 688 passed / 0 failed (2026-10-13)
- [x] 4.2 `python -m ruff check .` — 5 pré-existentes, nenhum novo
- [ ] 4.3 Cuitegi 2025: Σ `L27`/`L60` das UGs = consolidado − estorno sem unidade, com diferença 0,00; equilíbrio por UG pelo critério da proposal
- [x] 4.4 Reconferência cenário a cenário

## 5. Arquivamento
- [ ] 5.1 Mesclar os deltas em `openspec/specs/` e mover para `archive/`
- [ ] 5.2 Atualizar `openspec/AGENTS.md`
