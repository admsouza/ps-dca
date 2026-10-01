# Tasks — Completar linhas sem mapeamento IPC 06 (exercício atual)

**Repo:** `ps-dca` · **Não implementar sem aprovação explícita do PO nesta proposal.**
Fatia vertical: Recife (`2611606`), exercício 2025, `L22` = `1234567.89`.

## 0. Fundação
- [x] 0.1 Framing sênior aprovado (completar G8 ≠ Manual do atual) — 2026-09-24
- [x] 0.2 PO aprovou esta `proposal.md` — 2026-09-24

## 1. TEST (antes do código)
- [x] 1.1 Um teste por `#### Scenario:` do delta — `tests/bf/test_valores_sem_mapeamento.py` e `tests/pipeline/test_valores_sem_mapeamento.py`
- [x] 1.2 Rodou e falhou pelo motivo esperado (KeyError/202≠400/202≠422); depois ficou verde

## 2. IMPLEMENT
- [x] 2.1 Schema/corpo: `valores_sem_mapeamento` no POST; query com o mapa → `400`
- [x] 2.2 Whitelist G8 (`L22`, `L23`, `L28`, `L55`, `L56`, `L61`); fora → `422`
- [x] 2.3 Após apurar atual MSC: merge das células → compostas da coluna atual → limpar diagnóstico dessas células
- [x] 2.4 Persistir em `procedencia.valores_sem_mapeamento`; pedido sem mapa no body reaplica o salvo
- [x] 2.5 Mapa vazio no body limpa o override (células voltam não apuradas)
- [x] 2.6 Independente de `origem_exercicio_anterior` / `valores_anteriores`
- [x] 2.7 Sem migration; sem log do mapa

## 3. VERIFY
- [x] 3.1 Testes da change verdes (11 novos) + suíte inteira verde (`python -m pytest`)
- [x] 3.2 `ruff check` limpo nos arquivos tocados
- [ ] 3.3 Recife/2025 ao vivo: gravar `L22`, ler sem mapa, reprocessar, limpar — **não executado** nesta revisão (2026-10-01). Os cenários estão cobertos por teste. Exige
      ambiente com MSC/banco reais fora do alcance desta sessão

## 4. Arquivamento
- [x] 4.1 Arquivado em 2026-10-01 por conferência de código. O item 3.3 (Recife ao vivo) permanece aberto.
- [x] 4.2 Mesclar delta em `openspec/specs/dca/balanco-financeiro/spec.md`
- [x] 4.3 Mover para `openspec/changes/archive/2026-10-01-bf-completar-nao-apuradas-g8/`
- [x] 4.4 Atualizar "Change ativa" em `openspec/AGENTS.md`
