# Design — Apuração da DFC (F1)

**Change:** `openspec/changes/dfc-apuracao-f1/` · **Proposal:** aguardando PO

## Contexto

BO, BF, BP e DVP apuram uma linha por regra YAML, pelo mesmo motor (`app/domain/bo/matriz.py` +
`saldo.py`). As 84 regras da DFC já estão validadas e indexadas
(`ipc08-dfc-regras-canonicas`, arquivada em 2026-10-26). O par fonte já está decidido e testado:
`fonte_de("DFC")` = `MSCE` / abertura / classes 1–6 (`app/infra/msc/fonte.py:48`,
`tests/msc/test_fonte_por_demonstrativo.py:32`).

O motor **já suporta** o que a DFC pede e os outros não usavam: `filters` `in`/`not_in` sobre
`natureza_receita`, `natureza_despesa`, `funcao` e `subfuncao`, com casamento por prefixo e
coringa `x` (`app/domain/bo/saldo.py:31-99`). Isso foi verificado na medição, não suposto — `L14`
saiu 115.727.775,84 com os quatro filtros aplicados.

## Componentes afetados

| Componente | Papel |
|---|---|
| `app/services/dfc/quadro_principal.py` | **criar** — apuração das 84 linhas |
| `app/services/dfc/informados.py` | **criar** — whitelist `{L16, L21, L30}` e validação |
| `app/cli/dfc.py` | **criar** — espelho de `app/cli/dvp.py` |
| `app/services/pipeline/apuracao.py` | 1 linha: `services/dfc` em `_CODIGO_DA_APURACAO` |
| `app/domain/` | **nenhum** — o motor não muda (D2) |
| `knowledge/rules/dfc/` | **nenhum** — as regras estão fechadas |
| `registry.py`, `resultado.py`, rotas | **nenhum** — é a change `dfc-no-pipeline` |

## Fluxo da informação

```text
MSC MSCE/abertura classes 1-6 de N ──┐
MSC MSCE/abertura classes 1-6 de N-1 ┼─> saldo_da_celula (direção da coluna)
valores informados {L16,L21,L30} ────┘      │
                                            v
                              folhas apuradas + folhas informadas
                                            │
                                ordem_topologica -> agregadoras
                                            v
                              84 linhas x 2 colunas + diagnóstico
```

## Decisões

### D1 — Fatia: apuração e CLI, sem transporte
**Escolhido:** esta change entrega `apurar()` e o CLI; o `GET` fica para `dfc-no-pipeline`.
**Descartado:** tudo numa change. **Porquê:** é o corte que BF (`bf-apuracao-f1` →
`bf-no-pipeline`) e DVP (`dvp-quadro-principal` → `dvp-no-pipeline`) já usaram. O pipeline exige
mexer em asserções de percurso, notificação e no golden — ruído que esconderia a apuração.

### D2 — Agregadora totalizada no serviço, não no motor
**Medido (2026-10-26):** com o motor atual, `L1`, `L12`, `L17`, `L18`, `L26`, `L27`, `L34` e `L36`
saem **não apuradas** — "referências sem coluna em comum". A causa é estrutural: `L16`, `L21` e
`L30` não declaram `columns` (D3/D10 da change anterior), e a agregadora que as referencia morre
inteira.

**Escolhido:** o serviço apura as folhas pelo motor, injeta as três linhas informadas (`0,00` se
não informadas) e totaliza as agregadoras com `ordem_topologica`, como `dvp/quadro_principal.py`
já faz em `_totalizar` para a coluna manual. **Descartado:** (a) alterar `matriz.py` para ignorar
referência sem coluna — o motor é compartilhado por quatro demonstrativos e a regressão não
compensa; (b) dar `columns: []` às três linhas no YAML — contradiz a spec em vigor, que proíbe
`columns` nelas.

**Porquê:** o código já existe no DVP e resolve o caso com uma função, sem tocar no que BO, BF, BP
e DVP usam hoje.

### D3 — `L35` lê o exercício anterior
**Medido:** `L35` saiu 2.854.802.415,12, que é o caixa **final** de 2025, porque o motor leu a MSC
de N. O caixa inicial de N é o `1.1.1` da MSC de **N−1**: 2.785.855.199,20.

**Escolhido:** origem por linha, pelo mecanismo que o BF já tem — `DO_EXERCICIO_ANTERIOR` em
`app/services/bf/origem.py` e `registros_por_regra` em `apurar_matriz`. **Descartado:** ler
`TipoSaldo.ABERTURA` de uma competência diferente; a MSCE de N não contém a posição de N−1.

**Confere com o BF do mesmo ente:** `L29`/`L30` do BF ("Saldo do Exercício Anterior") já saem
2.785.855.199,20 da MSC, e `L62`/`L63` ("Saldo para o Exercício Seguinte") 2.854.802.415,12
(`docs/entes-homologacao/porto-alegre/auditoria-bf-2025.md:65,109`). A DFC tem de reproduzir os
mesmos dois números — é conferência cruzada entre demonstrativos, de graça.

### D4 — Aceite é a identidade de caixa, não o PDF do ente
**Escolhido:** o critério primário é `L34 = 1.1.1(N) − 1.1.1(N−1)` = **68.947.215,92** em Porto
Alegre 2025, medido na própria MSC. **Descartado:** 1:1 contra o PDF publicado. **Porquê:** o PDF
é da administração direta e a MSC é consolidada — a mesma ressalva que o BF do ente já carrega. A
identidade de caixa não depende de recorte: vale para qualquer conjunto de unidades, desde que
`L35`, `L36` e os fluxos venham do mesmo conjunto.

É também o teste mais severo que existe para esta apuração: ele só fecha se **todas** as linhas de
ingresso e desembolso estiverem certas ao mesmo tempo.

### D5 — `L9` zerada é defeito a investigar, não a contornar
**Medido:** `L9` (Remuneração das Disponibilidades) saiu 0,00 contra 301.239.717,16 publicados.
**Escolhido:** medir a causa antes de implementar (task 0.3) — suspeita no `not_in` de
`1.3.21.00.1.x` / `7.3.21.00.31.x`, que pode estar engolindo a receita inteira por prefixo. Nenhum
ajuste de regra sem medição: a base canônica está arquivada e só muda por nova change.

### D6 — Sem tocar no motor nem no registry
**Escolhido:** `app/domain/` e `app/services/pipeline/registry.py` intactos. A única linha fora de
`app/services/dfc/` e `app/cli/` é `services/dfc` em `_CODIGO_DA_APURACAO`
(`apuracao.py:25-33`), exigida por `tests/test_versao_do_codigo.py`: sem ela, mudança no código da
DFC não invalidaria cache já gravado. **Porquê:** foi exatamente o item "fora da lista do design"
que a change `dvp-no-pipeline` descobriu tarde (tasks §2.4.1); aqui já entra previsto.

## Impacto

| Eixo | Impacto |
|---|---|
| Banco / migration | nenhum |
| Cache / filas | nenhum nesta change (o anexo ainda não é servido) |
| APIs externas | nenhuma nova — mesma MSC |
| Regressão | BO, BF, BP e DVP bit a bit iguais; `VERSAO_API` muda por D6, invalidando cache (intencional) |

## Arquivos criados / alterados

| Arquivo | Ação |
|---|---|
| `app/services/dfc/__init__.py` | criar |
| `app/services/dfc/quadro_principal.py` | criar |
| `app/services/dfc/informados.py` | criar |
| `app/cli/dfc.py` | criar |
| `app/services/pipeline/apuracao.py` | 1 linha (D6) |
| `tests/dfc/test_apuracao_dfc.py` | criar |
| `tests/dfc/test_informados_dfc.py` | criar |
| `openspec/changes/dfc-apuracao-f1/**` | criar |
| `app/domain/**` | **nenhum** |

## Pendências conhecidas

- `L11` com duas naturezas ausentes da tabela STN (`2.9.40.00.1.1`, `2.9.90.00.1.1`) — segue
  `review_required`. Se `L34` não fechar por `L16`, é o próximo suspeito.
- Quadro de juros: a abertura interna/externa por subfunção não reproduz o publicado e `J.L3` sai
  com ~20,9 mi onde o ente publica zero (`docs/evidencia-dfc-d4-funcao-28.md`, achado colateral).
  Conferir se é desvio do ente antes de qualquer ajuste.
- `D2` da change anterior (executar as exclusões `not_in`) continua sem medição própria: esta
  change a executa e mede, pela primeira vez, no resultado de `L34`.
