# Proposal — BP espelha o DCA-Anexo I-AB declarado

**Status:** arquivada (2026-10-07)
**Repositório:** `ps-dca`
**Capability:** `dca/balanco-patrimonial` (existente)
**Anexo DCA:** `DCA-Anexo I-AB`
**Regra do projeto:** `openspec/project.md` — "Aceite = espelho 1:1 medido contra `tt/dca`"
**Revoga:** decisões P7-a e P8-a de `bp-apuracao-f1` (2026-10-07)

## Why

O PO definiu que o BP de Cuitegi precisa dar o valor do `DCA-Anexo I-AB` declarado
(`docs/entes-homologacao/cuitegi/SICONFI_DCA_2831_ANUAL_1.xls`, QDCC v14, exercício 2025). Hoje diverge
por duas causas, ambas medidas em 2026-10-07:

1. **Exclusões intra-OFSS (P8-a).** O IPC 04 de 2020 exclui, linha a linha, as contas de 5º nível = 2.
   O `I-AB` declarado não exclui. Sem as exclusões, **as 15 linhas medidas do Quadro Principal batem
   em centavos** com a planilha, e `L1 − L15` vai de −2.004.721,69 a 0,00.
2. **Passivo Financeiro (P7-a).** O IPC 04 lista `6.2.2.1.3.01` e `6.2.2.1.3.05`. O `I-AB` detalha o
   Passivo Financeiro como `2.1`/`2.2` Financeiro + `6.3.1.1` + `6.3.1.7.1`. Cuitegi 2025 registrou a
   inscrição só em `6.3.1.7.1` (387.532,93) e zerou `6.2.2.1.3.05`; por isso a `L5` erra
   387.532,93. Em João Pessoa as duas contas têm o mesmo valor (281.307.109,52 em 2025;
   231.796.527,70 em 2024), e o acerto lá era coincidência.

| Linha | I-AB declarado | Hoje (IPC 04) | Sem intra / L5 do I-AB |
|---|---|---|---|
| `L1` ATIVO | 76.314.331,92 | 47.083.540,63 | 76.314.331,92 |
| `L15` PASSIVO E PL | 76.314.331,92 | 49.088.262,32 | 76.314.331,92 |
| `L32` PL | −45.644.857,64 | −42.467.656,79 | −45.644.857,64 |
| F/P `L5` | 3.105.939,59 | 2.718.406,66 | 3.105.939,59 |
| F/P `L7` | −46.103.363,20 | −45.715.830,27 | −46.103.363,20 |

## What Changes

- Remover as exclusões intra-OFSS (contas de 5º nível = 2) dos filtros das linhas do Quadro Principal
  em `knowledge/rules/bp/quadro_principal.yaml`, preservando a transcrição do PDF na evidência da regra.
- `L5` Passivo Financeiro: `2.1` F + `2.2` F + `6.3.1.1` + `6.3.1.5` + `6.3.1.7.1`, sem
  `6.2.2.1.3.01`/`6.2.2.1.3.05`, com a composição do `I-AB` como fonte da decisão.
- Vale para as duas colunas e as duas origens (MSC e publicado).
- Policy `ipc04.exclusao_intra_so_no_consolidado` e P8 revistas: o equilíbrio volta a ser esperado.

**Fora de escopo:** Contas de Compensação e Superávit por fonte (continuam P5); BO e BF.

## Critérios de aceite

- [ ] Cuitegi 2025: as linhas do Quadro Principal e do F/P iguais à planilha em centavos, e
      `equilibrio` = 0,00 nas duas colunas.
- [ ] João Pessoa 2024 e 2025: Quadro Principal (âncoras `P1`, `P1.1`, `P1.2`, `P2.1`, `P2.2`, `P2.3`) e
      F/P iguais ao `I-AB` do `tt/dca` em centavos.
- [ ] `python -m scripts.validate_rules knowledge` sem erro `bp.*`; índice regenerado.
- [ ] `python -m pytest` e `python -m ruff check .` sem falha nova.

## Aprovação do PO

- [x] PO aprovou em 2026-10-07: espelho do `I-AB` declarado, sem exclusões intra e `L5` pela composição
      do `I-AB`
