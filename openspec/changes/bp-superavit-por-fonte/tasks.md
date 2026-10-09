# Tasks — Superávit / Déficit Financeiro por fonte

**Repo:** `ps-dca` · **Não implementar sem aprovação explícita do PO.**
Fatia vertical: Cuitegi `2505204`, exercício 2025, SICONFI.

## 0. Fundação
- [x] 0.1 PO aprova `proposal.md` e o delta spec

## 1. TEST (antes do código)
- [x] 1.1 Traduzir cada `#### Scenario:` do delta em `tests/bp/test_superavit_fonte.py`
- [x] 1.2 Rodar e confirmar que falha pelo motivo esperado

## 2. IMPLEMENT
- [x] 2.1 Ler a classe 8 no BP e guardar `complemento_fonte`
- [x] 2.2 Apurar uma linha por fonte+complemento, saldo `C − D` de `821110100` e `821110200`, nas duas colunas
- [x] 2.3 Incluir fonte que começa com `2`; omitir linha zerada; total = soma das linhas
- [x] 2.4 As duas visões recebem o mesmo quadro; Compensação continua `None`

## 3. REVIEW
- [x] 3.1 `git diff` completo: sem arquivo fora do escopo, sem código morto, sem `print`/segredo/`TODO` órfão
- [x] 3.2 `git diff tests/` contém apenas testes novos e mudanças justificáveis

## 4. VERIFY
- [x] 4.1 `python -m pytest` — suíte do BP verde; suíte inteira com 1 falha de docstring corrigida em seguida
- [x] 4.2 `python -m ruff check` — limpo nos arquivos da change
- [ ] 4.3 Cuitegi 2025: `17500000`, `18020000`, `25000000` e os dois totais da proposal
- [ ] 4.4 Recorrer os cenários do delta e apontar o teste de cada um

## 5. Arquivamento
- [ ] 5.1 `tasks.md` 100% marcado
- [ ] 5.2 Mesclar deltas em `openspec/specs/`
- [ ] 5.3 Mover para `openspec/changes/archive/AAAA-MM-DD-bp-superavit-por-fonte/`
- [ ] 5.4 Atualizar a tabela "Change ativa" em `openspec/AGENTS.md`
