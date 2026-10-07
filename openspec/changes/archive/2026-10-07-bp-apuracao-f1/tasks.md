# Tasks — Apuração do Balanço Patrimonial (F1)

**Repo:** `ps-dca` · **Não implementar sem aprovação explícita do PO.**
Fatia vertical: Cuitegi/PB (`2505204`) e João Pessoa/PB (`2507507`), exercício 2025, BP apurado ponta
a ponta pelo CLI e pelo pipeline.

## 0. Fundação
- [x] 0.1 Base canônica do IPC 04 transcrita: 58 regras em `knowledge/rules/bp/`, 21 `review_required`
      no total do repositório (15 do BP)
- [x] 0.2 `fonte_de("BP")` = `MSCE`/encerramento, coberto em `tests/msc/test_fonte_por_demonstrativo.py`
- [x] 0.3 PO aprova a proposal e decide P1–P6 — 2026-10-07, todas as recomendadas
- [x] 0.4 **Medir P4:** `financeiro_permanente` presente na `MSCE`/encerramento do SICONFI e da
      PublicSoft (Cuitegi e JP 2025), classes 1, 2 e 6 — registrar em `docs/evidencia-bp-fp-2025.md`
  - [x] SICONFI (2026-10-07): atributo presente; `L2`, `L3` e `L6` do quadro F/P conferem em
        centavos com Cuitegi 2025 e 2024; `L5` confere em 2024 e diverge 387.532,93 em 2025 (P7)
  - [x] PublicSoft (2026-10-07): Cuitegi 2025 idêntico ao SICONFI; 2024 responde 409 (auditoria
        da matriz não executada pelo ente)
- [x] 0.4b P3 medido: `2.3.2` tem saldo 0,00 em Cuitegi e JP, 2024 e 2025
- [x] 0.4c PO decide P7: opção (a), 2026-10-07
- [x] 0.5 `tt/dca` `I-AB` de JP 2025 baixado; de-para fixo de 11 âncoras em `docs/depara-bp-iab-ipc04.md`
- [x] 0.6 Publicado de Cuitegi transcrito direto no relatório de auditoria
      (`docs/entes-homologacao/cuitegi/auditoria-bp-2025.md`), sem arquivo de gabarito à parte. A
      inconsistência de `L24` anterior ficou resolvida pela MSC: 114.975.024,96

## 1. TEST (antes do código)
- [x] 1.1 `tests/test_regras_bp.py`: validador aceita IPC 04, índice com as 58 regras, termos
      qualificados, P2, P3 e o atributo recusado fora do IPC 04
- [x] 1.2 Cenários do delta spec em `tests/bp/test_apuracao.py` (17) e
      `tests/pipeline/test_bp_no_pipeline.py` (4)
- [x] 1.3 Regressão: shape da vigência do BO inalterado (`test_bo_publica_o_mesmo_shape_de_antes`)
- [x] 1.4 Rodados e **falhando pelo motivo esperado**: módulo `app.services.bp` inexistente, campos
      ausentes, BP fora do registry. O teste de ordem passava por coincidência (o template
      intercalava os quadros) e foi endurecido antes da implementação

## 2. IMPLEMENT
- [x] 2.1 `IPC04` no schema (`conta.financeiro_permanente`: `F`/`P`) e no validador (campos por
      documento, atributo só no IPC 04, bloqueio declarado aceito); índice regenerado (+58, BO/BF
      intactos)
- [x] 2.2 `Registro.financeiro_permanente` + normalização das duas fontes (`1`→F, `2`→P, outro→vazio)
- [x] 2.3 Atributo por termo de conta (`ContaCC.financeiro_permanente`, D2), e não filtro de linha:
      `L5` mistura `2.1`/`2.2` F com classe 6 sem atributo. Resíduo F/P no diagnóstico
- [x] 2.4 YAML: termos qualificados em `ativos_passivos_financeiros` L2/L3/L5/L6 (`extracted`); `L4`
      com `11382` (P2-a); `L34` segue `review_required` (P3-b)
- [x] 2.5 `fonte_de("BP").classes = (1, 2, 6)` (D3)
- [x] 2.6 `app/services/bp/quadro_principal.py`: duas colunas, equilíbrio, bloqueio como parcela
      inexistente (D2b), direção da coluna (D2c), conta **mista** do PCASP (`2.3.4`/`2.3.7`,
      `Credora/Devedora`) pela direção da classe. Medido: sem isso, `L39` e o PL inteiro saíam não
      apurados em todo ente
- [x] 2.7 `app/cli/bp.py`
- [x] 2.8 Registry (`BP`, P1-a), `apuracao.py` (`services/bp` na versão do código), `resultado.py`
      (ordem do IPC 04; `sem_atributo_fp` e `equilibrio` publicados), `vigencias.py` (ida e volta
      do atributo e do bloqueio; campos vazios fora do shape)
- [x] 2.9 Migration: n/a

## 3. REVIEW
- [x] 3.1 `git diff` completo: sem `print`, segredo nem `TODO` órfão. Credencial da PublicSoft usada
      só na medição, via variável de ambiente do comando, sem gravar em arquivo
- [x] 3.2 `git diff tests/`: testes novos; `test_fonte_por_demonstrativo` (classes do BP);
      `test_pipeline_completo` (o percurso passa a ter BO, BF **e** BP, exigido pela spec);
      `test_dois_documentos_integros` (3 documentos com o IPC 04 — falhava antes desta change)

## 4. VERIFY
- [x] 4.1 `python -m pytest` — **543 passed / 0 failed**. Linha de base: 516 passed / 1 failed
      (`test_dois_documentos_integros`, pré-existente e resolvida aqui)
- [x] 4.2 `python -m ruff check .` — 5 achados, todos pré-existentes no HEAD; nenhum novo
- [x] 4.3 `python -m scripts.validate_rules knowledge` — nenhum erro `bp.*`; restam 4 erros do BF
      (`L27`/`L28`/`L60`/`L61`), de changes ativas do BF
- [x] 4.4 `L1 = L15` **não fecha** nos entes reais: JP +5.946.040.575,02, Cuitegi −2.004.721,69. Causa
      medida: as exclusões intra-OFSS do IPC 04. **P8-a (PO, 2026-10-07):** exclusões mantidas,
      desequilíbrio declarado em `diagnostico.equilibrio`. Nos cenários sintéticos, fecha em 0,00
- [x] 4.5 Espelho `I-AB`: quadro F/P de JP **5/5 em centavos**; Quadro Principal diverge exatamente
      na parcela intra, conta a conta (`docs/depara-bp-iab-ipc04.md`)
- [x] 4.6 `docs/entes-homologacao/cuitegi/auditoria-bp-2025.md`, com toda divergência, hipótese e lado
- [x] 4.7 Regressão BO/BF: suíte verde e shape da vigência do BO inalterado. Mudança **aditiva** no
      payload: `diagnostico.equilibrio` passa a ser publicado também no BF (já era calculado e
      descartado na serialização)
- [x] 4.8 Reconferência da spec — cenário → cobertura:
      caixa de Cuitegi → `test_caixa_de_cuitegi_2025` · exclusão → `test_exclusao_declarada_na_linha` ·
      coluna anterior → `test_coluna_anterior_le_o_encerramento_do_exercicio_anterior` · balanço
      fecha/não fecha → `test_balanco_fecha`/`test_balanco_nao_fecha` (sintéticos; nos entes reais,
      4.4) · F/P pelo fato → `test_ativo_financeiro_pelo_atributo_do_fato` · termo sem qualificador
      → `test_termo_sem_qualificador_soma_todos_os_registros` · resíduo →
      `test_atributo_ausente_vira_residuo` · duas fontes → `test_as_duas_fontes_normalizam_para_o_mesmo_valor`
      · saldo patrimonial → `test_saldo_patrimonial_e_ativo_menos_passivo` + medição · fonte sem
      atributo → `test_fonte_sem_o_atributo` · compensação → `test_compensacao_fora_de_escopo` ·
      bloqueada → `test_linha_bloqueada_nao_zera_o_total` · âncoras de JP → **medição** (4.5) ·
      sem_cache → `test_bp_esta_no_conjunto_fechado_de_anexos` · leitura só pelo par →
      `test_coluna_anterior_le_o_encerramento_do_exercicio_anterior` + `test_balanco_patrimonial_e_a_unica_excecao`

## 5. Arquivamento
- [x] 5.1 `tasks.md` 100% marcado
- [x] 5.2 Delta mesclado em `openspec/specs/dca/balanco-patrimonial/spec.md` (16 cenários), com a
      capability em `CENARIOS_ESPERADOS`/`COM_TESTES` de `tests/test_cobertura_spec.py`. `fonte-msc`
      não muda: a spec não enumera classes
- [x] 5.3 Movido para `openspec/changes/archive/2026-10-07-bp-apuracao-f1/`
- [x] 5.4 Tabela "Change ativa" de `openspec/AGENTS.md` atualizada
