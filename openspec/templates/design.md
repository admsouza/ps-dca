# Design — <título curto>

**Change:** `openspec/changes/<slug>/` · **Proposal aprovada pelo PO em:** <data>

## Contexto

<Estado atual relevante e a restrição que força o desenho.>

## Componentes afetados

| Componente | Papel na change |
|---|---|
| `app/routes/<...>` | <...> |
| `app/services/<...>` | <...> |
| `worker.py` | <...> |

## Fluxo da informação

```text
<rota> → <validação> → <job/fila> → <service/cálculo> → <cache> → <leitura>
```

## Contratos / interfaces

<Assinaturas, schemas Pydantic, formato de cache, chaves.>

## Impacto

| Eixo | Impacto |
|---|---|
| Banco / migration | <tabela, coluna, índice; reversibilidade> |
| Cache | <chave, invalidação> |
| Filas / worker | <job novo, concorrência, lock> |
| APIs externas | <endpoint, timeout, paginação> |
| Regressão | <o que precisa sair bit a bit igual> |

## Decisões

### D1 — <decisão>
**Escolhido:** <opção> · **Descartado:** <alternativa> · **Porquê:** <trade-off real>

### D2 — <decisão>
...

## Arquivos criados / alterados

| Arquivo | Ação |
|---|---|
| `<caminho>` | criar / alterar / remover |

## Pendências conhecidas

- <lacuna assumida conscientemente e quando resolver>
