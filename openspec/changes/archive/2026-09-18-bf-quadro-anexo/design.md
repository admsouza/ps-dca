# Design — Quadro Anexo do Balanço Financeiro

## Componentes afetados

| Arquivo | Mudança |
|---|---|
| `app/services/bf/quadro_principal.py` | deixa de filtrar só `QUADRO_PRINCIPAL`; apura os dois quadros |
| `app/cli/bf.py` | `--quadro principal\|anexo\|todos` |
| `tests/bf/test_quadro_anexo.py` | novo |

Nada em `app/domain/`: o motor já calcula coluna derivada (`RefColuna`), e foi por isso que o BO
publicou `saldo = c − b` sem nenhum código próprio. O anexo usa o mesmo mecanismo.

## Decisões

### D1 — O serviço apura os dois quadros num passe

O carregador já devolve as 80 regras; a F1 as filtrava para o quadro principal. A filtragem sai, e
o resultado passa a trazer os dois quadros na mesma matriz, cada linha declarando o seu.

Alternativa descartada: um serviço por quadro. Duplicaria a leitura da MSC — as mesmas classes, o
mesmo ente, o mesmo exercício — para produzir dois pedaços do mesmo demonstrativo.

### D2 — As colunas `(c)` e `(f)` são derivadas, nunca somadas

O IPC 06 define `(c) = (a) − (b)`. Somar `(c)` das filhas daria o mesmo número na maioria dos
casos — e seria coincidência aritmética, não garantia. O motor já resolve isso no passo (c) da
apuração, depois das agregações, exatamente para que a identidade valha também nos totais.

Consequência declarada: parcela não apurada em `(a)` ou `(b)` torna `(c)` não apurada. É o
comportamento correto — a subtração com uma parcela ausente afirmaria um líquido que não se sabe.

### D3 — A conferência entre quadros é diagnóstico, não ajuste

`L14 (c)` do anexo e `L1` do principal deveriam ser a mesma receita líquida. Quando diferem, a
diferença entra no diagnóstico com o valor; nenhum dos dois é alterado.

Medido em Recife: a receita líquida direta das contas é 10.390.050.823,18 e `L1` composta pelas
linhas por fonte é 9.939.848.008,46 — a diferença de 450.202.814,72 é exatamente a receita sem
fonte de recursos na MSC. É essa diferença que o anexo torna visível, em vez de deixá-la implícita.

## Impacto

- **Banco, cache e APIs externas:** nenhum. As classes lidas são as mesmas do quadro principal.
- **Contrato do resultado:** a matriz ganha linhas; quem filtra por `quadro` não é afetado.
