# Tasks — Coluna do exercício anterior por unidade

**Repo:** `ps-dca` · **Não implementar sem aprovação explícita do PO.**
Fatia vertical: Cuitegi (`2505204`), BF e BP 2024 → 2025, PublicSoft por UG.
Ordem: depois de `pipeline-dca-por-unidade-gestora` e de `bf-por-unidade-gestora`.

## 0. Fundação
- [x] 0.1 Decisões do PO (2026-10-13): três origens; escolha por UG; padrão processado → msce; consolidado com processado; regra no pipeline; "não pelo SICONFI" = não pela DCA publicada; `po:` lê a MSC do SICONFI; processado aceita outra fonte; cache sem chave por fonte; manual do BP por unidade; UG nova com zero + aviso
- [x] 0.2 PO aprovou a proposal; design e tasks revisados depois do gate (2026-10-13)
- [ ] 0.3 `pipeline-dca-por-unidade-gestora` e `bf-por-unidade-gestora` arquivadas
- [ ] 0.4 Medir se o `ID_INSTITUICAO` de Cuitegi é estável em 2024 × 2025

## 1. TEST (antes do código)
- [x] 1.1 `tests/recorte/test_anterior_por_recorte.py`: padrão com/sem N−1; N−1 `processando`; origens mistas; escolha gravada reaplicada (também no percurso); `{"origem": "padrao"}` limpa; `processado` gravado sem N−1 cai em `msce` com motivo; escolha de unidade inexistente descartada da identidade; linha sem par; UG sem MSC N−1 (zero + aviso); unidade em processado não reapura N−1; `po:` em `msce` lê o SICONFI e nunca o publicado; N−1 de outra fonte com `anterior_processado.fonte`; estornos de N−1 em `anterior_processado`; Superávit pela união das fontes; `visoes` e `fonte_vazia` transpostos
- [x] 1.2 Aditividade (D4): o grupo somado é igual ao grupo filtrado em `msce`, no BF e no BP
- [x] 1.3 `tests/bp/test_anterior_manual.py`: folhas por prefixo; totalizadoras pela calculation; folha omitida não apurada; Superávit com fonte informada; `422` (prefixo, código, totalizadora, fonte, valor); manual no consolidado `422`
- [x] 1.4 `tests/pipeline/test_rota_anterior_por_recorte.py`: `422` (chave de grupo, origem inválida, manual sem valores); `409` processado explícito sem N−1; job em `erro` se N−1 sumir; consolidado com `processado` (corpo e percurso do BP); `/batch-jobs` recusa `anterior_por_recorte`
- [x] 1.5 `tests/pipeline/test_identidade_anterior_por_recorte.py`: `ar-<hash>` só com escolha explícita; GET depois do reprocessar sem `pedido` em `motivos_desatualizado`
- [x] 1.6 Regressão: consolidado bit a bit; unidades sem cache N−1 e sem escolha iguais às changes anteriores
- [x] 1.7 Rodar e confirmar que falham pelo motivo esperado

## 2. IMPLEMENT
- [x] 2.1 `OrigemAnterior` + `anterior.py` (resolver, transpor, somar grupo)
- [x] 2.2 BF: `Anterior.PROCESSADO`. BP: `Anterior.PROCESSADO` e `Anterior.MANUAL` + `bp/informados.py`
- [x] 2.3 `com_recortes`: origem por unidade; grupo pela soma
- [x] 2.4 `cache.py`: reconstrução das escolhas gravadas; `ar-<hash>`; `processado` no BP
- [x] 2.5 Rota e percurso: `anterior_por_recorte`, `409`, `processado` no consolidado
- [x] 2.6 Procedência por recorte

## 3. REVIEW
- [x] 3.1 `git diff` completo sem arquivo fora do escopo

## 4. VERIFY
- [x] 4.1 `python -m pytest` — `N passed / M failed`
- [x] 4.2 `python -m ruff check .`
- [ ] 4.3 Cuitegi: BF e BP 2025, anterior por UG = atual 2024 por UG, diferença 0,00 (`docs/entes-homologacao/cuitegi/`)
- [x] 4.4 Reconferência cenário a cenário

## 5. Arquivamento
- [ ] 5.1 Mesclar os deltas em `openspec/specs/` (`pipeline/anterior-por-recorte`, `pipeline/unidade-gestora`, `dca/balanco-patrimonial`)
- [ ] 5.2 Mover para `archive/` e atualizar `openspec/AGENTS.md`
