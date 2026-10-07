# Proposal — Apuração do Balanço Patrimonial (F1)

**Status:** aprovada pelo PO (2026-10-07)
**Repositório:** `ps-dca`
**Capability:** `dca/balanco-patrimonial` (**nova**)
**Anexo DCA:** `DCA-Anexo I-AB` — publicado pelo `tt/dca` (140 registros em JP/2025, data única
`31/12`, `cod_conta` `P1.*`, `P2.*`, `AtivoFinanceiro`, `AtivoPermanente` —
`docs/anexos-siconfi-inventario.md`). Ao contrário do BF, **há espelho oficial**.
**Base normativa:** IPC 04, ed. 2020-01 (`docs/referencia/ipc/IPC04 - BP atualizacao - 20200117.pdf`) —
base canônica já transcrita em `knowledge/rules/bp/` (58 regras, 4 quadros) e
`knowledge/policies/ipc04.yaml`
**Fonte da verdade externa:** `regras-rreo-api` / `regras-rgf-api` (padrão de pipeline); o fluxo do
BF (`openspec/specs/dca/balanco-financeiro/spec.md`) é o molde direto
**Base de homologação:** BP publicado pelo SIAFIC de Cuitegi/PB (`2505204`), PublicSoft 2026.19.5.0,
`docs/entes-homologacao/cuitegi/Balanço Patrimonial_2025_TCE-PB.pdf` — homologa o resultado, **não** é
fonte de mapeamento

## Why

A base canônica do BP existe e nada a executa. O registry já reserva o lugar (`Anexo("I-AB", None)`),
a fonte MSC já sabe ler o BP (`fonte_de("BP")` = `MSCE`/**encerramento**, classes 1 e 2), mas:

1. **Não há serviço, CLI, rota nem cache** para o BP — o resumo do pipeline reporta `I-AB` como
   `sem_cache`.
2. **O validador recusa a base do BP:** `python -m scripts.validate_rules knowledge` hoje sai com
   15 erros `bp.*` e o índice `knowledge/indexes/rules_index.json` não tem nenhuma das 58 regras do BP.
   O validador só conhece IPC 06 e IPC 07.
3. **O atributo Financeiro/Permanente não chega ao domínio.** O Quadro dos Ativos e Passivos
   Financeiros e Permanentes (Lei 4.320/64) depende dele, e ele vem do **registro do fato**
   (`financeiro_permanente` no SICONFI, `financeiroPermanente` na PublicSoft — `docs/source-analysis.md`
   §11.2), não do PCASP: 924 contas de ativo e passivo são `F/P` no plano. Hoje
   `app/infra/msc/normalizacao.py` descarta o campo e `Registro` não o tem.

Sem isso, o anexo que o STN **publica** e contra o qual a aceitação pode ser 1:1 medida é justamente
o que o `ps-dca` não apura.

## What Changes

- Capability nova `dca/balanco-patrimonial`: apuração do **Quadro Principal** (40 linhas, IPC 04
  pp. 8–10) e do **Quadro dos Ativos e Passivos Financeiros e Permanentes** (7 linhas), duas colunas
  (`exercicio_atual`, `exercicio_anterior`).
- Mesmo motor do BO/BF (`app/domain/bo/`), mesma forma de `Resultado` (matriz, template,
  procedência, diagnóstico), mesmo job `apurar_anexo`, mesma rota `/dca/{anexo}`, mesmo cache.
- `Registro.financeiro_permanente` (`"F"` | `"P"` | `""`) normalizado das duas fontes MSC, e o
  atributo declarado por termo de conta na regra, como o IPC 04 escreve (decisão P4, design D2).
- Validador e schema aceitam `IPC04` (campos `conta_contabil`, `financeiro_permanente`; colunas
  `exercicio_atual`/`exercicio_anterior`); índice regenerado.
- `app/services/bp/quadro_principal.py` e `app/cli/bp.py`, espelhando o BF.
- BP entra no `REGISTRY` com `base_canonica="bp"` (decisão P1).
- Conferência contra o `tt/dca` `I-AB`: as âncoras de conta (`P1`, `P1.1`, `P1.2`, `P2.1`, `P2.2`,
  `P2.3`, `AtivoFinanceiro`, `AtivoPermanente`) comparadas em centavos com as linhas do IPC 04.

**Fora de escopo:**
- **Quadro das Contas de Compensação** (10 linhas, 8 `review_required`): IPC 04 itens 12–13 — o PCASP
  não padroniza o desdobramento executado × a executar; depende de 6º/7º nível do ente. Entra com
  todas as células `None` + motivo no diagnóstico.
- **Quadro do Superávit/Déficit Financeiro por fonte** (1 regra de total, `review_required`):
  cardinalidade das linhas depende da classificação do ente. Mesmo tratamento.
- Coluna anterior **manual** (existe no BF): não há caso medido de ente que publique o BP anterior
  divergente da MSC. Entra quando houver (YAGNI).
- Exclusão de intraorçamentárias (`ipc04.exclusao_intra_so_no_consolidado`): declarada, não executada,
  como o item 38 do BF (G11-a) — decisão P6.

## Entradas e saídas

| Interface | Entrada | Saída |
|---|---|---|
| `apurar(ente, exercicio, fonte, direcao=None, mapa=None, competencia=12)` | cod. IBGE, exercício, `FonteSaldos` | `Resultado` com `matriz`, `linhas` (template), `procedencia`, `diagnostico` |
| `python -m app.cli.bp <cod_ibge> <exercicio> [--fonte siconfi\|publicsoft] [--json]` | idem | matriz em texto ou JSON |
| `POST /dca/BP/jobs` · `GET /dca/BP` | mesmos parâmetros do BF, sem `origem`/`valores_json` | mesmo contrato camelCase do BF |
| `carregar(exercicio, demonstrativo="bp")` | exercício | `Mapa` com 58 linhas da edição 2020-01 |

Colunas:

| Coluna | Leitura da MSC |
|---|---|
| `exercicio_atual` | `MSCE`/encerramento, competência 12 do exercício apurado |
| `exercicio_anterior` | `MSCE`/encerramento, competência 12 do exercício − 1, **mesmo mapa** (D6 do BF) |

## Exemplo concreto

Cuitegi/PB (`2505204`), exercício 2025, BP consolidado publicado pelo SIAFIC (PDF de 01/04/2026):

| Quadro | Linha IPC 04 | Exercício atual | Exercício anterior |
|---|---|---|---|
| Principal | `L1` ATIVO | 76.314.331,92 | 63.600.595,67 |
| Principal | `L2` Ativo Circulante | 26.431.637,72 | 25.488.615,42 |
| Principal | `L3` Caixa e Equivalentes de Caixa | 26.286.597,15 | 19.812.433,77 |
| Principal | `L4` Créditos a Curto Prazo (`1.1.2` + `1.1.3`) | 145.040,57 | 4.944.014,94 |
| Principal | `L9` Ativo Não Circulante | 49.882.694,20 | 38.111.980,25 |
| Principal | `L12` Imobilizado | 20.414.089,11 | 18.804.089,33 |
| Principal | `L15` PASSIVO E PATRIMÔNIO LÍQUIDO | 76.314.331,92 | 63.600.595,67 |
| Principal | `L16` Passivo Circulante | 2.647.434,03 | 6.496.569,60 |
| Principal | `L24` Passivo Não Circulante | 119.311.755,53 | 114.975.024,96 ⚠ |
| Principal | `L32` Patrimônio Líquido | (45.644.857,64) | (57.870.998,89) |
| F/P | `L2` Ativo Financeiro | 26.431.637,72 | 19.897.621,26 |
| F/P | `L3` Ativo Permanente | 49.882.694,20 | 43.702.974,41 |
| F/P | `L5` Passivo Financeiro | 3.105.939,59 | 6.618.515,01 |
| F/P | `L6` Passivo Permanente | 119.311.755,53 | 114.975.024,96 |
| F/P | `L7` Saldo Patrimonial | (46.103.363,20) | (57.992.944,30) |

⚠ O próprio PDF é inconsistente: a conta `2.2.0.0.0.00.00` traz 82.981.174,41 e o "Total do Passivo
Não Circulante" traz 114.975.024,96 na mesma coluna (diferença 31.993.850,55). Também
`L1 = L15` só fecha no anterior se `L24` for 114.975.024,96. **Resolvido por medição (2026-10-07):** a
MSC de 2024 dá 114.975.024,96. A linha de conta do PDF é que está errada
(`docs/evidencia-bp-fp-2025.md` §3).

Observação: o ente publica Ativo Financeiro = Ativo Circulante em 2025 (26.431.637,72), mas não em
2024 (19.897.621,26 × 25.488.615,42) — prova de que F/P **não** se deriva do grupo da conta.

## O que a apuração persegue

Igual ao BF (diretriz do PO de 2026-09-18): fidelidade ao **IPC 04** sobre a MSC. Divergência contra
o PDF do ente vira `docs/entes-homologacao/<ente>/auditoria-bp-2025.md`, nunca alteração de regra
sem citação do IPC 04. A diferença em relação ao BF: aqui existe o `tt/dca` `I-AB`, e é **ele** o
aceite oficial; o PDF do SIAFIC é homologação secundária.

## Critérios de aceite

- [ ] `L1 = L15` (Ativo = Passivo + PL) em centavos, nas duas colunas, em Cuitegi e em João Pessoa
      2025 — a identidade que define o demonstrativo.
- [ ] As 7 identidades internas do Quadro Principal (`L1 = L2 + L9`, `L2 = L3+…+L8`,
      `L9 = L10+…+L14`, `L15 = L16 + L24 + L32`, `L16`, `L24`, `L32`) fecham em 0,00.
- [ ] Quadro F/P: `L1` (F/P) = `L1` (Principal) e `L7 = L1 − L4`, em centavos.
- [ ] Espelho contra `tt/dca` `I-AB` de João Pessoa 2025: as 8 âncoras de conta batem em centavos;
      divergência listada conta a conta, nunca silenciada.
- [ ] Homologação Cuitegi 2025: as 15 células do exemplo confrontadas; divergência em
      `auditoria-bp-2025.md` com linha, coluna, apurado, publicado e hipótese.
- [ ] Linhas `review_required` e quadros fora de escopo: célula `None` + motivo; nenhuma vira `0`.
- [ ] `python -m scripts.validate_rules knowledge` sem erro `bp.*`; índice contém as 58 regras.
- [ ] Regressão BO e BF **bit a bit**: suíte inteira verde, índice das partes `BO` e `BF` inalterado.
- [ ] `python -m pytest` e `python -m ruff check .` sem falha nova.

## Casos de erro

| Situação | Comportamento esperado |
|---|---|
| Registro sem `financeiro_permanente` numa conta `F/P` do PCASP | não entra em `L2`/`L3`/`L5`/`L6` do quadro F/P; aparece em `diagnostico.residuos` com `campo: financeiro_permanente` |
| `financeiro_permanente` fora de `1`/`2` | idem — nunca inferido pelo grupo da conta |
| Fonte MSC sem o campo F/P em nenhum registro | quadro F/P inteiro `None` + `diagnostico.sem_atributo_fp: true`; quadro principal íntegro |
| Linha `review_required` (`L4`, `L34` do principal — decisões P2/P3) | `None` + motivo citando o blocker; total soma as demais (D5 do BF) e o diagnóstico nomeia a parcela |
| `MSCE` lida pela **abertura** no BP | recusa — o par do BP é encerramento (`fonte-msc`) |
| Exercício anterior sem dados na MSC | `diagnostico.sem_dados_exercicio_anterior: true`; coluna anterior `None`, atual íntegra |
| Exercício < 2020 (sem vigência do IPC 04 ed. 2020-01) | `SemVigencia`, nomeando as edições |
| `L1 ≠ L15` na apuração | publica e declara a quebra em `diagnostico.equilibrio` |

## Decisões pendentes do PO (gate desta proposta)

| # | Assunto | O que está em jogo | Opções |
|---|---|---|---|
| **P1** | Código do anexo no registry | O `tt/dca` publica o BP como `I-AB` por **conta** (`P1.1.1`…), não pelas linhas `Lnn` do IPC 04 | (a) registrar `BP` (derivado, layout IPC 04, como `BO`/`BF`) e manter `I-AB` reservado para o espelho por conta **(recomendado)**; (b) ocupar `I-AB` com o BP do IPC 04 |
| **P2** | `L4` — literal `1.1.3.8.2.000.00` (IPC 04 p. 8) | O PCASP sustenta o prefixo `11382`; o literal tem um zero a mais | (a) corrigir para `11382` com citação do PCASP **(recomendado)**; (b) manter `review_required` |
| **P3** | `L34` — `2.3.2.0.2.00.00` (IPC 04 p. 9) | O PCASP não tem prefixo `23202` | (a) apurar pelo grupo `232` declarado na coluna; (b) manter `review_required` **(recomendado até medir se `232` tem saldo nos entes)** |
| **P4** | Atributo F/P | Novo campo no `Registro` e no schema; precisa **medir** que SICONFI e PublicSoft o entregam na MSCE/encerramento | (a) medir em Cuitegi e JP antes do TEST **(recomendado)**; (b) entregar só o Quadro Principal nesta fatia |
| **P5** | Escopo: compensação e superávit por fonte | 9 regras `review_required` dependem de detalhamento do ente | (a) fora desta change, células `None` com motivo **(recomendado)**; (b) apurar só os totais |
| **P6** | Intraorçamentárias (itens 8 e 9 do IPC 04) | Mesmo dilema do G11 no BF | (a) declarar sem executar **(recomendado)**; (b) excluir 5º nível = 2 |
| **P7** | `L5` Passivo Financeiro e a conta `6.3.1.7.1` (RPNP a liquidar, inscrição no exercício) | **Medido em 2026-10-07:** com as 4 contas do IPC 04, Cuitegi 2024 confere em centavos (6.618.515,01). Em 2025 faltam 387.532,93, exatamente o saldo de `6.3.1.7.1`, que o IPC 04 (PCASP 2019) não lista. Em 2024 `6.2.2.1.3.05` e `6.3.1.7.1` têm os dois 48.335,00: somar as duas contas dobra o valor | (a) manter as 4 contas do IPC 04 e registrar a divergência na auditoria **(recomendado)**; (b) somar `6.3.1.7.1` (quebra Cuitegi 2024); (c) usar `6.3.1.7.1` só quando `6.2.2.1.3.05` estiver zerada (regra de fallback, sem base no IPC) |

### P8 — exclusões intra-OFSS e o equilíbrio (aberta pela verificação de 2026-10-07)

As exclusões explícitas do IPC 04 (5º nível = 2 em `L3`, `L4`, `L10`, `L17`, `L23`, `L25`, `L39`…)
estão aplicadas e explicam **todas** as diferenças do Quadro Principal contra o `I-AB`, nos dois entes
(`docs/depara-bp-iab-ipc04.md`). Elas quebram `L1 = L15` sempre que o intra do ente não fecha em zero:

| Ente | `L1 − L15` apurado | Origem |
|---|---|---|
| João Pessoa 2025 | +5.946.040.575,02 | superávit acumulado intra `2.3.7.x.2`, sem contrapartida (ativo e passivo intra se anulam: 1.071.096.046,10) |
| Cuitegi 2025 | −2.004.721,69 | ativo intra 29.230.791,29 ≠ passivo intra 30.403.270,45, mais PL intra −3.177.200,85 |

O `I-AB` não exclui intra e fecha nos dois. O quadro F/P também não exclui (P6-a) e bate 5/5 em JP.

| Opção | Consequência |
|---|---|
| (a) manter as exclusões do IPC 04 e declarar o desequilíbrio no diagnóstico, com auditoria por ente **(recomendado: fiel à norma)** | Quadro Principal ≠ `I-AB` em todo ente com intra; `L1 = L15` só fecha onde o intra é recíproco e o PL intra é zero |
| (b) não aplicar as exclusões intra (estender P6-a às listas explícitas) | Quadro Principal = `I-AB` nas âncoras medidas; diverge do texto do IPC 04 para o BP consolidado |
| (c) aplicar as exclusões e ajustar `L39` pela diferença | **descartada**: é ajuste para forçar o fechamento, o que a diretriz do PO proíbe |

## Restrições e riscos

- **Risco de inversão de fonte:** o PDF de Cuitegi já é inconsistente consigo mesmo (`L24` anterior).
  Nenhuma regra muda para fechar com ele.
- **F/P é o ponto mais frágil:** se uma das fontes não entregar o atributo na matriz de
  encerramento, o quadro F/P sai `None` naquela fonte — honesto, mas incompleto.
- **`L5` Passivo Financeiro** lê contas de classe 6 (`6.2.2.1.3.01`, `6.2.2.1.3.05`, `6.3.1.1`,
  `6.3.1.5` — RP e créditos empenhados a liquidar), que `fonte_de("BP")` hoje não lê (classes 1 e 2).
  A leitura cresce para classes 1, 2 e 6.
- O espelho `I-AB` é **por conta**; casar conta `P2.1` com linha `L16` é de-para fixo e pequeno, mas
  precisa existir só na conferência — nunca na apuração.

## Aprovação do PO

- [x] PO aprovou a proposal em 2026-10-07
- [x] PO decidiu P1–P6 em 2026-10-07, todas pela opção recomendada: P1 (a) anexo `BP`; P2 (a) `L4`
      com `11382`; P3 (b) `L34` `review_required` até medir `232`; P4 (a) medir antes do TEST;
      P5 (a) compensação e superávit fora; P6 (a) intraorçamentárias declaradas, não executadas
- [x] PO confirmou o domínio do atributo: `financeiroPermanente` (PublicSoft) e
      `financeiro_permanente` (SICONFI) — `1` = Financeiro, `2` = Permanente
- [x] PO decidiu P7 em 2026-10-07: opção (a), 4 contas do IPC 04, divergência na auditoria
- [x] PO decidiu P8 em 2026-10-07: opção (a), exclusões intra-OFSS do IPC 04 mantidas e
      desequilíbrio declarado no diagnóstico. O critério "`L1 = L15` em centavos nos entes reais"
      passa a valer só para ente com intra recíproco e PL intra zero; JP e Cuitegi ficam com o
      desequilíbrio medido e explicado em `docs/depara-bp-iab-ipc04.md`
