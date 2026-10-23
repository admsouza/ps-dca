# Tasks — DVP, Quadro Principal

**Repo:** `ps-dca` · **PO mandou abrir a change em 2026-10-23.**
Fatia vertical: João Pessoa (`2507507`) e Porto Alegre (`4314902`), exercícios 2025 e 2024, `DCA-Anexo I-HI`.

Nenhuma fase começa antes do gate da anterior. Pular gate é erro de processo.

## 0. SPEC

Gate: `proposal.md` e `specs/dca/demonstracao-variacoes-patrimoniais/spec.md` com requisitos, entradas, saídas, erros, exemplo medido e o motivo de a exclusão ficar fora do cálculo.

- [x] 0.1 Proposal com a tabela L6/L14 (João Pessoa 2025: 11.722.481.279,59 e 9.199.369.111,48 no `I-HI`; 3.151.851.371,43 e 628.739.203,32 com a lista do IPC 05)
- [x] 0.2 Delta spec com os cenários de João Pessoa, Porto Alegre, redutora e conta sintética
- [x] 0.3 PO mandou abrir a change em 2026-10-23

## 1. PLAN/ARCH

Gate: `design.md` com D1–D8, fluxo, contratos e a lista de arquivos. `tasks.md` com as fases seguintes.

- [x] 1.1 D1 exclusão fora do cálculo, com a medição
- [x] 1.2 D2 redutora na direção da coluna; D3 prefixo; D4 `MSCE`/abertura; D5 duas colunas; D6 um quadro; D7 L17; D8 contrato YAML de BO/BP/BF
- [x] 1.3 Lista de arquivos no design

## 2. TEST

Gate: cada cenário do delta vira teste. O teste roda e falha porque a DVP ainda não existe. Teste que passa antes da implementação não serve.

- [x] 2.1 Carregar 19 regras, ids únicos, zero `filters` e zero `exclusion_groups` — passou: o YAML já estava na base
- [x] 2.2 L1 = L2+…+L8, L9 = L10+…+L18, L19 = L1−L9 — passou no YAML
- [x] 2.3 João Pessoa 2025: L2 397.963.739,37, L6 11.722.481.279,59, L1 17.319.103.824,61, L9 17.046.926.343,10, L19 272.177.481,51 — `tests/dvp/test_conferencia_viva.py`
- [x] 2.4 Porto Alegre 2025: L1 53.603.764.288,49, L9 54.984.708.163,98, L19 −1.380.943.875,49 — mesmo arquivo
- [x] 2.5 Coluna anterior de 2025 igual ao `I-HI` de 2024 nos dois entes — mesmo arquivo
- [x] 2.5.1 Os três cenários acima vão à rede (`SiconfiMSC`/`SiconfiDCA`) e ficam fora da suíte
      padrão sob o marker `vivo` (`pyproject.toml`: `addopts = -q -m 'not vivo'`). Nenhum teste de
      `tests/bp` ou `tests/bf` chama o SICONFI: no BP a conferência contra ente real foi medição
      registrada em tasks (`bp-apuracao-f1` §4.4), não teste de suíte. Rodar com `pytest -m vivo`
- [x] 2.6 Redutora `411219700` reduz L2
- [x] 2.7 `442510000` entra em L5 pela direção do prefixo
- [x] 2.6.1 Docstrings dos testes com prefixo `Scenario:`/`Requisito:` — `tests/test_cobertura_spec.py::test_todo_teste_declara_o_que_cobre` acusava `test_regras.py::test_formulas_do_quadro`, `::test_prefixo_do_segundo_nivel_nas_duas_colunas` e `::test_validador_nao_acusa_regra_da_dvp`. Corrigido: 15 passed
- [x] 2.8 `python -m pytest tests/dvp` em 2026-10-23, depois de 2.5.1 e 2.6.1: **4 passed, 3 deselected, 4 errors**. A falha dos itens 2.3–2.7 é `ModuleNotFoundError: No module named 'app.services.dvp'` (`tests/dvp/conftest.py:21`). O serviço ainda não existe.
- [x] 2.9 Suíte inteira em 2026-10-23: **873 passed, 3 deselected, 4 errors** — os 4 erros são o mesmo `ModuleNotFoundError`. Nenhum outro teste vermelho. Esta é a linha de base do §5.1

## 3. IMPLEMENT

Gate: §2 falhou pelo motivo esperado. Código mínimo. YAML no contrato de `knowledge/schemas/rule.json`, legível como `knowledge/rules/bp/quadro_principal.yaml`.

- [x] 3.1 `knowledge/sources/ipc05/metadata.yaml` com sha256 medido do PDF
- [x] 3.2 `knowledge/policies/ipc05.yaml`: itens 15 e 16 declarados, texto de que a lista não é executada
- [x] 3.3 `knowledge/rules/dvp/quadro_principal.yaml`: 19 regras, sem `filters` e sem `exclusion_groups`
- [x] 3.4 `scripts/validate_rules.py` aceita IPC05 — **nada a fazer, medido em 2026-10-23**:
      `python -m scripts.validate_rules knowledge` imprime `DVP: quadro_principal 19` e não emite
      nenhum erro `dvp.*`. O enum `CAMPOS_POR_DOCUMENTO` (`scripts/validate_rules.py:29-32`) só
      rege campo de `filters`, e nenhuma regra da DVP tem `filters` (D1)
- [x] 3.5 Serviço `app/services/dvp/quadro_principal.py` no fluxo de BP/BF (2026-10-23)
- [x] 3.6 Direção por prefixo (D3) **sem tocar em `app/domain/bo/saldo.py`**: adaptador no próprio
      serviço, no formato de `_DirecaoDoBP` (`app/services/bp/quadro_principal.py:446-462`), com o
      `rstrip("0")` que `app/services/bp/publicado.py:40` já usa. Medido em 2026-10-23:
      `credora_prefixo("442510000")` é `None` e `credora_prefixo("44251")` é `True` — sem tirar os
      zeros, L5 de Porto Alegre sai não apurada

- [x] 3.8 Nada de pipeline aqui. Rota, registry, serializador, resumo, percurso e CLI estão na
      change `dvp-no-pipeline`; recorte por unidade gestora e origem do anterior, em
      `dvp-por-unidade-gestora`. Esta change entrega a apuração consolidada em `MSCE`

## 4. REVIEW

- [x] 4.1 `git diff` sem arquivo fora da lista do design — `app/services/dvp/`, `tests/dvp/`,
      `knowledge/` (fontes, policy, regras, índice), `pyproject.toml` (marker `vivo`) e
      `tests/test_regras_bf.py` (4 documentos). Nada de pipeline, rota ou CLI
- [x] 4.2 Sem `print`, segredo, `TODO` órfão ou exclusão reintroduzida
- [x] 4.2.1 Defeito de teste corrigido em 2026-10-23: `test_transferencia_intra_permanece_em_l6`
      usava `451110100`, que não existe no PCASP — `do_pcasp().credora` devolve `None` e o helper
      `saldo` (`tests/bo/conftest.py:132`) falhava **antes** de `apurar` rodar. Trocado pela folha
      real de `4.5.1`, `451120100` (COTA RECEBIDA, credora). O cenário do delta spec continua
      sendo o mesmo: conta de `4.5.1` entra em L6
- [x] 4.3 `git diff tests/`: `tests/test_regras_bf.py::test_dois_documentos_integros` passa de 3
      para 4 documentos — o IPC 05 é a quarta fonte. Mesmo movimento do BP (`bp-apuracao-f1` §3.2),
      que levou o teste de 2 para 3. Evidência: `python -m scripts.check_sources knowledge` →
      `✓ Fontes íntegras 4 documento(s)`, exit 0, com o sha256 do PDF conferido

## 5. VERIFY

- [x] 5.1 `python -m pytest` — **880 passed, 3 deselected, 0 failed** (2026-10-23). Linha de base
      antes da implementação: 873 passed, 3 deselected, 4 errors
- [x] 5.1.1 `python -m pytest -m vivo` — **3 passed** contra o SICONFI real (2026-10-23)
- [x] 5.2 `python -m ruff check .` — **6 achados, todos pré-existentes**
      (`app/infra/regras/vigencias.py` I001/E501, `tests/bo/test_template.py` I001,
      `tests/pipeline/test_autorizacao_por_ug.py` E501, `tests/pipeline/test_unidade_por_header.py`
      E501/F401). Nenhum novo
- [x] 5.3 `python -m scripts.validate_rules knowledge` — **exit 0, nenhum erro**. Os 4 erros do BF
      que `bp-apuracao-f1` §4.3 registrou como dívida foram corrigidos em
      `bf-l28-l61-contas-especificas` §2.3.1, não aqui
- [x] 5.4 Cada cenário do delta tem teste que o cita no docstring — os 9, inclusive
      "anexos já apurados permanecem iguais" (`tests/dvp/test_regressao_anexos.py`)
- [x] 5.5 BO, BP e BF sem diferença de valor — suíte inteira verde e o mapa de cada base isolado
      por diretório (`test_regressao_anexos.py`: BO 69/IPC07, BF 80/IPC06, BP 58/IPC04)
- [x] 5.6 Conferência viva: João Pessoa (`2507507`) e Porto Alegre (`4314902`), 2025 e a coluna
      anterior contra o `I-HI` de 2024, centavo a centavo — os três cenários de
      `tests/dvp/test_conferencia_viva.py` passaram contra a API do SICONFI em 2026-10-23

## 6. Arquivamento

Gate: §5 verde e o PO manda arquivar. Não arquivar no meio.

- [x] 6.1 `tasks.md` marcado
- [x] 6.2 Delta mesclado em `openspec/specs/dca/demonstracao-variacoes-patrimoniais/spec.md`
- [x] 6.2.1 `tests/test_cobertura_spec.py`: capability nova em `CENARIOS_ESPERADOS` (9) e em `COM_TESTES`
      (9 cenários deste delta) e em `COM_TESTES` — sem isso a contagem não é vigiada
- [x] 6.3 Pasta movida para `openspec/changes/archive/2026-10-23-dvp-quadro-principal/`
- [x] 6.4 Tabela de change ativa em `openspec/AGENTS.md` atualizada
