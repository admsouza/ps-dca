# Design — DVP, Quadro Principal

**Change:** `openspec/changes/dvp-quadro-principal/` · **PO mandou abrir em:** 2026-10-23

## Contexto

BO, BP e BF apuram uma linha por regra YAML no motor `app/domain/bo/saldo.py`. A DVP usa o mesmo motor. A medição de 2026-10-23 contra o `I-HI` fechou sem a coluna Exclusões do IPC 05.

## Componentes afetados

| Componente | Papel |
|---|---|
| `knowledge/rules/dvp/quadro_principal.yaml` | 19 regras, contrato de `rule.json` |
| `knowledge/policies/ipc05.yaml` | itens 15 e 16 declarados e não executados |
| `knowledge/sources/ipc05/` | metadado do PDF, sem copiar o PDF |
| `app/domain/bo/saldo.py` | direção da coluna; o fallback de prefixo **já existe** (`:209`) |
| `app/services/dvp/quadro_principal.py` | apuração, espelho de BP/BF |
| `app/services/pipeline/registry.py` | `I-HI` deixa de ser `None` e aponta o serviço da DVP |

## Fluxo da informação

```text
MSC MSCE abertura classes 3 e 4 (N e N-1)
  → mapa YAML sem filters
  → saldo_da_celula na direção da coluna
  → L1, L9, L19 por calculation
  → matriz conferida com o I-HI
```

## Contratos / interfaces

`rule_id`: `dvp.quadro_principal.<grupo>.l<n>`. Grupos `VPA` (L1–L8), `VPD` (L9–L18), `RESULTADO` (L19).

Colunas `exercicio_atual` e `exercicio_anterior`, as mesmas contas, sem `saldo: final` (movimento do período).

Prefixos: L2 `41`, L3 `42`, L4 `43`, L5 `44`, L6 `45`, L7 `46`, L8 `49`, L10 `31`, L11 `32`, L12 `33`, L13 `34`, L14 `35`, L15 `36`, L16 `37`, L17 `38`, L18 `39`.

## Impacto

| Eixo | Impacto |
|---|---|
| Banco / migration | nenhum |
| Cache | chave nova só quando a DVP entrar no pipeline; fora desta fatia até o serviço existir |
| Filas / worker | registro do anexo no mesmo ciclo de BO/BP/BF, na fase IMPLEMENT |
| APIs externas | `tt/msc_patrimonial` e `tt/dca` `DCA-Anexo I-HI`, timeout já existente |
| Regressão | BO, BP e BF bit a bit iguais |

## Decisões

### D1 — Exclusão do IPC 05 não entra no cálculo
**Escolhido:** nenhuma regra da DVP declara `filters` nem `exclusion_groups`. A policy dos itens 15 e 16 fica em `knowledge/policies/ipc05.yaml` com texto de que a lista não é executada. **Descartado:** `exclusion_groups` do YAML `yaml-dvp-ipc05` e o coringa de 5º nível = 2. **Porquê:** João Pessoa 2025, L6 11.722.481.279,59 e L14 9.199.369.111,48 no `I-HI`; com a lista, 3.151.851.371,43 e 628.739.203,32. Porto Alegre e o exercício 2024 fecham do mesmo modo. Decisão do PO em 2026-10-23.

### D2 — Redutora pela direção da coluna
**Escolhido:** `saldo_da_celula`, direção da classe (4 credora, 3 devedora). **Descartado:** somar cada conta na natureza dela. **Porquê:** `4.1.1.2.1.97` = 1.052.431,74 em João Pessoa 2025; na direção dela, L2 fica 2.104.863,48 acima do `I-HI` (397.963.739,37).

### D3 — Conta sem folha herda o prefixo
**Escolhido:** `credora` da conta e, se ausente, `credora_prefixo`. **Descartado:** deixar a célula inteira não apurada. **Porquê:** Porto Alegre 2025 movimenta `442510000`, que não é folha. Os 716,56 fecham L5. Sem fallback, o motor anula a linha.

**Onde isso vive (medido em 2026-10-23):** o motor já consulta `credora_prefixo` em `_direcao_da_coluna` (`app/domain/bo/saldo.py:209`) e `app/infra/pcasp/natureza.py:34` o implementa — mas **a consulta crua não resolve a conta de 9 dígitos preenchida com zeros**:

| Consulta | Resultado |
|---|---|
| `credora("442510000")` | `None` — não é folha do PCASP |
| `credora_prefixo("442510000")` | `None` — nenhuma folha começa com esses 9 dígitos |
| `credora_prefixo("44251")` | `True` |
| `credora_prefixo("442510000".rstrip("0"))` | `True` |

O adaptador do BP (`app/services/bp/quadro_principal.py:446-462`) também não resolve sozinho: ele trata a conta **mista** do PL, não a sintética. Quem já resolve isso no repo é `app/services/bp/publicado.py:40`, que consulta `credora_prefixo(conta.rstrip("0"))`.

A DVP junta os dois precedentes num adaptador próprio: `credora` da folha; se `None`, `credora_prefixo` da conta; se ainda `None`, `credora_prefixo` da conta sem os zeros à direita. Folha real não passa pelo último passo, porque o primeiro já respondeu (`credora("411210200")` = `True`, `credora("411219700")` = `False`). O motor compartilhado não é alterado.

### D4 — Fonte MSC já decidida
**Escolhido:** `fonte_de("DVP")` = `MSCE`, abertura, classes 3 e 4 (`app/infra/msc/fonte.py`). **Descartado:** saldo de encerramento. **Porquê:** encerramento zera as classes 3 e 4. Medido na change `msc-fonte-e-competencia`.

### D5 — Duas colunas, um mapa
**Escolhido:** as mesmas contas em `exercicio_atual` e `exercicio_anterior`. **Descartado:** outro plano para N−1. **Porquê:** 2024 de João Pessoa e de Porto Alegre fecha com o `I-HI` daquele ano no mesmo mapa.

### D6 — Dezenove linhas, um quadro
**Escolhido:** só `QUADRO_PRINCIPAL`. **Descartado:** as Notas I–XVI. **Porquê:** IPC 05 item 21 diz que os anexos são sugestão.

### D7 — L17 zero
**Escolhido:** prefixo `38` apura 0,00 quando não há movimento. **Descartado:** omitir a regra porque o `I-HI` não publica a linha. **Porquê:** o IPC 05 tem L17. João Pessoa e Porto Alegre 2025 mediram zero.

### D8 — YAML no contrato existente
**Escolhido:** `rule.json` e `policy.json` sem campo novo. `demonstrativo.codigo: DVP`, descrições preenchidas, `review.required: true`, `valid_from: 2020-01-20`, `valid_until: null`. **Descartado:** schema novo e o YAML de uma linha só do GitHub. **Porquê:** BO, BP e BF já carregam esse contrato. Campo fora do schema quebra a carga.

## Arquivos criados / alterados

| Arquivo | Ação |
|---|---|
| `knowledge/sources/ipc05/metadata.yaml` | criar |
| `knowledge/sources/ipc05/extracted.md` | criar, páginas 8–9 |
| `knowledge/policies/ipc05.yaml` | criar |
| `knowledge/rules/dvp/quadro_principal.yaml` | criar |
| `knowledge/indexes/rules_index.json` | regenerar |
| `scripts/validate_rules.py` | **nada** — medido em 2026-10-23: nenhum erro `dvp.*` sem alterar nada |
| `app/services/dvp/quadro_principal.py` | criar |
| `app/domain/bo/saldo.py` | **nada** — o fallback da D3 já está em `:209` com `credora_prefixo` |
| `tests/dvp/` | criar (`conftest.py`, `test_regras.py`, `test_apuracao.py`, `test_conferencia_viva.py`) |
| `pyproject.toml` | alterar, marker `vivo` fora da suíte padrão |
| `tests/test_regras_bf.py` | alterar, `test_dois_documentos_integros` passa a 4 documentos |
| `app/cli/dvp.py` | **não** — vai com o transporte, na change `dvp-no-pipeline` |
| `app/services/pipeline/*` | **não** — change `dvp-no-pipeline` |

## Pendências conhecidas

- Entrada da DVP no `GET /dca/{anexo}`, no resumo e no percurso completo: change `dvp-no-pipeline`, pelo recorte de `bf-no-pipeline`. Recorte por unidade gestora e escolha da origem do exercício anterior: change `dvp-por-unidade-gestora`. Decisão de 2026-10-23: três changes, pela complexidade de cada fatia — o BP juntou apuração e transporte (`bp-apuracao-f1` §2.8) e o BF separou; aqui vale o recorte do BF, porque a DVP ainda precisa de uma terceira fatia por unidade.
- `python -m scripts.validate_rules knowledge` passou a sair com exit 0 em 2026-10-23: os 4 erros pré-existentes do BF (`apenas_natureza` em `ingressos.l27`/`l28` e `dispendios.l60`/`l61`) foram corrigidos em `bf-l28-l61-contas-especificas` §2.3.1, a change que criou o campo. O gate 5.3 desta change volta a ser binário.
- Os cenários medidos contra o SICONFI (João Pessoa e Porto Alegre) vivem em `tests/dvp/test_conferencia_viva.py` sob o marker `vivo` e não entram na suíte padrão — nenhum teste de `tests/bp` ou `tests/bf` vai à rede.
- `4.2.1.7.2` do PDF não existe no `PCASP.md`. Como a exclusão não é executada, a conta não entra na regra.
