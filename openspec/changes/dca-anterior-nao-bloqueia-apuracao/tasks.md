# Tasks — O exercício anterior não bloqueia a apuração

**Repo:** `ps-dca` · **Aprovada pelo PO em 2026-10-22.**
Fatia vertical: BP 2025 do ente 2505204, sem BP 2024 em cache, `ug:1` em Manual e `ug:2` em `0,00`.

## 0. Fundação
- [x] 0.1 Fixture de MSC com duas UGs em N e nenhum resultado `ok` em N−1 (reproduz 2026-10-22)

## 1. TEST (antes do código)
- [x] 1.1 Traduzir cada `#### Scenario:` do delta spec em `tests/recorte/test_anterior_por_recorte.py`
      e `tests/pipeline/test_rota_anterior_por_recorte.py`
- [x] 1.2 Rodar e **confirmar que falha** pelo motivo esperado

## 2. IMPLEMENT
- [x] 2.1 `OrigemAnterior.SEM_ANTERIOR`; `resolver` devolve a origem em vez de levantar
- [x] 2.2 Remover `ProcessadoSemAnterior`, `exigir`, `faltam_processado`, `mensagem_sem_processado`
- [x] 2.3 Remover `_exigir_n1` e `_unidades_gravadas` de `anexos.py`, com as chamadas
- [x] 2.4 `da_unidade`: coluna anterior zerada + `sem_dados_exercicio_anterior` na unidade; sai o
      parâmetro `exigir_processado`
- [x] 2.5 BP: `zero_sem_anterior` passa a valer no ramo da coluna pronta (`_coluna_pronta`)
- [x] 2.6 BF: célula ausente da coluna pronta vira `0,00`, sem `NaoApurada`

## 3. REVIEW
- [x] 3.1 `git diff` completo: sem arquivo fora do escopo, sem código morto, sem `print`/segredo/`TODO` órfão
- [x] 3.2 `git diff tests/` contém apenas testes novos e mudanças justificáveis
- [x] 3.3 O `ponytail:` de `anexos.py:323` saiu junto com a causa
- [x] 3.4 A change é deleção líquida: conferir saldo de linhas

## 4. VERIFY
- [x] 4.1 `python -m pytest` — reportar `N passed / M failed`
- [x] 4.2 `python -m ruff check .` — limpo
- [x] 4.3 Regressão: BF/BP com Processado e Manual saem iguais ao atual
- [ ] 4.4 Medição viva no ente 2505204: BP 2025 conclui `ok` sem BP 2024 em cache
- [ ] 4.5 Medição viva: com `ug:1` em Manual e `ug:2` sem anterior, o consolidado traz o Manual
      somado a `0,00`
- [x] 4.6 Reconferência da spec: cada cenário → onde é coberto

## 5. Arquivamento
- [ ] 5.1 `tasks.md` 100% marcado
- [ ] 5.2 Mesclar deltas em `openspec/specs/` — a redação desta change prevalece sobre
      `dca-anterior-processado-manual`
- [ ] 5.3 Mover para `openspec/changes/archive/AAAA-MM-DD-dca-anterior-nao-bloqueia-apuracao/`
- [ ] 5.4 Atualizar a tabela "Change ativa" em `openspec/AGENTS.md`
