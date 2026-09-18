# Design — Competência de encerramento por fonte de MSC

## Componentes afetados

| Arquivo | Mudança |
|---|---|
| `app/infra/msc/publicsoft.py` | `_competencia(mes, matriz)`; saldos e auditoria na mesma competência |
| `app/infra/msc/fonte.py` | comentário declarando que o número é vocabulário de API |
| `tests/msc/test_competencia_de_encerramento.py` | novo, 4 cenários |

## Decisão — a tradução mora no adapter

O domínio já expressa a leitura como competência mais matriz, e cada adapter traduz o resto do
vocabulário: o SICONFI recebe `co_tipo_matriz` e `id_tv`, a PublicSoft recebe `tipoMatriz` e
`idTv`. A competência da matriz de encerramento é mais um item dessa lista — não uma exceção.

Alternativas descartadas:

| Opção | Por que não |
|---|---|
| `COMPETENCIA_DE_ENCERRAMENTO = 13` no domínio | quebraria o SICONFI, onde 13 devolve zero registros — e zero numa apuração vira demonstrativo zerado, não erro |
| parâmetro de configuração por ambiente | a diferença é da API, não do ambiente; configuração erraria em quem usa as duas fontes |

## Risco coberto

O gate de auditoria era consultado na competência recebida do domínio. Lendo o encerramento na 13 e
auditando a 12, uma competência seria liberada pela validação de outra — e o efeito seria servir
dado não validado, silenciosamente. Por isso `_competencia` é aplicada **antes** do gate.
