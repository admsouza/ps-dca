# Proposal — Quadro Anexo do Balanço Financeiro

**Status:** proposta
**Repositório:** `ps-dca`
**Capability:** `dca/balanco-financeiro` (delta)
**Base normativa:** IPC 06, ed. 2024-06 — 14 regras já transcritas em
`knowledge/rules/bf/quadro_anexo.yaml`
**Depende de:** `bf-apuracao-f1`

## Why

O Balanço Financeiro do IPC 06 tem **dois** quadros. O principal está apurado e verificado; o anexo
— *Demonstrativo da Receita Orçamentária por Fonte/Destinação de Recursos* — tem as 14 regras
transcritas na base canônica e **nenhuma linha de código que as execute**.

Sem ele o demonstrativo fica incompleto de um jeito específico: o quadro principal apresenta a
receita **líquida das deduções** (`L1`), e é o anexo que abre bruto, dedução e líquido por fonte. É
ali que se explica, por exemplo, por que Recife publica 10.390.050.823,18 de receita enquanto a
receita bruta da matriz é 11.401.998.580,10.

O anexo também é o lugar onde a divergência de fonte que a medição encontrou fica visível: os
450.202.814,72 sem fonte de recursos em Recife aparecem como resíduo do anexo, não como buraco no
quadro principal.

## What Changes

- Apuração das 14 linhas do Quadro Anexo, com as **seis colunas** do IPC 06:
  `(a)`/`(d)` receita orçamentária, `(b)`/`(e)` deduções, `(c)`/`(f)` derivadas como `(a) − (b)` e
  `(d) − (e)`.
- O serviço do BF passa a devolver os dois quadros no mesmo resultado, com o quadro declarado por
  linha — o motor já calcula coluna derivada, e o carregador já traz as 80 regras.
- Conferência entre os quadros: `L14 (c)` do anexo contra `L1 exercicio_atual` do principal,
  reportada no diagnóstico, **sem ajustar** nenhum dos dois.

**Fora de escopo:** quadro de detalhamento por fonte criado livremente pelo ente (o de João Pessoa
tem 6 colunas próprias e o de Recife é outro recorte); rota e cache (change `bf-no-pipeline`).

## Entradas e saídas

| Interface | Entrada | Saída |
|---|---|---|
| `apurar(ente, exercicio, fonte, ...)` | idem F1 | matriz com os dois quadros, `QUADRO_PRINCIPAL` e `QUADRO_ANEXO` |
| `python -m app.cli.bf <ibge> <ano> [--quadro principal\|anexo\|todos]` | idem | quadro pedido; `todos` é o padrão |

## Exemplo concreto

Recife/PE (2611606), 2025, coluna do exercício atual:

| | valor | origem |
|---|---|---|
| Receita bruta (`6.2.1.2`) | 11.401.998.580,10 | matriz |
| Deduções (`6.2.1.3`) | 1.011.947.756,92 | matriz |
| Líquida | **10.390.050.823,18** | igual ao RREO e ao BF publicados pelo ente |

O anexo SHALL abrir esses três valores por fonte de recursos, e `L14 (c)` SHALL ser a receita
líquida total.

## Critérios de aceite

- [ ] As 14 linhas saem nas 6 colunas, com `(c)` e `(f)` derivadas da própria linha — nunca somadas
      das filhas.
- [ ] `L14` fecha `L1 + L2 + L10` em cada uma das seis colunas.
- [ ] `L14 (c)` é comparada a `L1 exercicio_atual` do quadro principal e a diferença, quando
      houver, entra no diagnóstico com o valor — sem alterar nenhum dos dois.
- [ ] Receita sem fonte de recursos aparece como resíduo do anexo, com o valor, e não é rateada.
- [ ] Relatório de auditoria de cada ente passa a cobrir as linhas do anexo.
- [ ] Regressão: quadro principal e BO inalterados; suíte verde.

## Casos de erro

| Situação | Comportamento esperado |
|---|---|
| Coluna derivada com parcela não apurada | `(c)` sai `None`, nunca a subtração parcial |
| Fonte de recursos ausente no registro | resíduo declarado, nunca rateio entre as fontes |
| `L14 (c)` diferente de `L1` do principal | diferença no diagnóstico, os dois valores preservados |

## Restrições e riscos

- O ente **não é obrigado** a publicar o anexo no mesmo recorte do IPC 06 — dos 5 entes de
  homologação, João Pessoa e Recife publicam quadros anexos com colunas próprias. A conferência
  contra o publicado vale por soma, não célula a célula.

## Aprovação do PO

- [x] PO autorizou o fechamento em 2026-09-18, nesta sessão
