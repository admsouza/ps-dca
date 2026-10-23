# Tasks — DVP servida pelo pipeline

**Repo:** `ps-dca` · **Não implementar sem aprovação explícita do PO.**
Fatia vertical: `GET /dca/I-HI` de João Pessoa (`2507507`) 2025 devolvendo as 19 linhas, com o
mesmo JSON do CLI.

Nenhuma fase começa antes do gate da anterior.

## 0. Fundação
- [x] 0.1 `dvp-quadro-principal` arquivada em 2026-10-23, §5 verde
- [x] 0.2 Gaps levantados no código, não supostos (2026-10-23): `I-HI` com `servico=None`
      (`registry.py:46`); `ORDEM_POR_DOCUMENTO` sem `IPC05` (`resultado.py:33-37`); seis asserções
      fixando `["BO","BF","BP"]` (`test_pipeline_completo.py:121,408`,
      `test_notificacao_discord.py:145,228,247,252`)
- [x] 0.3 Verificado que **não** há gap de plataforma: rota genérica (`anexos.py:582,609`), cache
      genérico (`test_invalidacao.py:95` já usa `I-HI`), despacho por assinatura
      (`apuracao.py:478-490`), carregador com `demonstrativo="dvp"` devolvendo `Vigencia(IPC05, 2020-01)`
- [x] 0.4 PO aprovou a proposal em 2026-10-23

## 1. TEST (antes do código)
- [x] 1.1 `tests/pipeline/test_rota_dvp.py` (espelho de `test_rota_bf.py`): `GET /dca/I-HI` 200
      com 19 linhas, `POST /dca/i-hi/reprocessar` 202, `?recorte=` 422
- [x] 1.2 Ordem de apresentação do IPC 05, com linha sintética de `VPD` com `ordem` relativa ao
      grupo — falhava com `assert 8 < 1` antes da implementação
- [x] 1.3 `GET /dca/resumo` com `I-HI` `implementado: true` — falhava com `implementado False`
- [x] 1.4 Percurso completo e notificação com os quatro anexos — falhava com `['BO','BF','BP']`
- [x] 1.5 `tests/pipeline/test_dvp_no_pipeline.py` (espelho de `test_bf_no_pipeline.py`): JSON da
      rota igual ao de `app.cli.dvp` (`ModuleNotFoundError` antes) e apurador usando o serviço do
      registry (`NotImplementedError: anexo I-HI ainda não tem serviço`); mais o mapa de `I-HI`
      vindo do IPC 05 (`IPC07 == IPC05` antes — o defeito silencioso do BO)
- [x] 1.6 Regressão: ordem e template de BO, BF e BP inalterados
- [x] 1.7 Rodados e falhando pelo motivo esperado. Dois cenários **passavam** antes da
      implementação e não servem de gate, registrado aqui: `grafia não canônica` (o registry já
      canoniza em `registry.py:53`) e os três de `test_rota_dvp.py` (a rota é genérica por anexo e
      lê o cache sem consultar o serviço). A cobertura real de "anexo implementado" é a 1.5

## 2. IMPLEMENT
- [x] 2.1 `registry.py`: `Anexo("I-HI", "app.services.dvp.quadro_principal:apurar", base_canonica="dvp")`
- [x] 2.2 `resultado.py`: `ORDEM_POR_DOCUMENTO["IPC05"]`
- [x] 2.3 `app/cli/dvp.py`
- [x] 2.4 Asserções de percurso e notificação (D4). Foram **mais** que as seis previstas no design:
      7 testes de `test_pipeline_completo.py` (fakes de `_apurador_de`, totais de 3 para 4,
      sequência de notificação), 1 de `test_notificacao_discord.py` e o golden
      `tests/pipeline/golden/rota_recorte_sem_ug.json` (12 entradas de `I-HI`,
      `implementado` false → true). O golden é snapshot de regressão: a mudança é a intencional
- [x] 2.4.1 **Fora da lista do design:** `app/services/pipeline/apuracao.py` ganhou
      `services/dvp` em `_CODIGO_DA_APURACAO`. `VERSAO_API` é o hash do código de apuração
      (`tests/test_versao_do_codigo.py`); sem a linha, mudança no código da DVP não invalidaria
      cache já gravado. Uma linha, exigida por teste existente
- [x] 2.5 Migration: n/a

## 3. REVIEW
- [x] 3.1 `git diff` conferido: `registry.py`, `resultado.py`, `apuracao.py` (2.4.1),
      `app/cli/dvp.py`, os dois testes novos e os ajustes de D4. Duas edições desnecessárias em
      `test_notificacao_discord.py` (cenários de formatação com dados sintéticos, que passavam sem
      alteração) foram revertidas na revisão — ficou só a asserção do percurso enfileirado
- [x] 3.2 Nenhuma alteração de apuração: `app/services/dvp/quadro_principal.py` intacto

## 4. VERIFY
- [x] 4.1 `python -m pytest` — **893 passed, 3 deselected, 0 failed** (2026-10-23). Base: 882
- [x] 4.2 `python -m ruff check .` — 6 achados, todos pré-existentes
- [x] 4.3 `GET /dca/I-HI` contra a app com portas fakes (`tests/pipeline/test_rota_dvp.py`)
- [x] 4.4 Rota e CLI publicam o mesmo JSON (teste de contrato, `test_dvp_no_pipeline.py`).
      `python -m app.cli.dvp 2507507 2025` contra o SICONFI em 2026-10-23: exit 0, 19 linhas,
      L1 17.319.103.824,61 (2025) e 16.327.833.858,41 (2024), 0 células não apuradas.
      Em redirecionamento de saída no Windows é preciso `PYTHONUTF8=1` — vale para o CLI do BF
      também, é pré-existente
- [x] 4.5 BO, BF e BP sem diferença de valor — suíte inteira verde

## 5. Arquivamento
- [x] 5.1 `tasks.md` marcado
- [x] 5.2 Delta mesclado em `openspec/specs/pipeline/plataforma/spec.md`
- [x] 5.2.1 `CENARIOS_ESPERADOS["pipeline/plataforma"]`: 89 → 95 (+6 desta change), com o
      comentário da origem, como as changes anteriores fizeram
- [x] 5.3 Pasta movida para `openspec/changes/archive/2026-10-23-dvp-no-pipeline/`
- [x] 5.4 Tabela de change ativa em `openspec/AGENTS.md` atualizada
