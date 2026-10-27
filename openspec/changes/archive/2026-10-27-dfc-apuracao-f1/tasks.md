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
- [x] 0.4 Causa de `L9` = 0,00 medida (D5): **não é o `not_in`** — é o `in`. O padrão
      `1321001x` transcrito do IPC 08 não casa com a natureza que a MSC entrega
      (`13210101`, `13210401`), que existe e soma 776 mi em Porto Alegre. O IPC de 2020 usa o
      layout de natureza de 2019. Correção pertence a nova change da base canônica
- [x] 0.5 Resíduo medido: `L34` sem os Outros = 1.045.831.543,34 contra 68.947.215,92 reais.
      `L16` = **976.884.327,42** fecha exatamente (7,4% dos ingressos) — valor plausível para
      "outros desembolsos operacionais"; `L11` não precisa voltar ao PO
- [x] 0.6 PO aprovou em 2026-10-27 ("vamos concluir o backend do DFC")

## 1. TEST (antes do código)
- [x] 1.1 `tests/dfc/test_apuracao_dfc.py::test_nenhuma_linha_sem_coluna_em_comum` — as 84 linhas
      apuram; falha hoje com `não apurada` em 8 delas
- [x] 1.2 `test_identidades_do_demonstrativo` — `L2 = L3+…+L11`, `L12 = L13+…+L16`, `L1 = L2−L12`,
      `L17`, `L26`, `L34 = L1+L17+L26`, `L36 = L34+L35`, nas duas colunas, com fonte fake
- [x] 1.3 `test_amarracao_entre_quadros` — `P.L10 = T.L7`, `P.L13 = F.L29`, `P.L14 = J.L4`,
      `P.L15 = T.L15`
- [x] 1.4 `test_l35_le_o_exercicio_anterior` (D3) — `L35` = `1.1.1` de N−1 e `L36` = `1.1.1` de N;
      falha hoje com o caixa final nas duas
- [x] 1.5 `test_linha_sem_conta_nao_contamina_total` (D2) — `L16` não informada vale `0,00` na
      soma de `L12` e aparece como informável no diagnóstico, nunca `None`
- [x] 1.6 `tests/dfc/test_informados_dfc.py` — whitelist `{L16, L21, L30}`: código fora dela e
      valor não-decimal recusados antes de apurar, como em `bf/informados.py`
- [x] 1.7 `test_sem_dados` — fonte vazia dá coluna não apurada e `sem_dados`, nunca zeros
- [x] 1.8 Regressão: BO, BF, BP e DVP inalterados
- [x] 1.9 Rodados: todos falharam com `ModuleNotFoundError: app.services.dfc` — motivo esperado

## 2. IMPLEMENT
- [x] 2.1 `app/services/dfc/informados.py` — `CODIGOS_SEM_MAPEAMENTO = {"L16","L21","L30"}`,
      `validar_valores_informados`, reusando `decimal_informado` de `bf/informados.py`
- [x] 2.2 `app/services/dfc/quadro_principal.py` — `apurar()`, duas colunas, `Procedencia` e
      `Diagnostico` no contrato de DVP/BP
- [x] 2.3 D2: folhas pelo motor, informadas injetadas, agregadoras por `ordem_topologica`
- [x] 2.4 D3: `L35` da MSC de N−1 via `registros_por_regra`
- [x] 2.5 `app/cli/dfc.py` — espelho de `app/cli/dvp.py`, com os quatro quadros
- [x] 2.6 D6: `services/dfc` em `_CODIGO_DA_APURACAO` (`apuracao.py:25`)
- [x] 2.7 Migration: n/a
- [x] 2.8 **Fora da lista do design:** `resultado.py` ganhou `ORDEM_POR_DOCUMENTO["IPC08"]`.
      Sem ela o `template` intercala os quatro quadros na saída (medido no CLI). É apresentação,
      estava previsto para `dfc-no-pipeline`, mas o CLI desta change já precisa

## 3. REVIEW
- [x] 3.1 `git diff` — nada em `app/domain/`, nada em `knowledge/`, nada no `registry.py`
- [x] 3.2 Nenhuma regra YAML alterada; `validate_rules` e `check_sources` intactos

## 4. VERIFY
- [x] 4.1 `python -m app.cli.dfc 4314902 2025` contra o SICONFI: 84 linhas, **0 células não
      apuradas**
- [x] 4.2 **`L34` = 68.947.215,92** com `L16` = **976.884.327,42** (7,43% dos ingressos)
- [x] 4.3 `L35` = 2.785.855.199,20 e `L36` = 2.854.802.415,12; conferem com `L29`/`L62` do BF do
      mesmo ente (`auditoria-bf-2025.md:65,109`)
- [x] 4.4 Regressão dos valores já medidos: `L14` = 115.727.775,84, `L32` = 4.278.384,37
- [x] 4.5 Quatro entes medidos. `L34`/`L36` fecham em todos; **o resíduo de `L16` é negativo
      em João Pessoa** (−657 mi), o que denuncia ingresso que o mapa não alcança. Registrado em
      `docs/evidencia-dfc-apuracao-f1.md` — vira change de base canônica, não se corrige aqui
- [x] 4.6 `python -m pytest` — **961 passed, 7 deselected, 0 failed**. Base: 945
- [x] 4.7 `python -m ruff check .` limpo
- [x] 4.8 BO, BF, BP e DVP sem diferença de valor
- [x] 4.9 Evidência da rodada em `docs/evidencia-dfc-apuracao-f1.md`, no padrão das do BF

## 5. Arquivamento
- [x] 5.1 `tasks.md` 100% marcado
- [x] 5.2 Mesclar o delta em `openspec/specs/dca/demonstracao-fluxos-caixa/spec.md`
- [x] 5.3 `CENARIOS_ESPERADOS["dca/demonstracao-fluxos-caixa"]`: 13 → 24 (+11)
- [x] 5.4 Mover para `openspec/changes/archive/2026-10-27-dfc-apuracao-f1/`
- [x] 5.5 `openspec/AGENTS.md` atualizado; `dfc-no-pipeline` aberta e concluída no mesmo dia
