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
**Base de homologação:** BF publicado pelos SIAFIC de **5 entes**, extraído em 2026-09-18 — **não** é
fonte de mapeamento: o de-para conta → linha é o do IPC 06 em `knowledge/rules/bf/`; o SIAFIC só
homologa o resultado da apuração sobre a MSC. Gabaritos em `docs/entes-homologacao/<ente>/gabarito-bf-2025.md`,
de-para em `docs/depara-bf-siafic-ipc06.md`, PDFs em `docs/entes-homologacao/`

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
| `apurar(ente, exercicio, fonte, direcao=None, mapa=None, anterior=Anterior.MSCE)` | cod. IBGE, exercício, `FonteSaldos`, **origem da coluna do exercício anterior** | `Resultado` com `matriz`, `mapa`, `procedencia`, `diagnostico` |
| `Anterior.MSCE` (padrão) | — | coluna `exercicio_anterior` apurada da MSCE do **exercício anterior**, pelas mesmas regras |
| `Anterior.MANUAL` | `{"L1": Decimal, "L2": Decimal, …}` informado pelo usuário | coluna `exercicio_anterior` preenchida com o informado, linha a linha |
| `python -m app.cli.bf <cod_ibge> <exercicio> [--fonte siconfi\|publicsoft] [--anterior msce\|manual] [--anterior-arquivo <json>] [--json]` | idem | matriz em texto ou JSON |
| `carregar(exercicio, demonstrativo="bf")` | exercício | `Mapa` com 80 linhas da edição 2024-06 |

### Coluna do exercício anterior — duas origens, escolha do usuário

Todas as 66 linhas do quadro principal têm duas colunas. A do exercício anterior **SHALL** aceitar
duas origens, escolhidas por quem apura:

1. **`MSCE` do exercício anterior** (padrão) — a coluna é apurada pelas mesmas regras do IPC 06, sobre
   a matriz do exercício anterior. Medido em 2026-09-18: funciona, e já está no relatório de auditoria
   de cada ente (`docs/entes-homologacao/<ente>/auditoria-bf-2025.md`, coluna "Exercício 2024").
2. **Preenchimento manual** — o usuário informa os valores linha a linha. Existe porque o ente pode
   ter publicado o exercício anterior com números que a MSC daquele ano não reproduz: em Recife, `L17`
   e `L50` de 2024 saem 628.456.869,17 da matriz contra **0,00** publicado; em Cuitegi a divergência
   alcança quase toda a coluna. Reapurar o passado não é sempre o que o ente quer declarar.

Regras que valem nos dois casos:

- A **procedência SHALL declarar** a origem usada (`msce_exercicio_anterior` ou `manual`) e, no modo
  manual, a identidade do conjunto informado — sem isso, dois demonstrativos incomparáveis passam
  por iguais e o cache serve a coluna errada.
- No modo manual, valor **não informado** para uma linha é `None` (não apurada), nunca `0`.
- No modo manual, a coluna **não entra** na conferência contra a MSC: o relatório de auditoria marca
  aquelas células como `informado pelo usuário`, e as identidades do IPC 06 continuam sendo exigidas
  sobre o que foi informado (`L33 = L1+L15+L21+L24+L29` também vale na coluna manual).
- A coluna do exercício **atual** nunca é manual.

## Exemplo concreto

**O `tt/dca` não publica o Balanço Financeiro** — medido em 2026-09-14: 2.002 registros, 7 anexos,
nenhum deles é o BF (`docs/evidencia-bf-jp-2025.md` §1). A apuração continua sendo **MSC → regras do
IPC 06** (`knowledge/rules/bf/quadro_principal.yaml`, 80 linhas, ed. 2024-06); o que faltava era com
o que **conferir** o resultado. Entram aí os BF publicados pelos SIAFIC dos entes de homologação,
extraídos dos PDFs em 2026-09-18:

| Ente | SIAFIC | Cobertura do quadro principal | Gabarito |
|---|---|---|---|
| Recife/PE (2611606) | Anexo XIII da Lei 4.320/64 | **66/66**, mesma ordem e nomenclatura do IPC 06 | `docs/entes-homologacao/recife/gabarito-bf-2025.md` |
| Porto Alegre/RS (4314902) | Balanço Financeiro (**administração direta**) | 66/66; PDF é **imagem**, transcrito visualmente | `docs/entes-homologacao/porto-alegre/gabarito-bf-2025.md` |
| João Pessoa/PB (2507507) | SIGEF/JPA | 66/66, com 4 vinculações próprias agregadas em `L10`/`L43` | `docs/entes-homologacao/joao-pessoa/gabarito-bf-2025.md` |
| Belo Horizonte/MG (3106200) | Consolidação Geral | 62/66 (sem RGPS e militares); **origem OCR** | `docs/entes-homologacao/<ente>/belo-horizonte/gabarito-bf-2025.md` |
| Cuitegi/PB (2504801) | PublicSoft 2026.19.4.0 | 48/66, sem segregação do RPPS | `docs/entes-homologacao/cuitegi/gabarito-bf-2025.md` |

**Recife e Porto Alegre são os entes de referência:** publicam as 66 linhas na ordem e na nomenclatura
do IPC 06, e as 16 identidades internas do demonstrativo fecham em centavos nos dois. Porto Alegre traz
duas ressalvas próprias: o PDF é **imagem pura**, transcrito visualmente (a transcrição se valida pelas
32 conferências — 16 identidades × 2 colunas), e o recorte é da **administração direta**, não do
consolidado — nele `L15` ≠ `L48` em 728.820.927,09, diferença que num consolidado se anularia. É contra ele que a apuração deve fechar
primeiro; os demais medem a robustez do motor diante de layouts que agregam ou omitem linhas.

A extração foi conferida pela aritmética do próprio demonstrativo: as 16 identidades do BF
(`L1 = L2+L3+L11`, `L33 = L1+L15+L21+L24+L29`, e assim por diante) fecham em centavos em Recife, João
Pessoa e Belo Horizonte, e em Cuitegi nas linhas que ele publica separadas — o pareamento
rótulo × valor está correto nos quatro. O quadro de detalhamento da receita por fonte de João Pessoa
(págs. 5–6, 6 colunas) ficou **fora**, por ser quadro livre do ente.

**Hierarquia das fontes, para não inverter:**

1. **IPC 06, ed. 2024-06** — define quais contas compõem cada uma das 80 linhas. Fonte única do
   mapeamento; nenhuma regra é criada ou alterada a partir de PDF de ente.
2. **MSC do ente** — os saldos. É sobre ela que a apuração roda.
3. **BF do SIAFIC (JP e Cuitegi)** — homologação do resultado. É o demonstrativo **do ente**, não
   do STN: pode ter erro, classificação própria e nomenclatura fora do IPC 06. Divergência contra
   ele é hipótese a investigar em ambos os lados, nunca prova de erro da apuração — e nunca motivo
   para "ajustar" a regra canônica até o número fechar.

O de-para rótulo do SIAFIC → linha `Lnn` existe só para comparar e vale por layout:
`docs/depara-bf-siafic-ipc06.md` (2026-09-18). O que ele já mostra:

- **`L21`–`L23` e `L54`–`L56` existem e são materiais** — as linhas hoje `review_required` que o G8
  discute. Recife publica `L21` = `L22` = 370.110.128,29 e `L54` = `L55` = 690.544.116,24; Belo
  Horizonte, 3.440.368.037,80 e 4.055.640.501,83. João Pessoa e Cuitegi zeram as duas. Ou seja: o
  desequilíbrio de −228.702.095,15 medido em JP **não** vem delas, e o teste de G8 tem de ser feito
  em Recife ou BH, não em João Pessoa (Porto Alegre também zera as duas).
- **Recife e Porto Alegre são 1:1 com o IPC 06** — 66 rótulos, mesma ordem, mesma nomenclatura,
  nenhuma agregação.
- **João Pessoa cobre as 66 linhas** do quadro principal, mas agrega 4 vinculações próprias
  (operação de crédito, cultura e lazer, trânsito, outras destinações) no que o IPC 06 chama de
  `L10`/`L43` — a comparação nessas linhas é **soma contra soma** (383.875.863,35 em `L10`,
  277.578.365,98 em `L43`, em 2025).
- **Belo Horizonte cobre 62 linhas** (não tem RGPS nem militares: `L19`, `L20`, `L52`, `L53`) e vem
  de **PDF digitalizado**: 2 células saíram com leitura de OCR duvidosa (`L9` e `L41`) e estão
  marcadas no gabarito — conferir no PDF antes de usar como referência.
- **Cuitegi cobre 48 linhas e omite 18**: não separa RPPS dos demais vinculados (`L3+L11`,
  `L36+L44`), não separa o caixa do RPPS (`L30+L31`, `L63+L64`), não tem os fundos do RPPS
  (`L12`–`L14`, `L45`–`L47`), nem "Demais Vinculações" (`L8`, `L9`, `L41`, `L42`), nem o grupo
  "Outras Movimentações Financeiras" (`L21`–`L23`, `L54`–`L56`) — o que desloca sua numeração
  romana a partir do 3º grupo. Comparar por código `Lnn`, nunca por romano impresso.
- Nas 18 linhas omitidas, a homologação verifica apenas que a apuração não produz valor onde o ente
  não tem conteúdo; se produzir, é divergência estrutural a investigar dos dois lados.

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

## O que a apuração persegue (diretriz do PO, 2026-09-18)

O alvo é a **fidelidade ao mapeamento do IPC 06** sobre a matriz de saldos — não o número publicado
pelo ente. O BF do SIAFIC pode ter sido alterado na publicação e divergir da matriz que o próprio
ente enviou à MSC. Portanto:

1. Cada linha e cada coluna apurada **SHALL** refletir a regra canônica em `knowledge/rules/bf/`,
   com as contas e os códigos da STN que a regra declara.
2. Divergência contra o publicado **SHALL** virar **relatório de auditoria na pasta do ente**
   (`docs/entes-homologacao/<ente>/auditoria-bf-2025.md`), nomeando a **linha e a coluna** do IPC 06,
   o valor apurado e o valor publicado.
3. Divergência **NÃO É** motivo para alterar regra canônica. Alteração em `knowledge/rules/bf/` só
   com citação do texto do IPC 06.
4. A conferência que vale sem depender do ente são as **identidades do próprio demonstrativo**
   (`L1 = L2+L3+L11`, `L33 = L1+L15+L21+L24+L29`, …), apuradas sobre a matriz.

## Critérios de aceite

- [ ] Coluna do exercício anterior apurada nas duas origens: por `MSCE` do exercício anterior e por
      valores informados; a procedência declara qual foi usada, e o modo manual não é escolhido por
      omissão em nenhum caminho.
- [ ] Relatório de auditoria gerado na pasta de cada ente de homologação, com linha e coluna do
      IPC 06 de toda divergência — nenhuma silenciada.
- [ ] Homologação nos dois entes: cada linha apurada a partir da MSC pelas regras do IPC 06 é
      confrontada com `docs/entes-homologacao/joao-pessoa/gabarito-bf-2025.md` e `docs/entes-homologacao/cuitegi/gabarito-bf-2025.md`, na coluna
      do exercício apurado. Divergência é listada linha a linha, com hipótese e lado provável
      (regra, MSC do ente ou demonstrativo do ente) — nunca silenciada, nunca resolvida mudando a
      regra canônica sem base no IPC 06.
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
| Coluna anterior por `MSCE` e o exercício anterior sem dados na MSC | `diagnostico.sem_dados_exercicio_anterior: true`; coluna anterior toda `None`, coluna atual íntegra — nunca zero, nunca cair para o modo manual por omissão |
| Coluna anterior `MANUAL` com linha faltando | aquela célula é `None` + `NaoApurada` com motivo `não informado`; as demais valem |
| Coluna anterior `MANUAL` com linha inexistente no IPC 06 | erro explícito nomeando a linha recusada, antes de apurar |
| Coluna anterior `MANUAL` que quebra `L33 = L1+L15+L21+L24+L29` | apura e publica, com a quebra no diagnóstico: o informado é do usuário, mas a identidade violada é declarada |

## Decisões pendentes do PO (gate desta proposta)

| # | Assunto | O que está em jogo | Opções |
|---|---|---|---|
| ~~**G1**~~ | Casamento da fonte de recursos | **Medido:** `fonte_recursos` tem sempre 4 dígitos; o detalhamento do ente vai em `complemento_fonte`, coluna separada | (a) descartar o 1º dígito e casar os 3 seguintes por igualdade — **confirmado**: `L1 = L2+L3+L11` fecha em 0,00 e o resíduo de fonte é **zero** |
| ~~**G2**~~ | Saldo do exercício anterior (L30–L32) | **Medido:** `beginning_balance` responde nas classes 1 e 2 | (a) `beginning_balance` do exercício apurado — **confirmado** |
| ~~**G3**~~ | Movimento credor/devedor (L27/L60) | **Medido:** em `2.1.8.8`, `period_change` traz C = 127.592.727,15 e D = 145.790.710,23; o acumulado traz só o líquido −18.197.983,08 | (a) `period_change` com C em L27 e D em L60 — **confirmado** |
| ~~**G4**~~ | Coluna "Exercício Anterior" | **Medido:** 2024 completo baixa junto com 2025 em ~45 s no total, 8 classes × 3 tipos de valor | (a) apurar — **confirmado**, latência não é obstáculo |
| **G5** | Efeito das 6 linhas bloqueadas nos totais | **Medido em 2026-09-18:** sem a opção (a), Recife não fecha nenhum total; com ela, 42/66 linhas batem em centavos | Se `L22` é `None`, `L21` é `None`, `L33` é `None` — e o BF inteiro não fecha | (a) linha bloqueada contribui como **parcela inexistente** (total soma as demais), com o bloqueio no diagnóstico **(recomendado)**; (b) propagar `None` até o total, e o BF só fecha quando F1/F2 forem decididos |
| **G6** | Renomear `app/domain/bo/` → `app/domain/nucleo/` | Evita duplicar 500 linhas de motor entre BO e BF | (a) renomear nesta change **(recomendado)**; (b) manter e importar `MapaBO` no BF; (c) duplicar o motor em `app/domain/bf/` |
| ~~**G7**~~ | Critério de direção do saldo no BF | **Confirmado por medição em 3 entes (2026-09-18):** com direção por conta, todas as linhas por fonte fecham | **Medido:** com a direção da coluna (critério do BO), `L1` sai 5.872.854.713,27; com a direção **por conta**, sai 5.117.875.296,33 — exatamente o publicado. O par `6.2.1.2 (+) / 6.2.1.3 (−)` do IPC 06 já traz o sinal na regra | (a) direção por conta no BF, mantendo a direção de coluna no BO, escolhida pela regra **(recomendado)**; (b) direção por conta nos dois — exige remedir o BO inteiro |
| ~~**G9**~~ | Par (matriz, tipo de saldo) | **Decidido pelo PO em 2026-09-14:** todos os demonstrativos sobre a **matriz de encerramento (`MSCE`)**; tipo de saldo **abertura** no BO, BF, DVP e DFC, e **encerramento** no BP. Medido: `MSCC`/encerramento ≡ `MSCE`/abertura no BO, **0 divergências em 337 células** em Cuitegi **e** em João Pessoa | — |
| **G10** | **Periodicidade mensal além da anual, em todos os anexos** | Hoje `MES_DA_DCA = 12` é constante no serviço do BO, a chave de cache não tem mês e a decisão C1 do PO fixou dezembro. Mensal muda serviço, carregador, chave de cache, job e rota — e muda o significado do tipo de saldo: num mês qualquer, `ending_balance` é posição acumulada e `period_change` é o movimento do mês | (a) mês como parâmetro em toda a cadeia, com 12 como padrão **(a definir com o PO)**; (b) manter anual e tratar mensal em change própria |
| **G8** | Como apurar `L22` e `L55` sem conta de controle | **Hipótese (a) refutada em 2026-09-18:** busca reversa em 7 combinações de matriz e tipo de saldo, todos os prefixos de conta, saldo/créditos/débitos — nenhum valor publicado por Recife existe na MSC. Recomendação passa a ser (b) | **Medido:** as classes 7 e 8 do ente só têm controles de disponibilidade e programação financeira — nenhuma conta de movimentação de investimento. Já `1.2.1.3` tem 374.780.440,97 de movimento credor no período, e `1.1.4` está zerada | (a) apurar pela **variação patrimonial dos investimentos** (`1.1.4` + `1.2.1.3`): movimento credor → `L22`, devedor → `L55` **(recomendado)**; (b) manter `review_required` e entregar o BF com desequilíbrio declarado |

## Medição de 2026-09-18 — `docs/evidencia-bf-medicao-2026-09-18.md`

Apuração completa pelas regras do IPC 06 sobre a MSC do SICONFI, com o PCASP da STN, confrontada
com os gabaritos dos SIAFIC:

| Ente | Batem em centavos | Divergem | Não apuráveis | `L33 − L66` do apurado |
|---|---|---|---|---|
| Recife/PE | **42 / 66** | 18 (12 por propagação) | 6 | 18.025.391,58 |
| João Pessoa/PB | **40 / 66** | 20 | 6 | −972.846.807,25 |
| Porto Alegre/RS | 17 / 65 | 43 | 5 | 356.960.596,03 |

O que a medição fechou, e que muda esta proposta:

- **G1, G7 confirmados**; **G2 resolvido de forma diferente da prevista**: `L29`–`L32` são o
  **exercício anterior**, não um tipo de saldo distinto — MSCE/abertura de 2024, conta `1.1.1`
  (802.570.332,31) mais `1.1.3.5.1` (717.721,98), igual aos 803.288.054,29 publicados por Recife.
- **O tipo de saldo é por linha, não por demonstrativo** (refina G9): `L25`/`L26` só existem no
  saldo de **encerramento** — as contas `5.3.1.7` e `5.3.2.7` valem lá exatamente o publicado.
- **G8 refutado por medição:** nenhum dos valores que Recife publica em `L22`, `L28`, `L55`, `L61`,
  `L27` e `L60` existe na MSC, em nenhuma das 7 combinações, em nenhum prefixo de conta, como saldo,
  crédito ou débito — e a busca foi validada por controle (acha `L16` e `L25`). A hipótese de apurar
  `L22`/`L55` por `1.1.4` + `1.2.1.3` não se sustenta: `1.1.4` varia +710.419.938,88 e `1.2.1.3` não
  tem movimento no ente.
- **Porto Alegre não homologa no recorte atual:** a MSC é consolidada e o PDF é da administração
  direta — `L11`–`L14` saem 2,27 bi contra zero publicado.
- **A granularidade de JP não é 1:1, mas o bloco fecha em 0,00:** `L8+L9+L10` = 580.159.482,56 e
  `L41+L42+L43` = 529.816.473,72, iguais à soma dos rótulos do ente.

### G11 — escopo do item 38 (intraorçamentárias)

**Novo, aberto por medição em 2026-09-18.** A policy `ipc06.exclusao_de_intraorcamentarias` declara o
conceito sem os códigos. Aplicada pela interpretação natural (receita das categorias 7 e 8, despesa
com modalidade 91), ela **quebra linhas que batiam em centavos**: `L1` e `L34` de Belo Horizonte e de
João Pessoa conferem sem a exclusão e divergem com ela. Em Cuitegi não há intraorçamentária alguma.

| Opção | Consequência |
|---|---|
| (a) **não aplicar** e declarar no relatório **(recomendado)** | mantém 4 linhas que conferem em 2 entes; a policy fica declarada e não executada, com a medição anexa |
| (b) aplicar por categoria 7/8 e modalidade 91 | quebra `L1` e `L34` em BH e JP, sem nenhum ente onde melhore de forma inequívoca |
| (c) definir o escopo com o STN antes de implementar | correto no longo prazo; depende de terceiro |

## Restrições e riscos

- **G5 é o que decide se o BF fecha.** Na opção (b), `L21`, `L24`, `L33`, `L54`, `L57` e `L66` saem
  não apuradas enquanto as contas de controle do ente não forem mapeadas — a entrega vira um
  demonstrativo parcial, honesto mas não comparável ao publicado.
- A leitura da MSC cresce: classes 1–6, até 3 tipos de valor, 2 exercícios. **Medido:** ~45 s para
  tudo, maior resposta com 6.202 registros — não é obstáculo. Mas 2 das ~40 chamadas caíram por
  reset de conexão: o adapter precisa de **retry com backoff**, que o do BO não tem.
- **Não há gabarito do BF no SICONFI.** A homologação usa o BF do SIAFIC de JP e Cuitegi — fonte do
  ente, não do STN, em nomenclatura própria de cada sistema. O de-para rótulo → linha `Lnn` é da
  fase TEST e pode não ser 1:1 em toda linha; "bate 1:1 com o publicado" não é prometível aqui.
- **Risco de inversão de fonte:** fechar número mexendo na regra canônica para alcançar o PDF do
  ente descaracteriza a apuração. Toda alteração em `knowledge/rules/bf/` exige citação do IPC 06.
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

> Resumo das decisões, com a evidência de cada uma, em **`docs/decisoes-bf-para-po-2026-09-18.md`**.

- [x] PO autorizou o fechamento em 2026-09-18, nesta sessão
- [x] G1, G2, G3 e G4 **resolvidos por medição** em 2026-09-14 (`docs/evidencia-bf-jp-2025.md`)
- [x] **G9 decidido em 2026-09-14** — `MSCE`, saldo de abertura no BF
- [ ] PO decidiu G5, G6, G7, G8 e **G10** (periodicidade mensal)
