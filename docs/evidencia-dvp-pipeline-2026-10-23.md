# Evidência — DVP (`I-HI`) apurada pelo pipeline, ente real

**Data:** 2026-10-23 · **Ambiente:** containers `dca_api`/`dca_worker` reconstruídos do código desta
branch (`docker compose build api worker && up -d`) · **Fonte:** SICONFI · **Ente:** João Pessoa/PB
(`2507507`), exercício 2025.

Caminho exercitado: `apurador("I-HI")` — o mesmo que o worker executa —, passando por registry,
base canônica, carregador de regras, leitura da MSC e `com_recortes`. Sem HTTP (a camada de
autorização não foi exercitada aqui).

## Registry e listas

```
anexos:        ('BO','BF','BP','I-AB','I-C','I-D','I-E','I-F','I-G','I-HI')
I-HI       ->  app.services.dvp.quadro_principal:apurar | base: dvp | job: apurar_anexo
RECORTAVEIS:   ('BO','BP','BF','I-HI')
COM_UNIDADES:  ('BF','BP','I-HI')
```

## Consolidado

`19 linhas · IPC05 2020-01 · matriz encerramento · saldo abertura · classes [3, 4]`

| Linha | `exercicio_atual` | `I-HI` publicado |
|---|---:|---:|
| L1 VPA | 17.319.103.824,61 | igual |
| L2 | 397.963.739,37 | igual |
| L6 | 11.722.481.279,59 | igual |
| L9 VPD | 17.046.926.343,10 | igual |
| L14 | 9.199.369.111,48 | igual |
| L19 | 272.177.481,51 | igual |

`diagnostico.nao_apuradas` vazio, `sem_dados` falso.

## Recortes (change `dvp-por-unidade-gestora`)

Chaves produzidas: `po:10131`, `po:10132`, `po:20231`, `poder:executivo`, `poder:legislativo`,
`poder:executivo+legislativo` — `po:` porque a fonte é o SICONFI, que não informa unidade gestora.

| Linha | Consolidado | Σ das unidades | Diferença |
|---|---:|---:|---:|
| L1 | 17.319.103.824,61 | 17.319.103.824,61 | **0,00** |
| L9 | 17.046.926.343,10 | 17.046.926.343,10 | **0,00** |
| L19 | 272.177.481,51 | 272.177.481,51 | **0,00** |

## Coluna do exercício anterior: 0,00, e por quê

Pelo pipeline, a coluna anterior do consolidado sai `0,00`, com
`procedencia.origem_exercicio_anterior: "soma_das_unidades"` e
`diagnostico.sem_dados_exercicio_anterior: true`. Cada unidade sai com
`origem: "sem_anterior"`.

**Não é defeito da DVP.** O BP, no mesmo ente e exercício, responde igual: `L1` anterior `0,00`,
`origem: soma_das_unidades`, `sem_dados_exercicio_anterior: true`. É a regra de
`pipeline-consolidado-anterior-soma-unidades`: o consolidado não tem origem própria, e nenhuma
unidade tem processado de N−1 no cache nem MSC de N−1 por `po:`.

Pelo CLI (`python -m app.cli.dvp 2507507 2025`), que apura o consolidado direto em `MSCE` sem
recortes, a coluna anterior é **16.327.833.858,41**. A diferença entre os dois caminhos é de
desenho do pipeline, não de apuração — quem consome a API precisa ler
`sem_dados_exercicio_anterior` em vez de supor que `0,00` é posição real.

## O que esta medição **não** cobre

- Recorte `ug:` (base por unidade gestora da PublicSoft): exige `token_ps`, indisponível na sessão.
- A rota HTTP e a autorização por unidade no hub.
