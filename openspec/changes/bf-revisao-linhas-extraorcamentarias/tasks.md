# Tasks — Revisar linhas extraorçamentárias do Balanço Financeiro

**Repo:** `ps-dca` · **Não implementar sem aprovação explícita do PO.**
Fatia vertical: PM Cuitegi (`2505204`), caso outubro/2025 da SPEC-0001, totais `L24` e `L57`.

## 0. Fundação
- [ ] 0.1 PO aprova `proposal.md`
- [ ] 0.2 PO fecha D1 — o que "outubro/2025" é na apuração
- [ ] 0.3 PO fecha D2 — valor de `L27`, `L28`, `L60` e `L61`, e o que é ativo/passivo na composição
- [ ] 0.4 PO fecha D3 — contas de cada linha revisada

## 1. PLAN/ARCH
- [ ] 1.1 Completar componentes, fluxo e arquivos em `design.md` com D1–D3 fechadas
- [ ] 1.2 Traduzir D2 no delta spec: um cenário com o valor de cada linha

## 2. TEST (antes do código)
- [ ] 2.1 Traduzir cada `#### Scenario:` do delta spec em teste
- [ ] 2.2 Rodar e confirmar que falha pelo motivo esperado

## 3. IMPLEMENT
- [ ] 3.1 Código mínimo para `L24` = R$ 387.665,33 e `L57` = R$ 520.551,46 no caso Cuitegi
- [ ] 3.2 Procedência identifica a origem de `L27`, `L28`, `L60` e `L61`
- [ ] 3.3 Nenhuma linha fora do grupo muda de valor

## 4. REVIEW
- [ ] 4.1 `git diff` completo: sem arquivo fora do escopo, sem código morto, sem `print`/segredo/`TODO` órfão
- [ ] 4.2 `git diff tests/` contém apenas testes novos e mudanças justificáveis

## 5. VERIFY
- [ ] 5.1 `python -m pytest` — reportar `N passed / M failed`
- [ ] 5.2 `python -m ruff check .` — limpo
- [ ] 5.3 Medir `L24` e `L57` no caso Cuitegi da SPEC-0001
- [ ] 5.4 Reconferir cada `#### Scenario:` do delta e apontar o teste ou a medição

## 6. Arquivamento
- [ ] 6.1 `tasks.md` 100% marcado
- [ ] 6.2 Mesclar deltas em `openspec/specs/`
- [ ] 6.3 Mover para `openspec/changes/archive/AAAA-MM-DD-bf-revisao-linhas-extraorcamentarias/`
- [ ] 6.4 Atualizar a seção "Change ativa" em `openspec/AGENTS.md`
