# Tasks — BP: coluna do exercício anterior pela DCA publicada no SICONFI

**Repo:** `ps-dca` · **Não implementar sem aprovação explícita do PO.**
Fatia vertical: Cuitegi/PB (`2505204`) e João Pessoa/PB (`2507507`), BP 2025 com a coluna 2024 pelo
`I-AB` publicado.

## 0. Fundação
- [x] 0.1 `I-AB` de 2024 medido no `tt/dca`: 97 registros (Cuitegi), 136 (JP); hierarquia até o
      5º/6º nível; totais F/P e `SaldoPatrimonial` publicados
- [x] 0.2 PO decidiu: duas origens, publicado padrão, regras do IPC 04 sobre as contas publicadas
- [x] 0.3 PO aprova a proposal — 2026-10-07
- [x] 0.4 Medir folhas × grupo (`P1`, `P2`) e `L7` × `SaldoPatrimonial` em Cuitegi e JP 2024 →
      `docs/evidencia-bp-publicado-2024.md`

## 1. TEST
- [x] 1.1 Cenários do delta em `tests/bp/test_anterior_publicado.py` (dublê do `tt/dca`)
- [x] 1.2 Regressão: `msce_exercicio_anterior` bit a bit igual aos testes vigentes do BP
- [x] 1.3 Rodar e confirmar que falha pelo motivo esperado

## 2. IMPLEMENT
- [x] 2.1 `app/infra/siconfi/dca.py` com timeout e retry
- [x] 2.2 `app/services/bp/publicado.py`: folhas → `Registro`; totais F/P
- [x] 2.3 Serviço do BP: `Anterior`, coluna anterior pela origem, F/P publicado, diagnóstico
- [x] 2.4 Rota e percurso com a origem sempre explícita (D2)

## 3. REVIEW / 4. VERIFY
- [x] 3.1 `git diff` sem arquivo fora do escopo
- [x] 4.1 `python -m pytest` e `python -m ruff check .`
- [x] 4.2 Cuitegi e JP 2025 pelas duas origens: coluna anterior idêntica, atual idêntica; auditoria
      de Cuitegi atualizada (`docs/entes-homologacao/cuitegi/auditoria-bp-2025.md`, seção da coluna 2024)

## 5. Arquivamento
- [x] 5.1 Mesclar delta em `openspec/specs/dca/balanco-patrimonial/spec.md`; atualizar `CENARIOS_ESPERADOS`
- [x] 5.2 Mover para `openspec/changes/archive/` e atualizar `openspec/AGENTS.md`
