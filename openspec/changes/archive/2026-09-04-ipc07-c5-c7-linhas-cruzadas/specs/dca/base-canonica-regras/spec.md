# dca/base-canonica-regras — Delta spec

Fecha **C5** (as 4 linhas que cruzam receita e despesa) e **C7** (previsão inicial de `L29`), as
duas sobre prática do STN medida — `docs/evidencia-c5-deficit-superavit.md` e
`docs/evidencia-c6-c7.md`.

Três requisitos existentes alterados e **2 cenários novos** (49 → **51**).

## MODIFIED Requirements

### Requirement: Cálculo por referência a outras regras, inclusive entre grupos

Linha de total SHALL declarar suas parcelas em `calculation.references`, cada uma nomeando o
`rule_id` referenciado e o sinal. A validação SHALL aceitar referência entre grupos e SHALL rejeitar
referência órfã e ciclo de dependência.

Uma referência PODE nomear a **coluna** lida na linha referenciada, quando a coluna que está sendo
calculada tem outro nome. Sem esse campo, a coluna lida é a mesma que está sendo calculada — o
comportamento de toda linha de total dentro de um bloco. Com ele, a linha cruzada entre receita e
despesa se torna calculável: os dois blocos não têm coluna em comum, e a interseção vazia é o que
mantinha `L25`, `L26`, `L49` e `L50` sem apurar.

Linha cujas referências não compartilham coluna SHALL declarar explicitamente suas colunas. A
validação SHALL rejeitar referência que nomeie coluna ausente na linha referenciada.

Ao agregar uma coluna, a apuração SHALL distinguir **três** situações na parcela, que hoje colapsam
em `None`:

| Situação na linha referenciada | Contribuição | Efeito no total |
|---|---|---|
| **não declara** a coluna | nenhuma — a parcela não existe | o total é a soma das demais parcelas |
| declara e a célula foi **suprimida pela condição** | **zero** | o total tem valor |
| declara e a célula está **não apurada** | indeterminada | o total sai `None`, com aviso |

Colapsar as duas primeiras em `None` é o que faria `L27.previsao_inicial` sair não apurada quando
`L29` deixa de ter a coluna, e `L26`/`L50` saírem em branco quando a linha de ajuste não se aplica —
os dois contra o publicado do STN.

#### Scenario: referência do bloco de receitas para o de despesas

- **GIVEN** o IPC07 p. 9, `L25 Déficit (VI) = (L48 - L24)`, onde `L48` pertence ao bloco de
  despesas
- **WHEN** a regra `bo.quadro_principal.receitas.l25` é lida
- **THEN** ela referencia `bo.quadro_principal.despesas.l48` com sinal `+`, nomeando a coluna
  `empenhadas`, e `bo.quadro_principal.receitas.l24` com sinal `-`, na coluna calculada
- **AND** declara **uma** coluna própria: `receitas_realizadas`
- **AND** a validação aceita a referência entre grupos
- **AND** NÃO detecta ciclo, porque `L24 = (L16 + L17)` e `L48 = (L40 + L41)` não dependem de `L25`

#### Scenario: referência nomeia coluna ausente é rejeitada

- **GIVEN** uma regra cuja referência nomeia a coluna `pagas` de `bo.quadro_principal.receitas.l24`,
  que só tem colunas de receita
- **WHEN** a validação é executada
- **THEN** o erro nomeia a regra de origem, a linha referenciada, a coluna pedida e as colunas
  disponíveis, e o exit é `1`
- **AND** nenhuma célula é apurada com zero no lugar da coluna ausente

### Requirement: Guarda condicional no cálculo

Quando o documento condicionar a linha ao sinal do resultado, a regra SHALL declarar a condição em
`calculation.condition`, legível por máquina. A regra NÃO DEVE registrar a condição apenas como
texto descritivo.

As colunas em que a linha condicional é apresentada SHALL ser as medidas no publicado do STN, e
**não são simétricas** entre déficit e superávit: cada bloco recebe tantas células de ajuste quantas
colunas de realização ele tem — a receita tem uma, a despesa tem três.

#### Scenario: déficit orçamentário

- **GIVEN** o IPC07 p. 9, `L25 Déficit (VI) = (L48 - L24)`, "Somente quando o resultado for
  deficitário"
- **WHEN** a regra é lida
- **THEN** o cálculo declara `L48` com sinal `+`, na coluna `empenhadas`, e `L24` com sinal `-`
- **AND** declara **uma** coluna: `receitas_realizadas` — medido em 11 dos 12 estados deficitários
  de 2025, exato em centavos contra `Deficit` do `RREO-Anexo 01`
- **AND** declara que o valor só é apresentado quando o resultado dessa subtração for positivo
- **AND** `evidence.text` contém a frase literal do documento

#### Scenario: superávit orçamentário

- **GIVEN** o IPC07 p. 11, `L49 Superávit (XIV) = (L24 - L48)`, "Somente quando o resultado for
  superavitário"
- **WHEN** a regra é lida
- **THEN** o cálculo declara `L24` com sinal `+`, na coluna `receitas_realizadas`, e `L48` com
  sinal `-`, na coluna calculada
- **AND** declara **três** colunas: `empenhadas`, `liquidadas` e `pagas` — medido em João Pessoa
  2025, exato em centavos nas três contra `Superavit` do `RREO-Anexo 01`
- **AND** a condição é declarada de forma simétrica à de `L25`, mas o **conjunto de colunas não é**
- **AND** as duas regras coexistem sem que uma anule a outra

#### Scenario: total que agrega linha condicional declara as colunas do publicado

- **GIVEN** `L26 TOTAL (VII) = (L24 + L25)` e `L50 TOTAL (XV) = (L48 + L49)`
- **WHEN** as duas regras são lidas
- **THEN** `L26` declara `previsao_inicial`, `previsao_atualizada` e `receitas_realizadas`, e
  **não** declara `saldo`
- **AND** `L50` declara `dotacao_inicial`, `dotacao_atualizada`, `empenhadas`, `liquidadas` e
  `pagas`, e **não** declara `saldo_dotacao`
- **AND** nenhuma das duas declara conta contábil própria

### Requirement: Decisões do PO são aplicadas com escopo fechado e auditável

As decisões do PO sobre B1, B3, B5 e B6 SHALL ser registradas na regra e aplicadas somente ao caso
decidido. A validação SHALL rejeitar a ampliação dessas exceções para outros `rule_id`, contas ou
domínios. A decisão NÃO DEVE apagar o literal do IPC07 nem alterar as tabelas de
`docs/contas-stn/`.

Decisão revogada ou restringida por decisão posterior SHALL ter a mudança registrada, e a decisão
anterior NÃO DEVE ser apagada do histórico em `docs/source-analysis-ipc07.md`. A decisão **B1** de
2026-08-27 foi revogada em 2026-09-04 (change `ipc07-b1-remocao-termo-5313`). A decisão **B6** de
2026-09-03 — `L27` a `L30` com as quatro colunas de receita — foi **restringida em 2026-09-04**:
`L29` Superávit Financeiro NÃO declara `previsao_inicial`, porque **zero de 25 entes** publicam
`PREVISÃO INICIAL` para `SuperavitFinanceiro` no `RREO-Anexo 01`. O restante de B6 segue valendo, e
a decisão **B5** — a conta da linha em `L29` — não é afetada.

#### Scenario: L27, L28 e L30 têm as quatro colunas de receita, e L29 tem três

- **GIVEN** que a p. 15 mostra `L28`, `L29` e `L30` sem marcação de coluna, e o PO decidiu em
  2026-09-03 que a seção REGRAS prevalece
- **WHEN** `L27`, `L28`, `L29` e `L30` são lidas
- **THEN** `L27`, `L28` e `L30` declaram as 4 colunas de receita — `previsao_inicial`,
  `previsao_atualizada`, `receitas_realizadas` e `saldo`
- **AND** `L29` declara **três**: `previsao_atualizada`, `receitas_realizadas` e `saldo` — um
  superávit financeiro é apurado sobre o exercício fechado e não existe em previsão inicial
- **AND** `L27` mantém `calculation` como `L28 + L29 + L30` em cada coluna, e em
  `previsao_inicial` a parcela de `L29` **não existe** — o total é `L28 + L30` = 12.000.000,00 em
  João Pessoa 2025, e não sai `None`
- **AND** cada uma registra `provenance.decision: B6` e o literal divergente da p. 15 em
  `evidence.text`
- **AND** nenhuma delas fica `review_required`
