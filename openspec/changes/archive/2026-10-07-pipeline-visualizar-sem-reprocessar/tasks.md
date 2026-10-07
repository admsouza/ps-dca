# Tasks — Visualizar um anexo apurado nunca reprocessa

**Repo:** `ps-dca` · **Não implementar sem aprovação explícita do PO.**
Fatia vertical: Cuitegi/PB (`2505204`), 2025 — BF processado, visualizado com outra fonte, após deploy
e após percurso.

## 0. Fundação
- [x] 0.1 Causas medidas no código: percurso sem fonte na identidade; fonte da leitura ≠ fonte do
      processamento; `versao_api` = hash do código
- [x] 0.2 PO decidiu: visualizar nunca processa; motivos no corpo; change separada
- [x] 0.3 PO aprova a proposal — 2026-10-07

## 1. TEST (antes do código)
- [x] 1.1 Cenários do delta em `tests/pipeline/test_visualizar_sem_reprocessar.py` (6)
- [x] 1.2 Testes vigentes de miss por versão (`test_ciclo.py`, `test_invalidacao.py`) passam a
      esperar `200` marcado; `test_troca_de_fonte_nao_serve_o_cache_da_outra` alinhado, com o delta
      de `pipeline-fonte-por-pedido` anotado (o cenário dele dizia `202`)
- [x] 1.3 Falharam pelo motivo esperado (`motivos_desatualizado` inexistente, `202` no lugar de
      `200`, `pedido_do_percurso` ausente). "Reprocessar e percurso reapuram" já passava: guarda

## 2. IMPLEMENT
- [x] 2.1 `cache.py`: `com_resultado`, `motivos_desatualizado`; leitura sem `forcar` serve todo `ok`;
      `servivel` = com resultado e sem motivos (critério do percurso); rota publica
      `desatualizado` e `motivos_desatualizado` no `200`
- [x] 2.2 `completo.pedido_do_percurso`, usado pela rota (`versao_de`) e pelo worker (pedido e
      `fonte_nome` do apurador)
- [x] 2.3 Migration: n/a

## 3. REVIEW
- [x] 3.1 `git diff` completo: sem arquivo fora do escopo, sem código morto
- [x] 3.2 `git diff tests/`: testes novos, a troca de miss por desatualizado nos vigentes e o cenário
      de troca de fonte

## 4. VERIFY
- [x] 4.1 `python -m pytest` — **564 passed / 0 failed** (antes: 559)
- [x] 4.2 `python -m ruff check .` — 5 achados, todos pré-existentes
- [x] 4.3 Reconferência — cache válido → `test_cache_valido_serve_sem_enfileirar` · visualizar
      desatualizado → `test_visualizar_resultado_desatualizado_nao_processa` · ausente, em voo,
      falhou → testes vigentes de `test_ciclo.py` · regra alterada →
      `test_versao_de_regras_divergente_e_servida_marcada` · reprocessar e percurso →
      `test_reprocessar_e_percurso_reapuram_o_desatualizado` · formatação, outro anexo, entes →
      vigentes de `test_invalidacao.py` · alteração real → `test_alteracao_real_de_regra_desatualiza`
      · API alterada → `test_versao_de_api_divergente_desatualiza` · depois do percurso →
      `test_visualizacao_depois_do_percurso_reconhece_o_cache`

## 5. Arquivamento
- [x] 5.1 `tasks.md` 100% marcado
- [x] 5.2 Delta mesclado em `openspec/specs/pipeline/plataforma/spec.md`; `CENARIOS_ESPERADOS`
      80 → 83
- [x] 5.3 Movido para `openspec/changes/archive/2026-10-07-pipeline-visualizar-sem-reprocessar/`
- [x] 5.4 Tabela "Change ativa" de `openspec/AGENTS.md` atualizada
