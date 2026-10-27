# Proposal — "Intragovernamental" no IPC 08 × no SIAFIC do ente

**Status:** **investigada, decidida e arquivada** em 2026-10-27 — **opção A: manter o IPC 08**.
Nenhum código alterado: a apuração já estava correta pela norma.
**Repositório:** `ps-dca` · **Capability:** `dca/demonstracao-fluxos-caixa`

## O achado (A2 da auditoria de Cuitegi)

| Linha | Apurado | Publicado |
|---|---:|---:|
| `T.L5` Intragovernamentais recebidas | 0,00 | 7.648.660,37 |
| `T.L13` Intragovernamentais concedidas | 3.591.044,75 | 7.647.660,37 |

## O diagnóstico: dois conceitos diferentes com o mesmo nome

O IPC 08 é explícito (`knowledge/sources/ipc08/extracted.md`, pp. 12–13):

```
L5  Intragovernamentais  (-) 6.2.1.3.0.00.00   7.7.2.x.xx.x.x; 8.4.2.x.xx.x.x
L13 Intragovernamentais  (+) 6.3.1.4.0.00.00   4.4.91.xx.xx; 4.5.91.xx.xx
```

**IPC 08:** intragovernamental é a transferência **orçamentária** entre órgãos — modalidade de
aplicação **91** na despesa, categorias **7** e **8** (intra-orçamentárias) na receita.

**SIAFIC do ente:** intragovernamental é a transferência **financeira**, extraorçamentária. Prova:
os valores publicados na DFC são idênticos aos do **Balanço Financeiro** do mesmo ente —
"Transferências Financeiras Recebidas (II)" 7.648.660,37 e "Concedidas (VII)" 7.647.660,37 — e
batem em centavos com as contas `4.5.1.x` e `3.5.1.x` da MSC.

## Por que a apuração está certa como está

1. **`T.L13` = 3.591.044,75 é a modalidade 91**, exatamente o que o IPC declara.
2. **`T.L5` = 0,00 está correto para este ente.** A única receita de categoria 7 em Cuitegi é
   `7.2.1.5.02.11` (3.885.432,09) — contribuição patronal intra para o RPPS, **não** transferência.
   Pelo IPC ela pertence a `L4` Receita de Contribuições, que confere com o publicado
   (5.514.405,94). Cuitegi não tem transferência intra orçamentária na receita.
3. **As amarrações do IPC continuam valendo:** `P.L10 = T.L7` (48.596.165,81) e
   `P.L15 = T.L15` (3.591.044,75).

## O que foi tentado e revertido

Trocar as contas de `T.L5`/`T.L13` pelas de transferência financeira atinge os valores publicados
(7.648.660,37 e 7.647.660,37), mas:

- **quebra as duas amarrações** — `T.L7` passa a 56.244.826,18 contra `P.L10` 48.596.165,81, e
  `T.L15` a 7.647.660,37 contra `P.L15` 3.591.044,75;
- **perde a modalidade 91**, que é o que o IPC manda somar;
- **não cabe numa regra só**: o filtro de natureza de despesa vale para a linha inteira, então
  `6.2.2.1.3.04.00` com modalidade 91 e `3.5.1.1.0.00.00` sem natureza nenhuma não convivem no
  mesmo conjunto de contas. Somar os dois conceitos exigiria mudança de schema ou lógica no
  serviço.

Medido e revertido; a apuração voltou ao estado anterior, com as amarrações restauradas.

## Decisão para o PO

| Opção | Efeito |
|---|---|
| **A — manter o IPC** (atual) | `T.L5`/`T.L13` seguem a norma; diverge do SIAFIC do ente em 4.056.615,62 na concedida e 7.648.660,37 na recebida |
| **B — seguir o ente** | reproduz o publicado, mas exige mudar `P.L10`, `P.L13` e `P.L15` junto, e somar dois conceitos numa linha — schema ou serviço |

**Impacto no fechamento é quase nulo nas duas opções:** as transferências financeiras se anulam no
consolidado (recebidas 7.648.660,37 × concedidas 7.647.660,37, diferença de R$ 1.000,00). A
escolha é de **classificação**, não de valor.

**Recomendação:** manter A e registrar a divergência na auditoria do ente. A DFC é um demonstrativo
normatizado; reproduzir a leitura de um SIAFIC específico custa coerência interna.

## Decisão do PO

- [x] **2026-10-27 — opção A: manter o IPC 08.** A DFC é demonstrativo normatizado; a leitura do
      SIAFIC de um fornecedor não substitui a norma. `T.L5` e `T.L13` seguem a modalidade 91 e as
      categorias 7/8, as amarrações `P.L10 = T.L7` e `P.L15 = T.L15` permanecem, e a divergência
      com o publicado fica **registrada na auditoria do ente**, não corrigida no código.
- [x] A4 (`L13`/`L15`) fecha junto, pelo mesmo motivo: é a outra face do mesmo conceito.
