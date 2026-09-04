# Design — Base canônica de regras contábeis a partir dos IPC 04–08

**Change:** `openspec/changes/knowledge-base-ipc/` · **Proposal aprovada pelo PO em:** _pendente_

> Este design é o entregável da **Fase 2** do trabalho de descoberta. Ele não pode ser
> implementado antes do gate de aprovação da proposal (`AGENTS.md` §2).

## Contexto

`docs/source-analysis.md` mediu o corpus: **309 linhas de regra** em **15 quadros** de 5
demonstrativos, com **13 tipos distintos de critério** (§4) e **7 divergências de grafia** (§6.2),
sendo três delas erros de digitação do próprio PDF. Das 7 ambiguidades documentais originais
(§6.1), as decisões do PO de 2026-08-27 resolveram 2 e estreitaram uma terceira — restam **5**
(§11.5).

O repositório também traz as **tabelas oficiais da STN** em `docs/contas-stn/` (§10): 6.119 contas
do PCASP com indicador Financeiro/Permanente, 4.506 naturezas de receita, 174 NDs, 119 pares
função/subfunção, 98 fontes de recursos. Elas não são fonte normativa — são **domínio de
validação** dos códigos que as regras citam.

Quatro restrições moldam o desenho:

1. **Não inventar.** O modelo tem de conseguir dizer "não sei" de forma estruturada — não pode
   forçar todo campo a ter valor.
2. **Duas edições convivem** (IPC06 2024-06, os outros 2020-01) e mais virão. Versionamento não é
   retrofit.
3. **O consumidor final é um agente de código**, que precisa implementar a regra sem reler o PDF.
   Isso empurra o modelo para explícito e verboso, não para compacto.
4. **A regra é independente da fonte de dados.** O mesmo critério chega com chave diferente do
   SICONFI e da PublicSoft; isso é serialização, não norma, e não pode vazar para o `rule_id`.

## Componentes afetados

Não há código neste repositório. Todos os componentes são novos.

| Componente | Papel na change |
|---|---|
| `knowledge/sources/<ipc>/` | metadados e markdown intermediário auditável por documento; os PDFs continuam em `docs/referencia/ipc/` |
| `knowledge/rules/<demonstrativo>/<quadro>.yaml` | regras canônicas, uma por linha de quadro |
| `knowledge/policies/<ipc>.yaml` | regras gerais de documento, referenciadas pelas regras de linha |
| `knowledge/bindings/field_bindings.yaml` | campo canônico de filtro -> chave por fonte de dados (SICONFI, PublicSoft) |
| `knowledge/schemas/*.json` | JSON Schema Draft 2020-12 de regra, policy, documento, filtro e fonte |
| `knowledge/indexes/*.json` | índice gerado; nunca editado à mão |
| `docs/contas-stn/*.md` | tabelas oficiais da STN — **lidas, nunca alteradas**; domínio de validação dos códigos |
| `scripts/extract_ipc.py` | extração PDF -> `extracted.md` (dev; não roda em CI) |
| `scripts/load_stn_tables.py` | leitura das tabelas de `docs/contas-stn/` para conjuntos de códigos válidos |
| `scripts/validate_rules.py` | validação completa; é o gate de CI |
| `scripts/build_index.py` | geração dos índices |
| `scripts/check_sources.py` | integridade SHA-256 dos PDFs e das tabelas da STN |
| `tests/` | testes de comportamento normativo por regra e testes do validador |
| `AGENTS.md` (raiz) | **seção nova** "Regras contábeis canônicas"; o contrato existente não muda |

## Fluxo da informação

```text
docs/referencia/ipc/*.pdf  (imutável, fonte normativa)
        │  scripts/extract_ipc.py  (manual, dev)
        ▼
knowledge/sources/<ipc>/extracted.md   +   metadata.yaml (sha256, páginas, edição)
        │  transcrição assistida + conferência visual das 14 linhas de risco
        ▼
knowledge/rules/**/*.yaml   +   knowledge/policies/*.yaml     ← FONTE EXECUTÁVEL
        │
        │  docs/contas-stn/*.md  ──→ scripts/load_stn_tables.py ──┐  domínio de validação
        │                                                          │  (códigos existentes)
        │  scripts/validate_rules.py  ←───────────────────────────┘
        │      (schema · IDs · refs · ciclos · fontes · status · códigos)
        │  scripts/build_index.py
        ▼
knowledge/indexes/rules_index.json
        ▼
(fora desta change) rule engine → API FastAPI → consumidores
```

## Contratos / interfaces

### Modelo de regra (formato canônico)

Exemplo **real**, transcrito do IPC07 p. 8, `L2` — a mesma linha que o item 23 do IPC07 usa como
exemplo da própria norma:

```yaml
rule_id: bo.quadro_principal.receitas.l2

demonstrativo:
  codigo: BO
  descricao: Balanço Orçamentário

quadro:
  codigo: QUADRO_PRINCIPAL
  descricao: Quadro Principal

linha:
  codigo: L2
  descricao: Impostos, Taxas e Contribuições de Melhoria
  nivel: 2          # apresentação: profundidade de indentação no demonstrativo
  ordem: 2          # apresentação: posição no quadro

policies:
  - ipc07.receita_liquida_de_deducoes

filters:
  - field: natureza_receita
    operator: in
    values:
      - literal: "1100.00.00"     # grafia exata do PDF
        prefix: "11"              # normalizado (ver D5)
      - literal: "7100.00.00"
        prefix: "71"

columns:
  previsao_inicial:
    label: Previsão Inicial (a)
    accounts:
      - { literal: "5.2.1.1.0.00.00", prefix: "5.2.1.1", sign: "+" }

  previsao_atualizada:
    label: Previsão Atualizada (b)
    accounts:
      - { literal: "5.2.1.1.0.00.00", prefix: "5.2.1.1", sign: "+" }
      - { literal: "5.2.1.2.0.00.00", prefix: "5.2.1.2", sign: "+" }

  receitas_realizadas:
    label: Receitas Realizadas (c)
    accounts:
      - { literal: "6.2.1.2.0.00.00", prefix: "6.2.1.2", sign: "+" }
      - { literal: "6.2.1.3.0.00.00", prefix: "6.2.1.3", sign: "+" }

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
  text: >
    L2 Impostos, Taxas e Contribuições de Melhoria — 1100.00.00; 7100.00.00

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
review:
  required: true
```

### Variações do modelo, com o caso real que as exige

| Construção | Caso real | Forma canônica |
|---|---|---|
| Linha composta por outras linhas | IPC07 `L1 = (L2+...+L9)` | `calculation.references: [{rule: <rule_id>, sign: "+"}, ...]` no nível da regra; a regra **não** tem `columns.accounts` próprias |
| Subtração de linhas | IPC05 `L19 = (L1 – L9)` | mesmas `references`, com `sign: "-"` |
| Guarda condicional | IPC07 `L25 Déficit`, "somente quando deficitário" | `calculation.condition: { when: result_positive }` + `evidence.text` com a frase literal |
| Momento do saldo | IPC06 `L30`, IPC08 `L35` | `accounts[].moment: saldo_inicial \| saldo_final \| movimento_periodo` (default `movimento_periodo`) |
| Lado do lançamento | IPC06 `L27` credor / `L60` devedor, mesmas contas | `filters: [{ field: movimento, operator: equals, values: [{literal: credor}] }]` |
| Atributo Financeiro / Permanente | IPC04 quadro 2, `L2` atributo (F) | `filters: [{ field: financeiro_permanente, operator: equals, values: [{ literal: "1" }] }]`; chave por fonte de dados vem de `field_bindings.yaml` (D7, D12) |
| Fonte de recurso por vinculação | IPC06 `L4` Educação | `filters: [{ field: fonte_recurso, operator: in, values: [{literal: "540"}, ... {literal: "599"}] }]` com `provenance.extraction_method: derived` (D11) |
| Função e subfunção | IPC07 `28.841` vs IPC08 `Função 28` + `Subfunção 841` | dois filtros separados, `funcao` e `subfuncao`, com `literal` preservando a grafia do PDF |
| Exclusões | IPC04 `L4`, 9 contas intra | `columns.<col>.exclude: [{literal, prefix}]`, ou `filters` com `not_in` quando a exclusão é de natureza |
| Placeholder do documento | IPC06 `<nas fontes aplicáveis>` | `unresolved: [{ kind, literal, reason }]` — impede `status: validated` |
| Regra paramétrica | IPC04 quadro do superávit/déficit por fonte | uma regra com `parametric: { by: fonte_recurso }`; a cardinalidade vem do ente, não da norma |

### Modelo de policy

```yaml
policy_id: ipc04.exclusao_intraorcamentaria
descricao: >
  Exclusão das contas de nível intraorçamentário (5º nível = 2), inclusive os detalhamentos
  eventualmente criados pelo ente além dos previstos no PCASP.
aplica_a:
  demonstrativo: BP
  escopo: consolidado_do_ente     # não se aplica a órgão ou unidade isolada (IPC04 item 8)
efeito:
  field: nivel_5_conta
  operator: not_equals
  values: [{ literal: "2" }]
source:
  document: IPC04
  document_version: "2020-01"
  page: 7
  section: INSTRUÇÕES PARA PREENCHIMENTO DO BALANÇO PATRIMONIAL
  item: "9"
evidence:
  page: 7
  text: >
    o ente deverá deduzir as contas de nível intraorçamentário (5º nível = 2) eventualmente criadas
status: validated
```

As exclusões nominais que a matriz do PDF lista continuam **dentro** da regra de linha, como
exemplificação da policy — não como lista fechada. Isso é o que o IPC04 item 9 e o IPC05 item 16
literalmente dizem.

### Enums fechados

Definidos no schema; nada é adicionado sem um caso real no corpus.

```text
filters[].field      account | natureza_receita | natureza_despesa | funcao | subfuncao |
                     fonte_recurso | financeiro_permanente | movimento | nivel_5_conta

filters[].operator   in | not_in | equals | not_equals

accounts[].sign      + | -
accounts[].moment    movimento_periodo | saldo_inicial | saldo_final

calculation.condition.when   result_positive | result_negative

status               draft | extracted | review_required | validated | deprecated

provenance.extraction_method   automated | assisted | derived | manual

unresolved[].kind    conta_de_controle | conta_sob_demanda | saldo_a_executar |
                     fonte_nao_confirmada | grafia_do_documento
```

Comparado à versão anterior deste design: `atributo_conta` saiu e `financeiro_permanente` entrou
(D7); `atributo_pcasp` e `fonte_recurso` saíram de `unresolved[].kind` porque as decisões do PO
resolveram P3 e a maior parte de P4; `fonte_nao_confirmada` entrou para cobrir apenas R1 e R2;
`derived` entrou em `extraction_method` para marcar as faixas de fonte de D11.

### Binding de campo por fonte de dados

```yaml
# knowledge/bindings/field_bindings.yaml
financeiro_permanente:
  descricao: >
    Indicador Financeiro (1) / Permanente (2) do registro. Decisão do PO de 2026-08-27.
    O PCASP é domínio de validação, não origem do valor: 924 das 2.565 contas de classe 1 e 2
    têm indicador "Financeiro/Permanente" e portanto aceitam ambos.
  valores:
    "1": F
    "2": P
  chaves:
    siconfi: financeiro_permanente
    publicsoft: financeiroPermanente
  validacao:
    tabela: docs/contas-stn/PCASP.md
    coluna: INDICADOR DO SUPERÁVIT FINANCEIRO
    regra:
      Financeiro: ["1"]
      Permanente: ["2"]
      Financeiro/Permanente: ["1", "2"]
      "-": []
```

Operadores **deliberadamente ausentes**: `starts_with`, `contains`, `between`, comparadores
numéricos, `is_null`. O corpus não usa nenhum deles — o casamento por prefixo já está no campo
`prefix` do valor, não no operador. Adicionar quando aparecer um caso real (ver D5).

### Contrato do validador

```text
$ python scripts/validate_rules.py

✓ YAML valid                      20 arquivos (15 de regra + 5 de policy)
✓ Schema valid                    309 regras · N policies
✓ Fontes íntegras                 5 PDFs + 7 tabelas STN · sha256 conferido
✓ 0 IDs duplicados
✓ 0 referências inválidas
✓ 0 dependências circulares
✓ 0 regras sem source
✓ 0 páginas fora do documento
✓ 0 códigos inexistentes           conferidos contra docs/contas-stn/
✓ Índice sincronizado

Regras por demonstrativo   BP 57 · DVP 19 · BF 80 · BO 69 · DFC 84   (total 309)
Regras por status          validated 0 · extracted 0 · review_required 0 · draft 309
exit 0
```

Em erro, uma entrada por problema, sempre com `rule_id` + `arquivo:linha`:

```text
ERROR bo.quadro_principal.receitas.l2
  Invalid reference: bo.quadro_principal.receitas.l99
  Source: knowledge/rules/bo/quadro_principal.yaml:143

exit 1
```

## Impacto

| Eixo | Impacto |
|---|---|
| Banco / migration | **nenhum**. YAML + Git é a fonte canônica. Projeção em PostgreSQL fica para uma change futura, e só no sentido Git -> Postgres (`openspec/project.md`) |
| Cache | nenhum |
| Filas / worker | nenhum |
| APIs externas | nenhum. `scripts/extract_ipc.py` lê arquivo local; nenhuma chamada HTTP |
| Regressão | nenhuma — não há comportamento existente. `AGENTS.md` e `openspec/` só recebem adição |
| Dependências novas | runtime: `pyyaml`, `jsonschema`, `pydantic`. dev: `pymupdf`, `pytest`, `ruff` |
| CI | três comandos novos, todos determinísticos e offline |

## Decisões

### D1 — Granularidade: uma regra por linha, com mapa de colunas
**Escolhido:** regra por linha, `columns` dentro da regra.
**Descartado:** regra por célula (linha × coluna).
**Porquê:** o IPC07 item 23 define explicitamente que a coluna diz **de onde vem o valor** e a
linha diz **como filtrar**. Regra por célula geraria ~900 arquivos com os filtros de linha
duplicados em cada um, e a divergência entre células da mesma linha passaria a ser possível — o
que a norma não permite. Medido: 309 regras contra ~900.

### D2 — PDFs não são duplicados no repositório
**Escolhido:** `knowledge/sources/<ipc>/metadata.yaml` referencia o PDF em
`docs/referencia/ipc/` por caminho + SHA-256.
**Descartado:** copiar os 5 PDFs para `knowledge/sources/<ipc>/original.pdf` (a estrutura pedida
originalmente).
**Porquê:** dois locais para o mesmo binário criam a pergunta "qual é o original?" — exatamente o
problema que a estrutura queria evitar. O hash dá a garantia de integridade que a cópia daria, sem
~5 MB duplicados e sem ambiguidade de fonte. Custo: um nível de indireção em `metadata.yaml`.

### D3 — YAML canônico, sem banco de dados
**Escolhido:** YAML versionado em Git como fonte da verdade.
**Descartado:** PostgreSQL desde o início; base vetorial.
**Porquê:** `openspec/project.md` e o item 25 do escopo já fixam Git/YAML como fonte e Postgres
como projeção. Nesta fase o que se precisa é diff revisável, blame e PR — nada disso um banco dá
melhor. Sem RAG: RAG responde pergunta, não executa regra.

### D4 — Ambiguidade é dado, não exceção
**Escolhido:** `unresolved[]` estruturado + `status: review_required`, e a invariante de schema de
que `unresolved` não vazio impede `validated`.
**Descartado:** deixar o campo vazio; deixar a explicação só em comentário YAML.
**Porquê:** 3 das pendências que restam são estruturais — `P2` saldo a executar, `P5` conta de
controle, `P6` contas sob demanda (`source-analysis.md` §11.5) — e vão sobreviver a esta change.
Campo vazio é indistinguível de "esqueci de preencher"; comentário não é validável. Com
`unresolved` estruturado, o validador consegue **impedir** que uma regra incompleta seja marcada
como pronta.

### D5 — Grafia literal preservada + prefixo normalizado ao lado
**Escolhido:** todo código carrega `literal` (grafia exata do PDF) e `prefix` (dígitos
significativos, sem pontuação, com os grupos zerados/`xx` à direita descartados).
**Descartado:** guardar só a grafia literal (obrigaria o motor a reimplementar 7 convenções
distintas de escrita); guardar só o normalizado (perderia a rastreabilidade e apagaria os erros de
digitação do PDF, que precisam ficar visíveis).
**Porquê:** resolve N1–N4 de `source-analysis.md` §6.2 de forma auditável: `1100.00.00` (IPC07) e
`1.1.xx.xx.xx` (IPC08) normalizam ambos para `prefix: "11"`, e o `literal` prova de onde cada um
veio. O validador confere que `prefix` é derivação legítima de `literal`.
**Limite conhecido:** onde descartar grupos à direita for ambíguo, ou onde o `literal` estiver
grafado com erro (N5), `prefix` fica `null` e a regra vai para `review_required`. Não se
adivinha.

### D6 — Policies separadas das regras de linha
**Escolhido:** `knowledge/policies/<ipc>.yaml`, referenciadas por `policies: [policy_id]`.
**Descartado:** replicar a exclusão de intra dentro de cada uma das 76 regras de BP e DVP.
**Porquê:** o IPC04 item 9 diz que a lista de exclusões da matriz é **exemplificativa** e a regra
real é estrutural (5º nível = 2, "inclusive as eventualmente criadas"). Replicar transformaria
uma regra aberta em 76 listas fechadas — mudaria o significado da norma, o que é proibido.

### D7 — Atributo F/P é propriedade do registro, não da conta
**Escolhido:** filtro `field: financeiro_permanente` com valores `1` (F) e `2` (P), lidos do
registro do fato; `PCASP.md` entra como **domínio de validação**, não como origem do valor.
**Descartado:** derivar F/P da conta contábil; trazer uma tabela de atributos de conhecimento
geral de contabilidade pública.
**Porquê:** decisão do PO (2026-08-27) e confirmada pela medição: das 2.565 contas de classe 1 e
2 do `PCASP.md`, **924 são `Financeiro/Permanente`** — ambíguas no nível da conta. Derivar da
conta produziria valor errado em 36% dos casos. Preencher de memória seria o "conhecimento externo
sem marcação" que o escopo proíbe.
**Validação que isso habilita:** conta `Financeiro` só aceita `1`; `Permanente` só aceita `2`;
`Financeiro/Permanente` aceita ambos; `-` (classes 3 a 8, e 181 contas de passivo) não participa
do quadro F/P. Divergência é erro de dado, não de regra.

### D8 — Extração com PyMuPDF, sem detecção de tabela
**Escolhido:** `page.get_text()` linear + conferência visual das 14 linhas de risco.
**Descartado:** `find_tables()` do PyMuPDF, Camelot, Tabula, LlamaParse, Docling.
**Porquê:** medido em `source-analysis.md` §7 — `find_tables()` devolveu matrizes de até 26
colunas com ~90% de células vazias nesses arquivos, pior que a leitura linear. Os 5 PDFs têm
camada de texto completa, então OCR e parser pago não têm o que resolver. `pymupdf` fica em grupo
de dev: a extração é manual e não roda em CI.

### D9 — Índice gerado, nunca versionado à mão
**Escolhido:** `build_index.py` gera; `validate_rules.py` falha se o índice estiver dessincronizado.
**Descartado:** índice editado junto com a regra.
**Porquê:** duas fontes para a mesma informação divergem. O índice é cache de leitura, e o
validador é quem garante que ele não mente.

### D10 — `AGENTS.md` da raiz recebe seção, não reescrita
**Escolhido:** acrescentar "Regras contábeis canônicas" com o procedimento obrigatório de
implementação; nenhuma linha do contrato existente é alterada.
**Descartado:** substituir o `AGENTS.md` pelo modelo genérico proposto no escopo.
**Porquê:** o `AGENTS.md` atual é o contrato de processo OpenSpec do repositório e é referenciado
por `CLAUDE.md`, `openspec/AGENTS.md` e `openspec/config.yaml`. Sobrescrevê-lo apagaria os gates
que estão exatamente sendo cumpridos por esta change.

### D11 — Fonte de recurso resolvida por igualdade de nomenclatura, com as exceções declaradas
**Escolhido:** as 11 linhas de vinculação do IPC06 recebem faixas de fonte de
`docs/contas-stn/fonte-recursos.md`; 9 delas por **igualdade de nome literal** entre o rótulo da
linha e a nomenclatura da fonte. As 2 sem igualdade (`L7`/`L40` e `L10`/`L43`) ficam
`review_required`.
**Descartado:** deixar as 38 linhas com `<nas fontes aplicáveis>` todas `review_required`;
distribuir as 98 fontes por julgamento.
**Porquê:** decisão do PO (2026-08-27). Nas 9 linhas resolvidas a correspondência é verificável
sem interpretação — fonte 800 é literalmente "Recursos Vinculados ao RPPS - Fundo em Capitalização
(Plano Previdenciário)", igual ao rótulo de `L12`. Nas 2 restantes não há igualdade: a fonte 804
("Demais Recursos Previdenciários") não é citada por nenhum documento como pertencente a `L7`, e
as fontes 860–869 são nomeadas "Extraorçamentários", o que colidiria com o filtro próprio
`<fontes extraorçamentárias>` de `L27`/`L60` e contaria o mesmo recurso duas vezes.
**Registro:** cada faixa carrega `provenance.extraction_method: derived` e o critério de derivação
por escrito. Derivação declarada é auditável; derivação implícita não.

### D12 — Chave da fonte de dados fica em um arquivo de binding, não na regra
**Escolhido:** `knowledge/bindings/field_bindings.yaml` mapeia campo canônico -> chave por fonte
de dados (`siconfi: financeiro_permanente`, `publicsoft: financeiroPermanente`).
**Descartado:** repetir os dois nomes de chave em cada regra que usa o campo; criar um `rule_id`
por fonte de dados.
**Porquê:** a diferença é de serialização da fonte, não de norma. A regra canônica tem de
sobreviver à entrada de uma terceira fonte de dados sem ser reescrita, e um `rule_id` por fonte
duplicaria 309 regras por nada. Um arquivo, uma linha por campo.

### D13 — Todo código citado é conferido contra a tabela oficial da STN
**Escolhido:** `validate_rules.py` confere cada `literal` de conta, natureza de receita, natureza
de despesa, função, subfunção e fonte contra `docs/contas-stn/`. Código ausente da tabela vira
`review_required` com o candidato mais próximo **anotado em `review.reason`, não aplicado**.
**Descartado:** confiar na transcrição; corrigir automaticamente pelo candidato mais próximo.
**Porquê:** transforma N5 de "risco conhecido" em "erro detectado". As tabelas somam 6.119 contas,
4.506 naturezas de receita, 174 NDs, 119 pares função/subfunção e 98 fontes — cobertura suficiente
para que `45.80.66`, `4.4..22.xx.xx` e `1.1.1.0.0.00.0` sejam pegos pela máquina em vez de por
leitura. Correção automática está descartada porque o PDF prevalece sobre a tabela até haver
decisão registrada (`AGENTS.md` §4).

## Estrutura de diretórios

```text
knowledge/
├── README.md
├── sources/
│   ├── ipc04/ { metadata.yaml, extracted.md }
│   ├── ipc05/ …  ipc06/ …  ipc07/ …  ipc08/ …
├── rules/
│   ├── bp/  { quadro_principal.yaml, ativos_passivos.yaml,
│   │          contas_compensacao.yaml, superavit_deficit.yaml }
│   ├── dvp/ { quadro_principal.yaml }
│   ├── bf/  { quadro_principal.yaml, quadro_anexo.yaml }
│   ├── bo/  { quadro_principal.yaml, rp_nao_processados.yaml, rp_processados.yaml }
│   └── dfc/ { quadro_principal.yaml, transferencias.yaml,
│              desembolsos_funcao.yaml, juros_encargos.yaml }
├── policies/ { ipc04.yaml, ipc05.yaml, ipc06.yaml, ipc07.yaml, ipc08.yaml }
├── bindings/ { field_bindings.yaml }
├── schemas/  { rule.schema.json, policy.schema.json, document.schema.json,
│               filter.schema.json, source.schema.json }
└── indexes/  { rules_index.json, documents_index.json }
```

`knowledge/sources/stn/metadata.yaml` registra nome, contagem de registros e SHA-256 das 7 tabelas
de `docs/contas-stn/`, pelo mesmo motivo dos PDFs (D2): validação de código contra tabela que
mudou em silêncio é pior que validação nenhuma.

Um arquivo por quadro: 15 arquivos de regra, alinhados 1:1 com os 15 quadros medidos. O arquivo
não é identidade — `rule_id` é (D1 do escopo: IDs não dependem de posição física).

### Estratégia de identificadores

```text
rule_id = <demonstrativo>.<quadro>.<grupo?>.<linha>
```

- `demonstrativo` ∈ `bp | dvp | bf | bo | dfc`
- `quadro`: slug do quadro (`quadro_principal`, `rp_nao_processados`, `contas_compensacao`, …)
- `grupo`: presente só quando o quadro tem blocos disjuntos que reiniciam a semântica das linhas
  (BO principal: `receitas` / `despesas`; BF principal: `ingressos` / `dispendios`)
- `linha`: rótulo do PDF em minúsculas (`l2`, `l40`)

Exemplos reais: `bo.quadro_principal.receitas.l2` · `bp.ativos_passivos.l7` ·
`dfc.juros_encargos.l1` · `bf.quadro_principal.dispendios.l60`

O rótulo `L-40` do IPC07 p. 10 (erro de digitação, N6) vira `l40`, com o literal `L-40` preservado
em `evidence` e `source.row`.

### Estratégia de versionamento

- `version.edition` = edição do documento de origem (`"2020-01"`, `"2024-06"`).
- `version.valid_from` = data de publicação do PDF; `valid_until: null` porque nenhum documento
  declara fim de vigência.
- Edição nova de um IPC **não** sobrescreve: entra como conjunto novo de regras, e as antigas
  passam a `deprecated` com `valid_until` preenchido pela data de início da nova.
- A resolução "qual regra vale no exercício X" é responsabilidade do repositório de regras (change
  futura). A regra não infere vigência.

## Arquivos criados / alterados

| Arquivo | Ação |
|---|---|
| `docs/source-analysis.md` | criado (Fase 1, já entregue) |
| `docs/architecture.md` | criar |
| `docs/rule-model.md` | criar |
| `docs/contribution-guide.md` | criar |
| `knowledge/README.md` | criar |
| `knowledge/sources/ipc0{4,5,6,7,8}/metadata.yaml` | criar (5) |
| `knowledge/sources/ipc0{4,5,6,7,8}/extracted.md` | criar (5) |
| `knowledge/sources/stn/metadata.yaml` | criar — hashes e contagens das 7 tabelas da STN |
| `knowledge/schemas/{rule,policy,document,filter,source}.schema.json` | criar (5) |
| `knowledge/policies/ipc0{4,5,6,7,8}.yaml` | criar (5) |
| `knowledge/bindings/field_bindings.yaml` | criar |
| `knowledge/rules/bp/{quadro_principal,ativos_passivos,contas_compensacao,superavit_deficit}.yaml` | criar (4) |
| `knowledge/rules/dvp/quadro_principal.yaml` | criar |
| `knowledge/rules/bf/{quadro_principal,quadro_anexo}.yaml` | criar (2) |
| `knowledge/rules/bo/{quadro_principal,rp_nao_processados,rp_processados}.yaml` | criar (3) |
| `knowledge/rules/dfc/{quadro_principal,transferencias,desembolsos_funcao,juros_encargos}.yaml` | criar (4) |
| `knowledge/indexes/{rules,documents}_index.json` | criar (gerados) |
| `scripts/{extract_ipc,load_stn_tables,validate_rules,build_index,check_sources}.py` | criar (5) |
| `tests/test_validate_rules.py` | criar |
| `tests/test_rules_normativas.py` | criar |
| `tests/fixtures/` | criar |
| `pyproject.toml` | criar |
| `README.md` | alterar — seção apontando para `knowledge/` |
| `AGENTS.md` | alterar — **adicionar** seção "Regras contábeis canônicas" |
| `openspec/AGENTS.md` | alterar — tabela "Change ativa" |

## Pendências conhecidas

- Restam **5** pendências (`source-analysis.md` §11.5): `P2` saldo a executar, `P5` conta de
  controle, `P6` contas sob demanda, `R1` fonte 804, `R2` fontes 860–869. As regras afetadas ficam
  `review_required`. `P2`, `P5` e `P6` dependem de convenção do ente e provavelmente **não** se
  resolvem nesta change; `R1` e `R2` dependem de uma confirmação pontual.
- A ponte IPC -> anexo DCA não existe e não é inventada aqui.
- `docs/architecture.md` e `docs/rule-model.md` só são escritos na fase IMPLEMENT: hoje
  duplicariam este design, e duplicata divergente é pior que ausência.
- O rule engine e o `RuleRepository` não entram nesta change. O modelo foi desenhado para que
  `repository.get(rule_id)` e `repository.find(demonstrative=..., account=...)` sejam
  implementáveis sem alterar o YAML — mas isso é afirmação a ser provada por outra change, não
  por esta.
