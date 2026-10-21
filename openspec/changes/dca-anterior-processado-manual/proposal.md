# Proposal — Exercício anterior somente Processado ou Manual

**Status:** aprovada pelo PO
**Repositório:** `ps-dca`
**Capability:** `pipeline/anterior-por-recorte` (existente)
**Anexo DCA:** Balanço Financeiro (BF) e Balanço Patrimonial (BP)
**Base normativa:** IPC 06 e IPC 04; a mudança escolhe a origem, sem alterar regras contábeis

## Why

A origem automática atual usa o resultado processado de N−1 quando existe e cai silenciosamente
para a MSC de N−1 quando não existe. A interface também oferece Matriz/MSC como escolha explícita.
Isso cria três caminhos para a mesma coluna e não deixa claro ao usuário qual retrato foi usado.

## What Changes

- O padrão por unidade passa a ser exclusivamente o resultado Processado de N−1.
- A única alternativa escolhida pelo usuário é Manual, com valores da própria unidade.
- N−1 sem resultado processado responde `409`, sem fallback para MSC e sem resultado parcial.
- `msce_exercicio_anterior` deixa de ser aceito como escolha nova em `anterior_por_recorte`.
- Escolha antiga de MSCE é normalizada para o novo padrão; não continua ativa silenciosamente.

**Fora de escopo:** fonte do exercício atual, regras contábeis, ingestão da MSC, banco e migrations.

## Entradas e saídas

| Interface | Entrada | Saída |
|---|---|---|
| `POST /dca/{BF|BP}/reprocessar` | `anterior_por_recorte` ausente ou com `processado_exercicio_anterior` | `202`, se N−1 contém cada unidade; `409`, caso contrário |
| `POST /dca/{BF|BP}/reprocessar` | unidade com `manual` e mapa válido | `202`; mapa aplicado à unidade |
| `POST /dca/{BF|BP}/reprocessar` | unidade com `msce_exercicio_anterior` | `422`; nenhum job enfileirado |

## Exemplo concreto

| Ente | Exercício | Anexo | Situação | Resultado esperado |
|---|---|---|---|---|
| `2505204` — Cuitegi/PB | 2025 | BF e BP | unidade sem cache de 2024 | `409`: processar 2024 ou informar valores manualmente |

## Critérios de aceite

- [x] Existem exatamente 2 origens observáveis por unidade: Processado e Manual.
- [x] Existem 0 fallbacks automáticos para MSCE quando N−1 não está processado.
- [x] BF e BP preservam bit a bit o exercício atual.
- [x] Manual continua validado por unidade e participa da soma do consolidado.

## Casos de erro

| Situação | Comportamento esperado |
|---|---|
| N−1 ou unidade ausente no Processado | `409`, orientando processar N−1 ou usar Manual |
| escolha nova `msce_exercicio_anterior` | `422`, sem job e sem alterar cache |
| manual sem valores ou inválido | `422`, sem job e sem alterar cache |

## Restrições e riscos

- Processar N pela primeira vez exige N−1 processado ou valores manuais para cada unidade.
- Cache e preferências legadas podem declarar MSCE; serão tratados como padrão Processado, nunca
  como autorização para continuar lendo N−1 da matriz.

## Aprovação do PO

- [x] PO aprovou esta proposta em 2026-10-21.
