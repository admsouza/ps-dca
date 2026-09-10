# Tarefas — bo-template-no-resultado

## 0. SPEC
- [x] 0.1 `proposal.md` — por quê, decisões, impacto
- [x] 0.2 `specs/dca/balanco-orcamentario/spec.md` — delta com 2 Requirements e 8 cenários
- [x] 0.3 Aprovação do PO — 2026-09-10

## 1. TEST — antes do código
- [x] 1.1 `tests/bo/test_template.py` — os 8 cenários do delta, um teste cada
- [x] 1.2 Confirmado falhando pelo motivo esperado: 8 vermelhos, todos por `linhas` ausente do
      payload ou por `nivel`/`ordem` inexistentes no modelo

## 2. IMPLEMENT
- [x] 2.1 `app/domain/bo/modelo.py` — `Linha` ganha `nivel` e `ordem`, com default `0`. São
      metadados de apresentação **da norma**; não entram no cálculo
- [x] 2.2 `app/infra/regras/carregador.py` — lê `linha.nivel` e `linha.ordem` do YAML, que já
      estavam transcritos e eram descartados
- [x] 2.3 `app/infra/regras/vigencias.py` — `_achatar`/`_linha` transportam os dois campos;
      `_completar_apresentacao` preenche o que falta na vigência publicada antes desta change,
      pela transcrição versionada, com log. Tabela é INSERT-only: não havia como corrigir no lugar
- [x] 2.4 `app/services/bo/quadro_principal.py` — `Resultado` passa a carregar o `mapa`, que é
      quem tem o template
- [x] 2.5 `app/services/pipeline/resultado.py` — `template()` publica `linhas` na ordem da norma
      (`ORDEM_QUADROS`, `ORDEM_GRUPOS`), e `para_dados` a inclui

## 3. VERIFY
- [x] 3.1 `python -m pytest` — **232 passed**
- [x] 3.2 `python -m ruff check .` — limpo
- [x] 3.3 Contra a API real, no container: reapuração `done`, `GET /dca/BO` com as quatro seções,
      69 linhas em `linhas` e em `matriz` casando 1:1, quadros na ordem
      `QUADRO_PRINCIPAL` → `RP_NAO_PROCESSADOS` → `RP_PROCESSADOS`, grupos `RECEITAS` → `DESPESAS`
- [x] 3.4 Níveis normativos conferidos no payload: `L51` = 2, `L19` = 3, `L18` = 1 — os três casos
      em que a derivação por composição erraria
- [x] 3.5 `l48.dotacao_atualizada` segue `6043181131.90` — a mudança é aditiva e não tocou valor

## 4. Pendente
- [x] 4.1 Arquivada em 2026-09-10; os 2 Requirements e 8 cenários mesclados em
      `openspec/specs/dca/balanco-orcamentario/spec.md` (35 → 43 cenários)
- [ ] 4.2 Front consome `linhas` — `front-declaracoes`,
      `openspec/changes/dca-anexo01-bo-ui/` (spec atualizada nesta mesma sessão)
