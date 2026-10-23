# Tasks — DVP por unidade gestora

**Repo:** `ps-dca` · **Não implementar sem aprovação explícita do PO.**
Fatia vertical: ente de homologação com base por UG, DVP por `ug:` e por `po:`, exercícios 2025 e 2024.

## 0. Fundação
- [x] 0.1 `dvp-no-pipeline` arquivada em 2026-10-23, §4 verde
- [ ] 0.2 `pipeline-dca-por-unidade-gestora` e `pipeline-anterior-por-recorte` arquivadas —
      **ainda ativas em 2026-10-23**. O código desta change já está implementado e verde; o
      arquivamento dela espera as duas, porque o delta de `pipeline/unidade-gestora` só é
      mesclado quando a capability inteira fecha
- [x] 0.3 Manual por unidade e percurso por unidade **não são pergunta**: saem do comportamento de
      BP e BF (D3 e D4), verificado no código em 2026-10-23
- [x] 0.4 PO aprovou a proposal em 2026-10-23
- [x] 0.5 Verificado no código (2026-10-23): `RECORTAVEIS` (`apuracao.py:124`), `COM_UNIDADES`
      (`resumo.py:23`) e a introspecção `"anterior" in _aceitos_por(...)` que liga o modo por unidade

## 1. TEST (antes do código)
- [x] 1.1 Σ das 16 linhas-base das unidades = consolidado, em centavos
- [x] 1.2 `GET /dca/I-HI?recorte=ug:<id>` 200 sem enfileirar; visibilidade por poder (403)
- [x] 1.3 Origens por unidade: `processado`, `manual` e `padrao` aceitos; `msce` no pedido é 422
- [x] 1.4 Unidade sem MSC em N−1 → zero + `sem_dados_exercicio_anterior`
- [x] 1.5 Manual recusa L1, L9 e L19 pela estrutura, chave `L<n>` sem prefixo
- [x] 1.5.1 Percurso completo apura a DVP por unidade reaplicando a escolha gravada (D4)
- [x] 1.6 Consolidado bit a bit igual ao de `dvp-quadro-principal`
- [x] 1.7 Rodados e falhando pelo motivo esperado: 19 testes vermelhos — 14 com
      `TypeError: apurar() got an unexpected keyword argument` (`anterior_pronto`/
      `valores_anteriores`), 3 com `ModuleNotFoundError: app.services.dvp.informados`, 2 com
      `validar_escolhas` recusando `I-HI`; mais o de percurso, por `I-HI` fora de `RECORTAVEIS`.
      **Não serviram de gate:** os 5 casos de escolha inválida no `/reprocessar`, porque a rota já
      respondia 422 para anexo fora de BF/BP — o 422 muda de motivo com a implementação, e o teste
      não distingue a mensagem
- [x] 1.8 `tests/recorte/test_dvp_por_unidade.py` cobre os 14 cenários dos dois deltas; conferido
      cenário a cenário contra os docstrings em 2026-10-23

## 2. IMPLEMENT
- [x] 2.1 `"I-HI"` em `RECORTAVEIS` (`apuracao.py:124`)
- [x] 2.2 `"I-HI"` em `COM_UNIDADES` (`resumo.py:23`)
- [x] 2.3 `app/services/dvp/quadro_principal.py`: `Anterior` ganha `PROCESSADO` e `MANUAL`;
      `apurar` ganha `anterior_pronto`, `valores_anteriores` e `zero_sem_anterior`; `Procedencia`
      ganha `valores_anteriores`, `escolha_anterior` e `anterior_processado`; `_totalizar` e
      `_coluna_pronta` no molde do BP
- [x] 2.3.1 `anterior.validar_escolhas` aceita `I-HI` e `_validar_manual` despacha para a DVP
- [x] 2.3.2 `app/services/dvp/informados.py`: chave `L<n>` sem prefixo, totalizadora recusada por
      `linha.referencias`
- [x] 2.4 Migration: n/a

## 3. REVIEW
- [x] 3.1 `git diff` conferido: `apuracao.py` (1 linha), `resumo.py` (1 linha), `anterior.py`
      (3 linhas), `app/services/dvp/{quadro_principal,informados}.py`, os testes novos e dois
      ajustes esperados — `tests/recorte/test_apuracao_recortes.py` (o conjunto de recortáveis
      passa a ter quatro anexos) e o golden do resumo (`I-HI` ganha `"recortes": []`, como BF e BP)
- [x] 3.2 Nenhuma mudança no consolidado: `pytest -m vivo` continua verde com os mesmos valores

## 4. VERIFY
- [x] 4.1 `python -m pytest` — **916 passed, 3 deselected, 0 failed** (2026-10-23). Base: 893
- [x] 4.2 `python -m ruff check .` — 6 achados, todos pré-existentes
- [ ] 4.3 Ente de homologação: Σ das unidades = consolidado, diferença 0,00.
      **Feito por `po:`** em 2026-10-23, ente real, containers reconstruídos deste código: João
      Pessoa (`2507507`) 2025, `po:10131` + `po:10132` + `po:20231` = consolidado em L1, L9 e L19,
      diferença **0,00** (`docs/evidencia-dvp-pipeline-2026-10-23.md`).
      **Falta `ug:`** (base por unidade gestora da PublicSoft), que exige `token_ps`
- [x] 4.4 BO, BP e BF sem diferença de valor — suíte inteira verde
- [x] 4.5 `python -m pytest -m vivo` — 3 passed: a apuração consolidada da DVP não mudou de valor

## 5. Arquivamento
- [ ] 5.1 `tasks.md` marcado
- [ ] 5.2 Deltas mesclados em `openspec/specs/dca/demonstracao-variacoes-patrimoniais/spec.md` e
      `openspec/specs/pipeline/unidade-gestora/spec.md`
- [ ] 5.2.1 `CENARIOS_ESPERADOS`: `dca/demonstracao-variacoes-patrimoniais` +7 e
      `pipeline/unidade-gestora` +7, com o comentário da origem
- [ ] 5.3 Pasta movida para `openspec/changes/archive/AAAA-MM-DD-dvp-por-unidade-gestora/`
- [ ] 5.4 Tabela de change ativa em `openspec/AGENTS.md` atualizada
