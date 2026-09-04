# Evidência medida para as pendências C6 e C7

Mesmo método de `docs/evidencia-c5-deficit-superavit.md`: o que o STN publica e o que os entes
declararam, contra a API pública. **Nada foi aplicado ao código** — as duas seguem abertas.

## C7 — `L29` Superávit Financeiro não tem previsão inicial. Medido: nenhum ente tem.

A C7 nasceu de João Pessoa: o nosso `L27.previsao_inicial` sai 482.338.332,64 contra 12.000.000,00
do STN, porque `L29` é apurada com previsão inicial de 470.338.332,64 e sobe por
`L27 = L28 + L29 + L30`.

Restava saber se a ausência de `PREVISÃO INICIAL` em `SuperavitFinanceiro` era um caso de JP ou a
estrutura do demonstrativo. Varredura de **25 entes** (23 estados + DF, e os municípios de João
Pessoa, São Paulo e Rio de Janeiro), `RREO-Anexo 01` 2025 `nr_periodo=6`:

| Colunas publicadas em `SuperavitFinanceiro` | Entes |
|---|---|
| `PREVISÃO ATUALIZADA (a)` + `Até o Bimestre (c)` | 22 |
| `PREVISÃO ATUALIZADA (a)` apenas | 2 (PB, MG) |
| linha ausente | 1 (RS) |
| **contendo `PREVISÃO INICIAL`** | **0** |

**Zero de 25.** Nenhum ente publica previsão inicial para o superávit financeiro — nem os que
publicam as outras colunas todas. É estrutura do demonstrativo, não particularidade de JP.

Coerente com a natureza da coisa: um superávit financeiro é apurado sobre o exercício **fechado**,
logo não existe no orçamento originário — entra como crédito adicional, na previsão atualizada.

**O que a evidência não decide:** se `L29` deve sair **em branco** na coluna ou se a coluna não se
aplica à linha. Para o número apurado dá no mesmo; para o contrato de saída, não.

## C6 — `5.3.1.3.0.00.00`: impacto nulo, medido. Natureza, inferível mas não atestada.

A decisão B1 do PO (2026-08-27) mandou manter `5.3.1.3.0.00.00` na fórmula do IPC 07, porque
existia no PCASP 2019 — a edição que o IPC 07 declara usar — e foi extinta depois. O bloqueio
residual é que a conta está fora do PCASP atual, logo não tem direção de saldo, e o campo
`natureza_saldo` não existe no schema `knowledge/schemas/rule.json`.

### O impacto é nulo, e isso é medido

Varredura da MSC (`msc_orcamentaria`, classe 5, `MSCC`, `ending_balance`) de 12/2025 em 9 entes
grandes — SP, MG, RJ, BA, PR, RS, CE, PE e João Pessoa — **~185.000 registros**:

| Família | Contas que aparecem |
|---|---|
| `5.3.1` | `531100000` · `531200000` · `531700000` |
| `5.3.2` | `532100000` · `532200000` · `532700000` |
| **`5313` ou `5323`** | **nenhum registro, em nenhum ente** |

Ninguém escritura `5.3.1.3`. Também não aparecem `531600000`/`532600000` (transferência por
cisão/fusão), que existem no PCASP atual mas nenhum destes entes usou.

Isso confirma a leitura de simetria do IPC 07: o grupo `5.3.2` **também** não tem `5.3.2.3`, e a
fórmula de RP Processados tem 3 termos — o mesmo que a de RP Não Processados teria sem o termo.

### A natureza é inferível com margem estreita, e o grupo é unânime

Do PCASP atual (`docs/contas-stn/PCASP.md`):

| Grupo | Contas | Natureza |
|---|---|---|
| `5.3.1` | `531100000` · `531200000` · `531600000` · `531700000` | **Devedora**, 4 de 4 |
| `5.3.2` | `532100000` · `532200000` · `532600000` · `532700000` | **Devedora**, 4 de 4 |
| `6.3.1` | 10 contas | **Credora**, 10 de 10 |
| `6.3.2` | 6 contas | **Credora**, 6 de 6 |

Unânime nos quatro grupos, sem nenhuma redutora e sem direção mista. E a fórmula do IPC 07 soma
`5.3.1.3` com **`+`**, igual a `5.3.1.2` e `5.3.1.6`, com o `(-)` apenas em `6.3.1.6` — ou seja,
não é conta redutora.

Conclusão razoável: `5.3.1.3.0.00.00` era **Devedora**. O grupo não admite outra leitura.

### O que a evidência pública **não** dá

A conta não está no PCASP atual e não aparece em nenhuma declaração. Não há de onde **atestar** a
natureza: só derivá-la da uniformidade do grupo. O artefato que fecharia isso é o **PCASP 2019**,
publicação do STN que **não está na API** — é documento, e entra pelo mesmo processo de
`knowledge/sources/` (hash em `check_sources`) que a change de base canônica governa.

Diferença que importa: as outras contas têm direção **declarada na tabela**; esta teria direção
**derivada do grupo**. O repositório proíbe heurística de sinal por classe contábil, e é
exatamente essa a fronteira.

## Defeito encontrado de passagem — fixture do teste da C6

`tests/bo/test_saldo.py::test_excecao_historica_usa_a_natureza_declarada` monta
`DirecaoFake(credoras={"531100000", "531200000", "531600000", "631600000"})`.

As três contas `531*` são **Devedora** no PCASP; a fixture as declara credoras. Hoje é latente — o
teste só afirma que a célula não é `None`, não confere valor —, mas se a C6 fechar e o teste passar
a conferir número, a direção invertida dá sinal errado. Corrigir junto com a C6.

## Como reproduzir

```bash
# C7
#   https://apidatalake.tesouro.gov.br/ords/siconfi/tt/rreo
#     ?an_exercicio=2025&nr_periodo=6&co_tipo_demonstrativo=RREO
#     &no_anexo=RREO-Anexo%2001&id_ente=<ibge>
#   procurar cod_conta=SuperavitFinanceiro e listar as colunas
# C6 — o filtro conta_contabil é ignorado pela API; varrer e filtrar local
#   https://apidatalake.tesouro.gov.br/ords/siconfi/tt/msc_orcamentaria
#     ?id_ente=<ibge>&an_referencia=2025&me_referencia=12&co_tipo_matriz=MSCC
#     &classe_conta=5&id_tv=ending_balance&offset=<n>&limit=5000
```
