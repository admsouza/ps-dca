# Design — Leitura do DCA restrita às UGs autorizadas

**Change:** `openspec/changes/dca-autorizacao-por-unidade-gestora/` · **Proposal aprovada pelo PO em:** 2026-10-20

## Contexto

A visibilidade de recorte já tem **um único ponto de corte**: `recortes.visiveis`, usado pela
leitura (`_no_recorte`), pelo resumo e pela validação de `anterior_por_recorte`. A change não cria
mecanismo novo — acrescenta uma dimensão ao filtro que já existe e liga o campo `modulos` que o hub
já devolve e o `ps-dca` descarta.

## Componentes afetados

| Componente | Papel na change |
|---|---|
| `app/auth/hub.py` | `autorizar` devolve poderes + módulos + UGs |
| `app/routes/dependencias.py` | guarda os três em `request.state`; `403` sem o módulo `dca` |
| `app/domain/recorte.py` | `visiveis(..., ugs)` — a dimensão nova |
| `app/routes/anexos.py` | repassa `ugs` nas três chamadas de `visiveis` |
| `app/services/pipeline/resumo.py` | idem, no resumo por unidade |

## Fluxo da informação

```text
JWT + id_ente → unidade_autorizada → hub /internal/authorize {poderes, modulos, ugs}
                      |
                      +-- dca ∉ modulos --> 403
                      |
                      v
            request.state.{poderes, modulos, ugs}
                      |
       leitura/resumo/reprocessar → recortes.visiveis(chaves, poder_orgao, poderes, ugs)
                      |
                      +-- ugs == () --> filtro atual, só por poder
                      +-- ugs != () --> ug: ∩ ugs; consolidado/grupos só se cobertos
```

## Contratos / interfaces

```python
# app/auth/hub.py
@dataclass(frozen=True)
class Autorizacao:
    poderes: tuple[str, ...]
    modulos: tuple[str, ...]
    ugs: tuple[str, ...]      # () = sem restrição (legado, adm_sistema, ente sem UG)

async def autorizar(self, sub: str, cod_ibge: str) -> Autorizacao: ...

# app/domain/recorte.py
def visiveis(chaves, unidades: Mapping[str, str], poderes: Iterable[str],
             ugs: Iterable[str] = ()) -> list[str]: ...
```

Regra de `visiveis` com `ugs` preenchido:

1. permitidas por poder, como hoje;
2. interseção das chaves `ug:` com `{f"ug:{u}" for u in ugs}`;
3. `consolidado` e cada grupo `poder:` permanecem **somente** se todas as unidades que eles somam
   estiverem autorizadas. O conjunto somado por grupo já é calculado em `recortes()`.

## Impacto

| Eixo | Impacto |
|---|---|
| Banco / migration | Nenhum. A permissão vive no hub |
| Cache | Nenhum. O recorte é filtrado na leitura; o cache guarda todos os recortes apurados |
| Filas / worker | Nenhum. O worker apura tudo; quem filtra é a leitura |
| APIs externas | Um campo novo lido do `/internal/authorize` |
| Regressão | Usuário com `ugs` vazio tem de sair **bit a bit igual**: golden do payload de BO/BP/BF |

## Decisões

### D1 — Lista vazia é ausência de restrição
**Escolhido:** `ugs == ()` mantém o filtro só por poder. **Descartado:** `()` como "nenhuma UG".
**Porquê:** o PO proibiu revogar acesso de usuário legado na implantação, e `()` é o que o hub
devolve para todo usuário anterior à CH-49.

### D2 — Consolidado e grupos exigem cobertura total
**Escolhido:** com restrição de UG, `consolidado`/`poder:` só aparecem se as UGs autorizadas
cobrirem o que eles somam. **Descartado:** (a) manter o consolidado sempre — vaza o valor das UGs
não autorizadas num único número; (b) esconder sempre — quebraria o Cenário 02 do PO, em que o
mesmo contador responde por todas as UGs.

### D3 — O filtro fica em `visiveis`, não nas rotas
**Escolhido:** estender a função que já é o ponto de corte. **Descartado:** verificar nas rotas.
**Porquê:** leitura, resumo e `anterior_por_recorte` passam todos por ela; filtrar em cada chamador
deixaria um caminho para trás — foi exatamente o defeito da change
`pipeline-anterior-autorizacao-por-poder`.

### D4 — Guard de módulo na dependência de unidade
**Escolhido:** `unidade_autorizada` recusa sem `dca`, já que ela é dependência de toda rota de
anexo. **Descartado:** guard separado por rota. **Porquê:** uma rota nova nasceria sem o guard.

### D5 — `Autorizacao` em vez de tupla de poderes
**Escolhido:** dataclass com os três campos. **Descartado:** devolver uma tupla de três tuplas.
**Porquê:** três posicionais sem nome é o tipo de assinatura que se inverte em silêncio.

## Arquivos criados / alterados

| Arquivo | Ação |
|---|---|
| `tests/test_autorizacao_por_ug.py` | criar |
| `tests/test_guard_modulo_dca.py` | criar |
| `app/auth/hub.py` | alterar |
| `app/routes/dependencias.py` | alterar |
| `app/domain/recorte.py` | alterar |
| `app/routes/anexos.py` | alterar |
| `app/services/pipeline/resumo.py` | alterar |

## Pendências conhecidas

- Recorte `po:` não tem UG; ente sem SIAFIC continua só por poder (declarado na proposal).
- A apuração de produção do guard de módulo é tarefa da change do hub (CH-49, task 7.4) e é
  **gate de deploy** desta.
