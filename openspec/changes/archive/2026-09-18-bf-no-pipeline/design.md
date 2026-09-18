# Design — Balanço Financeiro no pipeline

## Componentes afetados

| Arquivo | Mudança |
|---|---|
| `app/services/pipeline/apuracao.py` | `_ComCache.registros` repassa `matriz` e `tipo_saldo` |
| `app/services/pipeline/registry.py` | entrada `BF` com serviço |
| `app/services/pipeline/resultado.py` | ordem de apresentação por demonstrativo; campos novos |
| `app/services/pipeline/cache.py` | origem da coluna anterior na identidade do resultado |
| `app/services/pipeline/job.py` | parâmetros do BF no job genérico |

Nada em `app/domain/` e nada em `app/services/bf/`: esta change transporta o que a F1 já produz.

## Decisões

### D1 — O envelope de cache repassa o par de leitura

`ler_ou_baixar` já aceita `matriz` e `tipo_saldo` e já os inclui na chave; quem os perde é
`_ComCache.registros`, escrito quando só existia o BO. A correção é repassá-los.

Por que é a decisão mais importante da change: o defeito **não levanta exceção**. O BF pediria as
três origens e receberia três vezes a mesma, e `L25`, `L26` e `L29`–`L32` sairiam com números
plausíveis e errados. Por isso o teste da 1.1 assere os **parâmetros recebidos pela fonte**, não o
valor apurado — um teste de valor passaria com dado sintético igual nas três origens.

### D2 — A ordem de apresentação é dado do demonstrativo

Hoje `ORDEM_QUADROS` e `ORDEM_GRUPOS` são constantes do serializador, com os nomes do IPC 07. O BF
usa `INGRESSOS`/`DISPENDIOS` e `QUADRO_ANEXO`.

Alternativas consideradas:

| Opção | Por que não |
|---|---|
| acrescentar os grupos do BF às constantes | funciona até o terceiro demonstrativo; a cada anexo novo o serializador aprende mais um vocabulário que não é dele |
| ordenar pela árvore de composição | medido no BO: dá resultado diferente do declarado (`Reserva do RPPS` é nível 2 na norma e 1 na composição) |
| **ordem declarada pelo demonstrativo** (escolhida) | o serializador passa a receber a ordem, e cada demonstrativo declara a sua ao lado das regras |

O fallback atual — quadro ou grupo desconhecido vai para o fim, sem quebrar — permanece: é o que
evita que um anexo novo derrube a serialização.

### D3 — A origem da coluna anterior entra na identidade do resultado

`versao_api` e `versao_regras` já invalidam o cache quando código ou regra mudam. A origem da
coluna do exercício anterior muda **o valor** sem mudar nenhum dos dois, então entra na chave. No
modo manual, entra também a identidade do conjunto informado (hash dos pares linha/valor): dois
preenchimentos diferentes são resultados diferentes.

### D4 — O job continua sendo um só

`apurar_anexo` é parametrizado por anexo (P4 da plataforma). O BF acrescenta parâmetros
(competência já existia; origem da coluna anterior é nova), que viajam no payload do job — nenhum
job novo.

## Fluxo

```text
GET /anexos/BF?ente&exercicio&competencia
  -> registry.validar_anexo("BF")            # canoniza e recusa desconhecido
  -> cache.decidir(chave com versao_regras + origem da coluna anterior)
       hit  -> resultado servido
       miss -> job apurar_anexo{anexo:"BF"} -> worker
                 -> apuracao.fonte(...)  (com cache de dados, agora com matriz/tipo_saldo)
                 -> services.bf.quadro_principal.apurar(...)
                 -> resultado.serializar(mapa, matriz, procedencia, diagnostico)
```

## Arquivos criados ou alterados

**Alterados:** `app/services/pipeline/{apuracao,registry,resultado,cache,job}.py`
**Criados:** `tests/pipeline/test_bf_no_pipeline.py`

## Impacto

- **Banco:** nenhum — o registro de cache já é genérico por anexo.
- **Cache:** chave ganha um componente; entradas antigas do BO não são invalidadas (o componente é
  vazio para quem não tem coluna anterior).
- **APIs externas:** nenhuma chamada nova; a correção do D1 muda **quais** leituras são feitas.
