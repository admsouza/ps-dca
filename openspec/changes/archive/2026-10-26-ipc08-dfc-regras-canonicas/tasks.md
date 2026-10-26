# Tasks — Regras canônicas da DFC (IPC 08)

**Repo:** `ps-dca` · **Não implementar a apuração sem aprovação explícita do PO.**
Fatia desta change: representação canônica das 84 linhas dos quatro quadros. Código Python,
pipeline e espelho SICONFI pertencem a change posterior.

## 0. SPEC
- [x] 0.1 Extrair o IPC 08 (`scripts/extract_ipc.py`) e conferir o SHA-256
      `fb04f03c2015ec61971fb87a1cbdd8f70c8596b7599b3f073ef61d6423442ac0` (21 páginas; 7–21
      rotacionadas).
- [x] 0.2 Ler as matrizes visualmente (pp. 7–16) e cruzar prefixos com `docs/contas-stn/`.
- [x] 0.3 Escrever `proposal.md`, `design.md` (D1–D8) e o delta
      `specs/dca/demonstracao-fluxos-caixa/spec.md`.
- [x] 0.4 Homologar a estrutura contra ente real — `docs/entes-homologacao/porto-alegre/gabarito-dfc-2025.md`
      (DFC 2025, administração direta): 36+14+29+4 publicados, 43 identidades fechando em centavos.
- [x] 0.5 PO decidiu (D10): linha sem conta vira campo informado pelo contador, como no BF.
      D3 confirmado, 84 regras inalteradas; a whitelist `{L16, L21, L30}` é escopo da apuração.
- [x] 0.6 PO decidiu (D9): `L27` soma `L30`, divergindo do literal do IPC 08. Aplicado em
      `knowledge/rules/dfc/quadro_principal.yaml` (`review.reason`; `evidence.text` intacto).
- [x] 0.7 Medir D4 contra a MSC de 5 entes (API SICONFI) — `docs/evidencia-dfc-d4-funcao-28.md`:
      leitura de inclusão confirmada, leitura de exclusão zeraria `L32` e `L14`.
- [x] 0.8 PO aprovou a proposal em 2026-10-26 — change de apuração liberada.

## 1. TEST
- [x] 1.1 `tests/test_regras_dfc.py` — contagem 84, L1 = L2 − L12, agregadora soma Outros (D9),
      L35 saldo inicial, L16 sem
      columns, N5 preservado, validador sem erro `dfc.*`.
- [x] 1.2 `tests/test_regras_bf.py::test_dois_documentos_integros` — 4 → 5 documentos.

## 2. IMPLEMENT (conhecimento)
- [x] 2.1 `knowledge/sources/ipc08/metadata.yaml` e `extracted.md`. PDF fora de `knowledge/`.
- [x] 2.2 `knowledge/policies/ipc08.yaml` — itens 13–17.
- [x] 2.3 84 regras nos quatro YAML de `knowledge/rules/dfc/`.
- [x] 2.4 `python -m scripts.build_index knowledge`.

## 3. REVIEW
- [x] 3.1 Sem `app/`, sem schema, sem `validate_rules.py`.
- [x] 3.2 Literal N5 intacto; L16/L21/L30 sem `columns`.

## 4. VERIFY
- [x] 4.1 `python -m scripts.validate_rules knowledge` — exit 0; DFC 36+15+29+4; total 310;
      `review_required` 18 (4 da DFC + pré-existentes).
- [x] 4.2 `python -m scripts.check_sources knowledge` — 5 documentos.
- [x] 4.3 jsonschema `rule.json` e `policy.json` — 84 + 5.
- [x] 4.4 `python -m pytest tests/test_regras_dfc.py tests/test_regras_bf.py::test_dois_documentos_integros` — 14 passed
- [x] 4.5 `python -m ruff check tests/test_regras_dfc.py tests/test_regras_bf.py` — limpo

## 5. Arquivamento
- [x] 5.1 `tasks.md` 100% marcado
- [x] 5.2 Mesclar o delta em `openspec/specs/dca/demonstracao-fluxos-caixa/spec.md`
- [x] 5.3 Mover para `openspec/changes/archive/2026-10-26-ipc08-dfc-regras-canonicas/`
- [x] 5.4 Atualizar a tabela "Change ativa" em `openspec/AGENTS.md`
