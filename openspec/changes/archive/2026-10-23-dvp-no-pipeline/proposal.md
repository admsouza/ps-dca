# Proposal — DVP servida pelo pipeline da DCA

**Status:** aprovada pelo PO em 2026-10-23
**Repositório:** `ps-dca`
**Capability:** `pipeline/plataforma` (delta) + `dca/demonstracao-variacoes-patrimoniais` (delta)
**Anexo DCA:** `DCA-Anexo I-HI`
**Base normativa:** IPC 05 ed. 2020-01 (`docs/referencia/ipc/IPC05 - DVP atualizacao - 20200117.pdf`)
**Depende de:** `dvp-quadro-principal` (apuração consolidada em `MSCE`)
**Vem antes de:** `dvp-por-unidade-gestora`
**Bloqueia:** o front, que hoje recebe `I-HI` como anexo sem serviço

## Why

Com a apuração pronta, a DVP continua inacessível ao front: `I-HI` está no registry com
`servico=None` (`app/services/pipeline/registry.py:46`), então o resumo a devolve como
`implementado: false` e o percurso completo a classifica como `nao_implementado`
(`app/services/pipeline/completo.py:70`).

Diferente do BF, a plataforma **não** tem gap funcional para a DVP — os gaps que `bf-no-pipeline`
corrigiu já estão corrigidos. Medido em 2026-10-23:

- a rota é genérica por anexo (`app/routes/anexos.py:582,609`);
- o cache é genérico por anexo, e `"I-HI"` já é o caso de teste disso
  (`tests/pipeline/test_invalidacao.py:95`);
- o despacho filtra parâmetros pela assinatura do serviço (`apuracao.py:478-490`), então a DVP não
  precisa aceitar os parâmetros do BF;
- o carregador já devolve a base canônica da DVP: `carregar(2025, demonstrativo="dvp")` →
  `Vigencia(IPC05, 2020-01)`, 19 linhas.

Sobram três pontos reais, dois deles com efeito silencioso.

## What Changes

- **`I-HI` aponta o serviço da DVP** no `REGISTRY`, com `base_canonica="dvp"`. Sem a base, o
  carregador devolveria as regras do BO — número errado, sem erro (foi o defeito 2.6a de
  `bf-no-pipeline`).
- **Ordem de apresentação do IPC 05** declarada em `ORDEM_POR_DOCUMENTO`
  (`app/services/pipeline/resultado.py:33-37`): quadros `("QUADRO_PRINCIPAL",)`, grupos
  `("VPA", "VPD", "RESULTADO")`. Hoje o documento `IPC05` cairia no padrão do IPC 07 e os três
  grupos ficariam todos "desconhecidos". Com as 19 linhas atuais a saída ainda sai na ordem certa,
  porque `ordem` é global de 1 a 19 — é acerto por coincidência, e some na primeira linha nova.
- **Percurso e notificação deixam de ser três anexos.** Ligar o `I-HI` muda o conjunto apurado, e
  seis asserções fixam hoje `["BO", "BF", "BP"]`: `tests/pipeline/test_pipeline_completo.py:121,408`
  e `tests/pipeline/test_notificacao_discord.py:145,228,247,252`. Mesmo movimento que
  `bp-apuracao-f1` §3.2 fez ao ligar o BP.
- **`app/cli/dvp.py`**, no padrão de `app/cli/bp.py`, com o mesmo serializador da rota.
- **`GET /dca/I-HI`, `POST /dca/I-HI/reprocessar` e o resumo** passam a responder.

**Fora de escopo:** recorte por unidade gestora e escolha da origem do exercício anterior (change
`dvp-por-unidade-gestora`); qualquer mudança na apuração; os quadros anexos do IPC 05; front.

## Entradas e saídas

| Interface | Entrada | Saída |
|---|---|---|
| `GET /dca/I-HI` | `ente`, `exercicio`, fonte do pedido | 19 linhas × 2 colunas, template, procedência e diagnóstico |
| `POST /dca/I-HI/reprocessar` | idem | job enfileirado |
| `GET /dca/resumo` | — | `I-HI` deixa de sair como `implementado: false` |
| `python -m app.cli.dvp <ibge> <exercicio> [--json]` | — | o mesmo JSON da rota |

O código do anexo na API é **`I-HI`**, a grafia do SICONFI que o registry já declara — não `DVP`.
`DVP` segue sendo só a base canônica das regras (`knowledge/rules/dvp/`).

## Critérios de aceite

- [ ] `GET /dca/I-HI` devolve as 19 linhas nas duas colunas, com `VPA` antes de `VPD` e
      `RESULTADO` por último.
- [ ] O JSON da rota é idêntico ao de `python -m app.cli.dvp --json` para o mesmo pedido — uma
      serialização só, como vale para BO, BF e BP.
- [ ] `GET /dca/resumo` traz `I-HI` com `implementado: true`.
- [ ] O percurso completo passa a enfileirar `BO`, `BF`, `BP` e `I-HI`, e a notificação os lista.
- [ ] Linha nova no YAML da DVP continua saindo na ordem da norma (ordem vem do documento, não da
      numeração global).
- [ ] Regressão: BO, BF e BP sem diferença de valor nem de contrato de rota.

## Casos de erro

| Situação | Comportamento esperado |
|---|---|
| Anexo grafado `i-hi`, `I_HI` | canonizado para `I-HI` (`registry.py:53`), sem fragmentar o cache |
| `GET /dca/I-HI?recorte=ug:3` | **422**, enquanto `dvp-por-unidade-gestora` não entrar (`anexos.py:179-180`) |
| MSC do exercício anterior indisponível | resultado servido com a coluna anterior não apurada e o motivo no diagnóstico, como no BP/BF |
| Exercício sem vigência do IPC 05 | `SemVigencia`, sem gravar cache |

## Restrições e riscos

- A chave de cache **não** ganha campo novo: a DVP consolidada lê só `MSCE` e não tem origem de
  coluna anterior escolhível. Quando `dvp-por-unidade-gestora` entrar, a origem por unidade passa a
  valer e a identidade do pedido muda — é lá que esse risco é tratado.
- Ligar o anexo muda o custo do percurso completo: um job a mais por ente/exercício.

## Aprovação do PO

- [x] PO aprovou abrir esta change em 2026-10-23
