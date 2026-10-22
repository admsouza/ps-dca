# Proposal — O exercício anterior não bloqueia a apuração

**Status:** aprovada pelo PO
**Repositório:** `ps-dca`
**Capability:** `pipeline/anterior-por-recorte` (existente)
**Anexo DCA:** `DCA-Anexo I-E` (BF) e `DCA-Anexo I-F` (BP)
**Base normativa:** MCASP 10ª ed. · layout SICONFI DCA
**Fonte da verdade externa:** n/a

## Why

A coluna do exercício anterior virou pré-requisito para apurar o exercício atual, e não é. O usuário
que está conferindo o **atual** fica impedido de ver qualquer número enquanto não resolver N−1 —
sendo que, na primeira apuração de um exercício, ele nem sabe quais unidades existem: a lista nasce
dentro do job.

Medido em produção (2026-10-22, ente 2505204, BP 2025): Manual informado para `ug:1`, rota devolveu
`202` porque não havia cache `ok` de N para conferir as demais, e o worker morreu com
`ProcessadoSemAnterior: ug:2` após 8,8 s. O usuário nunca soube que `ug:2` existia. É o impasse
registrado como `ponytail:` em `app/routes/anexos.py:323`.

A trava de qualidade do dado não pertence ao pipeline: a DCA vai ganhar módulo de homologação (em
auditoria / homologado), como o RREO. É lá que se decide o que é oficial — apurar é conferir.

## What Changes

- Unidade sem resultado processado em N−1 e sem Manual SHALL apurar com a coluna anterior em
  **`0,00`**, marcada no diagnóstico, em vez de falhar.
- O `409` "Processe N−1 ou use Manual" deixa de existir. Nenhum pedido válido é recusado por causa
  da coluna anterior.
- O resultado marca a unidade com `sem_dados_exercicio_anterior` (campo que já existe e já propaga
  a grupos e consolidado), como informação — **não** como bloqueio de emissão.
- Manual e Processado continuam exatamente como estão; MSCE continua fora.

**Fora de escopo:** o módulo de homologação (change própria); reabrir MSCE; mudar a coluna atual;
consulta de preparação de unidades — com a apuração sempre concluindo, o front lê as unidades do
próprio resultado.

## Entradas e saídas

| Interface | Entrada | Saída |
|---|---|---|
| `GET/POST /dca/{anexo}` | sem `anterior_por_recorte` e sem N−1 | `200/202` com coluna anterior `0,00` na unidade |
| `GET /dca/{anexo}` (resultado) | — | `diagnostico.sem_dados_exercicio_anterior` e `procedencia.origem_exercicio_anterior = "sem_anterior"` (campos existentes) |

## Exemplo concreto

| Ente | Exercício | Anexo | Célula | Valor esperado |
|---|---|---|---|---|
| 2505204 | 2025 | I-F (BP) | `ug:2` · coluna anterior | `0,00`, com `sem_dados_exercicio_anterior` no recorte |
| 2505204 | 2025 | I-F (BP) | `ug:1` · coluna anterior | o mapa Manual informado, inalterado |
| 2505204 | 2025 | I-F (BP) | consolidado · coluna anterior | o Manual de `ug:1` somado ao `0,00` de `ug:2` |

## Critérios de aceite

- [ ] Nenhum pedido de BF/BP é recusado com `409` por ausência de N−1.
- [ ] Nenhum job termina com `ProcessadoSemAnterior`.
- [ ] Primeira apuração de um exercício sem N−1 conclui `ok` e lista todas as unidades.
- [ ] BF/BP com Processado ou Manual saem bit a bit iguais ao comportamento atual.
- [ ] Toda unidade sem anterior sai com `sem_dados_exercicio_anterior`, sem campo novo.
- [ ] Grupo e consolidado somam a unidade sem anterior como `0,00`, sem tratamento especial.

## Casos de erro

| Situação | Comportamento esperado |
|---|---|
| N−1 em processamento ou com erro | apura com anterior zerado e registra o motivo no aviso |
| Manual com mapa inválido | `422`, como hoje — a validação do Manual não muda |
| `msce_exercicio_anterior` no pedido | `422`, como hoje |
| MSC do exercício atual indisponível | comportamento atual (sem registros), inalterado |

## Restrições e riscos

- `0,00` afirma um saldo anterior que ninguém conferiu. Mitigação: a unidade sai marcada com
  `sem_dados_exercicio_anterior`, e a exigência de dado conferido passa ao módulo de homologação.
- BP com anterior em `0,00` não fecha ativo/passivo e infla a variação patrimonial. Assumido: o anexo
  serve para conferência do atual, e a qualidade do que é oficial passa a ser do módulo de
  homologação.
- Reverte a recusa introduzida em `dca-anterior-processado-manual` (2026-10-21). A decisão central
  daquela change **permanece**: MSCE não volta — números não conferidos continuam proibidos. Zero é
  visivelmente ausente; MSCE parece correto e não é.
- Dependência futura: a homologação precisa poder exigir anterior resolvido para homologar. Pendência
  em aberto na proposal daquele módulo, não aqui.

## Aprovação do PO

- [x] PO aprovou esta proposta em 2026-10-22 — **gate para a fase PLAN/ARCH**
