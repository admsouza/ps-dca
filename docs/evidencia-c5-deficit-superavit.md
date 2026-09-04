# Evidência medida para a pendência C5

A C5 registra que o IPC 07 **não diz** em qual coluna `L25` Déficit, `L26` TOTAL (VII), `L49`
Superávit e `L50` TOTAL (XV) são apresentadas: elas cruzam os blocos de receita (4 colunas) e de
despesa (6), que não têm coluna em comum.

O documento não diz, mas **o que o STN publica diz**. Este arquivo registra a medição das duas
metades, contra o `RREO-Anexo 01` de 2025, `nr_periodo=6`.

**Nada disso foi aplicado ao código.** A C5 segue aberta: a decisão é do PO. O que mudou é que ela
decide sobre fato medido, não sobre interpretação.

## Resumo — e a assimetria

| | `L25`/`L26` Déficit | `L49`/`L50` Superávit |
|---|---|---|
| Bloco onde aparece | **receita** | **despesa** |
| Células da linha de ajuste | **1** | **3** |
| Coluna(s) | `receitas_realizadas` | `empenhadas` · `liquidadas` · `pagas` |
| Contraparte | despesa **empenhada** apenas | a respectiva coluna de execução |
| Coluna de saldo | em branco | em branco |

**As duas metades não são simétricas.** O superávit é apurado uma vez por coluna de execução da
despesa; o déficit, uma única vez e só contra a empenhada. Resolver `L25` "por simetria" com `L49`
daria **três** células de déficit onde o STN publica **uma** — era exatamente o risco de decidir
sem medir.

A leitura que explica a assimetria: cada bloco recebe tantas células de ajuste quantas colunas de
realização ele tem. A receita tem uma só (`Até o Bimestre (c)`); a despesa tem três (`f`, `h`, `j`).

## Metade do superávit — João Pessoa (2507507), 2025

Ente superavitário. `Superavit` sai em três colunas, cada uma contra a receita realizada
(`Até o Bimestre (c)` = 5.117.875.296,33):

| Coluna | `L48` apurado por este código | receita − despesa | `Superavit` do STN | Diferença |
|---|---|---|---|---|
| empenhadas (f) | 4.850.356.845,30 | 267.518.451,03 | 267.518.451,03 | **0,00** |
| liquidadas (h) | 4.569.049.735,78 | 548.825.560,55 | 548.825.560,55 | **0,00** |
| pagas (j) | 4.529.794.533,11 | 588.080.763,22 | 588.080.763,22 | **0,00** |

`Superavit` **não** é publicado em `DOTAÇÃO INICIAL (d)`, `DOTAÇÃO ATUALIZADA (e)`,
`SALDO (g)`, `SALDO (i)`, `INSCRITAS EM RP (k)` nem nas colunas "NO BIMESTRE".

`TotalDespesasComSuperavit` (`L50`) fecha a identidade: nas três colunas de execução vale
**5.117.875.296,33**, exatamente a receita realizada — diferença 0,00 nas três. Nas colunas de
dotação o superávit é zero e `L50` = `L48`. Também não traz `SALDO (g)` nem `SALDO (i)`.

## Metade do déficit — 12 estados deficitários de 2025

Nenhum município da amostra de referência serve: João Pessoa foi superavitária. A varredura dos 27
estados achou 12 com despesa empenhada acima da receita realizada.

`Deficit` aparece em **uma única coluna** — `Até o Bimestre (c)`, a da receita realizada — e vale
`despesa empenhada − receita realizada`:

| UF | Colunas de `Deficit` | `= empenhada − receita`? | `L26` tem `SALDO (a-c)`? | `L26(c) = empenhada`? |
|---|---|---|---|---|
| AC · TO · PI · RN · AL · SP · PR · SC · MS · GO · DF | `Até o Bimestre (c)` | **sim**, exato | não | **sim**, exato |
| PB | *nenhuma* — ver ressalva | — | não | não (dif. −35.893.050,14) |

Onze de doze, exatos em centavos. Exemplo em SP:

```
TotalDespesas   EMPENHADAS (f)   385.042.592.630,74
TotalReceitas   Até o Bimestre   372.818.667.132,35
                                 ──────────────────
Deficit         Até o Bimestre    12.223.925.498,39   ✓ publicado
TotalReceitasComDeficit (c)      385.042.592.630,74   = a despesa empenhada  ✓
```

`TotalReceitasComDeficit` (`L26`) traz `PREVISÃO INICIAL`, `PREVISÃO ATUALIZADA (a)`,
`No Bimestre (b)` e `Até o Bimestre (c)`, e **não** traz `SALDO (a-c)` — em nenhum dos 12. Nas
colunas de previsão o déficit é zero e `L26` = `L24`.

### Ressalva — a Paraíba não publicou a linha

O estado da PB tem despesa empenhada R$ 35.893.050,14 acima da receita realizada, mas **não
publicou** `Deficit`, e o seu `TotalReceitasComDeficit (c)` ficou igual ao `TotalReceitas (c)` em
vez da empenhada. É inconsistência de preenchimento do próprio ente, não outra regra: os outros 11
são unânimes.

Consequência prática: a regra não pode presumir que o ente publique a linha de ajuste. Conferir a
apuração contra o publicado vai divergir nesses casos — e a divergência é do ente.

## O que a decisão do PO implica no motor

A fórmula medida é **cruzada em coluna**, não só em bloco:

```
L49.empenhadas = L24.receitas_realizadas − L48.empenhadas
L25.receitas_realizadas = L48.empenhadas − L24.receitas_realizadas
                              ↑ nome de coluna diferente do que está sendo calculado
```

`RefLinha` (`app/domain/bo/modelo.py`) tem apenas `regra` e `sinal`, e `_agregar`
(`app/domain/bo/matriz.py`) lê **a mesma coluna** em todas as referências. Declarar as colunas nas
4 linhas **não basta**: `L49.empenhadas` iria buscar `L24.empenhadas`, que não existe, e a célula
sairia `None` por outro motivo.

Fechar a C5 exige, então:

1. coluna opcional em `RefLinha` — "leia *esta* coluna da linha referenciada", default no
   comportamento atual;
2. `_agregar` honrando o override;
3. as 4 linhas declarando colunas e o mapeamento cruzado;
4. **o campo no schema `knowledge/schemas/rule.json`** — que vive na change arquivada
   `ipc07-bo-regras-canonicas`, o mesmo bloqueio da **C6**.

Por isso C5 e C6 devem ir ao PO como **um pedido só**: uma change pequena de base canônica que
acrescente `natureza_saldo` na conta (C6) e a coluna em `RefLinha` (C5).

## Como reproduzir

```bash
python -m app.cli.bo 2507507 2025 --json      # metade do superávit
# gabarito, por ente (a API honra um id_ente por chamada):
#   https://apidatalake.tesouro.gov.br/ords/siconfi/tt/rreo
#     ?an_exercicio=2025&nr_periodo=6&co_tipo_demonstrativo=RREO
#     &no_anexo=RREO-Anexo%2001&id_ente=<ibge>
# deficitários de 2025: 12 17 22 24 25 27 35 41 42 50 52 53
```
