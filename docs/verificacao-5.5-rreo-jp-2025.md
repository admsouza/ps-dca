# Verificação 5.5 — quadro principal do BO contra `RREO-Anexo 01`

João Pessoa (`2507507`), exercício 2025, `nr_periodo=6` (exercício fechado). Apurado por
`python -m app.cli.bo 2507507 2025 --json` contra a API pública do SICONFI, e comparado célula a
célula com `RREO-Anexo 01` do mesmo ente e exercício.

## Resultado

| | |
|---|---|
| Células comparáveis | **123** |
| Conferem em centavos | **108** |
| Divergem só no sinal, por convenção do IPC 07 | **14** |
| Divergência real de valor | **1** (`L27.previsao_inicial` — pendência **C7**) |
| Linhas não comparadas | 11 — ver a ressalva abaixo |

O BO é **consolidado**; o RREO separa `exceto intra` de `intra`. A comparação soma os dois
`cod_conta` nas linhas em que isso ocorre (`L1`, `L3`, `L7`, `L31`, `L32`, `L34`).

**Ressalva sobre as 11 não comparadas.** Duas causas distintas, que não devem ser confundidas:

- `L18`–`L23`, `L30`, `L42`–`L47`, `L51` — o ente **não publica** essas linhas (sem refinanciamento,
  sem reabertura de créditos, sem reserva do RPPS). Não há gabarito.
- `L25`, `L26`, `L49`, `L50` — o RREO **publica**, como `TotalReceitasComDeficit`, `Superavit` e
  `TotalDespesasComSuperavit`. Não foram comparadas porque **o nosso lado sai vazio** (pendência
  C5), não porque falte gabarito. É a seção seguinte.

## As 14 divergências de sinal não são erro

O IPC 07 define a coluna de saldo da receita como `SALDO (d) = (c-b)` — **realizada menos
previsão**. O `RREO-Anexo 01` publica `SALDO (a-c)` — **previsão menos realizada**. São
demonstrativos diferentes com convenções opostas, e o código segue o rótulo do IPC 07.

Em todas as 14 células a magnitude bate em centavos e só o sinal se inverte. Exemplo em `L16`:

```
calculado (IPC 07, c-b)   -442.467.502,93
RREO      (a-c)            442.467.502,93
```

A coluna de despesa **não** tem esse efeito: `Saldo da Dotação (j) = (f-g)` do IPC 07 e
`SALDO (g) = (e-f)` do RREO apontam na mesma direção, e as 6 células de `saldo_dotacao` conferem.

## Evidência medida para a pendência C5

A conferência acima deixou `L25`, `L26`, `L49` e `L50` de fora porque **o nosso lado sai vazio**
(C5). O que o STN publica nessas linhas foi medido em separado, nas duas metades — a do superávit
em João Pessoa e a do déficit em 12 estados deficitários, já que JP foi superavitária.

→ **`docs/evidencia-c5-deficit-superavit.md`**

O resultado em uma linha: as duas metades **não são simétricas** — o superávit sai em 3 colunas de
execução da despesa, o déficit em 1 só, contra a empenhada.

## A única divergência de valor — pendência C7

| Linha · coluna | Calculado | RREO | Diferença |
|---|---|---|---|
| `L27` Saldos de Exercícios Anteriores · previsão inicial | 482.338.332,64 | 12.000.000,00 | **470.338.332,64** |

Causa: `L29` Superávit Financeiro é apurada com previsão inicial de R$ 470.338.332,64 — o saldo
inicial de `5.2.2.1.3.01.00`, a conta que a decisão B5 mandou declarar na linha. Por
`L27 = L28 + L29 + L30`, esse valor sobe para `L27`.

O STN **não publica** `PREVISÃO INICIAL` para `SuperavitFinanceiro` no `RREO-Anexo 01` — só
`PREVISÃO ATUALIZADA (a)` e `Até o Bimestre (c)`. E publica `L27` PREVISÃO INICIAL = 12.000.000,00,
que é exatamente `L28` sozinha:

```
SaldoDeExerciciosAnteriores...   PREVISÃO INICIAL          12.000.000,00
                                 PREVISÃO ATUALIZADA (a)  482.338.332,64
                                 Até o Bimestre (c)       470.338.332,64
RecursosArrecadadosEm...         PREVISÃO INICIAL          12.000.000,00
                                 PREVISÃO ATUALIZADA (a)   12.000.000,00
SuperavitFinanceiro              PREVISÃO ATUALIZADA (a)  470.338.332,64   ← sem previsão inicial
                                 Até o Bimestre (c)       470.338.332,64
```

Leitura plausível — **e não aplicada, porque é interpretação normativa**: um superávit financeiro
só é conhecido depois do exercício fechado, então não cabe em previsão inicial. O IPC 07 não diz se
a coluna se aplica a `L29`. **Decisão do PO.** Nada foi presumido no código.

A previsão atualizada de `L27` bate em centavos (482.338.332,64), e `L28` e `L29` conferem em todas
as colunas que o RREO publica.

## Como reproduzir

```bash
python -m app.cli.bo 2507507 2025 --json > bo.json
# gabarito: https://apidatalake.tesouro.gov.br/ords/siconfi/tt/rreo
#   ?an_exercicio=2025&nr_periodo=6&co_tipo_demonstrativo=RREO&no_anexo=RREO-Anexo%2001&id_ente=2507507
```

O mapeamento linha→`cod_conta` e coluna→coluna usado aqui é de conferência, não de produção: o
IPC 07 e o RREO são demonstrativos distintos, e nada disso entrou na base canônica.
