# Design — DCA processada com todas as unidades, emitida por recorte

**Change:** `openspec/changes/pipeline-dca-por-unidade-gestora/` · **Proposal aprovada pelo PO em:** 2026-10-09
**Revisão de 2026-10-09:** o PO trocou a "seleção de conjunto arbitrário de UGs" por **consolidado, grupo de poder ou uma unidade**. Saíram a composição na API, a separação do motor em folhas/composição e o delta em `pipeline/plataforma`.
**Irmãs:** `regras-rgf-api` CH-46 (`poderes` no `/internal/authorize`) · `front-declaracoes` `dca-recorte-unidade-gestora`

## Contexto

O job já roda dentro de `escopo()` (`app/infra/msc/escopo.py`). Toda leitura da fonte passa por
`_NoEscopo` (`app/services/pipeline/apuracao.py:77`) e fica memorizada até o fim do job. Uma segunda
chamada a `apurar(...)` no mesmo job **não consulta a fonte de novo**.

Por isso, apurar um recorte é chamar o mesmo serviço de hoje com uma fonte que **filtra** os
registros. O BO e o BP não mudam, nem o motor, e Déficit e Superávit continuam corretos, porque cada
recorte é uma apuração completa.

## Componentes afetados

| Componente | Papel |
|---|---|
| `app/domain/bo/modelo.py` | `Registro` ganha `unidade_gestora` e `nome_unidade_gestora` (default `""`) |
| `app/infra/msc/normalizacao.py` | mapeia `idUnidadeGestora` e `nomeUnidadeGestora` |
| `app/infra/msc/publicsoft.py` | lê `…/base-demonstrativos/unidades-gestoras`; se responder `422`, usa a base oficial |
| `app/domain/recorte.py` (novo) | chave da unidade, grupos de poder, recortes visíveis por poder |
| `app/services/pipeline/apuracao.py` | depois do consolidado, apura cada recorte com a fonte filtrada (BO e BP) |
| `app/services/pipeline/resultado.py` | serializa `recortes` |
| `app/auth/hub.py`, `app/routes/dependencias.py` | `poderes` do hub em `request.state` |
| `app/routes/anexos.py` | `recorte` no `GET`, padrão do poder, `recortesDisponiveis` |

## Fluxo da informação

```text
job (escopo aberto)
  apurar(ente, ano, fonte=Observada(fonte))           → consolidado (igual a hoje) + unidades vistas
  para cada recorte (grupos de poder + unidades):
      apurar(ente, ano, fonte=Filtrada(fonte, recorte), anterior=MSCE no BP)   → leitura memorizada, sem HTTP
  cache.resultado = consolidado + "recortes": {chave: para_dados(resultado do recorte)}

GET /dca/BP?recorte=ug:3
  unidade_autorizada (hub: vínculo + poderes) → cache ok
  → chave visível? (403) existe? (404) → corpo = resultado["recortes"][chave] → 200, sem cálculo
```

## Contratos / interfaces

```python
# app/domain/recorte.py
EXECUTIVO, LEGISLATIVO = ("10131", "10132"), ("20231",)

def unidade(registro: Registro) -> str:
    """'ug:<id>' se o registro traz UG; senão 'po:<poder_orgao>' ('po:' sem código, se vazio)."""

def grupos(unidades: dict[str, str]) -> dict[str, set[str]]:
    """{unidade: poder_orgao} → {'poder:executivo': {...}, 'poder:legislativo': {...},
    'poder:executivo+legislativo': {...}}. Unidade com PO fora da tabela fica fora."""

def visiveis(chaves: Iterable[str], unidades: dict[str, str], poderes: Iterable[str]) -> list[str]
def padrao(poderes: Iterable[str]) -> str | None     # None → 403
```

```python
# app/services/pipeline/apuracao.py — envolvem _NoEscopo, sem saber da fonte real
class _Observada:  # repassa registros() e anota {unidade: (nome, poder_orgao)}
class _Filtrada:   # repassa registros() só dos registros cujas unidades estão no recorte
```

Formato no JSONB (`dca_anexo_cache.resultado`):

```json
{ "...corpo consolidado de hoje...": "",
  "recortes": {
    "poder:executivo": {"linhas": [], "matriz": {}, "procedencia": {}, "diagnostico": {}, "visoes": {}},
    "ug:3": {"...": "", "rotulo": "Fundo Municipal de Saúde", "poderOrgao": "10131"}
  } }
```

## Impacto

| Eixo | Impacto |
|---|---|
| Banco / migration | Nenhum. A chave nova vai no JSONB, e a PK não muda |
| Cache | `VERSAO_API` muda, então BO e BP em cache saem `desatualizado` (motivo `versao_api`) e continuam legíveis. Com recorte, ou para usuário sem `consolidado`, a leitura dá `409` até reprocessar |
| Tamanho | Cerca de 15 KB por recorte. Cuitegi (4 UGs + 3 grupos) fica em ~120 KB; 20 UGs, em ~350 KB por anexo |
| CPU do job | 1 + n + 3 apurações em memória. Cada registro entra em 1 unidade e em até 2 grupos, então o custo fica em torno de 4 vezes o de hoje. É desprezível perto do HTTP |
| APIs externas | PublicSoft: endpoint por UG, com os mesmos parâmetros e timeout. BP com origem `publicado_siconfi`: +1 leitura do ano anterior (4 classes), memorizada para todos os recortes. Hub: lê o corpo do `200` |
| Leitura | Busca por chave no JSON, sem cálculo e sem fonte |
| Regressão | Recorte `consolidado` (padrão de quem tem esse poder): bit a bit igual. BF intacto (não recebe recortes) |

## Decisões

### D1 — Recorte = mesma apuração sobre fonte filtrada
**Escolhido:** `_Filtrada` sobre `_NoEscopo`, chamando o mesmo `apurar` do anexo.
**Descartado:**
- Folhas por unidade com composição na leitura: exigia mexer no motor e calcular na API. O PO
  dispensou a seleção arbitrária.
- Parâmetro novo nos serviços BO/BP: espalharia a noção de recorte por dois serviços.

### D2 — Unidades descobertas na apuração do consolidado
**Escolhido:** `_Observada` anota as unidades de todo registro lido pelo consolidado, inclusive o
ano anterior do BP. Não há leitura extra para descobrir unidades.
**Descartado:** reler as classes para listar unidades. É grátis por causa da memória do job, mas
duplica o conhecimento de quais classes cada anexo lê.

### D3 — Tipo da unidade inferido do registro
`ug:` se o registro traz UG, `po:` caso contrário. O domínio não sabe qual fonte respondeu.

### D4 — PublicSoft lê a base por UG, com recuo explícito
**Escolhido:** `registros()` chama `…/unidades-gestoras`. Se a resposta for `422`, chama a base
oficial e registra `warning`. A decisão fica memorizada no escopo, para não repetir o `422` por
classe. O `409` continua sendo conjunto vazio.
**Nota:** hoje o ente só-CSV nem chega à PublicSoft, porque o hub responde `siafic_disponivel=false`
e a rota dá `409`. O recuo existe para não quebrar o consolidado de um ente SIAFIC com MSC importada.

### D5 — BP fora do consolidado: anterior pela MSC
O recorte chama o BP com `anterior=msce_exercicio_anterior`. Com isso, `conferencia_publicado` fica
só no consolidado.

### D6 — Um parâmetro, chave com prefixo
**Escolhido:** `recorte=consolidado|poder:<…>|ug:<id>|po:<código>`. O prefixo impede ler um id de UG
como código de PO. O front recebe a lista pronta em `recortesDisponiveis` e só devolve a `chave`.
**Descartado:** `ug=`, `po=` e `poder=` separados: três validações e combinações inválidas a tratar.

### D7 — Poderes vêm do hub, junto com a autorização
`AutorizadorHub.autorizar` devolve `poderes` (CH-46), e `unidade_autorizada` guarda em
`request.state.poderes`. Os casos especiais são:
- Hub sem o campo, antes da CH-46: `[]`, e só `consolidado` explícito fica de fora (fail closed).
- Modo local, sem hub: `["consolidado"]`, com `warning`.

### D8 — Sem conferência extra no job
**Escolhido:** nenhuma conferência entre os recortes e o consolidado. A partição é completa por
construção: cada registro cai em exatamente uma unidade. Somar as UGs e comparar com a base oficial
é o GATE 3 do `ps-erp`, que já responde `409` quando diverge. Um teste cobre a partição.
**Descartado:** gate no job. Duplicaria o do `ps-erp`, e no BO daria falso alarme por causa do
Déficit e do Superávit.

## Arquivos criados / alterados

| Arquivo | Ação |
|---|---|
| `app/domain/bo/modelo.py` | alterar: 2 campos com default |
| `app/infra/msc/normalizacao.py` | alterar: `CAMPOS` de UG |
| `app/infra/msc/publicsoft.py` | alterar: D4 |
| `app/domain/recorte.py` | criar |
| `app/services/pipeline/apuracao.py` | alterar: `_Observada`, `_Filtrada`, laço dos recortes (BO e BP) |
| `app/services/pipeline/resultado.py` | alterar: `recortes` |
| `app/auth/hub.py` | alterar: `autorizar` devolve `poderes` |
| `app/routes/dependencias.py` | alterar: `request.state.poderes` |
| `app/routes/anexos.py` | alterar: `recorte`, padrão do poder, `recortesDisponiveis` |
| `tests/recorte/test_*.py` | criar |
| `docs/entes-homologacao/cuitegi/auditoria-recorte-2025.md` | criar: medições |

## Pendências conhecidas

- O `ID_INSTITUICAO` estável entre exercícios é premissa da coluna anterior por UG. Medir em Cuitegi 2024 × 2025.
- Medir o tempo do `/unidades-gestoras` do `ps-erp` em João Pessoa antes de liberar (tarefa 4.5).
- Sem a CH-46 em produção, usuário sem `consolidado` não vê nada.
