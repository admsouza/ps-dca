# Tasks — Apuração da DFC (F1)

**Repo:** `ps-dca` · **Não implementar sem aprovação explícita do PO.**
Fatia vertical: `python -m app.cli.dfc 4314902 2025` imprimindo as 84 linhas, com `L34` fechando
a variação de caixa da MSC.

Nenhuma fase começa antes do gate da anterior.

## 0. Fundação
- [x] 0.1 `ipc08-dfc-regras-canonicas` arquivada em 2026-10-26: 84 regras validadas, índice
      gerado, `fonte_de("DFC")` já testado em `tests/msc/test_fonte_por_demonstrativo.py:32`
- [x] 0.2 Gaps levantados **no código**, não supostos (medição de 2026-10-26, Porto Alegre 2025,
      24.214 registros): 8 agregadoras saem `não apurada` por referência a linha sem `columns`;
      `L35` lê N em vez de N−1; `L9` sai 0,00. O motor **já** aplica os filtros de
      natureza/função/subfunção (`L14` = 115.727.775,84 com os quatro filtros)
- [x] 0.3 Verificado que **não** há gap de plataforma: carregador genérico por diretório
      (`carregador.py:50`, `demonstrativo="dfc"`), `ordem_topologica` exportada
      (`app/domain/bo/matriz.py`), `_totalizar` do DVP como precedente de D2
- [ ] 0.4 Medir a causa de `L9` = 0,00 (D5) — isolar o `not_in` de `1.3.21.00.1.x` /
      `7.3.21.00.31.x` e dizer se come a receita inteira por prefixo. Resultado em
      `docs/evidencia-dfc-apuracao-f1.md`
- [ ] 0.5 Medir quanto falta a `L34` para fechar 68.947.215,92 com `L16`/`L21`/`L30` em zero —
      é o tamanho do campo informado, e decide se o mapa de `L11` precisa voltar ao PO
- [ ] 0.6 PO aprova a proposal

## 1. TEST (antes do código)
- [ ] 1.1 `tests/dfc/test_apuracao_dfc.py::test_nenhuma_linha_sem_coluna_em_comum` — as 84 linhas
      apuram; falha hoje com `não apurada` em 8 delas
- [ ] 1.2 `test_identidades_do_demonstrativo` — `L2 = L3+…+L11`, `L12 = L13+…+L16`, `L1 = L2−L12`,
      `L17`, `L26`, `L34 = L1+L17+L26`, `L36 = L34+L35`, nas duas colunas, com fonte fake
- [ ] 1.3 `test_amarracao_entre_quadros` — `P.L10 = T.L7`, `P.L13 = F.L29`, `P.L14 = J.L4`,
      `P.L15 = T.L15`
- [ ] 1.4 `test_l35_le_o_exercicio_anterior` (D3) — `L35` = `1.1.1` de N−1 e `L36` = `1.1.1` de N;
      falha hoje com o caixa final nas duas
- [ ] 1.5 `test_linha_sem_conta_nao_contamina_total` (D2) — `L16` não informada vale `0,00` na
      soma de `L12` e aparece como informável no diagnóstico, nunca `None`
- [ ] 1.6 `tests/dfc/test_informados_dfc.py` — whitelist `{L16, L21, L30}`: código fora dela e
      valor não-decimal recusados antes de apurar, como em `bf/informados.py`
- [ ] 1.7 `test_sem_dados` — fonte vazia dá coluna não apurada e `sem_dados`, nunca zeros
- [ ] 1.8 Regressão: BO, BF, BP e DVP inalterados
- [ ] 1.9 Rodar e conferir que cada teste falha **pelo motivo esperado**; registrar aqui os que
      passarem antes da implementação (não servem de gate)

## 2. IMPLEMENT
- [ ] 2.1 `app/services/dfc/informados.py` — `CODIGOS_SEM_MAPEAMENTO = {"L16","L21","L30"}`,
      `validar_valores_informados`, reusando `decimal_informado` de `bf/informados.py`
- [ ] 2.2 `app/services/dfc/quadro_principal.py` — `apurar()`, duas colunas, `Procedencia` e
      `Diagnostico` no contrato de DVP/BP
- [ ] 2.3 D2: folhas pelo motor, informadas injetadas, agregadoras por `ordem_topologica`
- [ ] 2.4 D3: `L35` da MSC de N−1 via `registros_por_regra`
- [ ] 2.5 `app/cli/dfc.py` — espelho de `app/cli/dvp.py`, com os quatro quadros
- [ ] 2.6 D6: `services/dfc` em `_CODIGO_DA_APURACAO` (`apuracao.py:25`)
- [ ] 2.7 Migration: n/a

## 3. REVIEW
- [ ] 3.1 `git diff` — nada em `app/domain/`, nada em `knowledge/`, nada no `registry.py`
- [ ] 3.2 Nenhuma regra YAML alterada; `validate_rules` e `check_sources` intactos

## 4. VERIFY
- [ ] 4.1 `python -m app.cli.dfc 4314902 2025` contra o SICONFI: 84 linhas, zero células não
      apuradas por "coluna em comum"
- [ ] 4.2 **`L34` = 68.947.215,92** (variação de `1.1.1` entre as MSC de 2025 e 2024), com o
      valor de `L16` que o fechamento exigir — registrar qual foi
- [ ] 4.3 `L35` = 2.785.855.199,20 e `L36` = 2.854.802.415,12; conferem com `L29`/`L62` do BF do
      mesmo ente (`auditoria-bf-2025.md:65,109`)
- [ ] 4.4 Regressão dos valores já medidos: `L14` = 115.727.775,84, `L32` = 4.278.384,37
- [ ] 4.5 Segundo ente (Recife `2611606` ou João Pessoa `2507507`) com a identidade de caixa
      fechando — uma medição só não basta
- [ ] 4.6 `python -m pytest` verde; base atual a registrar aqui
- [ ] 4.7 `python -m ruff check .` limpo
- [ ] 4.8 BO, BF, BP e DVP sem diferença de valor
- [ ] 4.9 Evidência da rodada em `docs/evidencia-dfc-apuracao-f1.md`, no padrão das do BF

## 5. Arquivamento
- [ ] 5.1 `tasks.md` 100% marcado
- [ ] 5.2 Mesclar o delta em `openspec/specs/dca/demonstracao-fluxos-caixa/spec.md`
- [ ] 5.3 `CENARIOS_ESPERADOS["dca/demonstracao-fluxos-caixa"]`: 13 → 13 + os desta change
- [ ] 5.4 Mover para `openspec/changes/archive/AAAA-MM-DD-dfc-apuracao-f1/`
- [ ] 5.5 Atualizar `openspec/AGENTS.md` e abrir `dfc-no-pipeline`
