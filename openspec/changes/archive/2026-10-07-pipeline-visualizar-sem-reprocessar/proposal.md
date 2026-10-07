# Proposal — Visualizar um anexo apurado nunca reprocessa

**Status:** arquivada (2026-10-07)
**Repositório:** `ps-dca`
**Capability:** `pipeline/plataforma` (existente)
**Anexo DCA:** n/a — vale para todos os anexos
**Fonte da verdade externa:** n/a. **Diverge** deliberadamente de RREO/RGF, que reapuram na leitura
quando a versão muda (decisão do PO, 2026-10-07)

## Why

O PO precisa garantir que, depois de processado, quem só quer **ver** o anexo receba o cache, sem
disparar processamento. Hoje o `GET /dca/{anexo}` enfileira um job novo em três situações com
resultado pronto:

1. **Depois do percurso completo, sempre (bug).** `POST /batch-jobs` não manda a fonte ao worker. O
   percurso grava `versao_regras` sem o sufixo `f=<fonte>`, e o `GET` sempre manda a fonte
   (`use_siconfi` → `siconfi`|`publicsoft`). A identidade nunca confere, e cada visualização de um
   anexo apurado pelo percurso reprocessa.
2. **Fonte diferente da processada.** Processado com SICONFI e aberto com `use_siconfi=false` (o
   padrão): a identidade muda, o anexo é reapurado e o cache, que tem uma linha por
   `(ente, exercício, anexo)`, é sobrescrito.
3. **Todo deploy.** `versao_api` é o hash do código da apuração. Depois de qualquer deploy, a primeira
   visualização de cada anexo de cada ente reprocessa. Com API e worker em imagens diferentes, os
   hashes nunca batem e toda visualização reprocessa.

Custo: carga na MSC e no worker sem ninguém ter pedido, número trocado na tela sem ação do usuário,
e o resultado que o ente já conferiu sobrescrito por uma visualização.

## What Changes

- **`GET /dca/{anexo}` com cache `ok` sempre responde `200` com o resultado.** Nunca enfileira.
- A resposta ganha `desatualizado` (bool) e `motivos_desatualizado` (lista): `versao_api` (o código
  da apuração mudou), `versao_regras` (a regra vigente mudou) e `pedido` (fonte, competência ou
  origem do exercício anterior diferentes das do processamento).
- **Processar continua explícito:** `POST /dca/{anexo}/reprocessar` e `POST /batch-jobs`. O percurso
  sem `forcar` continua reapurando o que estiver desatualizado. Processar é a ação dele.
- **O percurso grava a identidade completa:** fonte padrão (`DATA_SOURCE`) no pedido, na rota e no
  worker, e o apurador do percurso lê essa fonte. O `GET` seguinte reconhece o cache sem marcá-lo.
- Sem cache (`ausente`) ou com `erro`, o `GET` continua enfileirando, como hoje: não há resultado a
  mostrar.

**Fora de escopo:** escolher a fonte no percurso (`use_siconfi` em `/batch-jobs`), que fica com
`pipeline-fonte-por-pedido`; aviso visual no front (o front lê `desatualizado` quando quiser).

## Entradas e saídas

| Interface | Entrada | Saída |
|---|---|---|
| `GET /dca/{anexo}` com cache `ok` | `id_ente`, `anReferencia`, `use_siconfi`, parâmetros do BF | `200` com o resultado + `desatualizado` + `motivos_desatualizado` |
| `GET /dca/{anexo}` sem cache, ou com `erro` | idem | `202` + `job_id` (inalterado) |
| `GET /dca/{anexo}` com job em voo | idem | `202` `already_queued` (inalterado) |
| `POST /dca/{anexo}/reprocessar` | idem | `202` + `job_id` (inalterado) |
| `POST /batch-jobs` | `id_ente`, `anReferencia`, `forcar` | inalterado; o cache gravado passa a carregar `f=<fonte padrão>` |

## Exemplo concreto

Cuitegi/PB (`2505204`), 2025, BF processado por SICONFI às 10:13. Às 10:20 a tela abre o BF sem
`use_siconfi` (PublicSoft):

| | Hoje | Depois |
|---|---|---|
| Resposta | `202`, job novo; às 10:21 o cache vira PublicSoft | `200` com o BF das 10:13 |
| Corpo | — | `desatualizado: true`, `motivos_desatualizado: ["pedido"]` |
| Worker | apura de novo | nada |

Após um deploy, o mesmo `GET` responde `200` com `motivos_desatualizado: ["versao_api"]`, até alguém
reprocessar.

## Critérios de aceite

- [ ] `GET` com cache `ok` não enfileira job em nenhum dos três motivos (código, regra, pedido),
      medido por fila fake vazia.
- [ ] `GET` com cache atual responde `desatualizado: false` e `motivos_desatualizado: []`.
- [ ] Percurso seguido de `GET` com a mesma fonte: `200`, `desatualizado: false`, nenhum job.
- [ ] `reprocessar` e percurso sem `forcar` continuam reapurando o cache desatualizado.
- [ ] `GET` sem cache e com `erro` continuam enfileirando (`202`).
- [ ] `python -m pytest` e `python -m ruff check .` sem falha nova.

## Casos de erro

| Situação | Comportamento esperado |
|---|---|
| Cache `ok` com `resultado` vazio | tratado como ausente: enfileira (não há o que mostrar) |
| Cache `processando` com resultado anterior e job em voo | `202 already_queued` (inalterado) |
| Cache `processando` com lock órfão | recupera e enfileira (inalterado) |
| Cache `erro` | enfileira (inalterado) |

## Restrições e riscos

- **Resultado com regra antiga pode ser exibido.** Revoga "a apuração NÃO DEVE servir resultado cuja
  versão de regras não seja a vigente" da spec atual, por decisão do PO. A mitigação é o
  `desatualizado` com motivo no corpo, e o front decide como avisar.
- Com API e worker em imagens diferentes, o percurso reapura tudo sempre (o hash difere). Isso
  continua, mas deixa de afetar a visualização.

## Aprovação do PO

- [x] PO decidiu em 2026-10-07: visualizar nunca processa; desatualização marcada no corpo; change
      separada da de notificações
- [x] PO aprovou a proposal em 2026-10-07
