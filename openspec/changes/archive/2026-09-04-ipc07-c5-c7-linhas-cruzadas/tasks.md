# Tasks — C5 e C7

## 0. SPEC

- [x] 0.1 `proposal.md` com a evidência das duas pendências, exemplos reais em JP (superavitário) e
      SP/GO (deficitários), critérios de aceite medíveis e riscos.
- [x] 0.2 Delta de `dca/base-canonica-regras`: 3 requisitos MODIFIED, 2 cenários novos (49 → 51).
- [x] 0.3 Delta de `dca/balanco-orcamentario` (change ativa): requisito condicional ganha a regra
      de agregação; `exercício superavitário` alterado e `exercício deficitário` novo (33 → 34).
- [x] 0.4 **Achado que mudou o escopo:** em ente deficitário o STN deixa `Superavit` em branco e
      **publica** `TotalDespesasComSuperavit` igual a `TotalDespesas`. Exige que a célula suprimida
      contribua zero, e que a condição rode antes da agregação — o motor faz o contrário nos dois
      pontos. Estimativa revisada de 2–3× para 4–5× o diff da change anterior.
- [x] 0.5 **A C7 restringe a decisão B6**, que consta na lista de "não reabrir" do
      `PONTO-DE-PARADA.md`. Aprovada pelo PO em 2026-09-04 junto com o encaminhamento de C5/C7.

## 1. PLAN/ARCH

- [x] 1.1 `design.md` com o fluxo antes/depois e as decisões D1–D4.
- [x] 1.2 Confirmado que `app/domain/bo/matriz.py` **muda** — primeira change da série a mexer no
      motor.
- [x] 1.3 Confirmado que `versao_regras` muda e que não há cache a invalidar.

## 2. TEST — antes do código

- [x] 2.1 `tests/bo/test_linhas_cruzadas.py` — 10 testes.
- [x] 2.2 `test_l27_ignora_a_parcela_ausente_de_l29`.
- [x] 2.3 `test_total_com_deficit_tem_valor_com_a_parcela_suprimida` e `..._iguala_l48_...`.
- [x] 2.4 Coberto nos testes de branco, nas duas metades.
- [x] 2.5 `test_referencia_nomeia_coluna_ausente_e_rejeitada` e o par positivo. **Exigiu
      resolução transitiva de colunas no validador:** `L24` e `L48` são compostas e herdam por
      interseção, então o check ingênuo acusava erro na base real.
- [x] 2.6 `test_l27_ignora_a_parcela_ausente_de_l29`.
- [x] 2.7 Dois passaram sem alteração. O terceiro
      (`test_recursos_arrecadados_em_exercicios_anteriores`) esperava **resíduo** de
      `9.9.9.0.00.0.0`, e a expectativa era stale: `L28` classifica essa natureza por filtro
      (decisão B6), então não é resíduo — resíduo é classificação que nenhuma linha captura. O
      teste passou a afirmar o medido: fora de `L16`/`L24`/`L26`, dentro de `L28`, resíduos
      vazios.
- [x] 2.8 51 e 34.
- [x] 2.9 Os 10 novos falharam pelo motivo esperado; 1 passava por vazio e foi reforçado.

## 3. IMPLEMENT

- [x] 3.1 Feito, e também `condition.column`. **Armadilha encontrada:** o campo foi criado como
      `on`, e YAML 1.1 interpreta `on:` como o booleano `True` — o schema pegou. Renomeado para
      `column`, com a nota no próprio schema.
- [x] 3.2 Feito, mais `Linha.condicao_coluna`.
- [x] 3.3 Feito, e a condição passou a ser decidida por linha — ver 5.6.
- [x] 3.4 Com `_colunas_efetivas`, que resolve a interseção transitivamente.
- [x] 3.5 Feito.
- [x] 3.6 Registrada, com C5 e a observação de `L30` em GO.

## 4. REVIEW

- [x] 4.1 Confere, mais `tests/test_validador.py`, que a task 2.5 exigiu.
- [x] 4.2 As 12 colunas das 4 linhas estão declaradas no YAML.
- [x] 4.3 `_aplicar_condicao` é o único produtor, e sempre registra.
- [x] 4.4 Confere.

## 5. VERIFY

- [x] 5.1 **153 passed / 0 failed.** Suíte verde pela primeira vez no repositório.
- [x] 5.2 `All checks passed!`
- [x] 5.3 exit 0 · 69 regras · `review_required` 0.
- [x] 5.4 Íntegro.
- [x] 5.5 **João Pessoa: 13 de 13 células OK em centavos**, `nao_apuradas` = 0 e `residuos` = 0.
      `L49` = 267.518.451,03 · 548.825.560,55 · 588.080.763,22; `L50` = 5.117.875.296,33 nas três
      de execução; `L25` em branco nos dois lados; `L27.previsao_inicial` = 12.000.000,00.
- [x] 5.6 **GO: tudo OK.** **SP achou um erro real na primeira rodada:** eu aplicava a condição
      célula a célula, e SP tem déficit contra a empenhada mas superávit contra liquidadas e pagas
      — o STN deixa `Superavit` em branco nas três. A condição é decidida **uma vez, por linha**,
      na coluna declarada em `calculation.condition.column`. Corrigido, as 4 divergências de SP
      fecharam. Restam 2 células, ambas `L27.previsao_inicial` de SP e GO, que **o STN não publica
      nesses entes** — a de GO é `L30` (963.024,00), linha que GO omite do anexo. Registrada como
      observação aberta, fora do escopo de C5/C7.
- [x] 5.7 **0 divergentes em 63 linhas** fora de escopo (63, não 65: `L27` e `L29` entram no escopo).
- [x] 5.8 Coberto por `test_cobertura_spec.py`, verde nas duas capabilities com 51 e 34.

## 6. Arquivamento

- [x] 6.1 Atualizado.
- [x] 6.2 Mesclado — 49 → 51 cenários.
- [x] 6.3 Movida.
- [x] 6.4 Atualizada.
- [x] 6.5 C5 e C7 encerradas nos dois lugares. A change do BO fica com o arquivamento (7.x)
      liberado — sem teste vermelho e sem pendência normativa.
