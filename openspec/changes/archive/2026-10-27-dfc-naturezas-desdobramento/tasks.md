# Tasks — Desdobramento da natureza de receita no IPC 08

**Repo:** `ps-dca` · Correção de `pattern` na base canônica, com o literal do PDF intacto.

## 0. SPEC
- [x] 0.1 Causa medida na F1: `L9` = 0,00 porque `1321001x` não alcança `13210101`
- [x] 0.2 Cruzado com `docs/contas-stn/natureza-receita.md`: o IPC lista 4 variantes e a STN tem
      os desdobramentos `01`, `02`, `03` e `04` de `1.3.2.1` — correspondência inequívoca
- [x] 0.3 PO confirmou a leitura ("13210101 e não 1321001x") e decidiu o escopo e o caso ambíguo

## 1. TEST
- [x] 1.1 `tests/test_regras_dfc.py::test_desdobramento_da_natureza_de_receita` — os 8 patterns,
      literais intactos, e `L5` com blocker
- [x] 1.2 `tests/dfc/test_conferencia_viva.py` — `L9` e `L5` nos valores medidos (marker `vivo`)

## 2. IMPLEMENT
- [x] 2.1 8 patterns em `knowledge/rules/dfc/quadro_principal.yaml` (`L5` not_in, `L9` in)
- [x] 2.2 `L5`: `status: review_required` + `blocker` do `7.3.21.00.31.x`
- [x] 2.3 `L9`: nota da correção em `review.reason`, com o valor medido
- [x] 2.4 `scripts/validate_rules.py`: `IPC08` em `BLOQUEIO_DECLARADO`, com o porquê no comentário
- [x] 2.5 `python -m scripts.build_index knowledge`

## 3. REVIEW
- [x] 3.1 `git diff`: nenhum literal alterado — só `pattern`, `status`, `review`
- [x] 3.2 Sem alteração em `app/` nem no motor

## 4. VERIFY
- [x] 4.1 `python -m app.cli.dfc 4314902 2025`: `L9` 776.452.523,68 e `L5` 144.308.504,92 (2025);
      555.698.790,43 e 20.864.012,19 (2024)
- [x] 4.2 `L2`, `L1` e `L34` inalterados — reclassificação, não mudança de valor
- [x] 4.3 Quatro entes com `L9` apurando; resíduo de `L16` inalterado em todos
- [x] 4.4 `python -m scripts.validate_rules knowledge` — exit 0, `review_required` 18 → 19
- [x] 4.5 `python -m pytest` verde; `python -m ruff check .` limpo

## 5. Arquivamento
- [x] 5.1 `tasks.md` 100% marcado
- [x] 5.2 Delta mesclado em `openspec/specs/dca/demonstracao-fluxos-caixa/spec.md`
- [x] 5.3 `CENARIOS_ESPERADOS["dca/demonstracao-fluxos-caixa"]`: 24 → 26
- [x] 5.4 Mover para `openspec/changes/archive/2026-10-27-dfc-naturezas-desdobramento/`
- [x] 5.5 `openspec/AGENTS.md` atualizado
