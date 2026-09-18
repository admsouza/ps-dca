# Proposal — Balanço Financeiro servido pelo pipeline da DCA

**Status:** proposta
**Repositório:** `ps-dca`
**Capability:** `pipeline/plataforma` (delta) + `dca/balanco-financeiro` (delta)
**Depende de:** `bf-apuracao-f1` (apuração implementada e verificada em 2026-09-18)
**Bloqueia:** a implementação do front, que só começa com o BF concluído no backend

## Why

A apuração do BF está pronta e verificada: 66 linhas × 2 colunas, 24 identidades do IPC 06 fechando
nos 5 entes de homologação, CLI rodando ponta a ponta contra a API do SICONFI. Mas **o front não
tem como consumir**: `GET /anexos/BF` devolve `AnexoDesconhecido`, porque o BF não está no registry.

Não é só registrar. Quatro coisas do pipeline foram escritas quando só existia o BO, que lê **uma**
origem de saldo e tem **uma** coluna por linha. O BF lê três origens e tem duas colunas, e três
dessas quatro falham **em silêncio**, devolvendo número errado com aparência de certo:

1. `_ComCache.registros` (`app/services/pipeline/apuracao.py:47`) não repassa `matriz` nem
   `tipo_saldo`. Pelo caminho da plataforma, as três origens do BF viram uma só — `L25`, `L26` e
   `L29`–`L32` sairiam erradas sem erro nenhum. `ler_ou_baixar` já aceita os dois parâmetros; quem
   não os repassa é o envelope.
2. O serializador (`app/services/pipeline/resultado.py`) ordena por `ORDEM_QUADROS` e `ORDEM_GRUPOS`
   do IPC 07 (`RECEITAS`/`DESPESAS`). O BF tem `INGRESSOS`/`DISPENDIOS` e `QUADRO_ANEXO`: as 66
   linhas cairiam todas no fim, fora da ordem da norma, e o front receberia o demonstrativo
   embaralhado.
3. A chave de cache não tem a **origem da coluna do exercício anterior**. Com ela de fora, um
   resultado apurado com a coluna preenchida manualmente seria servido a quem pediu a coluna da
   MSCE, e vice-versa.
4. Os campos que o BF acrescenta ao resultado — `origens_por_linha`, `origem_exercicio_anterior`,
   `policies_nao_aplicadas`, `sem_dados_exercicio_anterior` — não são serializados. Sem eles o front
   não tem como mostrar por que uma célula está vazia.

## What Changes

- `BF` entra no `REGISTRY` apontando para `app.services.bf.quadro_principal:apurar`.
- `_ComCache.registros` passa a repassar `matriz` e `tipo_saldo` — a correção que evita a leitura
  errada silenciosa.
- Serializador: ordem de apresentação **declarada pelo demonstrativo**, não fixa no módulo.
- Chave de cache: `origem_exercicio_anterior` e, no modo manual, a identidade do conjunto informado.
- Serialização dos campos novos de procedência e diagnóstico.
- `GET /anexos/BF`, `POST /anexos/BF/reprocessar` e o resumo passam a responder, pelo mesmo job
  parametrizado (`apurar_anexo`) que o BO usa.

**Fora de escopo:** Quadro Anexo do BF (change `bf-quadro-anexo`); qualquer mudança na apuração;
tela ou componente de front.

## Entradas e saídas

| Interface | Entrada | Saída |
|---|---|---|
| `GET /anexos/BF?ente=<ibge>&exercicio=<ano>[&competencia=<mês>]` | idem BO | matriz, template, procedência e diagnóstico do BF |
| `POST /anexos/BF/reprocessar` | idem BO | job enfileirado |
| `GET /anexos/resumo` | — | o BF deixa de aparecer como anexo sem serviço |

## Critérios de aceite

- [ ] `GET /anexos/BF` devolve as 66 linhas nas duas colunas, na ordem do IPC 06 — ingressos antes
      de dispêndios, `ordem` relativa ao grupo.
- [ ] O JSON da rota é **idêntico** ao do `python -m app.cli.bf --json` para o mesmo ente,
      exercício e competência: uma serialização só, como já vale para o BO.
- [ ] Duas apurações do mesmo ente/exercício com origens diferentes da coluna anterior **não**
      compartilham entrada de cache.
- [ ] A leitura pela plataforma produz os mesmos valores da leitura direta: `L25`, `L26` e
      `L29`–`L32` conferem com o CLI, em centavos, nos 5 entes de homologação.
- [ ] `procedencia.origens_por_linha` e `diagnostico.policies_nao_aplicadas` chegam ao cliente.
- [ ] Regressão do BO: os 11 valores de `docs/validacao-bo-jp-2025.md` e o contrato da rota
      inalterados; suíte inteira verde.

## Casos de erro

| Situação | Comportamento esperado |
|---|---|
| Anexo grafado `bf`, `Bf`, `B-F` | canonizado para `BF`, sem fragmentar o cache |
| Coluna anterior manual sem os valores no pedido | erro explícito antes de enfileirar o job |
| MSC do exercício anterior indisponível | resultado servido com a coluna anterior não apurada e `sem_dados_exercicio_anterior` no diagnóstico |
| Cache com resultado de outra origem da coluna anterior | ignorado por chave diferente, nunca servido |

## Restrições e riscos

- **O gap do `_ComCache` é o risco central da change.** Ele não quebra: devolve dado da origem
  errada. O teste tem de ser sobre os **parâmetros repassados**, não só sobre o valor final.
- A ordem de apresentação passa a ser dado do demonstrativo. Feito no lugar errado, quebra o BO —
  por isso a regressão do template do BO entra no aceite.

## Aprovação do PO

- [x] PO autorizou o fechamento em 2026-09-18, nesta sessão
