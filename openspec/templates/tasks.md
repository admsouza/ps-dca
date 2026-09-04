# Tasks — <título curto>

**Repo:** `ps-dca` · **Não implementar sem aprovação explícita do PO.**
Fatia vertical: <anexo / ente / exercício validado ponta-a-ponta>.

## 0. Fundação
- [ ] 0.1 <fixtures, dependências, pré-requisitos>

## 1. TEST (antes do código)
- [ ] 1.1 Traduzir cada `#### Scenario:` do delta spec em `tests/test_<...>.py`
- [ ] 1.2 Rodar e **confirmar que falha** pelo motivo esperado

## 2. IMPLEMENT
- [ ] 2.1 <código mínimo para o cenário 1>
- [ ] 2.2 <código mínimo para o cenário 2>
- [ ] 2.3 Migration (se houver): validar `upgrade → downgrade → upgrade`

## 3. REVIEW
- [ ] 3.1 `git diff` completo: sem arquivo fora do escopo, sem código morto, sem `print`/segredo/`TODO` órfão
- [ ] 3.2 `git diff tests/` contém apenas testes novos e mudanças justificáveis

## 4. VERIFY
- [ ] 4.1 `python -m pytest` — reportar `N passed / M failed`
- [ ] 4.2 `python -m ruff check .` — limpo
- [ ] 4.3 `alembic upgrade head` (se houver schema)
- [ ] 4.4 Espelho 1:1 contra `tt/dca` (contagem + valores)
- [ ] 4.5 Reconferência da spec: cada cenário → onde é coberto

## 5. Arquivamento
- [ ] 5.1 `tasks.md` 100% marcado
- [ ] 5.2 Mesclar deltas em `openspec/specs/`
- [ ] 5.3 Mover para `openspec/changes/archive/AAAA-MM-DD-<slug>/`
- [ ] 5.4 Atualizar a tabela "Change ativa" em `openspec/AGENTS.md`
