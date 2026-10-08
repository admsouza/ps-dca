# Proposal — BP emitido isolado ou consolidado

**Status:** arquivada (2026-10-08)
**Repositório:** `ps-dca` (front: `front-declaracoes`, change `dca-bp-visao-consolidado`)
**Capability:** `dca/balanco-patrimonial` (existente)
**Anexo DCA:** `DCA-Anexo I-AB`
**Revê:** `bp-espelho-iab` (2026-10-07) — as exclusões intra-OFSS voltam às regras, mas só na visão
consolidada; o espelho do `I-AB` continua sendo o padrão.

## Why

A coluna **Exclusões** do IPC 04 (`docs/referencia/ipc/IPC04 - BP atualizacao - 20200117.pdf`, p. 7–10)
existe para a **consolidação** das unidades gestoras do ente: elimina os saldos intra-OFSS (5º nível = 2).
O próprio IPC 04, item 8, diz que no levantamento de órgão ou unidade específica as operações intra
**não** são excluídas (policy `ipc04.exclusao_intra_so_no_consolidado`). A change `bp-espelho-iab` tirou as
exclusões para bater com o `I-AB` declarado; o PO quer as duas emissões disponíveis (2026-10-08):

- **Isolado (padrão):** sem exclusões. É o que se apura hoje e bate 1:1 com o `I-AB` declarado.
- **Consolidado:** com as exclusões da coluna do IPC 04.

O usuário escolhe a visão ao consultar, **sem reprocessar**.

Medição de Cuitegi (`2505204`) 2025, MSC de encerramento (2026-10-07, antes de `bp-espelho-iab`):

| Linha | Isolado (= `I-AB`) | Consolidado (IPC 04) |
|---|---|---|
| `L1` ATIVO | 76.314.331,92 | 47.083.540,63 |
| `L15` PASSIVO E PL | 76.314.331,92 | 49.088.262,32 |
| `L32` PL | −45.644.857,64 | −42.467.656,79 |
| `L1 − L15` | 0,00 | −2.004.721,69 |

O desequilíbrio do consolidado é do dado do ente (intra registrado só de um lado) e é **achado, não ajuste**.

## What Changes

- Regras do Quadro Principal (`knowledge/rules/bp/quadro_principal.yaml`): as 20 exclusões intra do IPC 04
  voltam como `filters` marcados `visao: consolidado`. A `L34` usa `2.3.2.1.2.00.00` no lugar do
  `2.3.2.0.2.00.00` do PDF, que não existe no PCASP (PO 2026-10-08).
- Um processamento produz as duas visões; o cache do BP guarda as duas.
- `GET /dca/BP?visao=isolado|consolidado` escolhe a visão servida; padrão `isolado`.
- Front: seletor **Isolado | Consolidado** na página do BP, trocando a leitura sem novo job.

**Fora de escopo:** BO, BF e demais anexos; quadros F/P, Compensação e Superávit (o IPC 04 só tem coluna de
exclusões no Quadro Principal); a policy do item 9 (intra de 5º nível criada pelo ente) continua não executada.

## Entradas e saídas

- **Entrada:** `GET /dca/BP?id_ente=2505204&anReferencia=2025&visao=consolidado`.
- **Saída:** mesmo corpo de hoje, com `visao: "consolidado"`, `matriz` da visão pedida e
  `diagnostico.equilibrio` da visão pedida.
- **Erros:** `visao` fora de `isolado|consolidado` → `422`; `visao` em anexo que não é BP → `422`;
  cache do BP anterior a esta change sem a visão consolidada → `409` "reprocesse o BP para obter a visão
  consolidada".

## Critérios de aceite

- [x] Cuitegi 2025, `visao=isolado`: igual à planilha `SICONFI_DCA_2831_ANUAL_1.xls` (40/40 linhas do
      Quadro Principal, 5/5 do F/P, equilíbrio 0,00) — regressão bit a bit.
- [x] Cuitegi 2025, `visao=consolidado`: `L1` 47.083.540,63, `L15` 49.088.262,32, `L32` −42.467.656,79,
      equilíbrio −2.004.721,69 (valores de 2026-10-07; remedir e registrar na auditoria).
- [x] Trocar a visão não enfileira job (`200` direto do cache).
- [x] `python -m pytest`, `python -m ruff check .`, validador de regras sem erro `bp.*`.

## Aprovação do PO

- [x] PO pediu em 2026-10-08: processar sem excluir; consultar incluindo ou excluindo; padrão isolado; só BP
- [x] PO aprovou a proposal em 2026-10-08
