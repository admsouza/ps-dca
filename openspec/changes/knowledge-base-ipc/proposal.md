# Proposal — Base canônica de regras contábeis a partir dos IPC 04–08

**Status:** proposta
**Repositório:** `ps-dca`
**Capability:** `dca/base-canonica-regras` (nova)
**Anexo DCA:** `n/a` nesta change — ver "Fora de escopo"
**Base normativa:** IPC 04 (BP) · IPC 05 (DVP) · IPC 06 (BF) · IPC 07 (BO) · IPC 08 (DFC),
em `docs/referencia/ipc/`; tabelas oficiais da STN em `docs/contas-stn/` (PCASP, natureza de
receita, natureza de despesa, função/subfunção, fonte de recursos, complemento de fonte,
poder/órgão)
**Fonte da verdade externa:** não envolve importação XBRL nesta change
**Análise de descoberta:** [`docs/source-analysis.md`](../../../docs/source-analysis.md) (Fase 1,
concluída) · [`docs/source-analysis-ipc07.md`](../../../docs/source-analysis-ipc07.md) (IPC07 —
matriz reconstruída por geometria, 6 bloqueios e 11 ambiguidades resolvidas)

## Why

O cálculo dos anexos da DCA depende de regras que hoje existem apenas como **matriz em PDF**.
São **309 linhas de regra** distribuídas em **15 quadros** de 5 demonstrativos (contagem medida,
`source-analysis.md` §3). Sem uma representação estruturada:

- cada anexo reabre os mesmos PDFs e reinterpreta as mesmas matrizes — o RREO e o RGF já pagaram
  esse custo e a divergência entre projetos irmãos é conhecida;
- a regra vira `if natureza in [...]` espalhado no código, sem rastro de qual página do IPC a
  originou, o que torna a divergência código × normativo **silenciosa** — exatamente o que o
  `AGENTS.md` §4 proíbe;
- a atualização de um IPC (o IPC06 já está na edição 2024 enquanto os outros quatro são de 2020)
  não tem como ser propagada de forma auditável;
- as **7 ambiguidades reais** identificadas na descoberta (`source-analysis.md` §6.1) hoje seriam
  resolvidas por chute de quem implementa, em vez de decisão do PO registrada — 2 já foram
  resolvidas e 1 estreitada por decisão datada (§11), e as **5 restantes** precisam ficar
  declaradas em algum lugar que não seja a cabeça de quem escreveu o código.

## What Changes

- Passa a existir uma **base canônica versionada em YAML** sob `knowledge/rules/`, uma regra por
  linha de quadro, com o mapa de colunas da linha.
- Toda regra carrega **rastreabilidade obrigatória** até documento, edição, página, seção, quadro
  e linha; regra sem `source` é rejeitada na validação.
- Os PDFs continuam em `docs/referencia/ipc/` como fonte imutável; `knowledge/sources/<ipc>/`
  guarda `metadata.yaml` (inclusive SHA-256 do PDF) e `extracted.md`. Os PDFs **não** são
  duplicados.
- Passa a existir **JSON Schema (Draft 2020-12)** para regra, documento, filtro e fonte, e um
  validador `scripts/validate_rules.py` que checa schema, IDs duplicados, referências quebradas,
  ciclos de dependência e integridade do PDF de origem.
- Passa a existir `knowledge/indexes/rules_index.json` para localização de regra por `rule_id`
  sem varrer os YAMLs.
- Ambiguidade documental vira `status: review_required` com o motivo declarado — **nunca** uma
  interpretação escolhida em silêncio.
- Todo código citado nas regras (conta, natureza de receita, natureza de despesa, função,
  subfunção, fonte) passa a ser **conferido contra a tabela oficial da STN** em
  `docs/contas-stn/`. Código que não existir na tabela é erro de digitação do PDF e vira
  `review_required`, com o candidato correto anotado e **não aplicado**.
- Passa a existir `knowledge/bindings/field_bindings.yaml`, mapeando cada campo canônico de filtro
  para a chave correspondente em cada fonte de dados (SICONFI, PublicSoft). O `rule_id` fica
  independente da fonte; a tradução de chave é um só arquivo.
- `AGENTS.md` da raiz ganha uma seção nova ("Regras contábeis canônicas") com o procedimento
  obrigatório para implementar uma regra. O contrato de processo existente **não** é alterado.

**Fora de escopo:**

- Ligação IPC -> anexo DCA (`I-AB`, `I-C`, ..., `I-HI`). Nenhum dos 5 PDFs menciona a DCA ou o
  layout SICONFI; essa ponte é outra change de spec.
- Rule engine, API FastAPI, rotas `/rules`, banco, cache, worker. Esta change entrega a **camada
  normativa** e o formato que a API vai consumir depois — nada de HTTP.
- Os 16 "Quadros Anexos" do IPC05: o item 21 do próprio IPC05 declara que são sugestões, não
  norma. Não geram regra.
- RAG / busca semântica.

## Entradas e saídas

Esta change não expõe interface HTTP. As interfaces são de linha de comando e de arquivo:

| Interface | Entrada | Saída |
|---|---|---|
| `python scripts/validate_rules.py` | `knowledge/rules/**/*.yaml`, `knowledge/schemas/*.json`, `knowledge/sources/*/metadata.yaml` | relatório em stdout com contagem por status; exit `0` se nenhuma regra inválida, `1` caso contrário |
| `python scripts/build_index.py` | `knowledge/rules/**/*.yaml` | `knowledge/indexes/rules_index.json`, `knowledge/indexes/documents_index.json` |
| `python scripts/check_sources.py` | `knowledge/sources/*/metadata.yaml` + PDFs em `docs/referencia/ipc/` | confirmação de SHA-256 por documento; exit `1` em divergência |
| Arquivo de regra | — | YAML validável contra `rule.schema.json`, com `rule_id` legível e estável |

## Exemplo concreto

Não há exemplo com `cod_ibge`/valor em reais nesta change: ela não calcula nada, e inventar um
valor esperado violaria a regra "não inventar". O exemplo concreto é **documental** — a regra
citada literalmente pelo IPC07 item 23 como exemplo da própria norma:

| Documento | Edição | Página | Quadro | Linha | `rule_id` |
|---|---|---|---|---|---|
| IPC07 | 2020-01 | 8 | Quadro Principal | `L2` — Impostos, Taxas e Contribuições de Melhoria | `bo.quadro_principal.receitas.l2` |

Critério que a regra tem de reproduzir, conforme o texto da p. 8:

- filtro de linha: `natureza_receita in ("1100.00.00", "7100.00.00")`
- coluna `previsao_inicial` (a): `5.2.1.1.0.00.00`
- coluna `previsao_atualizada` (b): `5.2.1.1.0.00.00` + `5.2.1.2.0.00.00`
- coluna `receitas_realizadas` (c): `6.2.1.2.0.00.00` + `6.2.1.3.0.00.00`
- coluna `saldo` (d): `c - b`

O exemplo com ente, exercício e valor medido entra na change que ligar as regras ao anexo DCA e
ao espelho `tt/dca`.

## Critérios de aceite

- [ ] **309** regras de linha presentes em `knowledge/rules/`, distribuídas exatamente como a
      tabela de `source-analysis.md` §3 (BP 57, DVP 19, BF 80, BO 69, DFC 84).
- [ ] **0** regras sem `source.document`, `source.document_version` e `source.page`.
- [ ] **0** `rule_id` duplicados.
- [ ] **0** referências a `rule_id` inexistente e **0** ciclos de dependência.
- [ ] **0** regras inválidas contra `rule.schema.json`.
- [ ] Toda regra que dependa de uma das **5** pendências abertas de `source-analysis.md` §11.5
      (P2, P5, P6, R1, R2) está `status: review_required` com `review.reason` preenchido —
      **nenhuma** delas `validated`.
- [ ] **0** códigos de conta, natureza, função, subfunção ou fonte inexistentes nas tabelas de
      `docs/contas-stn/`, exceto os marcados `review_required` por erro de digitação do PDF.
- [ ] IPC04 quadro 2 (`L2`,`L3`,`L5`,`L6`) computável pelo campo `financeiro_permanente`, com o
      `PCASP.md` como domínio de validação (§11.2 da análise).
- [ ] As 9 linhas de vinculação do IPC06 com correspondência de nome literal resolvidas por faixa
      de fonte (§11.3); apenas `L7`/`L40` e `L10`/`L43` permanecem `review_required`.
- [ ] SHA-256 dos 5 PDFs em `knowledge/sources/*/metadata.yaml` confere com os arquivos em
      `docs/referencia/ipc/` (`scripts/check_sources.py` exit `0`).
- [ ] `python -m pytest` verde e `python -m ruff check .` limpo.
- [ ] Teste de leitura cega: dado apenas um `rule_id`, é possível obter demonstrativo, quadro,
      linha, filtros, colunas, cálculo, dependências e a página do PDF **sem abrir o PDF**.

Aceite de espelho 1:1 contra `tt/dca` **não se aplica** a esta change: nada é calculado aqui.
Ele passa a valer na change que consumir estas regras.

## Casos de erro

| Situação | Comportamento esperado |
|---|---|
| YAML sintaticamente inválido | `validate_rules.py` reporta arquivo e linha; exit `1` |
| Regra sem `source` | erro de schema (`required`); exit `1` |
| `rule_id` duplicado em dois arquivos | erro com os dois caminhos; exit `1` |
| `calculation.references` aponta para `rule_id` inexistente | erro com o `rule_id` órfão e o arquivo:linha de origem; exit `1` |
| Ciclo `A -> B -> A` nas dependências | erro com o caminho do ciclo; exit `1` |
| `source.page` fora do intervalo de páginas do documento declarado em `metadata.yaml` | erro; exit `1` |
| Operador de filtro fora do enum | erro de schema; exit `1` |
| SHA-256 do PDF divergente do registrado | `check_sources.py` reporta o documento; exit `1` |
| Regra com placeholder não resolvido (`<nas fontes aplicáveis>`) marcada `validated` | erro de consistência; exit `1` |

## Restrições e riscos

- **Não inventar** é restrição dura: após as decisões do PO restam **5** pendências documentais
  (`source-analysis.md` §11.5) e 7 divergências de grafia (§6.2), incluindo **erros de digitação
  do próprio PDF** (`45.80.66`, `4.4..22.xx.xx`, `1.1.1.0.0.00.0`, `L-40`). Nenhuma é corrigida em
  silêncio; todas nascem `review_required` com o texto literal em `evidence`.
- **Duas edições convivem** (IPC06 de 2024, os outros de 2020). Versionamento por edição é
  requisito desde a primeira regra, não retrofit.
- Risco de extração: 14 linhas do IPC08 têm listas de natureza quebradas em várias linhas
  físicas, onde a extração linear não recupera a associação célula -> coluna
  (`source-analysis.md` §7). Essas nascem `extracted` + `review.required: true` e exigem
  conferência visual.
- Risco de escopo: a tentação de já embutir o mapeamento IPC -> anexo DCA. Está fora de escopo
  justamente porque não tem respaldo documental nos 5 PDFs.
- Dependências novas de runtime: `pyyaml`, `jsonschema`, `pydantic`. `pymupdf` fica em grupo de
  dev (só a extração usa). Nenhuma dependência paga.

## Aprovação do PO

- [ ] PO aprovou esta proposta em ______ — **gate para a fase PLAN/ARCH**

### Decisões do PO — respondidas em 2026-08-27

| # | Pergunta | Decisão |
|---|---|---|
| 1 | **P1 (IPC05)** — nota de rodapé da coluna "Exclusões" ausente no PDF; metade das exclusões entre parênteses | Tratar parênteses e não-parênteses como **equivalentes**. Grafia original preservada em `evidence`; a equivalência fica registrada como decisão, não como leitura do documento. |
| 2 | **P3 (IPC04)** — atributo F/P das contas | O atributo vem do **registro do fato**: chave `financeiro_permanente` (SICONFI) / `financeiroPermanente` (PublicSoft), `1` = F, `2` = P. O `PCASP.md` entra como **domínio de validação** (924 contas de ativo/passivo são `Financeiro/Permanente`, ambíguas no nível da conta). |
| 3 | **P4/P7 (IPC06/IPC04)** — fonte/destinação de recurso | Usar `docs/contas-stn/fonte-recursos.md`. Correspondência por igualdade de nomenclatura resolve 9 das 11 linhas de vinculação; `L7`/`L40` e `L10`/`L43` seguem `review_required` (ressalvas R1 e R2 em §11.3 da análise). |
| 4 | Ligar IPC a anexo DCA | **Outra change.** Confirmado. |

Detalhamento medido de cada decisão em
[`docs/source-analysis.md`](../../../docs/source-analysis.md) §10–§11.

### Pendências que seguem abertas (não bloqueiam esta change)

`P2` saldo a executar · `P5` conta de controle · `P6` contas sob demanda · `R1` fonte 804 ·
`R2` fontes 860–869. As regras afetadas nascem `review_required` com o motivo declarado.

### Decisões pendentes específicas do IPC07 (primeiro a ser implementado)

Detalhamento medido em
[`docs/source-analysis-ipc07.md`](../../../docs/source-analysis-ipc07.md) §3.

| # | Bloqueio | Linhas | Trava a regra? |
|---|---|---|---|
| B3 | códigos de refinanciamento `2111.00.2.0`, `2118.01.6.0`, `2121.00.2.0`, `2128.01.6.0` não existem na tabela de natureza de receita, em nenhuma grafia | `L11`, `L19`, `L20`, `L22`, `L23` — propaga para `L17`, `L18`, `L21`, `L24`, `L25`, `L26` | **sim** |
| B1 | `5.3.1.3.0.00.00` não existe no PCASP e o quadro simétrico de RP Processados não tem termo equivalente | as 9 linhas do quadro de RP Não Processados | **sim** |
| B5 | `L29`/`L30` declaram **conta contábil** na coluna de natureza; exige semântica de override não declarada no documento | `L29`, `L30` (decisão estrutural — reaparece em IPC04 e IPC06) | **sim** |
| B6 | quais colunas se aplicam a `L27`–`L30` e a `L51`; REGRAS e ESTRUTURA do próprio IPC07 divergem | `L27`, `L28`, `L29`, `L30`, `L51` | **sim** |
| B2 | categorias 7 e 8 (intraorçamentárias) têm **zero** códigos em `natureza-receita.md` | 17 linhas | não — só a validação |
| B4 | `natureza_despesa.md` cobre apenas o grupo 3.1 (172 códigos, todos `31`) | 17 linhas | não — só a validação |

Efeito no IPC07: **19** das 69 linhas em `review_required` no cenário mínimo (só B1/B3/B5/B6);
**42** se B2 e B4 também bloquearem. As outras **50** podem ser transcritas de imediato.
