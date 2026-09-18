# Tasks — Competência de encerramento por fonte de MSC

## 0. Fundação
- [x] 0.1 Medido nos 4 entes: `me_referencia=13` no SICONFI devolve 0 registros; a MSCE está na 12
- [x] 0.2 Informação do PO sobre a API PublicSoft: `mesMsc=13` é a competência de encerramento

## 1. TEST
- [x] 1.1 Testes dos dois adapters em `tests/msc/test_competencia_de_encerramento.py`
- [x] 1.2 Confirmado que falhavam pelo motivo esperado (`assert 12 == 13`)

## 2. IMPLEMENT
- [x] 2.1 `PublicSoftMSC._competencia(mes, matriz)` traduz encerramento para 13
- [x] 2.2 Gate de auditoria consulta a mesma competência que será lida
- [x] 2.3 `COMPETENCIA_DE_ENCERRAMENTO` documentada como vocabulário do domínio
- [x] 2.4 Migration: n/a

## 3. REVIEW
- [x] 3.1 Diff restrito a `app/infra/msc/{publicsoft,fonte}.py` e ao teste novo

## 4. VERIFY
- [x] 4.1 `python -m pytest` — 341 testes, exit 0
- [x] 4.2 `python -m ruff check app/infra/msc tests/msc` — limpo

## 5. Arquivamento
- [x] 5.1 PO aprova retroativamente
- [x] 5.2 Mesclar delta em `openspec/specs/dca/fonte-msc/spec.md`
- [x] 5.3 Mover para `openspec/changes/archive/AAAA-MM-DD-msc-competencia-de-encerramento/`
