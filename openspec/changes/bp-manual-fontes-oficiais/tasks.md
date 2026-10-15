# Tasks — BP manual com catálogo oficial de fontes

**Repo:** `ps-dca` · **Não implementar sem aprovação explícita do PO.**
Fatia vertical: catálogo oficial e manual do BP de Cuitegi (`2505204`), exercício 2025.

## 0. Fundação
- [x] 0.1 PO aprova `proposal.md` e o delta spec
- [x] 0.2 Confirmar que a change `bp-superavit-por-fonte` permanece sem alteração

## 1. TEST (antes do código)
- [x] 1.1 Traduzir cada `#### Scenario:` em testes do service e da rota
- [x] 1.2 Cobrir regressão dos rótulos já produzidos pelo quadro apurado
- [x] 1.3 Rodar testes focados e confirmar falha pelo motivo esperado

## 2. IMPLEMENT
- [x] 2.1 Extrair o carregador canônico e a geração `1xxx`/`2xxx`
- [x] 2.2 Reusar o carregador nos rótulos e na validação manual
- [x] 2.3 Expor `GET /dca/fontes-recursos` autenticado e sem leitura externa
- [x] 2.4 Recusar código desconhecido antes de enfileirar

## 3. REVIEW
- [x] 3.1 `git diff` completo: preservar alterações locais fora do escopo
- [x] 3.2 Confirmar ausência de tabela duplicada, fallback permissivo e dados sensíveis
- [x] 3.3 Confirmar que rota não consulta MSC, cache de anexos ou fila

## 4. VERIFY
- [ ] 4.1 `python -m pytest` — reportar `N passed / M failed`
- [ ] 4.2 `python -m ruff check .` — limpo
- [x] 4.3 `python -m scripts.check_sources knowledge`
- [x] 4.4 Reconferir cada cenário do delta contra seu teste
- [x] 4.5 Confirmar regressão bit a bit do BP nos testes existentes

## 5. Arquivamento
- [ ] 5.1 `tasks.md` 100% marcado
- [ ] 5.2 Mesclar delta em `openspec/specs/dca/balanco-patrimonial/spec.md`
- [ ] 5.3 Mover para `openspec/changes/archive/2026-10-15-bp-manual-fontes-oficiais/`
- [ ] 5.4 Atualizar a tabela de changes ativas em `openspec/AGENTS.md`

## Validação parcial em 2026-10-15
- `tests/bp`: 72 passed.
- Cenários da rota de fonte oficial/inválida: 2 passed.
- Demais grupos não concorrentes: 296 passed.
- Suíte global: duas tentativas excederam 5 e 10 minutos enquanto outro `pytest` alterava/executava a rota.
- Ruff global: bloqueado por alterações concorrentes fora desta change; arquivos da change estavam limpos antes dessas alterações.
