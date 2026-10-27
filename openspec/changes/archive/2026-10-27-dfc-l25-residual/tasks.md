# Tasks — `L25` residual

**Repo:** `ps-dca` · Medido contra Cuitegi/PB 2025, consolidado.

## 0. SPEC
- [x] 0.1 Achado A1 da auditoria de Cuitegi, com valor: 1.791.501,94 contado duas vezes
- [x] 0.2 Conferido que a transcrição é fiel ao PDF — a dupla contagem é do IPC 08
- [x] 0.3 PO aprovou abrir em 2026-10-27

## 1. TEST
- [x] 1.1 `test_aquisicao_de_ativo_nao_entra_duas_vezes` — elemento 52, modalidade 90
- [x] 1.2 `test_o_que_l23_exclui_continua_em_l25` — registro recusado pelo `not_in` de `L23`
- [x] 1.3 `test_conferencia_viva` — Cuitegi: `L25` = 0,00 e `L22` = 1.791.501,94
- [x] 1.4 Rodados e falhando pelo motivo esperado

## 2. IMPLEMENT
- [x] 2.1 `app/services/dfc/quadro_principal.py`: `L25` recebe, por `registros_por_regra`, o
      conjunto menos os registros que atendem a `L23` ou `L24`
- [x] 2.2 Nenhum YAML alterado

## 3. REVIEW
- [x] 3.1 `git diff`: só o serviço e os testes
- [x] 3.2 `L23` e `L24` inalterados

## 4. VERIFY
- [x] 4.1 Cuitegi: `L23`, `L25`, `L22` e `L17` conferem em centavos com o publicado
      (1.791.501,94 · 0,00 · 1.791.501,94 · −1.791.501,94)
- [x] 4.2 Quatro entes medidos. `L25` cai em todos; **o resíduo negativo de João Pessoa encolhe
      de −657.093.004,03 para −217.997.300,88** — dois terços daquele defeito eram esta dupla
      contagem. Nos demais o resíduo sobe o valor de `L23`, como esperado
- [x] 4.3 Suíte verde; `ruff` limpo

## 5. Arquivamento
- [x] 5.1 `tasks.md` 100%
- [x] 5.2 Delta mesclado; `CENARIOS_ESPERADOS` 26 → 28
- [x] 5.3 Movida para `archive/`; `AGENTS.md` atualizado
