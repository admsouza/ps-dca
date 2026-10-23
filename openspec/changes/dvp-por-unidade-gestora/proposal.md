# Proposal — DVP emitida por unidade gestora, com origem do exercício anterior por recorte

**Status:** aprovada pelo PO em 2026-10-23
**Repositório:** `ps-dca`
**Capability:** `dca/demonstracao-variacoes-patrimoniais` (existente) · `pipeline/unidade-gestora`
**Anexo DCA:** `DCA-Anexo I-HI`
**Base normativa:** IPC 05 ed. 2020-01 · IPC 04 item 8 (levantamento de unidade específica)
**Depende de:** `dvp-no-pipeline`, `pipeline-dca-por-unidade-gestora` e `pipeline-anterior-por-recorte`

## Why

BO, BP e BF saem por unidade gestora; a DVP não. Com `dvp-no-pipeline`, `GET /dca/I-HI?recorte=ug:3`
responde **422** (`app/routes/anexos.py:179-180`), porque `RECORTAVEIS` é `("BO", "BP", "BF")`
(`app/services/pipeline/apuracao.py:124`), e o resumo não publica `recortes` para ela
(`COM_UNIDADES = ("BF", "BP")`, `app/services/pipeline/resumo.py:23`).

Sem isso a PCA por unidade fica incompleta e o usuário do Legislativo não emite a DVP da Câmara —
o mesmo motivo que abriu `bf-por-unidade-gestora`.

A DVP é o caso **mais simples** dos quatro: lê só a MSC (classes 3 e 4, saldo de abertura) e não
tem estorno de GRE/GDE, que foi o que segurou o BF. O que falta é ligar o recorte e dar à coluna do
exercício anterior as mesmas três origens por unidade que BP e BF têm.

## What Changes

- **A DVP entra nos anexos com recorte.** O job apura o consolidado, os grupos de poder e cada
  unidade — `ug:` quando a fonte informa a unidade, `po:` quando não informa — e
  `GET /dca/I-HI?recorte=` serve do cache sem enfileirar job, com as mesmas regras de visibilidade
  por poder do BO, do BP e do BF.
- **Coluna do exercício anterior por unidade**, no mesmo contrato de BF e BP: o pedido escolhe
  `processado_exercicio_anterior`, `manual` ou `padrao` por unidade;
  `msce_exercicio_anterior` **não é escolha do pedido** — é o padrão resolvido quando não há
  processado de N−1 (`app/services/pipeline/anterior.py:177-180`). A assinatura de `apurar` já
  declarava `anterior` desde `dvp-quadro-principal` — é o que faz `com_recortes` tratar o anexo
  como anexo por unidade (`apuracao.py`, `por_unidade = "anterior" in _aceitos_por(...)`) —, e o
  que falta é aceitar `anterior_pronto` e `valores_anteriores` (medido em 2026-10-23: sem eles o
  job quebra com `TypeError: apurar() got an unexpected keyword argument`).
- **`validar_escolhas` passa a conhecer o `I-HI`.** Hoje ela recusa qualquer anexo fora de
  `("BF", "BP")` (`anterior.py:163`), e `_validar_manual` (`anterior.py:184`) despacha só para
  `bp/informados.py` ou `bf/informados.py`. A DVP ganha o seu
  `app/services/dvp/informados.py`, no mesmo formato.
- **Consolidado sem origem própria.** A coluna anterior dele é a soma das colunas já resolvidas das
  unidades do job, como em `pipeline-consolidado-anterior-soma-unidades`. O consolidado da DVP
  continua sem `publicado_siconfi`: o `I-HI` publicado é o demonstrativo do ente, não por unidade.
- **Grupo de poder sem origem própria**, pela soma das unidades.
- **Manual por unidade** nas 16 linhas-base (L2–L8 e L10–L18), com a chave `L<n>` sem prefixo.
  Nada disso é escolha nova: o manual por unidade é o do BP, que recusa totalizadora por
  `linha.referencias` (`app/services/bp/informados.py:58-59`, cenário em
  `tests/bp/test_anterior_manual.py:104`) e tira a totalizadora da `calculation`
  (`:31`). O prefixo de chave existe só onde há mais de um quadro — `P:`/`FP:`/`C:`/`S:` no BP,
  `A:` no quadro anexo do BF (`app/services/bf/informados.py:73`). A DVP tem um quadro só, como o
  principal do BF, então a chave é o código da linha.
- **A DVP entra no percurso completo por unidade sem nada a decidir.** Anexo em `RECORTAVEIS` é
  apurado com recortes em qualquer job (`apuracao.py:472`), inclusive o do percurso, e
  `parametros_efetivos` (`app/services/pipeline/cache.py:128-151`) reaplica as escolhas gravadas
  por unidade. `pipeline-anterior-por-recorte` já fixou que no percurso cada unidade usa a escolha
  gravada ou o padrão — `anterior_por_recorte` não viaja no `/batch-jobs`, que não tem corpo.
- **Resumo** passa a publicar `recortes` para `I-HI`.

**Fora de escopo:** estorno (a DVP não abate GRE/GDE); manual no consolidado; combinação arbitrária
de unidades; os quadros anexos do IPC 05.

## Entradas e saídas

| Interface | Entrada | Saída |
|---|---|---|
| `GET /dca/I-HI?recorte=consolidado\|poder:executivo\|ug:3\|po:20231` | recorte pedido | o recorte do cache, sem enfileirar |
| `POST /dca/I-HI/reprocessar` | `anterior_por_recorte: {unidade: {origem, valores?}}` | job com as escolhas por unidade |
| `GET /dca/resumo` | — | `I-HI` com `recortes` |

## Critérios de aceite

- [ ] Σ das 16 linhas-base das unidades = consolidado, em centavos, no ente de homologação.
- [ ] `GET /dca/I-HI?recorte=ug:<id>` responde 200 lendo do cache, sem enfileirar job.
- [ ] Visibilidade por poder idêntica à do BO, BP e BF.
- [ ] Unidade com `processado` traz `procedencia.anterior_processado` do N−1.
- [ ] Unidade sem MSC em N−1 em `msce` sai com a coluna anterior em zero e
      `sem_dados_exercicio_anterior` no diagnóstico.
- [ ] Manual recusa L1, L9 e L19.
- [ ] Consolidado da DVP permanece igual ao de `dvp-quadro-principal` em centavos.
- [ ] BO, BP e BF sem diferença de valor.

## Casos de erro

| Situação | Comportamento esperado |
|---|---|
| `recorte` inexistente ou malformado | 422, sem job |
| Unidade fora do poder do usuário | mesma recusa que BO, BP e BF |
| `manual` sem valores | 422 antes de enfileirar (`anterior.py:173-174`) |
| `origem: msce_exercicio_anterior` no pedido | 422 — `msce` é padrão resolvido, não escolha (`anterior.py:180`) |
| `processado` cujo N−1 sumiu do cache | cai em `msce`, com o motivo registrado, sem travar o job |

## Aprovação do PO

- [x] PO aprovou abrir esta change em 2026-10-23
