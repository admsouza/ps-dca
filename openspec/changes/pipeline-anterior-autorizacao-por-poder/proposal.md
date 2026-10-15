# Proposal — Escolha do exercício anterior só nas unidades do poder do usuário

**Status:** implementação autorizada pelo dev em 2026-10-15; aprovação formal do PO pendente. Bugfix de segurança (OWASP A01).
**Repositório:** `ps-dca`
**Capability:** `pipeline/anterior-por-recorte` (MODIFIED)
**Anexo DCA:** BF e BP (coluna "Exercício Anterior")
**Base normativa:** n/a (autorização; não muda número)
**Origem:** revisão de segurança de `pipeline-resumo-com-unidades` / `dca-dados-exercicio-anterior` (2026-10-15)

## Why

`POST /dca/{BF|BP}/reprocessar` só confere o acesso ao **ente** (`unidade_autorizada`).
`anterior_por_recorte` é validado só no formato (`app/routes/anexos.py:293-298`,
`anterior.validar_escolhas`), sem considerar o poder do usuário sobre cada unidade.

A leitura e o resumo já filtram as unidades por poder (`recortes.visiveis`, fail closed). A
escrita não filtra. Um usuário só do Executivo não vê a Câmara na tela, mas pode enviar pelo
DevTools ou por curl:

```json
{"anterior_por_recorte": {"ug:<Câmara>": {"origem": "manual", "valores": {"P:L3": "1.00"}}}}
```

Esse pedido grava a coluna anterior da Câmara e altera as somas de `poder:legislativo` e de
`poder:executivo+legislativo`. A escolha persiste e é reaplicada nos jobs seguintes. Atenuantes: o
usuário precisa estar autenticado e ter acesso ao ente, e o solicitante fica registrado.

## What Changes

- A chave de unidade em `anterior_por_recorte` (BF e BP, `reprocessar`) MUST pertencer ao poder do
  usuário. Caso contrário, a resposta é `403`, sem job e sem gravar nenhuma escolha do pedido
  (tudo ou nada).
- O poder da unidade é resolvido assim:
  - `po:<código>`: pelo próprio código (`PODER_ORGAO`);
  - `ug:<id>`: pelo `poderOrgao` gravado no cache de N e, na falta dele, no de N−1.
  - Unidade cujo poder não se resolve (UG que não está em nenhum cache, PO vazio ou PO com mais de um
    poder): só quem tem `consolidado` pode escolher. Para os demais, `403` (fail closed).
- Quem tem `consolidado` continua podendo escolher qualquer unidade, como hoje.
- Sem `poderes` no estado da requisição: `403` para qualquer `anterior_por_recorte`.
- Mesma regra que a leitura usa (`recortes.visiveis`). Nenhuma regra nova de visibilidade.

**Fora de escopo:**
- `origem_exercicio_anterior` do consolidado (ver D1).
- O reprocessar do ente em si (sem `anterior_por_recorte`), que segue com a autorização de hoje.
- `POST /batch-jobs`, que não aceita escolhas por unidade.

## Decisões do PO

| # | Pergunta | Recomendação |
|---|---|---|
| D1 | Mudar `origem_exercicio_anterior` do consolidado (BF/BP) deve exigir o poder `consolidado`? Hoje qualquer usuário do ente pode mudar. | **Sim**, `403` sem `consolidado`. Há o risco de bloquear quem hoje opera só com Executivo, então o PO precisa confirmar. |

## Entradas e saídas

| Interface | Entrada | Saída |
|---|---|---|
| `POST /dca/{BF\|BP}/reprocessar` | sem mudança | `403` "sem acesso à unidade {chave}" quando alguma chave de `anterior_por_recorte` está fora do poder do usuário; demais casos sem mudança |

## Exemplo concreto

Cuitegi/PB (`2505204`), BP 2025, cache de N com a Câmara (`poderOrgao` 20231) e a Prefeitura (10131).

| Usuário (poderes) | `anterior_por_recorte` | Resposta |
|---|---|---|
| `executivo` | `ug:<Prefeitura>` manual | `202` |
| `executivo` | `ug:<Câmara>` manual | `403`, nenhuma escolha gravada |
| `executivo` | `ug:<Prefeitura>` + `ug:<Câmara>` | `403`, nenhuma das duas gravada |
| `executivo` | `po:20231` | `403` |
| `consolidado` | `ug:<Câmara>` | `202` |
| `executivo` | `ug:999` (fora dos dois caches) | `403` |

## Critérios de aceite

- [ ] Os 6 casos do exemplo, cada um com um teste.
- [ ] `403` sem nenhum job enfileirado e sem escrita no cache (contagem de jobs = 0, escolhas gravadas inalteradas).
- [ ] Pedidos de quem tem `consolidado`: bit a bit iguais ao comportamento atual.
- [ ] Suíte inteira verde.

## Casos de erro

| Situação | Comportamento esperado |
|---|---|
| Chave fora do poder | `403`, sem job |
| Chave com formato inválido ou de grupo | `422`, como hoje (o formato é validado antes do poder) |
| Sem `poderes` no estado | `403` |

## Restrições e riscos

- Usuários que hoje escolhem a origem de unidades de outro poder vão passar a receber `403`. Esse é
  o efeito desejado, mas precisa ser comunicado.
- O front já esconde as unidades fora do poder (o resumo filtra). Por isso o fluxo normal da tela
  não muda.

## Aprovação do PO

- [ ] D1 decidido
- [ ] PO aprovou esta proposta em <data> — **gate para a fase PLAN/ARCH** (implementação autorizada pelo dev em 2026-10-15; aprovação formal do PO pendente)
