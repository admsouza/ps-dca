# Proposal — Regras canônicas da Demonstração dos Fluxos de Caixa (IPC 08)

**Status:** aprovada e arquivada em 2026-10-26 — YAML transcrito; apuração Python fora desta change
**Repositório:** `ps-dca`
**Capability:** `dca/demonstracao-fluxos-caixa` (nova)
**Anexo DCA:** `n/a` nesta change — a DFC não é `I-E` (I-E no SICONFI é despesa por função)
**Base normativa:** IPC 08 ed. 2020-01 (`docs/referencia/ipc/IPC08 - DFC atualizacoes final - 20200116.pdf`), 21 páginas, SHA-256 `fb04f03c2015ec61…`
**Fonte da verdade externa:** tabelas STN em `docs/contas-stn/`. Aceite desta change = YAML válido no contrato de BO/BF/BP/DVP, não espelho `tt/dca`.

## Why

A DFC ainda não tem base canônica. Sem YAML no contrato dos demais anexos, o programador implementaria direto do PDF paisagem rotacionado — 84 linhas em 4 quadros, 14 delas com listas de natureza quebradas em várias linhas físicas (`docs/source-analysis.md` §7). A associação célula→coluna não sobrevive à leitura linear.

## What Changes

- 84 regras em `knowledge/rules/dfc/`: Quadro Principal 36, Transferências 15, Pessoal por Função 29, Juros e Encargos 4.
- 5 policies em `knowledge/policies/ipc08.yaml` (itens 13–17 da p. 6).
- `knowledge/sources/ipc08/` com `metadata.yaml` (hash medido) e `extracted.md`. O PDF não é copiado.
- Exclusões do PDF entram como `filters` `not_in`. L16, L21 e L30 nascem sem `columns` (item 17).
- Literal do PDF preservado, inclusive N5 (`45.80.66`, `4.4..22.xx.xx`, `7.3.21.00.31.x`).

**Fora de escopo:** código Python (`app/`, CLI, pipeline, registry); schema e `validate_rules.py`; recorte por UG; espelho `tt/dca`; coringa de 5º nível = 2; `visao: consolidado`.

## Entradas e saídas

Esta change não expõe HTTP. As interfaces são arquivo e linha de comando:

| Interface | Entrada | Saída |
|---|---|---|
| `knowledge/rules/dfc/*.yaml` | transcrição do IPC 08 | 84 regras no schema `rule.json` |
| `python -m scripts.validate_rules knowledge` | a base | exit 0; DFC 36+15+29+4 |
| `python -m scripts.check_sources knowledge` | metadata | 5 documentos íntegros |

## Exemplo concreto

IPC 08 p. 7, L3 Impostos, Taxas e Contribuições de Melhoria: contas `(+) 6.2.1.2.0.00.00 (-) 6.2.1.3.0.00.00`, naturezas `1.1.xx.xx.xx` e `7.1.xx.xx.xx`. Folhas no `PCASP.md`: `621200000` RECEITA REALIZADA e prefixo `6213` das deduções. Ente/exercício/valor medido pertence à change de apuração.

## Critérios de aceite

- [x] 84 regras, `rule_id` `dfc.<quadro>.<grupo?>.l<n>`, duas colunas `exercicio_atual` e `exercicio_anterior`.
- [x] L1 = L2 − L12; L17 = L18 − L22; L26 = L27 − L31; L34 = L1 + L17 + L26; L36 = L34 + L35.
- [x] L35 declara `saldo: inicial` em `1.1.1.0.0.00.00`.
- [x] L16, L21 e L30 sem `columns`, `status: review_required`.
- [x] `jsonschema` de `rule.json` e `policy.json` aceita a base.
- [x] `python -m scripts.check_sources knowledge` — 5 documentos.
- [x] `python -m scripts.validate_rules knowledge` — exit 0; nenhum erro `dfc.*`.
- [x] Homologação estrutural contra ente real substituiu o espelho `tt/dca` (a DFC não é
      anexo publicado): `docs/entes-homologacao/porto-alegre/gabarito-dfc-2025.md`,
      43 identidades fechando em centavos.

## Casos de erro

| Situação | Comportamento esperado |
|---|---|
| Código do PDF ausente da tabela STN, sem coringa e fora de B2/B4 | `status: review_required`; `pattern` preenchido com a normalização; literal intacto |
| L16/L21/L30 | linha existe, sem `columns`; o ente adapta (item 17) |
| Grafia `45.80.66` / `4.4..22.xx.xx` | literal do PDF; pattern em dígitos; reason N5 |

## Restrições e riscos

- O PDF de 2020 cita PCASP 2019; a tabela do repo é outra edição. Prefixo que a folha não sustenta não é corrigido em silêncio.
- `validate_rules.py` não ganha enum IPC08: o default de `CAMPOS` já cobre natureza, função e subfunção.
- 14 linhas de lista longa exigiram leitura visual da página (PNG de conferência, não versionado).
- Função 28 / subfunções 841–844 aparecem na coluna Exclusões em L32 (p. 11) e L3 do quadro de juros (p. 16). Leitura adotada: filtro de inclusão, o mesmo de L14.

## Aprovação do PO

- [x] PO aprovou esta proposta em 2026-10-26 — **change de apuração liberada**
