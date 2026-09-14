# Pendência — critério da MSC de encerramento na periodicidade mensal

**Aberta em:** 2026-09-14 · **Aguarda:** decisão do PO, com **um ente real de prestação mensal**
**Afeta:** `app/infra/msc/fonte.py` (`fonte_de`), capability `dca/fonte-msc`, e todo demonstrativo
apurado fora da competência 12.

## O que está implementado hoje

A change `msc-fonte-e-competencia` entregou a apuração mensal com esta regra:

| Competência | Matriz | Tipo de saldo |
|---|---|---|
| 12 | encerramento (`MSCE`) | abertura — exceto o BP, que lê o de encerramento |
| 1 a 11 | consolidada (`MSCC`) | encerramento (posição acumulada até o mês) |

## Por que a parte mensal é uma suposição, não um fato

A regra dos meses 1 a 11 veio de uma medição feita em **2026-09-14**: a `MSCE` foi sondada nas
competências 1, 3, 6, 9 e 11 de 2025, em João Pessoa/PB (`2507507`) e Cuitegi/PB (`2505204`), e
**não respondeu em nenhuma**; a `MSCC` respondeu em todas.

O problema da amostra: **os dois entes prestam contas anualmente**. É esperado que não tenham matriz
de encerramento em meses intermediários — eles não encerram nada fora de dezembro. A medição
mostra, portanto, que *esses* entes não têm `MSCE` mensal; **não** mostra que ela não exista para
quem encerra mensalmente.

A periodicidade mensal existe justamente para atender a entes que prestam contas por mês. Se algum
deles publicar `MSCE` em competência intermediária, a regra implementada hoje leria a matriz
**errada** para esse ente — e leria em silêncio, porque a consolidada responde normalmente.

## O que precisa ser decidido

Com um ente real de prestação mensal em mãos:

1. Ele publica `MSCE` em competência diferente de 12? Em quais?
2. Se publica, **qual é o critério de identificação** da matriz de encerramento no mês — é a
   competência do encerramento do período de prestação, um marcador próprio da MSC, ou outra coisa?
3. O tipo de saldo por demonstrativo (abertura para BO/BF/DVP/DFC, encerramento para o BP) vale
   igual no encerramento mensal, ou muda?
4. Um mesmo ente pode alternar periodicidade dentro do exercício? Se sim, o critério é por
   competência, não por ente.

## Como verificar quando houver o ente

```
GET tt/msc_orcamentaria?id_ente=<ente>&an_referencia=<ano>&me_referencia=<1..12>
    &co_tipo_matriz=MSCE&classe_conta=6&id_tv=beginning_balance&limit=1
```

Responder com itens em competência diferente de 12 **derruba** a regra atual. O piloto de
comparação está descrito em `docs/evidencia-matriz-mscc-vs-msce.md` › Reprodução: apurar o mesmo
demonstrativo pelos dois pares e comparar célula a célula contra o publicado do ente.

## Risco enquanto a pendência estiver aberta

| Situação | Efeito hoje |
|---|---|
| Ente anual, competência 12 | correto — medido em dois entes, 337 células cada, zero divergências |
| Ente anual, competências 1–11 | correto — é acompanhamento de execução, e só a consolidada existe |
| **Ente mensal com `MSCE` no mês** | **leria a consolidada, possivelmente errada, sem acusar** |

A terceira linha é o motivo desta pendência. Enquanto ela não fechar, resultado mensal de ente com
prestação mensal deve ser tratado como **não verificado** — a procedência já declara matriz, tipo de
saldo e competência, o que permite identificar depois o que foi apurado com a regra provisória.
