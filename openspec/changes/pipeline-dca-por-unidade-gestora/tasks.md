# Tasks — DCA processada com todas as unidades, emitida por recorte

**Repo:** `ps-dca` · **Não implementar sem aprovação explícita do PO.**
Fatia vertical: Cuitegi (`2505204`) 2025, BO e BP, unidades por UG (PublicSoft) e por PO (SICONFI).

## 0. Fundação
- [x] 0.1 Proposal aprovada pelo PO (2026-10-09)
- [x] 0.2 PO aprovou `design.md` e `tasks.md` (2026-10-09)
- [ ] 0.3 CH-46 (`regras-rgf-api`) em homologação; `poderes` conferido para um usuário de Cuitegi
- [ ] 0.4 Arquivar `bp-superavit-por-fonte` (mesmo serviço do BP)
- [ ] 0.5 Fixture: resposta real de `/base-demonstrativos/unidades-gestoras` de Cuitegi 2025/13 (classes do BO e do BP), sem token nem dado pessoal

## 1. TEST (antes do código)
- [x] 1.1 `tests/recorte/test_dominio.py`: `unidade()` UG × PO × PO vazio; grupos; `visiveis`/`padrao` pela tabela de poderes
- [x] 1.2 `tests/recorte/test_apuracao_recortes.py`: chaves geradas; a partição cobre todo registro uma vez; a fonte bruta é chamada o mesmo número de vezes que hoje; Déficit/Superávit por recorte; BP fora do consolidado com anterior MSCE e sem `conferencia_publicado`; consolidado bit a bit
- [x] 1.3 `tests/msc/test_publicsoft_ug.py`: endpoint por UG; `422` → base oficial com uma única tentativa por job; `409` → vazio; camelCase de UG
- [x] 1.4 `tests/pipeline/test_rota_recorte.py`: `recorte=ug:3` `200` sem `enqueue`; inexistente `404`; malformado `422`; BF `422`; cache antigo `409`
- [x] 1.5 `tests/pipeline/test_poderes.py`: padrão por poder; Executivo pedindo Câmara ou `consolidado` → `403` sem valor; judiciário `403`; hub fora `503`; PO vazio só para `consolidado`
- [x] 1.6 Rodar e **confirmar que cada teste falha** pelo motivo esperado — 2026-10-09: 27 falharam por funcionalidade ausente (campo, módulo ou rota); 2 de regressão (`409`, erro 500 da PublicSoft) passaram. Linha de base: 619 passed sem os testes novos

## 2. IMPLEMENT
- [x] 2.1 `Registro` + `normalizacao`: campos de UG
- [x] 2.2 `app/domain/recorte.py`
- [x] 2.3 `PublicSoftMSC`: D4
- [x] 2.4 `apuracao`: `_Observada`, `_Filtrada` e o laço dos recortes para BO e BP (D1, D2, D5)
- [x] 2.5 `resultado.para_dados`: `recortes`
- [x] 2.6 `hub.autorizar` → `poderes`; `request.state.poderes` (D7)
- [x] 2.7 `GET /dca/{BO|BP}`: `recorte`, padrão do poder, `recortesDisponiveis` (D6)

## 3. REVIEW
- [x] 3.1 `git diff` completo: sem arquivo fora do escopo, sem código morto, sem `print`/segredo/`TODO` órfão
- [x] 3.2 `git diff tests/`: testes novos + 5 ajustes justificados em testes existentes — dublê de `unidade_autorizada` passa a gravar `poderes` (fail closed sem eles: `test_bp_visao`, `test_notificacao_discord`, `test_visualizar_sem_reprocessar`, `test_percurso_origem_bp`); URL da base por UG em `test_cache_de_execucao` (ainda uma leitura por classe); fonte observada envolve a do escopo em `test_fonte_por_pedido`

## 4. VERIFY
- [x] 4.1 `python -m pytest` — 656 passed / 0 failed (2026-10-09; base 619 + 37 novos)
- [x] 4.2 `python -m ruff check .` — nenhum erro novo; restam 5 pré-existentes fora do escopo (`vigencias.py`, `test_template.py`, `test_unidade_por_header.py`). `validate_rules`: 4 erros pré-existentes, todos do BF (`l27`, `l28`, `l60`, `l61` — change bloqueada `bf-l28-l61-contas-especificas`); `knowledge/` intocado
- [ ] 4.3 (SICONFI ✔ bit a bit em BO e BP, 2026-10-09; PublicSoft pendente — exige `token_ps` em homologação) Cuitegi 2025, recorte `consolidado`, PublicSoft e SICONFI: BO e BP bit a bit iguais ao cache anterior
- [ ] 4.4 (por PO ✔ — Σ `L1` = 76.314.331,92, sem registro sem PO; por UG pendente) Cuitegi 2025: `L1`, `L15` e equilíbrio do BP e totais do BO por UG, por PO e por grupo; Σ das UGs no `L1` = consolidado; valor sem PO. Registrar em `docs/entes-homologacao/cuitegi/auditoria-recorte-2025.md`
- [ ] 4.5 (Cuitegi SICONFI: BO +2,0 s / 182 KB, BP +3,4 s / 296 KB; João Pessoa e PublicSoft pendentes) Tempo do job do BP e tamanho do `resultado` em Cuitegi e em João Pessoa (`2507507`) × hoje
- [x] 4.6 Reconferência da spec (2026-10-09):
  - ente com UG → `test_chaves_e_rotulos_do_bo`, `test_fonte_bruta_lida_uma_vez_por_classe`
  - ente sem UG → `test_ente_sem_ug_recorta_por_po`, `test_unidade_e_o_po_quando_nao_ha_ug`
  - grupo sem unidade → `test_grupo_sem_unidade_nao_e_apurado`
  - Déficit e Superávit por recorte → `test_deficit_e_superavit_por_recorte`
  - consolidado inalterado → `test_consolidado_bit_a_bit` (fonte fake); **medição real pendente (4.3)**
  - consolidado pelo publicado, UG pela MSC → `test_bp_fora_do_consolidado_usa_msce_do_ano_anterior`
  - uma UG / grupo de poder / inexistente / malformado / anexo sem recorte / cache anterior → `tests/pipeline/test_rota_recorte.py` (mesmos nomes); malformado também `test_chave_valida`
  - usuário do Legislativo / Executivo pede a Câmara / consolidado sem mudança → `test_rota_recorte.py`
  - registro sem PO → `test_visiveis_pelo_poder` (`ug:0` sem PO fora do Executivo) e `test_ente_sem_ug_recorta_por_po`
  - hub fora do ar → cobertura existente (`HubIndisponivel` → `503` em `unidade_autorizada`); `autorizar` só ganhou o retorno
  - fonte (BO delta): mesma matriz / gate 409 / camelCase / base por UG indisponível → testes existentes do BO + `tests/msc/test_publicsoft_ug.py`

## 5. Arquivamento
- [ ] 5.1 `tasks.md` 100% marcado
- [ ] 5.2 Mesclar deltas em `openspec/specs/` (`pipeline/unidade-gestora` nova; `dca/balanco-orcamentario` alterada)
- [ ] 5.3 Mover para `openspec/changes/archive/AAAA-MM-DD-pipeline-dca-por-unidade-gestora/`
- [ ] 5.4 Atualizar a tabela "Change ativa" em `openspec/AGENTS.md`
