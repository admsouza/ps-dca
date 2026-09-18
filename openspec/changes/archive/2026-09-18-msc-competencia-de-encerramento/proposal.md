# Proposal — Competência de encerramento por fonte de MSC

**Status:** implementada, aguardando aprovação retroativa do PO
**Repositório:** `ps-dca`
**Capability:** `dca/fonte-msc` (delta)
**Vale para:** todos os anexos da DCA, não só o BF

## Why

A matriz de encerramento **não tem o mesmo número de competência nas duas fontes**, e o código
tratava as duas como iguais:

| Fonte | Como se chega à matriz de encerramento |
|---|---|
| **SICONFI** | competência **12**, identificada por `co_tipo_matriz=MSCE` |
| **PublicSoft** | competência especial **13** (`?exercicio=2026&mesMsc=13`, alias `?anReferencia=2026&meReferencia=13`); 12 é dezembro |

Medido em 2026-09-18 nos 4 entes de homologação com MSC no SICONFI: `me_referencia=13` devolve
**HTTP 200 com zero registros** em todos, contra 448+ na competência 12.

O adapter da PublicSoft pedia a competência recebida do domínio — dezembro — e receberia a posição
do mês em vez do encerramento do exercício. Pior: a auditoria que libera a leitura era consultada
para dezembro, liberando uma competência com base na validação de outra.

## What Changes

- O adapter PublicSoft traduz matriz de encerramento para a competência **13**, tanto na consulta
  de saldos quanto no gate de auditoria.
- O adapter SICONFI permanece na competência 12 com `co_tipo_matriz=MSCE`.
- `COMPETENCIA_DE_ENCERRAMENTO` fica documentada como vocabulário **do domínio**: o número de cada
  API mora no adapter, como já vale para `co_tipo_matriz` e `id_tv`.

## Critérios de aceite

- [x] PublicSoft pede `meReferencia=13` para a matriz de encerramento e mantém o mês pedido para a
      consolidada.
- [x] A auditoria é consultada na **mesma** competência que será lida.
- [x] SICONFI permanece em 12 com `co_tipo_matriz=MSCE`.
- [x] O domínio continua falando em competência 1–12 mais a matriz; nenhum serviço conhece o 13.
- [x] Suíte verde: 341 testes, exit 0.

## Casos de erro

| Situação | Comportamento esperado |
|---|---|
| Encerramento pedido ao SICONFI como competência 13 | não acontece: a tradução é por adapter, e o do SICONFI não a faz |
| Auditoria reprovada na competência 13 | sem dados — conjunto vazio, como já vale para as demais competências |

## Aprovação do PO

- [x] PO autorizou o fechamento em 2026-09-18, nesta sessão
- [x] Implementada em 2026-09-18, com 4 testes em `tests/msc/test_competencia_de_encerramento.py`
