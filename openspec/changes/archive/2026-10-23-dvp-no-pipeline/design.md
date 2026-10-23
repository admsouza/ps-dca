# Design — DVP servida pelo pipeline da DCA

**Change:** `openspec/changes/dvp-no-pipeline/` · **Proposal aprovada pelo PO em:** 2026-10-23

## Contexto

`dvp-quadro-principal` entrega `app/services/dvp/quadro_principal.apurar` e as 19 regras em
`knowledge/rules/dvp/`. A plataforma já transporta BO, BF e BP pelo mesmo job parametrizado
(`apurar_anexo`); `bf-no-pipeline` tirou da plataforma as suposições do tempo em que só existia o
BO. Esta change liga a DVP a esse transporte e nada mais.

## Componentes afetados

| Componente | Papel |
|---|---|
| `app/services/pipeline/registry.py` | `Anexo("I-HI", …)` deixa de ter `servico=None`; `base_canonica="dvp"` |
| `app/services/pipeline/resultado.py` | `ORDEM_POR_DOCUMENTO["IPC05"]` |
| `app/services/pipeline/resumo.py` | nenhuma alteração: `implementado` vem do registry (`resumo.py:89`) |
| `app/cli/dvp.py` | criar, no padrão de `app/cli/bp.py` |
| `tests/pipeline/` | percurso, notificação, rota e contrato rota = CLI |

## Fluxo da informação

```text
GET /dca/I-HI → autorização por unidade → cache (ente, exercício, I-HI, identidade do pedido)
  → job apurar_anexo → apurador("I-HI") → registry: serviço + base canônica
  → carregar(exercicio, demonstrativo="dvp") → apurar → para_dados → cache → leitura
```

## Contratos / interfaces

A assinatura é a mesma de BO/BF/BP: `apurar(ente, exercicio, fonte=…, mapa=…)`. O despacho filtra
o que a assinatura não declara (`apuracao._aceitos_por`), então a DVP consolidada não precisa
conhecer `anterior`, `valores_anteriores` nem `valores_sem_mapeamento`.

Serialização: `resultado.para_dados`, a mesma da rota, do worker e do CLI.

## Impacto

| Eixo | Impacto |
|---|---|
| Banco / migration | nenhum — o registro de cache já é genérico por anexo |
| Cache | uma entrada nova por ente/exercício; sem campo novo na identidade |
| Filas / worker | um job a mais no percurso completo |
| APIs externas | nenhuma nova: a DVP lê a MSC, como BO e BF |
| Regressão | BO, BF e BP bit a bit iguais; o percurso passa a ter quatro anexos |

## Decisões

### D1 — Ordem de apresentação vem do documento
**Escolhido:** `ORDEM_POR_DOCUMENTO["IPC05"] = (("QUADRO_PRINCIPAL",), ("VPA", "VPD", "RESULTADO"))`.
**Descartado:** confiar na numeração global das 19 linhas. **Porquê:** hoje `ordem` vai de 1 a 19
sem repetir, e a saída sairia certa mesmo sem declarar — por coincidência. `_posicao`
(`resultado.py:40-46`) manda grupo desconhecido para o fim; na primeira linha nova com `ordem`
relativa ao grupo, a DVP sairia embaralhada sem erro nenhum. É o mesmo defeito que
`bf-no-pipeline` corrigiu para `INGRESSOS`/`DISPENDIOS`.

### D2 — Código do anexo é `I-HI`
**Escolhido:** o código do SICONFI já declarado no registry. **Descartado:** `DVP` como código de
anexo. **Porquê:** o registry é a lista dos anexos da DCA na grafia do SICONFI
(`registry.py:1-8`), e `_CANONICO` (`registry.py:53`) já canoniza `i-hi`/`I_HI`. `DVP` continua
sendo o nome da base canônica de regras, não do anexo.

### D3 — Nada muda na identidade do cache
**Escolhido:** a DVP consolidada entra sem campo novo na chave. **Descartado:** antecipar a origem
do exercício anterior na identidade. **Porquê:** a apuração consolidada lê só `MSCE`
(`dvp-quadro-principal` D4). A escolha de origem só existe por unidade, e é `dvp-por-unidade-gestora`
que a introduz — foi assim que o BF fez (`bf-no-pipeline` 2.5 só tratou o que já existia).

### D4 — Testes de percurso e notificação mudam junto
**Escolhido:** atualizar as seis asserções que fixam `["BO", "BF", "BP"]`. **Descartado:** manter a
DVP fora do percurso completo. **Porquê:** anexo com serviço entra no percurso por definição
(`completo.py:66-70`); mantê-la fora exigiria uma exceção na plataforma. `bp-apuracao-f1` §3.2
tratou a mesma mudança como consequência esperada, não como regressão.

## Arquivos criados / alterados

| Arquivo | Ação |
|---|---|
| `app/services/pipeline/registry.py` | alterar (serviço e base canônica do `I-HI`) |
| `app/services/pipeline/resultado.py` | alterar (`ORDEM_POR_DOCUMENTO["IPC05"]`) |
| `app/cli/dvp.py` | criar |
| `tests/pipeline/test_dvp_no_pipeline.py` | criar — espelho de `test_bf_no_pipeline.py`, inclusive `test_rota_e_cli_publicam_o_mesmo_json` (`:130`) e `test_apurador_usa_o_servico_declarado_no_registry` (`:143`) |
| `tests/pipeline/test_rota_dvp.py` | criar — espelho de `test_rota_bf.py` (rota contra a app, portas fakes) |
| `tests/pipeline/test_pipeline_completo.py` | alterar (percurso com quatro anexos) |
| `tests/pipeline/test_notificacao_discord.py` | alterar (lista de anexos) |

## Pendências conhecidas

- Recorte por unidade e origem do exercício anterior: change `dvp-por-unidade-gestora`. Até lá,
  `GET /dca/I-HI?recorte=` responde 422 pela regra geral de `anexos.py:179-180`. Isso é estado de
  transição, não requisito: não entra no delta da plataforma, para não virar um `MODIFIED` logo na
  change seguinte. O recorte da DVP é especificado em `pipeline/unidade-gestora`, onde o BF e o BO
  especificaram os seus (`bf-por-unidade-gestora/specs/pipeline/unidade-gestora/spec.md`).
- `resumo.COM_UNIDADES` (`resumo.py:23`) continua `("BF", "BP")`: a DVP só entra nele quando tiver
  recortes para publicar.
