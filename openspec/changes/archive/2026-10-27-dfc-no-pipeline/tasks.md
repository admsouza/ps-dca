# Tasks — DFC servida pelo pipeline

**Repo:** `ps-dca` · Fatia vertical: `GET /dca/DFC` de Porto Alegre (`4314902`) 2025 devolvendo as
84 linhas, com o mesmo JSON do CLI.

## 0. Fundação
- [x] 0.1 `dfc-apuracao-f1` com §4 verde: 84 linhas, 0 não apuradas, identidade de caixa fechando
- [x] 0.2 Gaps levantados no código, não supostos: `DFC` ausente do `REGISTRY` → `GET /dca/DFC`
      responde **404** (`anexos.py:101`); seis asserções fixando 4 anexos; golden com 12 resumos
- [x] 0.3 Verificado que **não** há gap de plataforma: rota genérica (`anexos.py:583`), cache
      genérico, despacho por registry, `ORDEM_POR_DOCUMENTO["IPC08"]` já posta na F1
- [x] 0.4 PO aprovou em 2026-10-27

## 1. TEST (antes do código)
- [x] 1.1 `tests/pipeline/test_dfc_no_pipeline.py` — registry, grafia, serviço, mapa do IPC 08,
      resumo e ordem dos quatro quadros
- [x] 1.2 `tests/pipeline/test_rota_dfc.py` — `GET /dca/DFC` 200 com 84 linhas,
      `POST /dca/dfc/reprocessar` 202, e rota == CLI
- [x] 1.3 Rodados e falhando pelo motivo esperado (`StopIteration` no resumo, `AnexoDesconhecido`
      na grafia, `NotImplementedError` no serviço)

## 2. IMPLEMENT
- [x] 2.1 `registry.py`: `ANEXO_DFC` e `Anexo("DFC", "app.services.dfc.quadro_principal:apurar",
      base_canonica="dfc")` entre os derivados (D1)
- [x] 2.2 Asserções de percurso e notificação: 4 anexos → 5 (6 testes)
- [x] 2.3 Golden: 12 entradas de resumo, alteração cirúrgica (D2)
- [x] 2.4 Migration: n/a

## 3. REVIEW
- [x] 3.1 `git diff` conferido: só `registry.py` em `app/`; o resto é teste e golden
- [x] 3.2 Nenhuma alteração de apuração: `app/services/dfc/` intacto nesta change

## 4. VERIFY
- [x] 4.1 `python -m pytest` — **961 passed, 7 deselected, 0 failed** (2026-10-27)
- [x] 4.2 `python -m ruff check .` — limpo
- [x] 4.3 `GET /dca/DFC` contra a app com portas fakes: 200, 84 linhas, quadros em bloco
- [x] 4.4 Rota e CLI publicam o mesmo JSON (teste de contrato)
- [x] 4.5 BO, BF, BP e DVP sem diferença de valor — suíte inteira verde

## 5. Arquivamento
- [x] 5.1 `tasks.md` 100% marcado
- [x] 5.2 Delta mesclado em `openspec/specs/pipeline/plataforma/spec.md`
- [x] 5.3 `CENARIOS_ESPERADOS["pipeline/plataforma"]`: 97 → 102
- [x] 5.4 Pasta movida para `openspec/changes/archive/2026-10-27-dfc-no-pipeline/`
- [x] 5.5 `openspec/AGENTS.md` atualizado
