# Design — BP espelha o DCA-Anexo I-AB declarado

**Change:** `openspec/changes/bp-espelho-iab/` · **Proposal aprovada pelo PO em:** 2026-10-07

## O que muda

Só a base canônica (`knowledge/rules/bp/`). O motor, o serviço e as origens não mudam: as exclusões
são filtros `not_in conta_contabil` nas regras, e a composição da `L5` são termos de conta.

| Arquivo | Mudança |
|---|---|
| `knowledge/rules/bp/quadro_principal.yaml` | remover dos `filters` os valores de 5º nível = 2 (intra); a `evidence.text` do PDF fica intacta; `review.reason` registra a decisão |
| `knowledge/rules/bp/ativos_passivos_financeiros.yaml` | `L5`: termos `21` F, `22` F, `6311`, `6315`, `63171`; remover `6221301`/`6221305` |
| `knowledge/policies/ipc04.yaml` | registrar que a exclusão intra não é executada (espelho do `I-AB`) |
| `knowledge/indexes/rules_index.json` | regenerar |
| `tests/test_regras_bp.py`, `tests/bp/*` | expectativas de L4 (`11382`), termos da L5 e testes que dependiam da exclusão intra |
| `docs/entes-homologacao/cuitegi/auditoria-bp-2025.md`, `docs/depara-bp-iab-ipc04.md` | refazer com o espelho |

## Decisões

### D1 — Filtro vazio some
Linha cujo filtro `not_in` fica sem valores perde o filtro inteiro (o schema exige `minItems: 1`).

### D2 — Literal do PDF preservado onde vai a regra
`evidence.text` continua com as exclusões do IPC 04; a divergência deliberada fica em `review.reason`,
com a referência à planilha e a esta change.

### D3 — `6.3.1.5` mantido
O `I-AB` não o detalha porque é zero nos entes medidos; é "RPNP a liquidar bloqueados", mesma natureza
de `6.3.1.1`. Sem ele, um ente com bloqueio teria o passivo financeiro subestimado.

## Regressão

BO e BF intactos. O `versao_regras` do BP muda, e todo BP em cache passa a `desatualizado`
(`versao_regras`) na leitura, sem reprocessar.
