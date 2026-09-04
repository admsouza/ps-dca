# Design — Regras canônicas do Balanço Orçamentário (IPC 07)

**Change:** `openspec/changes/ipc07-bo-regras-canonicas/` · **Proposal aprovada pelo PO em:** 2026-09-04 (Jackson S. da Silva (PO))

> Entregável da **Fase 2**. Não pode ser implementado antes do gate de aprovação da proposal
> (`AGENTS.md` §2).

## Contexto

`docs/source-analysis-ipc07.md` mediu o IPC07: **69 linhas** de regra em **3 quadros**, com 4 a 6
colunas de valor. A matriz foi reconstruída por geometria — as pp. 8–13 são paisagem rotacionada
90°, e leitura linear não preserva a associação célula→coluna.

Estado da análise: **11 ambiguidades internas resolvidas** por evidência do próprio documento
(R1–R11); B1, B3 e B5 resolvidos pelo PO em 2026-08-27; B6, B2 e B4 em 2026-09-03. **As 69
linhas** estão livres de decisão adicional.

Códigos classificados contra `docs/contas-stn/`: 41 contas/padrões PCASP (32 atuais + 9 exceções
históricas B1/B3), 7 de 7 pares função/subfunção OK, 13 naturezas intra e 13 NDs não validáveis por
lacuna das tabelas.

Quatro restrições moldam o desenho:

1. **Não inventar.** B3 tem candidato plausível por nomenclatura; o modelo precisa de um lugar para
   guardá-lo **sem aplicá-lo**.
2. **O documento se contradiz.** REGRAS × ESTRUTURA divergem em 5 pontos. O modelo tem de registrar
   qual leitura foi adotada e com base em qual página.
3. **O consumidor é um agente de código**, que precisa implementar sem reler o PDF. Isso empurra o
   modelo para explícito e verboso.
4. **Escopo de um documento só.** Os enums cobrem o que o IPC07 usa; as changes dos outros IPCs
   estendem. Nada de campo especulativo.

## Componentes afetados

Não há código neste repositório. Todos os componentes são novos.

| Componente | Papel na change |
|---|---|
| `knowledge/sources/ipc07/` | `metadata.yaml` (SHA-256, páginas, edição) e `extracted.md`; o PDF continua em `docs/referencia/ipc/` |
| `knowledge/sources/stn/metadata.yaml` | hashes e contagens das tabelas de domínio |
| `knowledge/rules/bo/*.yaml` | 69 regras, 3 arquivos (um por quadro) |
| `knowledge/policies/ipc07.yaml` | regras gerais do BO, referenciadas pelas regras de linha |
| `knowledge/schemas/*.json` | JSON Schema Draft 2020-12 de regra, filtro, coluna, fonte |
| `knowledge/indexes/*.json` | índice gerado; nunca editado à mão |
| `docs/contas-stn/*.md` | tabelas oficiais — **lidas, nunca alteradas** |
| `scripts/extract_ipc.py` | extração por geometria (dev; não roda em CI) |
| `scripts/load_stn_tables.py` | conjuntos de códigos válidos a partir de `docs/contas-stn/` |
| `scripts/validate_rules.py` | validação completa; gate de CI |
| `scripts/build_index.py` | geração dos índices |
| `scripts/check_sources.py` | integridade SHA-256 do PDF e das tabelas |
| `tests/` | testes normativos por regra e testes do validador |
| `AGENTS.md` (raiz) | **seção nova** "Regras contábeis canônicas"; o contrato existente não muda |

## Fluxo da informação

```text
docs/referencia/ipc/IPC07*.pdf   (imutável, fonte normativa)
        │  scripts/extract_ipc.py  — reconstrução geométrica (manual, dev)
        ▼
knowledge/sources/ipc07/extracted.md  +  metadata.yaml
        │  transcrição assistida + aplicação de R1–R11
        ▼
knowledge/rules/bo/*.yaml  +  knowledge/policies/ipc07.yaml     ← FONTE EXECUTÁVEL
        │
        │  docs/contas-stn/*.md ──→ load_stn_tables.py ──┐  domínio de validação
        │  scripts/validate_rules.py  ←─────────────────┘
        │      (schema · IDs · refs · ciclos · fonte · status · códigos)
        │  scripts/build_index.py
        ▼
knowledge/indexes/rules_index.json
        ▼
(fora desta change) rule engine → API FastAPI → consumidores
```

## Contratos / interfaces

### Matriz do IPC07, por quadro

| Quadro | Arquivo | Págs. | Linhas | Colunas de valor |
|---|---|---|---|---|
| Quadro Principal | `knowledge/rules/bo/quadro_principal.yaml` | 8–11 | 51 | receitas 4 · despesas 6 |
| Execução de RP Não Processados | `rp_nao_processados.yaml` | 12 | 9 | 6 |
| Execução de RP Processados | `rp_processados.yaml` | 13 | 9 | 5 |

Colunas nomeadas (chaves canônicas → rótulo do PDF):

```text
receitas   previsao_inicial (a) · previsao_atualizada (b) · receitas_realizadas (c) · saldo (d)=(c-b)
despesas   dotacao_inicial (e) · dotacao_atualizada (f) · empenhadas (g) · liquidadas (h)
           · pagas (i) · saldo_dotacao (j)=(f-g)
RPNP       inscritos_exerc_anteriores (a) · inscritos_31_dez (b) · liquidados (c) · pagos (d)
           · cancelados (e) · saldo_a_pagar (f)=(a+b-d-e)
RPP        inscritos_exerc_anteriores (a) · inscritos_31_dez (b) · pagos (c) · cancelados (d)
           · saldo_a_pagar (f)=(a+b-c-d)
```

### Modelo de regra — linha com filtros e contas

Transcrição real do IPC07 p. 8, `L2` (a linha que o item 23 usa como exemplo da própria norma):

```yaml
rule_id: bo.quadro_principal.receitas.l2

demonstrativo: { codigo: BO, descricao: Balanço Orçamentário }
quadro:        { codigo: QUADRO_PRINCIPAL, descricao: Quadro Principal }
grupo:         { codigo: RECEITAS, descricao: Receitas Orçamentárias }

linha:
  codigo: L2
  descricao: Impostos, Taxas e Contribuições de Melhoria
  nivel: 2          # apresentação: indentação no demonstrativo
  ordem: 2          # apresentação: posição no quadro

policies:
  - ipc07.receita_liquida_de_deducoes

filters:
  - field: natureza_receita
    operator: in
    values:
      - { literal: "1100.00.00", pattern: "11" }   # grafia do PDF + normalizado (D3)
      - { literal: "7100.00.00", pattern: "71" }

columns:
  previsao_inicial:
    label: Previsão Inicial (a)
    accounts:
      - { literal: "5.2.1.1.0.00.00", pattern: "5211", sign: "+" }
  previsao_atualizada:
    label: Previsão Atualizada (b)
    accounts:
      - { literal: "5.2.1.1.0.00.00", pattern: "5211", sign: "+" }
      - { literal: "5.2.1.2.0.00.00", pattern: "5212", sign: "+" }
  receitas_realizadas:
    label: Receitas Realizadas (c)
    accounts:
      - { literal: "6.2.1.2.0.00.00", pattern: "6212", sign: "+" }
      - { literal: "6.2.1.3.0.00.00", pattern: "6213", sign: "+" }
  saldo:
    label: SALDO (d) = (c-b)
    calculation:
      references:
        - { column: receitas_realizadas, sign: "+" }
        - { column: previsao_atualizada, sign: "-" }

source:
  document: IPC07
  document_version: "2020-01"
  page: 8
  section: REGRAS DE PREENCHIMENTO DO BALANÇO ORÇAMENTÁRIO
  item: "23"
  table: Quadro Principal
  row: L2

evidence:
  page: 8
  text: "L2 | Impostos, Taxas e Contribuições de Melhoria | 1100.00.00; 7100.00.00"

version:
  source_document: IPC07
  edition: "2020-01"
  valid_from: "2020-01-20"
  valid_until: null

provenance:
  extraction_method: assisted
  extractor_version: "1.0"
  extracted_at: "2026-08-27"

status: extracted
review: { required: true }
```

### Construções do IPC07 e a forma canônica de cada uma

| # | Construção | Caso real | Forma canônica |
|---|---|---|---|
| 1 | linha composta por outras | `L1 = (L2+…+L9)` | `calculation.references: [{ rule, sign }]`; a regra **não** tem `columns` próprias |
| 2 | subtração entre linhas | `L48 = (L40 + L41)`, `L25 = (L48 - L24)` | mesma lista, com `sign: "-"` |
| 3 | referência entre grupos | `L25` (receitas) → `L48` (despesas) | `rule` com `rule_id` completo; validador aceita cruzamento de grupo |
| 4 | coluna derivada de outras colunas | `saldo (d) = (c-b)`, `f = (a+b-d-e)` | `columns.<col>.calculation.references[].column` |
| 5 | contas assinadas na coluna | RPNP col. (a): `5.3.1.2 + 5.3.1.3 + 5.3.1.6 (-) 6.3.1.6` | `accounts[].sign` |
| 6 | filtro por natureza de receita | `L2`: `1100.00.00; 7100.00.00` | `filters: [{ field: natureza_receita, operator: in }]` |
| 7 | filtro por natureza de despesa | `L32`: `ND: 3.1.00.00.00` | `field: natureza_despesa` |
| 8 | exclusão por conta PCASP | `L11`: 8 padrões PCASP | `field: conta_contabil`, `operator: not_in` |
| 9 | função + subfunção concatenadas | `L38`: `Função: 28.841` | dois filtros, `funcao in ("28")` e `subfuncao in ("841")`, com `literal: "28.841"` preservado |
| 10 | dois grupos de exclusão na mesma célula | `L38`: `46.xx.76` + funções **e** `46.xx.77` + funções | `exclusion_groups: [[filtros…], [filtros…]]` (D2) |
| 11 | guarda condicional | `L25` "somente quando deficitário" | `calculation.condition: { when: result_positive }` |
| 12 | leitura adotada contra literal divergente | `L40`: `(VII + IX + X)` na p. 10 × `(VIII + IX + X)` na p. 15 | `provenance.reading: { adopted_from_page: 15 }` + literal em `evidence` (D4) |
| 13 | padrão PCASP histórico | `L19`: `2111.00.2.0`; `L11`: `2111.00.20` | `field: conta_contabil` + exceção histórica B3 (D5) |
| 14 | override de conta restrito | `L29` e `L30` | `line_account_override: true`; rejeitado nos demais `rule_id` (D14) |

### Modelo de policy

O IPC07 traz duas regras gerais que valem para o demonstrativo inteiro, e **não** traz exclusão de
contas intraorçamentárias — ao contrário do IPC04 e do IPC05 (ver D7).

```yaml
policy_id: ipc07.receita_liquida_de_deducoes
descricao: >
  No Quadro Principal, as receitas são informadas pelos valores líquidos das respectivas deduções
  (restituições, descontos, retificações, deduções para o Fundeb, repartições de receita tributária
  entre entes), quando registradas como dedução.
aplica_a:
  demonstrativo: BO
  quadro: QUADRO_PRINCIPAL
  grupo: RECEITAS
source:
  document: IPC07
  document_version: "2020-01"
  page: 6
  section: INSTRUÇÕES PARA PREENCHIMENTO DO BALANÇO ORÇAMENTÁRIO
  item: "19"
evidence:
  page: 6
  text: >
    as receitas são informadas pelos valores líquidos das respectivas deduções, tais como
    restituições, descontos, retificações, deduções para o Fundeb e repartições de receita
    tributária entre os entes da Federação, quando registradas como dedução
status: validated
```

A segunda é `ipc07.refinanciamento_destacado` (item 15, p. 6): os valores de refinanciamento da
dívida mobiliária e de outras dívidas constam destacadamente nas receitas de operações de crédito e,
no mesmo nível de agregação, nas despesas de amortização. É a policy que **explica** por que `L11`
exclui exatamente o que `L19`–`L23` capturam — e por que B3 é grave.

### Enums fechados para o IPC07

```text
filters[].field       conta_contabil | natureza_receita | natureza_despesa | funcao | subfuncao
filters[].operator    in | not_in

accounts[].sign       + | -

calculation.condition.when   result_positive | result_negative

status                draft | extracted | review_required | validated | deprecated
provenance.extraction_method   automated | assisted | manual

review.blocker        (nenhum — B1, B3, B5 e B6 decididos)
provenance.decision  B1 | B3 | B5 | B6
line_account_override  false | true  (true somente em L29 e L30)
```

**Deliberadamente ausentes**, porque o IPC07 não usa: `fonte_recurso`, `financeiro_permanente`,
`movimento`, `nivel_5_conta`, `accounts[].moment`,
`equals`, `not_equals`, `starts_with`, `contains`, comparadores numéricos, `is_null`,
`unresolved[]`, `parametric`. Cada um entra na change do IPC que o exigir, com o caso real citado.

### Contrato dos scripts

Fixado pelos testes da fase TEST (2026-09-04). Cada script é importável e tem `main()` fino por
cima — os testes chamam a função, o CI chama o CLI.

```python
# scripts/validate_rules.py
def validar(base: Path) -> Relatorio

# scripts/check_sources.py
def verificar(base: Path) -> Relatorio

# scripts/build_index.py
def construir(base: Path) -> dict          # rule_id -> {file, demonstrativo, quadro, document, page}

# scripts/load_stn_tables.py
def carregar(raiz_docs: Path) -> dict[str, set[str]]
```

`base` é o diretório `knowledge/`, com `rules/`, `policies/`, `sources/`, `schemas/` e `indexes/` —
receber o caminho, em vez de resolvê-lo internamente, é o que permite validar uma árvore de teste
sem tocar na do repositório.

```python
@dataclass(frozen=True)
class Erro:
    rule_id: str | None
    mensagem: str
    arquivo: str | None
    linha: int | None

@dataclass(frozen=True)
class Relatorio:
    erros: list[Erro]
    contagens: dict     # rule_ids · por_quadro · por_status · valid_until · excecoes_dominio · total
    exit_code: int      # 0 sem erro, 1 com erro
```

**Formato do arquivo de regras.** Cada YAML é um mapeamento com a chave `rules:` (uma lista), e o de
policy com `policies:`. Documento YAML com uma lista solta na raiz não é aceito: a chave nomeada
deixa espaço para metadado de arquivo sem quebrar quem já lê a base.

```yaml
# knowledge/rules/bo/quadro_principal.yaml
rules:
  - rule_id: bo.quadro_principal.receitas.l1
    ...
```

### Contrato do validador

```text
$ python scripts/validate_rules.py

✓ YAML valid                      4 arquivos (3 de regra + 1 de policy)
✓ Schema valid                    69 regras · 2 policies
✓ Fontes íntegras                 IPC07 + 7 tabelas STN · sha256 conferido
✓ 0 IDs duplicados
✓ 0 referências inválidas
✓ 0 dependências circulares
✓ 0 regras sem source
✓ 0 páginas fora de 1..17
✓ 0 códigos ausentes sem review_required, exceção de domínio ou decisão histórica

Regras por quadro    quadro_principal 51 · rp_nao_processados 9 · rp_processados 9   (total 69)
Regras por status    validated 0 · extracted 69 · review_required 0 · draft 0
Bloqueios            nenhum
Decisões do PO       B1 1 código / 6 linhas · B3 16 grafias (8 padrões) / 5 linhas · B5 2 linhas
                     B6 5 linhas (L27–L30 com 4 colunas · L51 sem coluna)
Exceções de domínio  B2 13 códigos / 13 linhas · B4 13 códigos / 21 linhas
exit 0

> Contagens conferidas contra a base gerada em 2026-09-04. As previsões anteriores de B1 (9 linhas),
> B3 (8 padrões) e B4 (17 linhas) eram estimativas da descoberta; a diferença é de contagem, não de
> conteúdo — detalhe em `tasks.md` § "Medições da base gerada".
```

Em erro, uma entrada por problema, sempre com `rule_id` + `arquivo:linha`:

```text
ERROR bo.quadro_principal.receitas.l28
  line_account_override não permitido para este rule_id
  Permitido somente em: bo.quadro_principal.receitas.l29, bo.quadro_principal.receitas.l30
  Source: knowledge/rules/bo/quadro_principal.yaml:612

exit 1
```

## Impacto

| Eixo | Impacto |
|---|---|
| Banco / migration | **nenhum**. YAML + Git é a fonte canônica |
| Cache | nenhum |
| Filas / worker | nenhum |
| APIs externas | nenhum — tudo local e offline |
| Regressão | nenhuma — não há comportamento existente. `AGENTS.md` e `openspec/` só recebem adição |
| Dependências | runtime `pyyaml`, `jsonschema`; dev `pymupdf`, `pytest`, `ruff` |
| CI | três comandos novos, determinísticos e offline |

## Decisões

### D1 — Granularidade: uma regra por linha, com mapa de colunas
**Escolhido:** regra por linha; `columns` dentro da regra.
**Descartado:** regra por célula (linha × coluna).
**Porquê:** o item 23 do IPC07 define que a coluna diz **de onde vem o valor** e a linha diz **como
filtrar**. Medido: 69 regras contra ~360 células. Regra por célula duplicaria os filtros de linha em
cada célula e permitiria divergência entre células da mesma linha, o que a norma não admite.

### D2 — Exclusão em grupos, não em lista achatada
**Escolhido:** `exclusion_groups`, cada grupo com seus próprios filtros combinados por E lógico.
**Descartado:** uma lista `not_in` por campo, achatando os dois blocos de `L38`.
**Porquê:** `L38` exclui `{ND 46.xx.76} × {841,842,843,844}` **e** `{ND 46.xx.77} ×
{841,842,843,844,846}`. Achatar produziria `{76,77} × {841,842,843,844,846}` — o que excluiria
`46.xx.76` com subfunção `846`, que o documento **não** manda excluir. Verificado: a união dos dois
grupos é exatamente o que `L43`, `L44`, `L46` e `L47` capturam; a versão achatada não é.

### D3 — Grafia literal preservada + padrão normalizado ao lado
**Escolhido:** todo código carrega `literal` (grafia exata do PDF) e `pattern` (dígitos
significativos, `x` como coringa, zeros à direita descartados).
**Descartado:** só a grafia literal (obrigaria o motor a reimplementar as convenções de escrita);
só o normalizado (apagaria a rastreabilidade e os erros do PDF, que precisam ficar visíveis).
**Porquê:** o IPC07 usa **três convenções** para o mesmo domínio — `1100.00.00` e `2111.00.2.0`
(natureza de receita), `3.1.00.00.00` e `3.1.00.00` (ND, 5 e 4 grupos), `4.6.00.00.00` e `46.xx.76`
(ND, na mesma célula de `L38`). Com `pattern`, `2111.00.20` (exclusão de `L11`) e `2111.00.2.0`
(critério de `L19`) normalizam ambos para `2111002`, e o `literal` prova de onde cada um veio.
**Limite:** onde o descarte à direita for ambíguo, ou o `literal` estiver grafado com erro,
`pattern` fica `null` e a regra vai para `review_required`. Não se adivinha.

### D4 — Contradição interna resolvida, com a página que sustenta a leitura
**Escolhido:** `provenance.reading.adopted_from_page` + literal divergente em `evidence.text`.
**Descartado:** marcar as 5 linhas como `review_required`; corrigir sem registro.
**Porquê:** em R1–R5 a contradição é **do próprio documento**, e uma das leituras é impossível —
`(VII + IX + X)` usa o TOTAL das receitas dentro de um subtotal de despesa. Mandar isso para
revisão humana seria terceirizar uma decisão que o documento já toma na p. 15. Mas corrigir sem
registrar violaria "PDF prevalece": o registro é o que torna a correção auditável.
**Não se aplica a B6:** ali nenhuma leitura era sustentada pelo documento, e o PO decidiu em
2026-09-03 pela seção REGRAS. B1, B3, B5 e B6 seguem decisões explícitas do PO, não inferência
documental.

### D5 — B3 pertence ao domínio PCASP, não ao ementário de receita
**Escolhido:** os oito padrões `2111/8111`, `2118/8118`, `2121/8121` e `2128/8128` usam
`field: conta_contabil`; as duas grafias do PDF são preservadas e normalizadas para o mesmo padrão.
**Descartado:** tratá-los como natureza de receita e aplicar candidatos do ementário.
**Porquê:** decisão do PO em 2026-08-27. A coluna do PDF não prevalece sobre o domínio explicitado
pelo PO. Como os padrões são do PCASP 2019 e não aparecem na tabela atual, recebem
`provenance.decision: B3`, não `review_required`.

### D6 — Exceção de domínio é categoria própria, distinta de erro
**Decidido pelo PO em 2026-09-03.**
**Escolhido:** códigos de faixa comprovadamente ausente da tabela (B2: categorias 7 e 8 da natureza
de receita; B4: ND fora do grupo 3.1) são reportados como **exceção declarada** e não levam a regra
a `review_required`.
**Descartado:** tratar como código inexistente (30 linhas iriam para revisão sem necessidade);
ignorar em silêncio.
**Porquê:** medido — `natureza-receita.md` tem **zero** códigos nas categorias 7 e 8, e
`natureza_despesa.md` tem 172 códigos **todos** do grupo 3.1. A lacuna é da tabela, não da regra: o
IPC07 é explícito nessas 30 linhas e o par "principal + intra" é sistemático. Confundir lacuna de
domínio com ambiguidade normativa levaria 30 linhas a revisão sem necessidade.

### D7 — O BO não tem policy de exclusão de intraorçamentárias
**Escolhido:** nenhuma policy de exclusão de intra em `ipc07.yaml`.
**Descartado:** replicar a policy do IPC04/IPC05 por simetria.
**Porquê:** o IPC07 **inclui** as intraorçamentárias: cada linha de receita soma explicitamente o
par principal + intra (`1100.00.00` e `7100.00.00`), e o item 14 (p. 6) manda apresentar o
detalhamento das intra em notas explicativas, não excluí-las. Copiar a policy do BP inverteria a
regra. É o exemplo mais claro de por que fatiar por documento: a "regra geral" de um IPC não vale
para o outro.

### D8 — PDF não é duplicado
**Escolhido:** `knowledge/sources/ipc07/metadata.yaml` referencia o PDF em `docs/referencia/ipc/`
por caminho + SHA-256.
**Descartado:** copiar o PDF para `knowledge/sources/ipc07/original.pdf`.
**Porquê:** dois locais para o mesmo binário criam a pergunta "qual é o original?". O hash dá a
garantia de integridade que a cópia daria, sem ambiguidade de fonte.

### D9 — Extração por geometria, sem detecção de tabela
**Escolhido:** `page.get_text("words")` do PyMuPDF + agrupamento por banda de coordenada (linha =
banda em `x`, coluna = banda em `y`, por causa da rotação de 90°).
**Descartado:** `find_tables()`, Camelot, Tabula, LlamaParse, Docling.
**Porquê:** medido — `find_tables()` devolveu nestes arquivos matrizes de até 26 colunas com ~90% de
células vazias, pior que a leitura linear; e a leitura linear não preserva a associação
célula→coluna nas pp. 8–13. A reconstrução por banda fecha as 69 linhas sem célula indeterminada.
O IPC07 tem camada de texto completa: OCR e parser pago não têm o que resolver.

### D10 — Índice gerado, nunca versionado à mão
**Escolhido:** `build_index.py` gera; `validate_rules.py` falha se estiver dessincronizado.
**Descartado:** índice editado junto com a regra.
**Porquê:** duas fontes para a mesma informação divergem. O índice é cache de leitura, e o validador
garante que ele não mente.

### D11 — `AGENTS.md` da raiz recebe seção, não reescrita
**Escolhido:** acrescentar "Regras contábeis canônicas" com o procedimento obrigatório; nenhuma
linha do contrato existente é alterada.
**Descartado:** substituir o `AGENTS.md`.
**Porquê:** o `AGENTS.md` atual é o contrato de processo OpenSpec e é referenciado por `CLAUDE.md`,
`openspec/AGENTS.md` e `openspec/config.yaml`. Sobrescrevê-lo apagaria os gates que esta change está
cumprindo.

### D12 — Uma change por IPC
**Escolhido:** esta change cobre só o IPC07; IPC04, IPC05, IPC06 e IPC08 ganham uma cada, sobre a
mesma capability `dca/base-canonica-regras`.
**Descartado:** a change única `knowledge-base-ipc`, que abrangia os cinco (fica em espera).
**Porquê:** as pendências não são compartilhadas — D7 mostra que uma "regra geral" de um IPC pode ser
o oposto no outro, e as decisões P1/P3/P4 do PO não incidem em nenhuma linha do BO. Com a change
única, o IPC07 só fecharia depois de resolver `<nas fontes aplicáveis>` do IPC06 e o atributo F/P do
IPC04, que não têm nada a ver com o Balanço Orçamentário.

### D13 — B1 preserva a conta histórica da família 531
**Escolhido:** manter `5.3.1.3.0.00.00` na fórmula do RPNP e registrar
`provenance.decision: B1`; a implementação inclui comentário adjacente sobre a descontinuação após
o PCASP 2019.
**Descartado:** remover o termo por simetria com RPP ou por ausência no PCASP atual.
**Porquê:** decisão do PO em 2026-08-27. A regra normativa usa o recorte histórico de 2019; uma
tabela atual não pode reescrever silenciosamente a fórmula daquela edição.

### D14 — Override de conta somente em L29 e L30
**Escolhido:** `line_account_override: true` substitui as contas padrão das colunas apenas em
`bo.quadro_principal.receitas.l29` e `.l30`.
**Descartado:** tornar o override comportamento geral para qualquer linha que declare conta.
**Porquê:** decisão expressa do PO em 2026-08-27. O schema aceita o campo, e a validação semântica
rejeita `true` em qualquer outro `rule_id`.

## Estrutura de diretórios

```text
knowledge/
├── README.md
├── sources/
│   ├── ipc07/ { metadata.yaml, extracted.md }
│   └── stn/   { metadata.yaml }
├── rules/bo/  { quadro_principal.yaml, rp_nao_processados.yaml, rp_processados.yaml }
├── policies/  { ipc07.yaml }
├── schemas/   { rule.schema.json, policy.schema.json, filter.schema.json,
│                column.schema.json, source.schema.json, document.schema.json }
└── indexes/   { rules_index.json, documents_index.json }
```

Um arquivo por quadro — 3 arquivos, alinhados 1:1 com os 3 quadros medidos. O arquivo não é
identidade; `rule_id` é.

### Estratégia de identificadores

```text
rule_id = bo.<quadro>.<grupo?>.<linha>
```

- `quadro` ∈ `quadro_principal | rp_nao_processados | rp_processados`
- `grupo` presente **só** no Quadro Principal, onde os blocos de receita e despesa têm numeração
  contínua mas semântica disjunta: `receitas` (`L1`–`L30`) e `despesas` (`L31`–`L51`)
- `linha` = rótulo do PDF em minúsculas

Exemplos reais: `bo.quadro_principal.receitas.l2` · `bo.quadro_principal.despesas.l48` ·
`bo.rp_nao_processados.l1` · `bo.rp_processados.l1`

Os quadros de RP **reiniciam** em `L1`, então o segmento de quadro é o que garante unicidade.
O rótulo `L-40` da p. 10 vira `l40`, com `L-40` preservado em `source.row` e `evidence` (R1).

### Estratégia de versionamento

- `version.edition` = `"2020-01"`; `valid_from` = `"2020-01-20"` (data de geração do PDF);
  `valid_until` = `null`, porque o IPC07 não declara fim de vigência.
- Edição futura do IPC07 entra como conjunto novo de regras; as atuais passam a `deprecated` com
  `valid_until` preenchido. Nada é sobrescrito.
- A resolução "qual regra vale no exercício X" é do repositório de regras (change futura). A regra
  não infere vigência.

## Arquivos criados / alterados

| Arquivo | Ação |
|---|---|
| `docs/source-analysis.md` | criado (Fase 1 — já entregue) |
| `docs/source-analysis-ipc07.md` | criado (Fase 1 do IPC07 — já entregue) |
| `docs/rule-model.md` | criar |
| `docs/architecture.md` | criar |
| `docs/contribution-guide.md` | criar |
| `knowledge/README.md` | criar |
| `knowledge/sources/ipc07/{metadata.yaml,extracted.md}` | criar (2) |
| `knowledge/sources/stn/metadata.yaml` | criar |
| `knowledge/schemas/{rule,policy,filter,column,source,document}.schema.json` | criar (6) |
| `knowledge/policies/ipc07.yaml` | criar |
| `knowledge/rules/bo/{quadro_principal,rp_nao_processados,rp_processados}.yaml` | criar (3) |
| `knowledge/indexes/{rules,documents}_index.json` | criar (gerados) |
| `scripts/{extract_ipc,load_stn_tables,validate_rules,build_index,check_sources}.py` | criar (5) |
| `tests/test_validate_rules.py` | criar |
| `tests/test_rules_bo.py` | criar |
| `tests/fixtures/` | criar |
| `pyproject.toml` | criar |
| `README.md` | alterar — seção apontando para `knowledge/` |
| `AGENTS.md` | alterar — **adicionar** seção "Regras contábeis canônicas" |
| `openspec/AGENTS.md` | alterar — tabela "Change ativa" |

## Pendências conhecidas

- **B6** resolvido pelo PO em 2026-09-03: `L27`–`L30` com as 4 colunas de receita, `L51` com
  `columns: []`. B1, B3 e B5 foram resolvidos em 2026-08-27. Consequência de schema: `columns`
  aceita lista vazia, e uma regra sem coluna não é erro.
- **B2 e B4** resolvidos pelo PO em 2026-09-03 como exceção declarada (D6). Completar as tabelas
  de `docs/contas-stn/` é escopo de outra change.
- `docs/rule-model.md` e `docs/architecture.md` só são escritos na fase IMPLEMENT: hoje
  duplicariam este design, e duplicata divergente é pior que ausência.
- O rule engine e o `RuleRepository` não entram nesta change. O modelo foi desenhado para que
  `repository.get(rule_id)` e `repository.find(quadro=..., account=...)` sejam implementáveis sem
  alterar o YAML — afirmação a ser provada por outra change, não por esta.
- Os enums são o mínimo do IPC07. Espera-se que as changes de IPC04/05/06/08 os estendam; se alguma
  precisar **alterar** semântica em vez de acrescentar, o schema volta para revisão.
