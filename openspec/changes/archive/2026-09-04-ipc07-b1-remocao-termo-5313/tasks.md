# Tasks — remoção do termo `5.3.1.3.0.00.00`

## 0. SPEC

- [x] 0.1 `proposal.md` com why, escopo, exemplo real (JP 2025: R$ 67.299.876,72 e R$ 6.520,06),
      critérios de aceite medíveis, casos de erro e riscos.
- [x] 0.2 Delta spec com 1 requisito MODIFIED (3 cenários) e 1 REMOVED, com motivo e migração.
- [x] 0.3 Correção no delta **antes** de implementar: o cenário afirmava que registro de `5.3.1.3`
      não casado apareceria em `residuos`. **Falso** — `_residuos`
      (`app/services/bo/quadro_principal.py:90`) classifica por `natureza_receita` e
      `natureza_despesa`, nunca por conta contábil. O cenário passou a declarar o que de fato
      acontece: o registro é ignorado sem aviso.
- [x] 0.4 PO aprovou em 2026-09-04.

## 1. PLAN/ARCH

- [x] 1.1 `design.md` com fluxo, impacto e decisões D1–D4.
- [x] 1.2 Previsto que nenhum arquivo de `app/` mudaria — o motor já trata conta declarada sem
      escrituração como zero, e a direção da coluna vem da tabela. **A previsão estava certa para a
      apuração e errada para o resto:** a remoção deixou `natureza_saldo` sem declarante, e o campo
      virou código morto. Ver 4.2 e D3.
- [x] 1.3 Confirmado que `versao_regras` muda (regras mudaram) e que não há cache a invalidar,
      porque a F3 não entrou.

## 2. TEST — antes do código

- [x] 2.1 `tests/bo/test_saldo.py::test_conta_descontinuada_nao_apaga_a_celula` substituiu
      `test_excecao_historica_usa_a_natureza_declarada`.
- [x] 2.2 `test_coluna_a_do_rpnp_declara_tres_contas` — nas 6 folhas; `L1`, `L5` e `L9` agregam.
- [x] 2.3 `test_coluna_a_e_simetrica_nos_dois_quadros`.
- [x] 2.4 Fixture corrigida: `531*` como **devedoras**, `631600000` credora, conforme o PCASP.
- [x] 2.5 Os 3 falharam pelo motivo esperado. **Um deles falhou pelo motivo errado na primeira
      rodada** (`StopIteration`): o teste varria `l1..l9`, e `L1`/`L5`/`L9` são compostas e não
      declaram coluna. Corrigido antes de seguir — teste que falha pelo motivo errado não cumpre
      o gate.

## 3. IMPLEMENT

- [x] 3.1 Removida. Entrada única — as 9 linhas compartilham o anchor `&id001`.
- [x] 3.2 As 6 notas reescritas, e `decision: B1` removida das 6 folhas — sem conta ausente da
      tabela, a regra não invoca mais exceção histórica. O validador deixou de reportar
      `Exceção B1`.
- [x] 3.3 **D2 corrigida na execução:** o literal de 4 termos **não estava** em `evidence.text` —
      esse campo traz o rótulo da linha e a ND, não a fórmula da coluna. A única cópia era a
      própria conta declarada. A nota de proveniência passou a carregar o literal completo, e
      `test_conta_531_descontinuada_nao_e_declarada` afirma que ele está lá.
- [x] 3.4 Registrada. A de 2026-08-27 ficou marcada **SUPERADA**, não apagada.

## 4. REVIEW

- [x] 4.1 Três arquivos fora da lista original de `design.md`, todos consequência descoberta na
      execução e registrados abaixo: `tests/test_base_ipc07.py`, o delta spec da change ativa do
      BO, e `app/domain/` (D3 revertida).
- [x] 4.2 **Não se sustentou — D3 revertida.** `natureza_saldo` era meio-ligado: alimentava
      `_direcao_da_coluna`, mas a checagem por registro (`saldo.py:109`) rejeitava o registro de
      qualquer forma, então a célula saía `None` mesmo com a direção declarada. Nunca funcionou de
      ponta a ponta — era por isso que o teste de C6 estava vermelho. Sem declarante (0 regras,
      ausente do schema), virou código morto e saiu de `modelo.py`, `saldo.py` e `carregador.py`.
      Junto saiu `_direcao_da_conta`, **função nunca chamada** — código morto pré-existente que
      existia só para esse campo.
- [x] 4.3 Confirmado: só na nota de proveniência.
- [x] 4.4 Sim, na nota, com teste que o afirma.

## 5. VERIFY

- [x] 5.1 **138 passed / 3 failed.** As 3 são as de C5, pré-existentes. A de C6 deixou de existir.
      Nenhuma falha nova.
- [x] 5.2 `All checks passed!`
- [x] 5.3 exit 0 · 69 regras (51 · 9 · 9) · `review_required` 0 · `Exceção B1` não mais
      reportada (era 1 código / 6 linhas).
- [x] 5.4 Fontes íntegras — nenhuma tabela STN tocada.
- [x] 5.5 **Regressão bit a bit: 0 células divergentes em 69 linhas**, comparando o JSON do CLI
      antes e depois. `rp_nao_processados.l9` = 67.299.876,72 e `l2` = 6.520,06. As 11 células de
      referência não se moveram. `versao_regras` mudou de `c9466276…` para `95cd533c…` — correto,
      as regras mudaram; sem cache em produção, nada a invalidar.
- [x] 5.6 Cobertura dos cenários do delta:
      `coluna com contas de sinal negativo` → `test_coluna_com_contas_de_sinal_negativo` +
      `test_coluna_a_do_rpnp_declara_tres_contas`;
      `a fórmula fica simétrica à do quadro de RP Processados` →
      `test_coluna_a_e_simetrica_nos_dois_quadros` + `test_conta_531_descontinuada_nao_e_declarada`;
      `escrituração em conta descontinuada não apaga a célula` (delta do BO) →
      `test_conta_descontinuada_nao_apaga_a_celula`.
      `test_cobertura_spec.py` passa nas duas capabilities, **sem mudança de contagem** (49 e 33).

## 6. Arquivamento

- [x] 6.1 Atualizado.
- [x] 6.2 Mesclado. **A contagem NÃO mudou (49):** o delta original previa remover um cenário,
      mas o certo era **substituir** `conta 531 histórica é preservada` por
      `a fórmula fica simétrica à do quadro de RP Processados`. Mesmo raciocínio no delta do BO —
      `exceção histórica usa a natureza declarada` deu lugar a
      `escrituração em conta descontinuada não apaga a célula`, e a contagem segue 33.
      O delta também nomeava dois requisitos inexistentes; foi reescrito contra os nomes reais
      (`Regra por linha, com o mapa de colunas do quadro` e
      `Decisões do PO são aplicadas com escopo fechado e auditável`).
- [x] 6.3 Movida.
- [x] 6.4 Atualizada — a change saiu da tabela de ativas e entrou nas arquivadas.
- [x] 6.5 C6 encerrada nos dois lugares. O requisito do delta do BO deixou de citar
      `natureza_saldo` e passou a declarar o que de fato acontece: conta ausente da tabela torna a
      célula não apurada, com aviso.
