# Design — Fonte MSC por demonstrativo e competência mensal

**Change:** `openspec/changes/msc-encerramento-por-demonstrativo/` · **Proposal aprovada em:** 2026-09-14

## Contexto

Hoje o par (matriz, tipo de saldo) está **hardcoded no adapter**: `SiconfiMSC.registros` fixa
`co_tipo_matriz="MSCC"` e `id_tv="ending_balance"`, com o comentário explicando que a DCA é anual.
Isso funcionou enquanto havia um demonstrativo só. Com cinco, e com o BP precisando do saldo
oposto ao dos outros quatro, o par tem de sair da infraestrutura e virar declaração.

A decisão do PO (2026-09-14) é contábil, não técnica: a matriz de encerramento é a base de todos os
demonstrativos; o BP lê a posição **depois** do encerramento porque é ali que o resultado entra no
patrimônio líquido; os demais leem **antes**, porque descrevem o fluxo do exercício.

## Componentes afetados

| Componente | Papel na change |
|---|---|
| `app/domain/*/portas.py` | `FonteSaldos.registros(..., matriz, tipo_saldo)` |
| `app/infra/msc/fonte.py` (novo) | a tabela por demonstrativo, e só ela |
| `app/infra/msc/siconfi.py`, `publicsoft.py`, `cache.py` | tradução do par + retry com backoff |
| `app/services/bo/quadro_principal.py` | pede o par pelo demonstrativo, não pelo adapter |
| `app/services/pipeline/resultado.py` | procedência com matriz, tipo de saldo, competência, classes |

## Fluxo da informação

```text
apurar("BO", ente, exercicio)
        │
        ├─ fonte_de("BO") ──► (encerramento, abertura, classes 5 e 6)
        │
        └─ FonteSaldos.registros(..., matriz, tipo_saldo) ──► adapter traduz ──► MSC
                                                                     │
                                                       procedência registra o par
```

## Contratos / interfaces

```python
# app/infra/msc/fonte.py
class Matriz(StrEnum):      CONSOLIDADA = "consolidada"; ENCERRAMENTO = "encerramento"
class TipoSaldo(StrEnum):   ABERTURA = "abertura"; ENCERRAMENTO = "encerramento"; PERIODO = "periodo"

# Competência 12 — exercício fechado.
ENCERRAMENTO_DO_EXERCICIO = {
    "BO":  (Matriz.ENCERRAMENTO, TipoSaldo.ABERTURA,     (5, 6)),
    "BF":  (Matriz.ENCERRAMENTO, TipoSaldo.ABERTURA,     (1, 2, 3, 4, 5, 6)),
    "BP":  (Matriz.ENCERRAMENTO, TipoSaldo.ENCERRAMENTO, (1, 2)),
    "DVP": (Matriz.ENCERRAMENTO, TipoSaldo.ABERTURA,     (3, 4)),
    "DFC": (Matriz.ENCERRAMENTO, TipoSaldo.ABERTURA,     (1, 2, 3, 4, 5, 6)),
}

# Competências 1-11 não têm MSCE: a leitura é a consolidada, acumulada até o mês.
def fonte_de(demonstrativo: str, competencia: int = 12) -> Fonte: ...
```

Tradução, só no adapter do SICONFI:

| Domínio | `co_tipo_matriz` | `id_tv` |
|---|---|---|
| `consolidada` | `MSCC` | — |
| `encerramento` | `MSCE` | — |
| `abertura` | — | `beginning_balance` |
| `encerramento` | — | `ending_balance` |
| `periodo` | — | `period_change` |

## Impacto

| Eixo | Impacto |
|---|---|
| Banco / migration | nenhum |
| Cache | par **e competência** entram na identidade; entrada cacheada antes da troca deve invalidar. Enquanto `P9` de `plataforma-pipeline-dca` não entrar, resultado mensal não é cacheado |
| Filas / worker | nenhum |
| APIs externas | mesma quantidade de chamadas; muda `co_tipo_matriz` e `id_tv` |
| Regressão | **337 células × 2 entes, zero divergências** — é o gate desta change |

## Decisões

### D1 — O par é propriedade do demonstrativo, não parâmetro de chamada
**Escolhido:** tabela `FONTE_POR_DEMONSTRATIVO`, consultada pelo serviço · **Descartado:** parâmetro
com padrão · **Porquê:** com parâmetro livre, `MSCE` + saldo de encerramento continua exprimível — e
essa combinação erra 47 das 337 células do BO com o total ainda fechando. Amarrar ao demonstrativo
torna o erro impossível de escrever, em vez de improvável.

### D1b — A competência escolhe a matriz, e isso não é configuração
**Escolhido:** `fonte_de(demonstrativo, competencia)` decide `MSCE` em dezembro e `MSCC` nos demais
meses · **Descartado:** exigir que quem chama saiba disso · **Porquê:** medido — a `MSCE` não
responde nas competências 1, 3, 6, 9 e 11 em nenhum dos dois entes sondados. Não é preferência, é
disponibilidade. Quem chama pedindo `MSCE` em junho receberia vazio, e vazio numa apuração vira
demonstrativo zerado, não erro.

### D2 — Vocabulário do domínio, tradução no adapter
**Escolhido:** `matriz` e `tipo_saldo` como enums do domínio · **Descartado:** passar
`co_tipo_matriz`/`id_tv` · **Porquê:** são nomes da API do SICONFI; a PublicSoft usa outros. O
domínio já não conhece HTTP, e não deve passar a conhecer o dicionário de um fornecedor.

### D3 — Classes lidas entram na mesma tabela
**Escolhido:** `(matriz, tipo_saldo, classes)` juntos · **Descartado:** classes no serviço de cada
demonstrativo · **Porquê:** é a mesma decisão — de onde vem o dado — e separar faria o BF declarar
classes num arquivo e a matriz em outro.

### D4 — Retry com backoff entra aqui
**Escolhido:** retry nos adapters, nesta change · **Descartado:** deixar para a F1 do BF ·
**Porquê:** a medição derrubou 2 de ~40 chamadas por reset de conexão. Como a coleta é paginada,
uma falha silenciosa vira matriz incompleta — que é resultado errado com aparência de certo, o
mesmo risco que esta change existe para eliminar.

## Arquivos criados / alterados

| Arquivo | Ação |
|---|---|
| `app/infra/msc/fonte.py` | criar |
| `app/infra/msc/siconfi.py`, `publicsoft.py`, `cache.py` | alterar |
| `app/domain/bo/portas.py` | alterar |
| `app/services/bo/quadro_principal.py` | alterar (competência como parâmetro, `MES_DA_DCA` sai) |
| `app/cli/bo.py` | alterar (`--competencia`) |
| `app/services/pipeline/resultado.py` | alterar (procedência) |
| `tests/msc/test_fonte_por_demonstrativo.py` | criar |
| `tests/bo/test_regressao_matriz.py` | criar (337 células × 2 entes) |
| `docs/validacao-bo-jp-2025.md` | alterar (nota da troca de origem) |

## Pendências conhecidas

- **Critério da MSCE na periodicidade mensal — aguarda o PO, com um ente real de prestação
  mensal.** A regra dos meses 1 a 11 (`MSCC`/encerramento) foi medida em João Pessoa e Cuitegi, que
  prestam contas anualmente; nenhum ente de prestação mensal foi sondado. Se algum publicar `MSCE`
  em competência intermediária, a regra atual lê a matriz errada em silêncio. Detalhe e roteiro de
  verificação em `docs/pendencias-periodicidade-mensal.md`.

- A chave de cache, o job e a rota mensais são `P9` de `plataforma-pipeline-dca` — esta change
  entrega a apuração mensal, não o pipeline mensal.
- O aceite mensal é **coerência**, não gabarito: o `RREO-Anexo 01` do 6º bimestre é anual, e não há
  publicado mensal para conferir célula a célula. Confere-se monotonia dos acumulados e a
  procedência.
- A equivalência entre os pares foi medida em **dois** entes. A regressão roda nos dois; divergência
  em outro ente é achado a registrar, não a acomodar.
