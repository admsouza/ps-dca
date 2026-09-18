# Tasks — Quadro Anexo do Balanço Financeiro

**Repo:** `ps-dca` · Fatia: as 14 linhas × 6 colunas apuradas e conferidas contra o quadro principal.

## 0. Fundação
- [x] 0.1 14 regras transcritas em `knowledge/rules/bf/quadro_anexo.yaml` (change arquivada
      `ipc06-bf-regras-canonicas`)
- [x] 0.2 Motor já calcula coluna derivada (`RefColuna`) e carregador já traz as 80 regras
- [x] 0.3 PO aprova a proposal — autorizado em 2026-09-18

## 1. TEST (antes do código)
- [x] 1.1 Cenários do delta spec em `tests/bf/test_quadro_anexo.py`
- [x] 1.2 Teste de coluna derivada com parcela não apurada — `(c)` é `None`, não subtração parcial
- [x] 1.3 Teste da conferência `L14 (c)` × `L1` do principal
- [x] 1.4 Rodar e confirmar que falham pelo motivo esperado

## 2. IMPLEMENT
- [x] 2.1 Serviço do BF devolve os dois quadros, com `quadro` declarado por linha
- [x] 2.2 Resíduo de fonte no anexo: receita sem fonte declarada, com valor
- [x] 2.3 Conferência entre quadros no diagnóstico
- [x] 2.4 `--quadro principal|anexo|todos` no CLI
- [x] 2.5 Migration: n/a

## 3. REVIEW
- [x] 3.1 `git diff` completo; nenhuma alteração no quadro principal

## 4. VERIFY
- [x] 4.1 `python -m pytest` — **362 testes, exit 0**
- [x] 4.2 `python -m ruff check .` — limpo nos arquivos tocados
- [x] 4.3a Medido em Recife com dados reais: `L14` fecha `L1 + L2 + L10` nas 6 colunas;
      `L14 (c)` = 9.939.848.008,46 = `L1` do quadro principal, diferença **0,00**; resíduo de fonte
      declarado em 450.202.814,72
- [x] 4.3b Medido nos **5 entes**: `L14` fecha nas 6 colunas em todos (6/6) e `L14` Saldo é igual
      a `L1` do quadro principal, diferença **0,00** em todos. Resíduo de receita sem fonte só em
      Recife (450.202.814,72); os outros quatro entes não têm registro sem fonte na MSC
- [x] 4.4 Relatório de auditoria de cada ente estendido ao anexo, gerado pelo **código de
      produção**: as 14 linhas × 6 colunas e as conferências internas. A comparação contra o
      quadro anexo publicado não é feita célula a célula — os entes que o publicam usam recorte
      próprio (JP tem 6 colunas com outra semântica; Recife, outro corte)
- [x] 4.5 Regressão: quadro principal e BO inalterados — 364 testes, exit 0

## 5. Arquivamento
- [x] 5.1 `tasks.md` 100% marcado
- [x] 5.2 Mesclar delta em `openspec/specs/dca/balanco-financeiro/spec.md`
- [x] 5.3 Mover para `openspec/changes/archive/AAAA-MM-DD-bf-quadro-anexo/`
- [x] 5.4 Atualizar a tabela "Change ativa" em `openspec/AGENTS.md`
