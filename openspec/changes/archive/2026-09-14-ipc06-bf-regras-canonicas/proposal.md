# Proposal — Base canônica de regras do Balanço Financeiro (IPC 06)

**Status:** aprovada pelo PO
**Repositório:** `ps-dca`
**Capability:** `dca/base-canonica-regras` (existente)
**Anexo DCA:** `DCA-Anexo I-D` (Balanço Financeiro)
**Base normativa:** MCASP · IPC 06 — Metodologia para Elaboração do Balanço Financeiro,
edição 2024-06 (`docs/referencia/ipc/IPC06 - Balanço Financeiro_2024- 2.pdf`,
19 páginas, sha256 `e663ffe5ee0376fd03e7cd340e79a9f6a4a8e265e9e4863098f7f1773dc1d097`)
**Fonte de domínio das fontes de recursos:** Anexo I da Portaria STN nº 710/2021, atualizado até
a Portaria STN/MF nº 2.897/2025 — `docs/contas-stn/fontes-recursos-stn-2026.xlsx`
(sha256 `2996eb9890283aa6e5ae658bb92f9eb2eddd60a2209d59b7fbf80659ec9594cf`), cujos **cabeçalhos de
bloco** são a evidência do agrupamento por subgrupo. Os códigos em si já estão em
`docs/contas-stn/fonte-recursos.md` (100 registros, cobre os 98 do bloco 500–999).
**Fonte da verdade externa:** n/a nesta change (sem ingestão XBRL)

## Why

O Balanço Financeiro é o próximo anexo da DCA e hoje não existe nenhuma regra canônica dele no
repositório. Sem a base, o processamento do BF teria de nascer com o mapeamento conta→linha
embutido no código — exatamente o que a base canônica do IPC 07 eliminou. Além disso, o IPC 06
introduz duas dimensões que o BO não tem (**fonte ou destinação de recursos** e **saldo de conta
patrimonial em data**); decidir isso dentro do código significaria decidir sem rastreabilidade
até a página do documento.

## What Changes

- `knowledge/sources/ipc06/metadata.yaml` com arquivo, páginas, edição e SHA-256 do PDF.
- `knowledge/sources/ipc06/extracted.md` gerado por `scripts/extract_ipc.py` (parametrizado por IPC).
- `knowledge/rules/bf/quadro_principal.yaml` — **66 linhas** (L1–L66), duas colunas de valor.
- `knowledge/rules/bf/quadro_anexo.yaml` — **14 linhas** (L1–L14), seis colunas de valor.
- `knowledge/policies/ipc06.yaml` — regras gerais dos itens 27, 30, 33, 37 e 38.
- `knowledge/schemas/rule.json` estendido: `field: fonte_recurso`, `saldo` (inicial/final) e
  `movimento` (credor/devedor) nas colunas; `decision` aceita os códigos `F*` desta change.
- `scripts/validate_rules.py` e `scripts/build_index.py` passam a cobrir o demonstrativo `BF`.

**Fora de escopo:** apuração do BF (motor, service, rota, cache, job) — isso é trabalho
posterior, equivalente à F1 do BO; o quadro de detalhamento por fonte criado livremente pelo ente
(item 22) além dos subgrupos dos itens 23 e 24; notas explicativas (item 26).

## Entradas e saídas

| Interface | Entrada | Saída |
|---|---|---|
| `python -m scripts.validate_rules` | `knowledge/` | contagem por quadro e por status; exit `0`/`1` |
| `python -m scripts.build_index` | `knowledge/rules/**` | `knowledge/indexes/rules_index.json` com `BO` + `BF` |
| `python -m scripts.check_sources` | `knowledge/sources/*/metadata.yaml` | `2 documento(s)` íntegros; exit `0`/`1` |

## Exemplo concreto

| Ente | Exercício | Anexo | Célula | Valor esperado |
|---|---|---|---|---|
| 2507507 — João Pessoa/PB | 2025 | I-D | `bf.quadro_principal.ingressos.l33` (TOTAL VI) | igual a `bf.quadro_principal.dispendios.l66` (TOTAL XII), em centavos |
| 2507507 — João Pessoa/PB | 2025 | I-D | `bf.quadro_anexo.l14` coluna `(c)` | `(a) - (b)` da mesma linha, em centavos |

A conferência de valor 1:1 contra `tt/dca` pertence à change de apuração; nesta change o aceite é
a **base**, e a identidade acima é o critério de coerência interna do mapeamento.

## Critérios de aceite

- [ ] 80 regras carregadas: `quadro_principal 66 · quadro_anexo 14`.
- [ ] `review_required` em exatamente **6** linhas (L22, L23, L28, L55, L56, L61), por F1 e F2.
- [ ] Toda regra cita `source.page` entre 1 e 19, seção e `row` do documento.
- [ ] Toda linha composta fecha: as referências de L1, L3, L11, L15, L21, L24, L29, L33, L34, L36,
      L44, L48, L54, L57, L62 e L66 apontam para `rule_id` existentes, sem ciclo.
- [ ] `python -m pytest` e `python -m ruff check .` limpos; nenhuma regra do BO alterada
      (regressão bit a bit no `rules_index.json` da parte `BO`).

## Casos de erro

| Situação | Comportamento esperado |
|---|---|
| Regra do BF declara `field` fora do conjunto do IPC 06 | validação reporta campo não suportado, exit `1` |
| Regra do BF declara coluna fora do conjunto do quadro | validação reporta coluna inválida, exit `1` |
| Regra com conta patrimonial sem declarar `saldo` | validação reporta saldo não declarado, exit `1` |
| SHA-256 do PDF do IPC 06 divergente | `check_sources` reporta esperado × obtido, exit `1` |
| `L33` e `L66` com conjuntos de referência que não se equilibram estruturalmente | validação reporta, exit `1` |

## Decisões do PO

| # | Assunto | Literal do IPC 06 | Opções |
|---|---|---|---|
| **F1** | Contas de controle de `L22`, `L23`, `L55`, `L56` | `<conta de controle>` (pp. 11–12, itens 31–33) | **Decidido em 2026-09-14:** `review_required` com `review.candidate` nas classes 7/8 |
| **F2** | `L28` e `L61` "Outros Recebimentos/Pagamentos Extraorçamentários" | `<contas sob demanda>` (item 29: "cabendo a cada ente adaptá-los") | **Decidido em 2026-09-14:** `review_required` |
| ~~**F3**~~ | ~~Tradução de "nas fontes aplicáveis"~~ | — | **Decidido pelo PO em 2026-09-14:** faixas do Anexo I, conforme a tabela abaixo |
| **F4** | `L27`/`L60` Depósitos Restituíveis | `2.1.8.8 + 2.2.8.8 <movimento credor>` / `<movimento devedor>` | **Decidido em 2026-09-14:** novo campo `movimento` na coluna |
| **F5** | `L33 TOTAL (VI)` impressa na p. 12 depois dos dispêndios | ordem física do PDF | **Decidido em 2026-09-14:** `ordem` normativa dos ingressos, literal preservado em `evidence` |

## F3 — Subgrupo do IPC 06 × faixa de fonte do Anexo I

Os cabeçalhos de bloco do `fontes-recursos-stn-2026.xlsx` mapeiam 1:1 nos subgrupos dos itens 23 e
24 do IPC 06. A DCA é entregue por estados, DF e municípios — só o bloco 500–999 se aplica.

| Linha (ingresso / dispêndio) | Subgrupo IPC 06 | Bloco do Anexo I | Faixa |
|---|---|---|---|
| L2 / L35 | Recursos Não Vinculados | RECURSOS LIVRES (NÃO VINCULADOS) | `500`–`503` |
| L4 / L37 | Educação | RECURSOS VINCULADOS À EDUCAÇÃO | `540`–`599` |
| L5 / L38 | Saúde | RECURSOS VINCULADOS À SAÚDE | `600`–`659` |
| L6 / L39 | Assistência Social | RECURSOS VINCULADOS À ASSISTÊNCIA SOCIAL | `660`–`669` |
| L7 / L40 | Previdência Social (exceto RPPS) | RECURSOS VINCULADOS À PREVIDÊNCIA SOCIAL, menos o RPPS | `803`, `804` |
| L8 / L41 | Demais Vinculações Decorrentes de Transferências | idem | `700`–`749` |
| L9 / L42 | Demais Vinculações Legais | idem | `750`–`799` |
| L10 / L43 | Outras Vinculações | OUTRAS VINCULAÇÕES | `880`–`899` |
| L12 / L45 | RPPS — Fundo em Capitalização | RECURSOS VINCULADOS À PREVIDÊNCIA SOCIAL | `800` |
| L13 / L46 | RPPS — Fundo em Repartição | idem | `801` |
| L14 / L47 | RPPS — Taxa de Administração | idem | `802` |
| L27 / L60 | "fontes extraorçamentárias" do literal | RECURSOS EXTRAORÇAMENTÁRIOS | `860`–`869` |

`803 Sistema de Proteção Social dos Militares` e `804 Demais Recursos Previdenciários` compõem
L7/L40 exatamente como o item 25 descreve — SPSM e benefícios previdenciários mantidos pelo ente
fora do RPPS.

A fonte escriturada traz **1 dígito de prefixo de exercício** (`1` corrente, `2` anteriores,
`9` condicionados) antes do código principal de 3 dígitos. O filtro `fonte_recurso` opera sobre o
**código principal**; o prefixo não separa subgrupo e não entra na regra.

## Restrições e riscos

- O IPC 06 **não** traz coluna de exclusões nem classificação funcional — nenhum
  `exclusion_groups` deve aparecer na base do BF.
- O quadro de detalhamento por fonte é aberto (item 22): a base cobre os subgrupos normativos dos
  itens 23–24, não a lista de fontes de cada ente.
- O bloco 000–499 do Anexo I é da União, que não entrega DCA — fora do domínio destas regras.
- O `rule_id` do BF usa o prefixo `bf.`; o requisito de identificador da capability hoje está
  redigido só com `bo.` e precisa ser generalizado (delta `MODIFIED`).

## Aprovação do PO

- [x] PO aprovou esta proposta em 2026-09-14 — **gate para a fase PLAN/ARCH**
- [x] PO decidiu F1, F2, F3, F4 e F5 em 2026-09-14
