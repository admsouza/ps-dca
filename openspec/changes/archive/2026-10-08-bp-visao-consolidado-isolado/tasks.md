# Tasks — BP emitido isolado ou consolidado

**Repo:** `ps-dca` · front: `front-declaracoes`, change `dca-bp-visao-consolidado`

## 0. Fundação
- [x] 0.1 Consolidado de Cuitegi 2025 medido antes de `bp-espelho-iab` (2026-10-07)
- [x] 0.2 PO aprovou a proposal — 2026-10-08

## 1. TEST
- [x] 1.1 Cenários do delta em `tests/bp/test_visao.py` e `tests/pipeline/test_bp_visao.py`
- [x] 1.2 Rodar e confirmar que falham pelo motivo esperado

## 2. IMPLEMENT
- [x] 2.1 Schema e carregador: `filters[].visao` (D1), ida e volta pela vigência no banco
- [x] 2.2 YAML: 20 exclusões intra com `visao: consolidado`; `L34` com `2.3.2.1.2.00.00`; policy; índice
- [x] 2.3 Serviço do BP: duas visões sobre uma leitura (D2)
- [x] 2.4 Serialização e rota `GET /dca/BP?visao=` (D3, D4)

## 3. VERIFY
- [x] 3.1 `python -m pytest`, `python -m ruff check .`, validador sem erro `bp.*`
- [x] 3.2 Cuitegi 2025 real: isolado = planilha (regressão); consolidado medido e registrado na auditoria
- [x] 3.3 Front `dca-bp-visao-consolidado` contra a API local — conferido no navegador pelo PO em 2026-10-08: consolidado correto.

## 4. Arquivamento
- [x] 4.1 Mesclar delta, atualizar `CENARIOS_ESPERADOS`, arquivar e atualizar `openspec/AGENTS.md`
