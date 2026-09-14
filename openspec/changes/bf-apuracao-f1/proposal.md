# Proposal — Apuração do Balanço Financeiro (F1)

**Status:** proposta
**Repositório:** `ps-dca`
**Capability:** `dca/balanco-financeiro` (**nova**)
**Anexo DCA:** nenhum — o BF **não** é publicado pelo `tt/dca` (medido, §1 da evidência).
Âncoras de conferência em `DCA-Anexo I-C`, `I-D` e `I-AB`
**Base normativa:** IPC 06, ed. 2024-06 — base canônica já entregue em `knowledge/rules/bf/`
(change `ipc06-bf-regras-canonicas`, arquivada em 2026-09-14)
**Fonte da verdade externa:** `regras-rreo-api` / `regras-rgf-api` (padrão de pipeline)
**Evidência medida:** `docs/evidencia-bf-jp-2025.md` (G1–G4) e `docs/evidencia-matriz-mscc-vs-msce.md`
(matriz consolidada × encerramento, piloto em Cuitegi/PB) — ambas de 2026-09-14

## Why

A base canônica do BF existe, mas nada a executa: hoje o repositório sabe *o que* cada uma das 80
linhas significa e não sabe *quanto* elas valem. É o mesmo ponto em que o BO estava em 2026-09-04,
e a F1 do BO resolveu com núcleo puro verificável sem Postgres, Redis ou container.

O IPC 06 introduz três coisas que o motor atual **não** resolve — e cada uma delas, se resolvida no
lugar errado, vira número errado sem erro:

1. **Fonte de recursos.** `Registro.fonte_recursos` existe e é normalizado pelas duas fontes MSC,
   mas o campo declarado na regra é `fonte_recurso` (singular): `saldo._campo` faria
   `getattr(registro, "fonte_recurso")` → `""` e **nenhuma linha casaria**, silenciosamente. Pior:
   a fonte escriturada traz o prefixo de exercício (`1500`), e `_casa` compara por prefixo —
   `"1500".startswith("500")` é falso. As 22 linhas por fonte sairiam zeradas, não com erro.
2. **Saldo em data.** O adapter SICONFI fixa `id_tv=ending_balance`. As linhas L30–L32 pedem saldo
   **inicial**, e hoje não há como pedi-lo.
3. **Sentido do movimento.** L27 e L60 declaram as mesmas contas e se separam por
   crédito × débito. Com `ending_balance` (saldo líquido acumulado) os dois sentidos são
   indistinguíveis.

## What Changes

- Capability nova `dca/balanco-financeiro`: apuração das 80 linhas dos 2 quadros do BF.
- Núcleo genérico: `app/domain/bo/` passa a `app/domain/nucleo/` (`MapaBO` → `Mapa`), com o BO
  e o BF usando o **mesmo** motor de matriz, saldo e filtros. Nenhuma regra e nenhum valor do BO
  muda — renomeação mecânica coberta pelos 287 testes atuais.
- `fonte_recurso` vira campo de filtro do motor, com normalização própria (G1).
- `FonteSaldos` passa a aceitar o tipo de valor (`id_tv`): saldo inicial, saldo final e variação
  do período (G2/G3).
- Carregador de regras parametrizado por demonstrativo (`bo` | `bf`), hoje fixo em `rules/bo`.
- `app/services/bf/quadro_principal.py` e `app/cli/bf.py`, espelhando os do BO.
- Resultado do BF publica matriz, template de apresentação, procedência e diagnóstico — o mesmo
  contrato que a plataforma já serializa para o BO.

- **Fonte passa a ser `MSCE`/abertura** (decisão G9 do PO). Alcança o BO já entregue, que hoje lê
  `MSCC`/encerramento — troca neutra em valor, medida nos dois entes, mas que exige change própria.
- **Competência é parâmetro, não constante.** A apuração passa a aceitar o mês, para atender à
  periodicidade **mensal além da anual** em todos os anexos (G10). Hoje `MES_DA_DCA = 12` está fixo
  no serviço do BO.

**Fora de escopo:** rota, job ARQ, cache, registry e SSE do BF (isso é `plataforma-pipeline-dca`,
igual às F2/F3 do BO); fechar F1/F2 do IPC 06 com o plano de contas do ente; quadro de
detalhamento por fonte criado livremente pelo ente.

## Entradas e saídas

| Interface | Entrada | Saída |
|---|---|---|
| `apurar(ente, exercicio, fonte, direcao=None, mapa=None)` | cod. IBGE, exercício, `FonteSaldos` | `Resultado` com `matriz`, `mapa`, `procedencia`, `diagnostico` |
| `python -m app.cli.bf <cod_ibge> <exercicio> [--fonte siconfi\|publicsoft] [--json]` | idem | matriz em texto ou JSON |
| `carregar(exercicio, demonstrativo="bf")` | exercício | `Mapa` com 80 linhas da edição 2024-06 |

## Exemplo concreto

**O `tt/dca` não publica o Balanço Financeiro** — medido em 2026-09-14: 2.002 registros, 7 anexos,
nenhum deles é o BF (`docs/evidencia-bf-jp-2025.md` §1). Não existe gabarito célula a célula, como
havia no `RREO-Anexo 01` para o BO. O aceite se apoia em três coisas, nesta ordem:

**a) Âncoras já medidas** — batem em centavos contra o publicado:

| Linha | Apurado | Publicado | Fonte |
|---|---|---|---|
| `L1` Receita Orçamentária | 5.117.875.296,33 | 5.117.875.296,33 | I-C (bruta − deduções) |
| `L25` Inscrição de RP Não Processados | 281.307.109,52 | 281.307.109,52 | I-D |
| `L26` Inscrição de RP Processados | 39.255.202,67 | 39.255.202,67 | I-D |
| `L34` Despesa Orçamentária | 4.850.356.845,30 | 4.850.356.845,30 | I-D (empenhadas) |

**b) Identidades internas** — `L1 = L2 + L3 + L11` e `L34 = L35 + L36 + L44` já fecham em 0,00, sem
resíduo de fonte; falta `L33 = L66`, hoje a −228.702.095,15.

**c) Conciliação de caixa** — ingressos menos dispêndios devem explicar a variação de caixa do
exercício: 2.613.640.800,87 → 3.248.364.442,41, ou seja +634.723.641,54.

## Critérios de aceite

- [ ] `L33 TOTAL (VI)` = `L66 TOTAL (XII)`, em centavos, no caso de referência — a identidade que
      define o demonstrativo. Hoje a diferença é **−228.702.095,15**, e fechá-la depende de G8.
- [ ] As 4 âncoras publicadas (`L1`, `L25`, `L26`, `L34`) seguem batendo em centavos.
- [ ] Ingressos menos dispêndios explicam a variação de caixa do exercício, em centavos.
- [ ] Divergência remanescente é registrada em `docs/validacao-bf-jp-2025.md`, nunca silenciada.
- [ ] As 22 linhas por fonte somam exatamente a linha-pai: `L2 + L3 + L11 = L1` e
      `L35 + L36 + L44 = L34`, sem resíduo de fonte não classificada.
- [ ] Nenhuma célula apurada como `0` por fonte que não casou — fonte não classificada aparece em
      `diagnostico.residuos`, não em zero silencioso.
- [ ] Regressão do BO **bit a bit**: os 11 valores de `docs/validacao-bo-jp-2025.md` inalterados, e
      a suíte inteira verde.
- [ ] A procedência declara tipo de matriz, tipo de saldo e competência apurada — qualquer que
      seja a decisão do PO em G9 e G10, o resultado diz sobre o que foi apurado.
- [ ] `python -m pytest` e `python -m ruff check .` sem falha nova.

## Casos de erro

| Situação | Comportamento esperado |
|---|---|
| Conta sem direção de saldo no PCASP | célula `None` + `NaoApurada`, nunca `0` (regra já vigente do BO) |
| Linha `review_required` (L22, L23, L28, L55, L56, L61) | célula `None`, com motivo citando o bloqueio F1/F2 — decidir G5: se contribui como parcela inexistente ao total |
| `MSCE` lida pelo **encerramento** | recusa explícita: nela as classes 3 e 4 não têm registro, e o BF sairia sem transferências financeiras. O par do BF é `MSCE`/abertura |
| Competência mensal sem dados na MSC | `sem_dados: true` para aquele mês, sem cair para dezembro por omissão |
| Fonte MSC sem dados para o exercício | `diagnostico.sem_dados: true`, matriz vazia, sem exceção |
| Exercício sem vigência do IPC 06 (< 2024) | `SemVigencia`, nomeando as edições disponíveis |
| `id_tv` pedido que a fonte não suporta | erro explícito da fonte, não `ending_balance` por omissão |

## Decisões pendentes do PO (gate desta proposta)

| # | Assunto | O que está em jogo | Opções |
|---|---|---|---|
| ~~**G1**~~ | Casamento da fonte de recursos | **Medido:** `fonte_recursos` tem sempre 4 dígitos; o detalhamento do ente vai em `complemento_fonte`, coluna separada | (a) descartar o 1º dígito e casar os 3 seguintes por igualdade — **confirmado**: `L1 = L2+L3+L11` fecha em 0,00 e o resíduo de fonte é **zero** |
| ~~**G2**~~ | Saldo do exercício anterior (L30–L32) | **Medido:** `beginning_balance` responde nas classes 1 e 2 | (a) `beginning_balance` do exercício apurado — **confirmado** |
| ~~**G3**~~ | Movimento credor/devedor (L27/L60) | **Medido:** em `2.1.8.8`, `period_change` traz C = 127.592.727,15 e D = 145.790.710,23; o acumulado traz só o líquido −18.197.983,08 | (a) `period_change` com C em L27 e D em L60 — **confirmado** |
| ~~**G4**~~ | Coluna "Exercício Anterior" | **Medido:** 2024 completo baixa junto com 2025 em ~45 s no total, 8 classes × 3 tipos de valor | (a) apurar — **confirmado**, latência não é obstáculo |
| **G5** | Efeito das 6 linhas bloqueadas nos totais | Se `L22` é `None`, `L21` é `None`, `L33` é `None` — e o BF inteiro não fecha | (a) linha bloqueada contribui como **parcela inexistente** (total soma as demais), com o bloqueio no diagnóstico **(recomendado)**; (b) propagar `None` até o total, e o BF só fecha quando F1/F2 forem decididos |
| **G6** | Renomear `app/domain/bo/` → `app/domain/nucleo/` | Evita duplicar 500 linhas de motor entre BO e BF | (a) renomear nesta change **(recomendado)**; (b) manter e importar `MapaBO` no BF; (c) duplicar o motor em `app/domain/bf/` |
| **G7** | Critério de direção do saldo no BF | **Medido:** com a direção da coluna (critério do BO), `L1` sai 5.872.854.713,27; com a direção **por conta**, sai 5.117.875.296,33 — exatamente o publicado. O par `6.2.1.2 (+) / 6.2.1.3 (−)` do IPC 06 já traz o sinal na regra | (a) direção por conta no BF, mantendo a direção de coluna no BO, escolhida pela regra **(recomendado)**; (b) direção por conta nos dois — exige remedir o BO inteiro |
| ~~**G9**~~ | Par (matriz, tipo de saldo) | **Decidido pelo PO em 2026-09-14:** todos os demonstrativos sobre a **matriz de encerramento (`MSCE`)**; tipo de saldo **abertura** no BO, BF, DVP e DFC, e **encerramento** no BP. Medido: `MSCC`/encerramento ≡ `MSCE`/abertura no BO, **0 divergências em 337 células** em Cuitegi **e** em João Pessoa | — |
| **G10** | **Periodicidade mensal além da anual, em todos os anexos** | Hoje `MES_DA_DCA = 12` é constante no serviço do BO, a chave de cache não tem mês e a decisão C1 do PO fixou dezembro. Mensal muda serviço, carregador, chave de cache, job e rota — e muda o significado do tipo de saldo: num mês qualquer, `ending_balance` é posição acumulada e `period_change` é o movimento do mês | (a) mês como parâmetro em toda a cadeia, com 12 como padrão **(a definir com o PO)**; (b) manter anual e tratar mensal em change própria |
| **G8** | Como apurar `L22` e `L55` sem conta de controle | **Medido:** as classes 7 e 8 do ente só têm controles de disponibilidade e programação financeira — nenhuma conta de movimentação de investimento. Já `1.2.1.3` tem 374.780.440,97 de movimento credor no período, e `1.1.4` está zerada | (a) apurar pela **variação patrimonial dos investimentos** (`1.1.4` + `1.2.1.3`): movimento credor → `L22`, devedor → `L55` **(recomendado)**; (b) manter `review_required` e entregar o BF com desequilíbrio declarado |

## Restrições e riscos

- **G5 é o que decide se o BF fecha.** Na opção (b), `L21`, `L24`, `L33`, `L54`, `L57` e `L66` saem
  não apuradas enquanto as contas de controle do ente não forem mapeadas — a entrega vira um
  demonstrativo parcial, honesto mas não comparável ao publicado.
- A leitura da MSC cresce: classes 1–6, até 3 tipos de valor, 2 exercícios. **Medido:** ~45 s para
  tudo, maior resposta com 6.202 registros — não é obstáculo. Mas 2 das ~40 chamadas caíram por
  reset de conexão: o adapter precisa de **retry com backoff**, que o do BO não tem.
- **Não há gabarito do BF no SICONFI.** O aceite passa a ser identidade interna + âncoras + caixa,
  e isso precisa estar claro antes de começar: "bate 1:1 com o publicado" não é prometível aqui.
- G8 é o que falta para o BF fechar. Sem ele, a entrega é um demonstrativo com desequilíbrio
  declarado de −228.702.095,15 — honesto, mas incompleto.
- **G9 e G10 atravessam o repositório inteiro, não só o BF.** O tipo de matriz e a competência valem
  igualmente para o BO já entregue e para os anexos futuros (IPC 04, 05, 08). Se o PO decidir a
  `MSCE`, ou a periodicidade mensal, o BO precisa ser reapurado e revalidado contra o publicado — e
  a decisão **C1** (mês 12, MSCC) passa a ser revisitada, não confirmada.
- Periodicidade mensal muda a **chave de cache** e a identidade do resultado: a change
  `plataforma-pipeline-dca` precisa do mês na chave, no job e na rota. Enquanto isso não for
  decidido, cachear resultado mensal com chave anual devolveria o demonstrativo do mês errado.

## Aprovação do PO

- [ ] PO aprovou esta proposta em ______ — **gate para a fase PLAN/ARCH**
- [x] G1, G2, G3 e G4 **resolvidos por medição** em 2026-09-14 (`docs/evidencia-bf-jp-2025.md`)
- [x] **G9 decidido em 2026-09-14** — `MSCE`, saldo de abertura no BF
- [ ] PO decidiu G5, G6, G7, G8 e **G10** (periodicidade mensal)
