# Proposal — Regras canônicas do Balanço Orçamentário (IPC 07)

**Status:** proposta
**Repositório:** `ps-dca`
**Capability:** `dca/base-canonica-regras` (nova)
**Anexo DCA:** `n/a` nesta change — ver "Fora de escopo"
**Base normativa:** IPC 07 — Metodologia para Elaboração do Balanço Orçamentário,
`docs/referencia/ipc/IPC07 - BO atualizacoes - 20200117.pdf`, edição 2020-01, 17 páginas,
SHA-256 `51b9eeddcfb523ae…`; tabelas oficiais da STN em `docs/contas-stn/` como domínio de
validação
**Fonte da verdade externa:** não envolve importação XBRL nesta change

**Análise de descoberta (concluída):**
[`docs/source-analysis-ipc07.md`](../../../docs/source-analysis-ipc07.md) — matriz reconstruída por
geometria, 69 linhas, 6 bloqueios/lacunas isolados, 11 ambiguidades resolvidas por evidência
interna; B1, B3 e B5 decididos pelo PO em 2026-08-27.
Contexto dos 5 IPCs em [`docs/source-analysis.md`](../../../docs/source-analysis.md).

> **Escopo desta change: somente o IPC 07.** A change `knowledge-base-ipc`, que abrangia os cinco
> IPCs de uma vez, fica **em espera** — ela é sucedida por esta e pelas equivalentes de IPC04,
> IPC05, IPC06 e IPC08, uma por documento. Motivo: o IPC07 é o primeiro a ser implementado, e
> fatiar por documento faz cada spec fechar com o PO sem carregar as pendências dos outros
> quatro.

## Why

O Balanço Orçamentário é o primeiro demonstrativo a ser implementado, e sua regra hoje existe
apenas como **matriz em PDF paisagem rotacionada** — 69 linhas em 3 quadros, com 4 a 6 colunas de
valor cada. Sem representação canônica:

- a associação célula→coluna **não sobrevive** à leitura linear do PDF (medido: a extração de texto
  embaralha as bandas; só a reconstrução geométrica fecha as 69 linhas). Quem implementar direto do
  PDF vai errar coluna sem perceber;
- a regra vira `if natureza in [...]` sem rastro da página, tornando silenciosa a divergência
  código × normativo que o `AGENTS.md` §4 proíbe;
- os **6 bloqueios/lacunas** medidos (`source-analysis-ipc07.md` §3) exigiam classificação
  explícita. B1, B3 e B5 foram decididos pelo PO em 2026-08-27; B6, B2 e B4 em 2026-09-03;
- as **11 ambiguidades internas** do documento (`L-40`, `(-VIII)`, `(VII + IX + X)`,
  `(L31 + L35 + L39 + -)`, `28.842, - 28.844`) seriam "corrigidas" ou copiadas erradas, sem registro
  de qual leitura foi adotada.

## What Changes

- Passa a existir `knowledge/rules/bo/` com **69 regras YAML**, uma por linha de quadro, cada uma
  com o mapa de colunas da linha.
- Toda regra carrega rastreabilidade obrigatória até documento, edição, página, seção, quadro e
  linha. Regra sem `source` é rejeitada na validação.
- O IPC07 continua em `docs/referencia/ipc/` como fonte imutável;
  `knowledge/sources/ipc07/` guarda `metadata.yaml` (SHA-256, páginas, edição) e `extracted.md`.
  O PDF **não** é duplicado.
- Passa a existir **JSON Schema (Draft 2020-12)** para regra, filtro, coluna e fonte, com os enums
  restritos ao que o IPC07 usa — extensíveis pelas changes dos outros IPCs.
- Passa a existir `scripts/validate_rules.py` (schema, IDs duplicados, referências quebradas,
  ciclos, página fora do documento, código inexistente), `scripts/build_index.py` e
  `scripts/check_sources.py`.
- Todo código citado é classificado no domínio correto e conferido contra `docs/contas-stn/`.
  Exceções históricas do PCASP 2019 decididas pelo PO são preservadas sem substituição silenciosa.
- As 11 ambiguidades internas (R1–R11) são aplicadas com o `literal` original preservado em
  `evidence` e a leitura adotada registrada em `provenance`.
- Todas as 69 linhas nascem `extracted`: **nenhuma** regra fica `review_required` por bloqueio
  documental. B1, B3, B5 e B6 seguem as decisões registradas do PO. Por B6, `L27`–`L30` recebem as
  4 colunas de receita e `L51` nasce com `columns: []` — linha de filtro e rótulo, sem coluna de
  valor.
- `AGENTS.md` da raiz ganha a seção "Regras contábeis canônicas". O contrato de processo existente
  **não** é alterado.

**Fora de escopo:**

- IPC04, IPC05, IPC06 e IPC08 — uma change por documento.
- Ligação IPC07 → anexo DCA (`I-AB`, `I-C`, …). O IPC07 não menciona a DCA nem o layout SICONFI;
  essa ponte é outra change.
- Rule engine, API FastAPI, rotas `/rules`, banco, cache, worker. Esta change entrega a camada
  normativa e o formato que a API vai consumir — nada de HTTP.
- A seção "ESTRUTURA DO BALANÇO ORÇAMENTÁRIO" (pp. 14–17) como regra executável: é layout de
  publicação. Entra apenas como metadado de apresentação (rótulo, ordem) e como **evidência** para
  R2, R3, R4 e B6.

## Entradas e saídas

Esta change não expõe interface HTTP. As interfaces são de linha de comando e de arquivo:

| Interface | Entrada | Saída |
|---|---|---|
| `python scripts/validate_rules.py` | `knowledge/rules/bo/*.yaml`, `knowledge/schemas/*.json`, `knowledge/sources/ipc07/metadata.yaml`, `docs/contas-stn/*.md` | relatório em stdout com contagem por quadro e por status; exit `0` se nenhuma regra inválida, `1` caso contrário |
| `python scripts/build_index.py` | `knowledge/rules/bo/*.yaml` | `knowledge/indexes/rules_index.json`, `documents_index.json` |
| `python scripts/check_sources.py` | `knowledge/sources/ipc07/metadata.yaml` + PDF + tabelas STN | confirmação de SHA-256; exit `1` em divergência |
| Arquivo de regra | — | YAML validável contra `rule.schema.json`, com `rule_id` legível e estável |

## Exemplo concreto

Não há exemplo com `cod_ibge` e valor em reais: esta change não calcula nada, e inventar um valor
esperado violaria a regra "não inventar". O exemplo é **documental** — a linha que o próprio item 23
do IPC07 usa para explicar a mecânica matricial:

| Documento | Edição | Página | Quadro | Linha | `rule_id` |
|---|---|---|---|---|---|
| IPC07 | 2020-01 | 8 | Quadro Principal | `L2` — Impostos, Taxas e Contribuições de Melhoria | `bo.quadro_principal.receitas.l2` |

Critério que a regra tem de reproduzir, conforme a p. 8:

- filtro de linha: `natureza_receita in ("1100.00.00", "7100.00.00")`
- coluna `previsao_inicial` (a): `5.2.1.1.0.00.00`
- coluna `previsao_atualizada` (b): `5.2.1.1.0.00.00` **+** `5.2.1.2.0.00.00`
- coluna `receitas_realizadas` (c): `6.2.1.2.0.00.00` **+** `6.2.1.3.0.00.00`
- coluna `saldo` (d): `c − b`

Segundo exemplo, para a construção de sinais explícitos — p. 12, quadro de RP Não Processados,
coluna "Inscritos — Em Exercícios Anteriores (a)":

`5.3.1.2.0.00.00 (+) · 5.3.1.3.0.00.00 (+) · 5.3.1.6.0.00.00 (+) · 6.3.1.6.0.00.00 (−)`

O exemplo com ente, exercício e valor medido entra na change que ligar as regras ao anexo DCA e ao
espelho `tt/dca`.

## Critérios de aceite

- [ ] **69** regras em `knowledge/rules/bo/`, distribuídas como
      `quadro_principal 51 · rp_nao_processados 9 · rp_processados 9`.
- [ ] **0** regras sem `source.document`, `source.document_version` e `source.page`.
- [ ] **0** `rule_id` duplicados; **0** referências a `rule_id` inexistente; **0** ciclos.
- [ ] **0** regras inválidas contra `rule.schema.json`.
- [ ] **0** regras `review_required`: B1, B3, B5 e B6 estão decididos. `L27`–`L30` têm as 4
      colunas de receita com `provenance.decision: B6`; `L51` tem `columns: []` com a mesma
      marcação. Regra que nasça `review_required` por bloqueio documental é erro de consistência.
- [ ] As **11** ambiguidades R1–R11 aplicadas, com `evidence.text` preservando o literal do PDF e
      `provenance` registrando a leitura adotada. **0** correções sem registro.
- [ ] **41** contas/padrões PCASP classificados: **32** conferidos na tabela atual e **9** exceções
      históricas decididas pelo PO — B1 (`5.3.1.3.0.00.00`) e os 8 padrões de B3.
- [ ] **7 de 7** pares função/subfunção conferidos em `funcao-subfuncao.md`.
- [ ] Os códigos não validáveis por lacuna de tabela (B2: 13 naturezas intra; B4: 13 NDs fora do
      grupo 3.1) reportados pelo validador como **exceção declarada**, distinta de erro.
- [ ] SHA-256 do IPC07 e das tabelas da STN conferem (`check_sources.py` exit `0`).
- [ ] `python -m pytest` verde e `python -m ruff check .` limpo.
- [ ] Teste de leitura cega: dado apenas um `rule_id`, obtêm-se quadro, linha, filtros, colunas com
      contas e sinais, cálculo, dependências e página — **sem abrir o PDF**.

Aceite de espelho 1:1 contra `tt/dca` **não se aplica**: nada é calculado nesta change.

## Casos de erro

| Situação | Comportamento esperado |
|---|---|
| YAML sintaticamente inválido | reporta arquivo e linha; exit `1` |
| Regra sem `source` | erro de schema (`required`); exit `1` |
| `rule_id` duplicado | erro com os dois caminhos; exit `1` |
| `calculation.references` aponta para `rule_id` inexistente | erro com o `rule_id` órfão e `arquivo:linha`; exit `1` |
| Ciclo `A → B → A` | erro com o caminho do ciclo; exit `1` |
| `source.page` fora de 1..17 | erro; exit `1` |
| Operador ou campo de filtro fora do enum | erro de schema; exit `1` |
| Código inexistente na tabela oficial, sem `review_required` | erro; exit `1` |
| Regra de bloqueio marcada `validated` | erro de consistência; exit `1` |
| SHA-256 do PDF ou de tabela da STN divergente | reporta esperado × obtido; exit `1` |

## Restrições e riscos

- **Não inventar** é restrição dura. Os candidatos de natureza antes levantados para B3 foram
  descartados pela decisão do PO: os códigos são padrões de conta PCASP e o literal do IPC07 deve
  ser preservado.
- **Vigência:** o IPC07 é de 2020-01 e declara PCASP 2019; o `PCASP.md` do repositório é atual
  (traz contas de LC 212/2025). Por decisão do PO, B1 e B3 são exceções históricas do PCASP 2019.
  A implementação deve documentar esse recorte e não apagar os padrões ausentes da tabela atual.
- **Extração:** as pp. 8–13 são paisagem rotacionada 90°. O extrator precisa reconstruir por
  geometria (linha = banda em `x`, coluna = banda em `y`); leitura linear não fecha.
- Risco de escopo: embutir o mapeamento IPC07 → anexo DCA. Fora de escopo por falta de respaldo
  documental no IPC07.
- Dependências novas: runtime `pyyaml`, `jsonschema`; dev `pymupdf`, `pytest`, `ruff`. Nenhuma
  paga. `pydantic` foi retirado em 2026-09-03: a validação é JSON Schema Draft 2020-12 via
  `jsonschema`, e esta change não expõe interface HTTP nem modela objeto de runtime.

## Aprovação do PO

- [x] PO aprovou esta proposta em **2026-09-04** — Jackson S. da Silva (PO). Gate da fase SPEC fechado; PLAN/ARCH liberada.
      Aprovação cobre a proposta e o delta `specs/dca/base-canonica-regras/spec.md`.

### Decisões já tomadas pelo PO (2026-08-27)

| # | Assunto | Decisão | Vale para o IPC07? |
|---|---|---|---|
| P1 | exclusões entre parênteses no IPC05 | parênteses ≡ sem parênteses | não — IPC07 não tem esse padrão |
| P3 | atributo Financeiro/Permanente | vem do registro: `financeiro_permanente` (SICONFI) / `financeiroPermanente` (PublicSoft), `1`=F, `2`=P | não — o BO não usa atributo F/P |
| P4 | fonte/destinação de recurso | usar `docs/contas-stn/fonte-recursos.md` | não — o BO não filtra por fonte |
| — | ligação IPC → anexo DCA | outra change | sim — fora de escopo aqui |
| B1 | `5.3.1.3.0.00.00` ausente do PCASP atual | manter a leitura pelo prefixo `531` e exigir comentário no código sobre a descontinuação após 2019 | sim — resolvido |
| B3 | códigos de refinanciamento | são padrões de contas PCASP; não são naturezas de receita e não serão substituídos pelos candidatos do ementário | sim — resolvido |
| B5 | conta declarada na linha | substitui as contas da coluna exclusivamente em `L29` e `L30` | sim — resolvido |
| B6 | colunas de `L27`–`L30` e `L51` (decidido em 2026-09-03) | `L27`–`L30` têm as **4** colunas de receita; `L51` **não tem coluna** de valor — permanece como filtro e rótulo, fora do total | sim — resolvido |
| B2 | naturezas intra ausentes de `natureza-receita.md` (2026-09-03) | **exceção declarada**: as tabelas do repositório não são completadas nesta change; o validador reporta os 13 códigos como exceção, não como erro | sim — resolvido |
| B4 | ND fora do grupo `3.1` ausentes de `natureza_despesa.md` (2026-09-03) | **exceção declarada**, mesma regra de B2 — 13 códigos | sim — resolvido |

As decisões P1, P3 e P4 não incidem sobre o IPC07: o Balanço Orçamentário não usa atributo
F/P, não filtra por fonte de recurso e não tem a coluna de exclusões ambígua do IPC05. Elas ficam
registradas para as changes de IPC04, IPC05 e IPC06.

### Decisões que esta change precisa — bloqueiam a regra

**Nenhuma.** O último bloqueio de regra (B6) foi decidido pelo PO em 2026-09-03: a seção REGRAS
prevalece sobre a ESTRUTURA em `L27`–`L30`, que têm as 4 colunas de receita, e `L51` fica sem
coluna de valor. Detalhamento medido em
[`docs/source-analysis-ipc07.md`](../../../docs/source-analysis-ipc07.md) §3.

### Lacunas de domínio — decididas como exceção declarada (2026-09-03)

| # | Lacuna medida | Códigos | Linhas | Decisão do PO |
|---|---|---|---|---|
| **B2** | `natureza-receita.md` tem categorias `1` (4.269), `2` (234), `9` (1). Categorias **7 e 8 têm zero códigos** | 13 | 13 | exceção declarada; não trazer o Ementário completo nesta change |
| **B4** | `natureza_despesa.md` tem 172 códigos, **todos** do grupo `3.1` | 13 | 17 | exceção declarada; não trazer a tabela completa de ND nesta change |

O validador reporta esses 26 códigos como **exceção declarada** — categoria própria, distinta de
erro — sem levar as 30 linhas afetadas a `review_required` e sem alterar as tabelas de
`docs/contas-stn/`. Completar as tabelas fica para uma change de domínio própria.

### Caminho que não depende de decisão

**As 69 linhas** podem ser transcritas de imediato, e nada mais depende de decisão do PO: B1, B3,
B5, B6, B2 e B4 estão todos decididos.

`L24`, `L25` e `L26` entram nessa lista porque a regra é inequívoca e B3 foi resolvido como padrão
de conta PCASP. Não há mais pendência propagada de `L19`–`L23` por B3.
