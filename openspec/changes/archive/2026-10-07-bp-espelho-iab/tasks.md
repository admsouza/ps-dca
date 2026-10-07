# Tasks — BP espelha o DCA-Anexo I-AB declarado

**Repo:** `ps-dca`

## 0. Fundação
- [x] 0.1 Divergência medida contra `SICONFI_DCA_2831_ANUAL_1.xls` (Cuitegi 2025) e contra o `I-AB` de
      JP 2024/2025 no `tt/dca`
- [x] 0.2 PO aprovou a proposal — 2026-10-07

## 1. TEST
- [x] 1.1 Cenários do delta em `tests/bp/test_espelho_iab.py`
- [x] 1.2 Ajustar os testes vigentes que dependiam das exclusões intra e dos termos antigos da `L5`
- [x] 1.3 Rodar e confirmar que falham pelo motivo esperado (antes de mexer no YAML)

## 2. IMPLEMENT
- [x] 2.1 `quadro_principal.yaml`: remover exclusões intra (D1, D2)
- [x] 2.2 `ativos_passivos_financeiros.yaml`: nova composição da `L5` (D3)
- [x] 2.3 Policy `ipc04.yaml`; `python -m scripts.build_index knowledge`; validador sem erro `bp.*`

## 3. VERIFY
- [x] 3.1 `python -m pytest` e `python -m ruff check .` sem falha nova
- [x] 3.2 Cuitegi 2025 contra a planilha, linha a linha; JP 2024/2025 contra o `I-AB` do `tt/dca`
- [x] 3.3 Auditoria de Cuitegi e de-para refeitos

## 4. Arquivamento
- [x] 4.1 Mesclar delta, atualizar `CENARIOS_ESPERADOS`, arquivar e atualizar `openspec/AGENTS.md`
