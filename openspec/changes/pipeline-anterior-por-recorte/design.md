# Design — Coluna do exercício anterior por unidade

**Change:** `openspec/changes/pipeline-anterior-por-recorte/` · **Proposal aprovada pelo PO em:** 2026-10-13.
**Rascunho:** escrito para dar base à aprovação da proposal. A fase PLAN/ARCH só começa depois do
gate (AGENTS.md §2).

## Contexto

Depois de `pipeline-dca-por-unidade-gestora` e de `bf-por-unidade-gestora`, `com_recortes`
(`app/services/pipeline/apuracao.py`) apura cada recorte com o mesmo `apurar` sobre `_Filtrada` e
força `anterior=msce_exercicio_anterior`.

O que cada serviço já tem:
- BF: `Anterior.MSCE` e `Anterior.MANUAL` (`bf/quadro_principal.py:70`).
- BP: só `PUBLICADO` e `MSCE` (`bp/quadro_principal.py:57`), sem manual.

A identidade do pedido e a reaplicação do que foi digitado moram em `app/services/pipeline/cache.py`:
- `identidade_do_pedido`;
- `parametros_efetivos`;
- `_mapa_salvo`, que hoje lê só a procedência de topo;
- `_parametros_bp`, que hoje não reaplica nada.

O cache tem a chave `(id_ente, an_referencia, anexo)`. O `resultado` JSONB guarda os `recortes`, e
cada um tem `resultado` completo (`resultado.py:143`). A fonte entra só como `f=<fonte>` dentro de
`versao_regras` (`cache.py:94`).

## Componentes afetados

| Componente | Papel na change |
|---|---|
| `app/services/pipeline/anterior.py` (novo) | resolve a origem por unidade; lê N−1 do cache; transpõe a coluna atual para a anterior (com `visoes`, `fonte_vazia` e a união das fontes do Superávit); soma o grupo |
| `app/services/pipeline/apuracao.py` | `com_recortes` pede ao `anterior.py` a origem e a coluna de cada unidade; o grupo recebe a soma |
| `app/services/pipeline/cache.py` | `parametros_efetivos` reconstrói `anterior_por_recorte` a partir das procedências dos recortes gravados; `identidade_do_pedido` ganha `ar-<hash>` das escolhas explícitas; `_parametros_bp` aceita `processado` |
| `app/services/pipeline/completo.py` | o percurso aceita `processado` como origem do BP e reaplica as escolhas gravadas |
| `app/services/pipeline/job.py` | repassa o repositório de cache ao apurador; falha o job quando o `processado` explícito não acha N−1 |
| `app/services/bf/quadro_principal.py` | `Anterior.PROCESSADO`, com `coluna_anterior` pronta (sem leitura de N−1 para ela) |
| `app/services/bp/quadro_principal.py` | `Anterior.PROCESSADO` e **`Anterior.MANUAL`** (novo): folhas por quadro, totalizadoras pela calculation, Superávit pela união das fontes |
| `app/services/bp/informados.py` (novo) | validação do manual do BP antes do job (prefixos `P:`/`FP:`/`C:`/`S:`), espelhando `bf/informados.py` |
| `app/routes/anexos.py` | `anterior_por_recorte` no corpo do `reprocessar` (BF e BP); `409` do `processado` explícito; `processado` em `origem_exercicio_anterior` |
| `app/services/pipeline/resultado.py` | `escolha_anterior`, `anterior_processado` e `valores_anteriores` por recorte |

## Fluxo da informação

```text
POST reprocessar {anterior_por_recorte?}
  → valida chaves, origens e manual por anexo (422)
  → processado explícito sem cache N−1 ok/recorte → 409
  → parametros_efetivos: pedido ∪ escolhas gravadas nas procedências dos recortes → identidade (ar-<hash>)
  → job:
     consolidado: origem do consolidado (processado = recorte "consolidado" de N−1)
     por unidade u:
       escolha(u) = pedido[u] ?? gravada[u] ?? None
       origem(u)  = escolha(u) ?? (processado se cacheN−1 ok e tem u, senão msce [+ motivo])
       processado → transpor(cacheN−1.recortes[u])      # o serviço não apura N−1 para u
       msce       → apurar(..., anterior=msce) sobre _Filtrada(u)   # zero + aviso se N−1 vazio
       manual     → apurar(..., anterior=manual, valores=…)
       explícito processado e N−1 sumiu → job em erro
     por grupo g: Σ folhas das unidades (Superávit: união das fontes); totalizadoras pela calculation
  → grava N: cada recorte com origem, escolha_anterior, anterior_processado/valores_anteriores
```

## Contratos / interfaces

```python
class OrigemAnterior(StrEnum):
    PROCESSADO = "processado_exercicio_anterior"
    MSCE = "msce_exercicio_anterior"
    MANUAL = "manual"

class AnteriorDaUnidade(BaseModel):
    origem: OrigemAnterior
    valores: dict[str, str] | None = None   # obrigatório no manual

anterior_por_recorte: dict[str, AnteriorDaUnidade] | None   # só no reprocessar
```

Procedência por recorte:
- `origem_exercicio_anterior` (resolvida);
- `escolha_anterior` (`{origem, valores?}` explícita, ou `null`);
- no `processado`: `anterior_processado: {exercicio, calculado_em, versao_regras, fonte, estorno_receita_extra?, estorno_despesa_extra?}`.

O `fonte` é o `f=` de `versao_regras` de N−1, ou `null`. Os estornos são os da procedência do
recorte em N−1.

## Impacto

| Eixo | Impacto |
|---|---|
| Banco / migration | nenhum: lê `dca_anexo_cache` de N−1 |
| Cache | sufixo `ar-<hash>` em `versao_regras` só quando houver escolha explícita; sem escolha, a identidade não muda |
| Filas / worker | o job lê uma linha extra do Postgres; a unidade em `processado` não é reapurada para N−1 |
| APIs externas | nenhuma nova |
| Regressão | consolidado bit a bit; unidades sem cache N−1 e sem escolha bit a bit iguais às changes anteriores |

## Decisões

### D1 — Ler N−1 do cache, não reapurar
**Escolhido:** a coluna atual do resultado `ok` de N−1. **Descartado:** reapurar N−1 no job, o que
a `msce` já faz. **Porquê:** o PO quer o retrato do que foi apurado, com estorno, G8 e manual daquela
época.

### D2 — Padrão decidido no job, por unidade
**Escolhido:** o job olha o cache de N−1 e decide a origem de cada unidade sem escolha.
**Descartado:** o front decidir. **Porquê:** a origem certa depende do que existe no cache no
momento do job, e o front não sabe disso.

### D3 — `409` só no `processado` explícito; erro no job se N−1 sumir
Quando o pedido não escolhe, a ausência de N−1 cai em `msce`, com o motivo registrado. Quando o
pedido escolhe `processado` **agora**, a ausência é um erro do pedido: `409` na rota e `erro` no
job, se a situação mudar entre os dois. Uma escolha `processado` **gravada** (não pedida agora) sem
N−1 cai em `msce`, com o motivo registrado. Sem isso, um N−1 apagado travaria todo job seguinte,
inclusive o percurso e o reprocessamento de outra UG. **Descartado:** cair em `msce` também no explícito, o que entregaria
outra coisa do que foi pedido sem avisar.

### D4 — Grupo = soma das unidades
**Escolhido:** a soma das folhas, com o Superávit pela união das fontes, e as totalizadoras pela
calculation. **Descartado:** o grupo com origem própria (`msce` do filtro do grupo), que divergiria
das UGs mostradas sempre que uma delas fosse manual ou processada. **Premissa verificada:** BF e BP
não têm linha condicional (`condition` só existe no YAML do BO). Um teste compara o grupo somado com
o grupo filtrado em `msce`. Isso é diferente do BO, em que somar recortes é proibido.

### D5 — Uma regra para o BF e o BP
`anterior.py` não conhece anexo: recebe as matrizes e o mapa. Cada serviço ganha só a origem
`PROCESSADO`, com a coluna pronta, e o BP ganha o `MANUAL`. **Descartado:** implementar no BF e no
BP em separado.

### D6 — Processado aceita N−1 de outra fonte
**Escolhido:** aceitar e declarar `anterior_processado.fonte` (PO 2026-10-13). **Descartado:**
exigir a mesma fonte. **Porquê:**
- o Processado é o retrato do que foi apurado;
- as unidades não se misturam, porque `ug:` ≠ `po:`, e só o consolidado cruza fontes;
- há evidência de que o consolidado é igual nas duas fontes: Cuitegi 2025 `L27` = 4.486.188,21 nas
  duas (`bf-estorno-siconfi`).

### D7 — Cache sem chave por fonte
**Escolhido:** manter `(ente, exercício, anexo)`, em que vale o último processamento (PO
2026-10-13). **Descartado:** a fonte na chave, que exige migration em banco compartilhado sem nenhum
requisito que peça as duas fontes ao mesmo tempo. A troca de fonte já aparece como `desatualizado`
(`pipeline-visualizar-sem-reprocessar`).

### D8 — "Não pelo SICONFI" = não pela DCA publicada
Na `msce`, a unidade lê a MSC da fonte do pedido, o que inclui a MSC do SICONFI no `po:`. O
`publicado_siconfi` nunca vale fora do consolidado (PO 2026-10-13).

### D9 — Toda escolha explícita persiste; o padrão não
**Escolhido:** a procedência de cada recorte grava `escolha_anterior`, e `parametros_efetivos` a
reconstrói, então o percurso e um reprocessar parcial reaplicam o que o usuário escolheu. A origem
resolvida pelo padrão não entra na identidade. **Descartado:** persistir só o manual, o que faria a
escolha `msce` ou `processado` de uma UG voltar ao padrão quando outra UG é reprocessada.
`{"origem": "padrao"}` limpa a escolha. A escolha gravada de uma unidade que não existe mais no
job, por exemplo depois de trocar a fonte (`ug:` → `po:`), é descartada sem aviso e sai do
`ar-<hash>`. As escolhas também ficam na procedência de topo
(`procedencia.anterior_por_recorte`, `{chave: {origem, valores?}}`): o job em erro zera o
`resultado` mas preserva a procedência, e `parametros_efetivos` lê de lá, com os recortes como
fallback para cache gravado antes disso.

### D10 — Manual do BP por prefixo de quadro
**Escolhido:** `P:`, `FP:`, `C:` e `S:<fonte>`, porque os códigos `L<n>` se repetem entre os quadros
do BP. É o mesmo formato do anexo do BF (`A:L1:receita`). **Descartado:** `rule_id` como chave, que é
estável mas ilegível para quem digita e para o front.

## Arquivos criados / alterados

| Arquivo | Ação |
|---|---|
| `app/services/pipeline/anterior.py` | criar |
| `app/services/bp/informados.py` | criar |
| `app/services/pipeline/apuracao.py` | alterar |
| `app/services/pipeline/cache.py` | alterar |
| `app/services/pipeline/completo.py` | alterar |
| `app/services/pipeline/job.py` | alterar |
| `app/services/pipeline/resultado.py` | alterar |
| `app/services/bf/quadro_principal.py` | alterar |
| `app/services/bp/quadro_principal.py` | alterar |
| `app/routes/anexos.py` | alterar |
| `tests/recorte/test_anterior_por_recorte.py` | criar |
| `tests/bp/test_anterior_manual.py` | criar |
| `tests/pipeline/test_rota_anterior_por_recorte.py` | criar |
| `tests/pipeline/test_identidade_anterior_por_recorte.py` | criar |

## Pendências conhecidas

- **N−1 processado depois de N.** N foi para `msce` por falta de N−1, e não é marcado como
  desatualizado, porque a origem resolvida não entra na identidade. Reprocessar N passa a usar o
  `processado`.
- **N−1 reprocessado depois.** A peça de N continua com o retrato antigo. Candidato:
  `motivos_desatualizado += "anterior_processado"` quando o `calculado_em` de N−1 mudar. Fica fora
  até o PO pedir.
- **`ID_INSTITUICAO` estável entre exercícios.** Medir em Cuitegi 2024 × 2025. É pendência herdada
  da change de UG.
- **N−1 em cache `desatualizado`** (regra antiga). Ele é usado assim mesmo, por ser um retrato, e a
  procedência mostra a `versao_regras`. Confirmar com o PO.
- **Manual no consolidado do BP:** fora, até o PO pedir.
