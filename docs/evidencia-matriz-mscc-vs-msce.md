# Evidência — matriz consolidada (MSCC) × matriz de encerramento (MSCE)

**Medido em:** 2026-09-14 · **Piloto:** Cuitegi/PB `2505204`, exercício 2025 · **Competência:** 12
**Gabarito:** `tt/rreo`, `RREO-Anexo 01`, `nr_periodo=6` (exercício fechado)

Pergunta que originou a medição: o Balanço Financeiro deve ser apurado sobre a MSC de **dezembro**
ou sobre a de **encerramento**? O piloto usa o Balanço Orçamentário, que já tem gabarito publicado,
para responder com dado.

## O que a MSC oferece

Sondagem em `msc_orcamentaria` e `msc_patrimonial`, exercício 2025, ente Cuitegi:

| `co_tipo_matriz` | `me_referencia=12` | `me_referencia=13` |
|---|---|---|
| `MSCC` (consolidada) | **responde** — `data_referencia` 2025-12-31 | vazio |
| `MSCE` (encerramento) | **responde** — `data_referencia` 2025-12-31 | vazio |
| `MSCT` | vazio | vazio |

Não existe mês 13. As duas matrizes convivem na mesma competência 12/2025.

## Piloto: o BO de Cuitegi pelas duas matrizes

Apuração feita com o serviço real (`app.services.bo.quadro_principal.apurar`), trocando apenas o
`co_tipo_matriz` da fonte.

- **337 células** comparadas · **47 divergentes** · todas no bloco de **despesas**
- Receitas: **idênticas** nas duas matrizes
- Volume: classe 5 — 1.522 (MSCC) × 1.424 (MSCE); classe 6 — 1.293 × 1.272

### Contra o publicado

| Célula do `RREO-Anexo 01` | MSCC | MSCE | Publicado |
|---|---|---|---|
| `TotalDespesas` DOTAÇÃO INICIAL (d) | **47.880.373,00** | 42.578.614,24 | 47.880.373,00 |
| `TotalDespesas` DOTAÇÃO ATUALIZADA (e) | **53.568.335,00** | 47.517.614,24 | 53.568.335,00 |
| `TotalDespesas` EMPENHADAS (f) | **44.557.533,10** | 38.506.812,34 | 44.557.533,10 |
| `TotalDespesas` LIQUIDADAS (h) | **44.170.000,17** | 38.128.947,36 | 44.170.000,17 |
| `TotalDespesas` PAGAS (j) | **43.634.689,81** | 37.593.637,00 | 43.634.689,81 |
| `Superavit` EMPENHADAS (f) | **6.166.171,81** | 12.216.892,57 | 6.166.171,81 |
| `Superavit` LIQUIDADAS (h) | **6.553.704,74** | 12.594.757,55 | 6.553.704,74 |
| `Superavit` PAGAS (j) | **7.089.015,10** | 13.130.067,91 | 7.089.015,10 |
| `TotalReceitas` (4 colunas) | igual | igual | igual |

**A MSCC bate 1:1 em centavos nas 8 células de despesa; a MSCE erra todas, por até
R$ 6.050.720,76.** A diferença aparece inteira na linha de Superávit, que absorve o que sumiu das
linhas de despesa — por isso `L50 TOTAL (XV)` mantém o mesmo valor em empenhadas, liquidadas e
pagas, e só dotação inicial e atualizada divergem. Um total que continua fechando é exatamente o
tipo de erro que passaria despercebido sem conferir linha a linha.

Efeito colateral da medição: **é a segunda validação do BO contra o publicado**, agora num ente
pequeno (6.890 habitantes) e diferente de João Pessoa.

## Segundo comparativo: MSCC/encerramento × MSCE/**abertura**

A pergunta seguinte do PO: e se a MSCE for lida pelo saldo de **abertura**? Mesmo piloto, mesmo
serviço, trocando só `id_tv`:

| Par (matriz, tipo de saldo) | Células divergentes de `MSCC/ending_balance` | Registros classe 5 / 6 |
|---|---|---|
| `MSCC` / `ending_balance` | — (referência, bate com o publicado) | 1.522 / 1.293 |
| **`MSCE` / `beginning_balance`** | **0 de 337** | **1.522 / 1.293** |
| `MSCE` / `ending_balance` | 47 de 337 | 1.424 / 1.272 |

**A matriz de encerramento serve — desde que lida pelo saldo de abertura.** Ela carrega as duas
posições: a abertura é o estado **pré-encerramento**, idêntico ao que a MSCC mostra em dezembro; o
encerramento é o estado **pós-encerramento**, que não corresponde ao publicado.

Vale também para as classes que o BF precisa, e que na MSCE/encerramento estavam zeradas:

| Classe | `MSCC`/ending | `MSCE`/beginning | `MSCE`/ending |
|---|---|---|---|
| 3 (VPD, `3.5.1` transf. concedidas) | 98 regs · 7.647.660,37 | **98 regs · 7.647.660,37** | 0 regs · 0,00 |
| 4 (VPA, `4.5.1` transf. recebidas) | 40 regs · 7.648.660,37 | **40 regs · 7.648.660,37** | 0 regs · 0,00 |
| 1 (caixa `1.1.1`) | 26.286.597,15 | 26.286.597,15 | 26.286.597,15 |
| 2 (passivo) | 105 regs · 72.425.452,53 | 105 regs · 72.425.452,53 | 115 regs · 76.314.331,92 |

Ou seja: **a escolha não é entre matrizes, é do par (matriz, tipo de saldo)**. Duas combinações
produzem o demonstrativo publicado; uma produz outro.

## Achado colateral: `beginning_balance` é da competência, não do exercício

Medido em João Pessoa, caixa e equivalentes (`1.1.1`), matriz `MSCC`:

| Leitura | Valor |
|---|---|
| 2025, mês **1**, `beginning_balance` | **1.865.100.624,27** |
| 2024, mês **12**, `ending_balance` | **1.865.100.624,27** |
| 2025, mês **12**, `beginning_balance` | 2.613.640.800,87 |
| 2025, mês **12**, `ending_balance` | 3.248.364.442,41 |

O saldo de abertura do **exercício** está em `(ano, mês 1, beginning)` ou, equivalente ao centavo,
em `(ano-1, mês 12, ending)`. O `beginning_balance` da competência 12 é a abertura de **dezembro** —
748.540.176,60 acima do correto, neste ente.

Isso corrigiu um erro da medição exploratória do BF: `L29 Saldo do Exercício Anterior` tinha sido
apurado como 2.613.640.800,87 e vale **1.865.100.624,27**. Ver
`docs/evidencia-bf-jp-2025.md` §7, já retificado.

## Por que a MSCE/encerramento não serve — e por que isso é ainda mais grave no BF

Comparação por classe contábil, mesmo ente e competência:

| Classe | MSCC | MSCE | Efeito |
|---|---|---|---|
| 1 (ativo) | 134 regs · caixa 26.286.597,15 | 134 regs · caixa **26.286.597,15** | **idêntica** |
| 2 (passivo) | 105 regs · 72.425.452,53 | 115 regs · 76.314.331,92 | +3.888.879,39 — o resultado do exercício já incorporado ao PL |
| 3 (VPD) | 98 regs · 7.647.660,37 | **0 registros** | **zerada** |
| 4 (VPA) | 40 regs · 7.648.660,37 | **0 registros** | **zerada** |

A MSCE é a posição **depois** dos lançamentos de encerramento: as contas de resultado (classes 3 e
4) foram encerradas contra o patrimônio líquido e não existem mais, e o passivo já absorveu o
resultado do exercício.

Para o Balanço Financeiro isso é terminal: `L16`–`L20` (Transferências Financeiras Recebidas,
`4.5.1.x`) e `L49`–`L53` (Concedidas, `3.5.1.x`) sairiam **zeradas**. Em João Pessoa 2025 essas
duas linhas valem **8.570.629.908,16** cada — o BF perderia metade do seu volume sem acusar erro,
porque zero é resposta sintaticamente válida.

O saldo de caixa, ao contrário, é **igual** nas duas matrizes: a escolha não afeta `L29`–`L32` nem
`L62`–`L65`.

## Conclusão — o que a medição mostra

| Par (matriz, tipo de saldo) | Serve? | Por quê |
|---|---|---|
| `MSCC` / `ending_balance` | **sim** | bate 1:1 com o `RREO-Anexo 01` em Cuitegi e em João Pessoa |
| `MSCE` / `beginning_balance` | **sim** | 0 divergências em 337 células contra o par acima, classes 3 e 4 íntegras |
| `MSCE` / `ending_balance` | **não** | pós-encerramento: erra 47 células e zera as classes 3 e 4 |

Para as linhas de **saldo de abertura do exercício** (`L29`–`L32` do BF), a origem é
`(ano, mês 1, beginning)` ou `(ano-1, mês 12, ending)` — **nunca** `(ano, mês 12, beginning)`.

## Decisão do PO — 2026-09-14

Todos os demonstrativos passam a ser apurados sobre a **matriz de encerramento (`MSCE`)**, com o
tipo de saldo definido por demonstrativo:

| Demonstrativo | Matriz | Tipo de saldo |
|---|---|---|
| Balanço Orçamentário (IPC 07) | `MSCE` | **abertura** (`beginning_balance`) |
| Balanço Financeiro (IPC 06) | `MSCE` | **abertura** |
| Balanço Patrimonial (IPC 04) | `MSCE` | **encerramento** (`ending_balance`) |
| Demonstração das Variações Patrimoniais (IPC 05) | `MSCE` | **abertura** |
| Demonstração dos Fluxos de Caixa (IPC 08) | `MSCE` | **abertura** |

### O que a medição diz sobre a decisão

**Para o BO, a troca é neutra — medido em dois entes:**

| Ente | Células comparadas | Divergentes | Registros classe 5 / 6 |
|---|---|---|---|
| Cuitegi/PB `2505204` | 337 | **0** | 1.522 / 1.293 nos dois pares |
| João Pessoa/PB `2507507` | 337 | **0** | 4.600 / 4.320 nos dois pares |

`MSCC`/encerramento e `MSCE`/abertura produzem o **mesmo** Balanço Orçamentário, ao centavo. A
migração não altera nenhum valor já validado contra o `RREO-Anexo 01`.

**Para o BF, a abertura do exercício vem do exercício anterior.** No par decidido, o saldo de
`L29`–`L32` é `(ano-1, competência 12, MSCE, abertura)` — medido em João Pessoa:

| Linha | Leitura | Valor |
|---|---|---|
| `L62`/`L63` Saldo para o Exercício Seguinte | 2025 m12 `MSCE`/abertura | 3.248.364.442,41 |
| `L29`/`L30` Saldo do Exercício Anterior | **2024** m12 `MSCE`/abertura | 1.865.100.624,27 |
| (referência já medida) | 2024 m12 `MSCC`/encerramento | 1.865.100.624,27 |

**Por que o BP é a exceção.** O encerramento incorpora o resultado do exercício ao patrimônio
líquido, e é isso que o Balanço Patrimonial precisa mostrar. Medido em João Pessoa, conta `2.3`:

| Leitura | Patrimônio Líquido |
|---|---|
| `MSCE`/abertura (pré-encerramento) | 3.543.761.526,91 |
| `MSCE`/encerramento (pós-encerramento) | **3.815.939.008,42** |

A diferença de 272.177.481,51 é o resultado do exercício. Os demais demonstrativos descrevem o
**fluxo** do exercício e precisam da posição anterior ao encerramento; o BP descreve a **posição
final** e precisa da posterior. O caixa (`1.1.1`) é idêntico nas duas leituras — o encerramento não
toca contas financeiras.

### O que a decisão obriga

- O **Balanço Orçamentário já entregue** muda de fonte: hoje lê `MSCC`/encerramento. A troca é
  neutra em valor (acima), mas é mudança de comportamento e exige change própria, com a regressão
  medida célula a célula nos dois entes.
- A decisão **C1** (mês 12, `MSCC`) fica **revogada** na parte da matriz; a competência 12 segue,
  agora como padrão e não como constante (ver G10).
- O tipo de saldo passa a ser **propriedade do demonstrativo**, não do adapter — e entra na
  procedência do resultado, junto com a matriz e a competência.

## Decisão anterior — histórico

Esta medição é **evidência, não decisão**. Ficam aguardando o PO, registrados como **G9** e **G10**
na change `bf-apuracao-f1`:

- ~~**G9 — o par (matriz, tipo de saldo).**~~ **Decidido pelo PO em 2026-09-14** — ver acima.
- **G10 — periodicidade mensal além da anual, em todos os anexos.** Informado pelo PO em
  2026-09-14. A competência deixa de ser constante: alcança o serviço, o carregador, a chave de
  cache (`P9` da change `plataforma-pipeline-dca`), o job e a rota. Muda também o significado do
  tipo de saldo — num mês qualquer, o saldo de encerramento é posição acumulada e a variação do
  período é o movimento daquele mês, distinção que no exercício fechado não aparecia.

O que **não** depende de decisão: o resultado tem de declarar na procedência qual matriz, qual tipo
de saldo e qual competência o produziram. Sem isso, duas apurações incomparáveis passam por
iguais.

## Reprodução

```
GET tt/msc_orcamentaria?id_ente=2505204&an_referencia=2025&me_referencia=12
    &co_tipo_matriz=MSCC|MSCE&classe_conta=5|6&id_tv=ending_balance&limit=5000
GET tt/msc_patrimonial?...&classe_conta=1|2|3|4
GET tt/rreo?an_exercicio=2025&nr_periodo=6&co_tipo_demonstrativo=RREO
    &no_anexo=RREO-Anexo 01&id_ente=2505204
```
