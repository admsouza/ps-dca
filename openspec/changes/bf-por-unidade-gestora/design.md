# Design — Balanço Financeiro por unidade gestora

**Change:** `openspec/changes/bf-por-unidade-gestora/` · **Proposal aprovada pelo PO em:** 2026-10-13.
**Rascunho:** escrito para dar base à aprovação da proposal. A fase PLAN/ARCH só começa depois do
gate (AGENTS.md §2).

## Contexto

- `RECORTAVEIS = ("BO", "BP")` em `app/services/pipeline/apuracao.py:117`. O BF ficou de fora
  porque o estorno era tratado como escalar do ente.
- `PublicSoftMSC.estorno_*` (`app/infra/msc/publicsoft.py`) lê só o `data.totalGeral`.
- `_abater_estorno` (`app/services/bf/quadro_principal.py`) abate esse escalar.
- `_Filtrada` repassa `estorno_*` direto para a fonte. Com recortes, cada um refaria as chamadas e
  abateria o total do ente.
- `com_recortes` força `anterior=msce_exercicio_anterior` nos recortes, mas só remove `dca` dos
  extras (`apuracao.py:186-187`). `valores_anteriores` e `valores_sem_mapeamento` vazariam para as
  unidades.

O relatório do `ps-erp` já devolve `totaisPorUnidadeGestora` por `ID_INSTITUICAO`, que é a mesma
chave de `Registro.unidade_gestora`.

## Componentes afetados

| Componente | Papel na change |
|---|---|
| `app/infra/msc/publicsoft.py` | `estorno_*` devolve `Estorno(total, por_unidade, poder_orgao)` |
| `app/services/pipeline/apuracao.py` | `_NoEscopo` memoriza o estorno; `_Filtrada` restringe o estorno ao recorte; `_Observada` anota as unidades por exercício; `"BF"` em `RECORTAVEIS`; os recortes não recebem `valores_anteriores` nem `valores_sem_mapeamento`; `estorno_sem_unidade` |
| `app/services/bf/quadro_principal.py` | `_abater_estorno` usa `Estorno.total`; parâmetro `g8_so_no_consolidado` (marca as linhas G8 não apuradas com o motivo) |
| `app/services/pipeline/resultado.py` | `estorno_sem_unidade` no diagnóstico |
| `app/routes/anexos.py` | `recorte` aceito no BF; `avisoRecorte` calculado na leitura de BO/BP/BF (fonte SICONFI + token resolvido + recortes `po:`) |

## Fluxo da informação

```text
job BF
  _NoEscopo.estorno_receita_extra(2025) → GET sintetico (1×, memorizado)
      → Estorno(total=115679.40, por_unidade={"ug:1": …, "ug:3": …}, poder_orgao={"ug:1": "10131", …})
  consolidado: abate Estorno.total; G8 e manual como hoje            # bit a bit igual
  recorte R = _Filtrada(fonte, unidades); extras sem valores_anteriores/valores_sem_mapeamento;
              anterior = msce; marcar G8 "informado só no consolidado"
      estorno_*(ano) → Estorno(total = Σ por_unidade[u] para u ∈ R)                # ug:
                                     Σ por_unidade[i] com poder_orgao[i] == código # po:
  sem_unidade(ano) = ug: por_unidade − unidades observadas em ano
                     po: poder_orgao nulo, ou PO não observado em ano
      → diagnostico.estorno_sem_unidade (consolidado)
```

## Contratos / interfaces

```python
@dataclass(frozen=True)
class Estorno:
    total: Decimal
    por_unidade: dict[str, Decimal]          # "ug:<idInstituicao>"
    poder_orgao: dict[str, str | None] | None  # None = campo ausente (ps-erp antigo)
```

No recorte `po:`, `_Filtrada` soma `por_unidade` onde `poder_orgao[u]` é o código do recorte. Com
`poder_orgao is None` e `total > 0`, `estorno_*` levanta `EstornoSemPoderOrgao`, e o BF trata isso
**no recorte**: `L27`/`L60` não apuradas.

`_Observada` passa a guardar as unidades **por exercício**, porque o estorno sem unidade é por ano.
Num job por UG (algum registro de N com UG), os registros de N−1 sem UG não viram unidade.

## Impacto

| Eixo | Impacto |
|---|---|
| Banco / migration | nenhum |
| Cache | o BF passa a gravar `recortes`; um cache de BF antigo responde `409` para recorte ≠ consolidado (regra existente) |
| Filas / worker | N apurações do BF em memória por job; zero chamada extra de fonte e de estorno |
| APIs externas | lê os novos campos do relatório; `poderOrgao` depende do `ps-erp` |
| Regressão | BF consolidado bit a bit, nas duas fontes, com e sem token |

## Decisões

### D1 — Estorno filtrado no mesmo lugar que os registros
**Escolhido:** `_Filtrada` restringe também o estorno, e o BF continua sem saber o que é recorte.
**Descartado:** parâmetro `recorte` no serviço do BF, que repetiria a noção de recorte dentro do
anexo (D1 da change de UG). A exceção é o motivo do G8: o BF recebe `g8_so_no_consolidado`, um
booleano sobre o motivo e não sobre o recorte. A alternativa, reescrever as não apuradas em
`com_recortes`, duplicaria o conhecimento de quais linhas são G8.

### D2 — Uma chamada por exercício, total e por unidade juntos
**Escolhido:** o sintético sem `idInstituicao`, que já traz as duas coisas, memorizado no escopo.
**Descartado:** `?idInstituicao=` por recorte (N chamadas).

### D3 — Estorno sem unidade no diagnóstico, sem rateio
**Escolhido:** declarar e não falhar (PO 2026-10-13), por UG e por PO. **Descartado:** falhar o job
ou ratear entre as UGs. O consolidado está certo, e só a soma das unidades não fecha, de forma
explicada.

### D4 — PO pelo `ps-erp`
**Escolhido:** `poderOrgao` em `totaisPorUnidadeGestora`, derivado de `TIPO_INSTITUICAO` pela tabela
que o balancete do `ps-erp` já usa (PO 2026-10-13). **Descartado:** `L27`/`L60` brutas no `po:`.
Campo ausente e valor `null` são tratados de forma diferente: o ausente indica um `ps-erp` antigo, e
o `null` é uma instituição sem PO.

### D5 — Valores digitados só no consolidado
O anterior manual e o G8 foram digitados para o ente. Distribuí-los inventaria um número da UG. Os
recortes saem com o anterior pela MSC, que é a regra da change de UG estendida ao BF.

### D6 — Ente com SIAFIC pela MSC: PO com aviso, calculado na leitura
**Escolhido:** a leitura calcula `avisoRecorte` com fonte SICONFI, token resolvido e recortes `po:`
(PO 2026-10-13). O `GET` com `use_siconfi=true` já resolve o token (`fonte_do_pedido` →
`_token_opcional`). Não há estado novo, e funciona com cache antigo.
**Descartado:** gravar um flag no job, que é estado a mais para o mesmo resultado.
**Descartado:** bloquear o recorte, que tiraria do Legislativo a própria peça (`po:20231` = Câmara)
só por causa da fonte.
Ente CSV não tem token (`siafic_disponivel=false`), e com o hub fora o token também falta. Nesses
dois casos não há aviso. É aceitável: o aviso é informativo, e o próprio BF já sai sem estorno,
declarado na procedência.

## Arquivos criados / alterados

| Arquivo | Ação |
|---|---|
| `app/infra/msc/publicsoft.py` | alterar |
| `app/services/pipeline/apuracao.py` | alterar |
| `app/services/bf/quadro_principal.py` | alterar |
| `app/services/pipeline/resultado.py` | alterar |
| `app/routes/anexos.py` | alterar |
| `tests/recorte/test_bf_estorno_por_unidade.py` | criar |
| `tests/msc/test_estorno_por_unidade.py` | criar |
| `docs/entes-homologacao/cuitegi/auditoria-recorte-2025.md` | alterar: BF por UG |

## Pendências conhecidas

- Confirmar em Cuitegi que toda `idInstituicao` com estorno existe na base `unidades-gestoras`.
- `bf-estorno-siconfi` aguarda o PO. A regra do SICONFI com token vale igual por recorte.
