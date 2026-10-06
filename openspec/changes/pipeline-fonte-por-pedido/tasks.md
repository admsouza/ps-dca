# Tasks — Fonte de dados escolhida por pedido (`use_siconfi`)

**Repo:** `ps-dca` · **Não implementar sem aprovação explícita do PO.**
Fatia vertical: BF de Cuitegi/2025 (`2505204`) com `use_siconfi=false` e worker em `DATA_SOURCE=siconfi`.

## 0. Fundação
- [x] 0.1 PO aprova proposal e D1–D3 (2026-10-06)
- [ ] 0.2 Confirmar `AUTH_API_URL`, `S2S_API_SECRET` e `TOKEN_ENCRYPTION_KEY` na API e no worker (CapRover)

## 1. TEST (antes do código)
- [x] 1.1 `tests/pipeline/test_fonte_por_pedido.py`: um teste por cenário de "Fonte de dados escolhida por pedido"
- [x] 1.2 mesmo arquivo, hub `resolver_token`: 200, 403, 404, 409, rede fora
- [x] 1.3 Cenários de credencial: token guardado no cofre, ausente do payload; `409`/`503` sem job
- [x] 1.4 Rodar e confirmar que falham pelo motivo esperado

## 2. IMPLEMENT
- [x] 2.1 `hub.resolver_token`
- [x] 2.2 Rota: `use_siconfi` → `parametros["fonte"]`; token quando PublicSoft
- [x] 2.3 `cache.py`: `fonte` em `parametros_efetivos` e `identidade_do_pedido`; `credencial` em `ler_ou_enfileirar`
- [x] 2.4 `worker.py`: `fonte_nome=parametros.get("fonte")`

## 3. REVIEW
- [x] 3.1 `git diff` completo: sem arquivo fora do escopo, sem código morto, sem `print`/segredo/`TODO` órfão
- [x] 3.2 `git diff tests/` contém apenas testes novos e mudanças justificáveis

## 4. VERIFY
- [x] 4.1 `python -m pytest` — reportar `N passed / M failed` (pré-existente: `test_dois_documentos_integros`)
- [x] 4.2 `python -m ruff check .` — limpo
- [ ] 4.3 Produção: SIAFIC na tela → BF Cuitegi/2025 com `L27` = 4486188.21 e `L60` = 4479755.61
- [ ] 4.4 Reconferência da spec: cada cenário → onde é coberto

## 5. Arquivamento
- [ ] 5.1 `tasks.md` 100% marcado
- [ ] 5.2 Mesclar deltas em `openspec/specs/`
- [ ] 5.3 Mover para `openspec/changes/archive/AAAA-MM-DD-pipeline-fonte-por-pedido/`
- [ ] 5.4 Atualizar a tabela "Change ativa" em `openspec/AGENTS.md`
