# Design — Estorno de receita extra no BF

**Change:** `openspec/changes/bf-estorno-receita-extra/` · **Proposal aprovada pelo PO em:** 2026-10-05

## Contexto

`L27` soma créditos e `L60` soma débitos de `2.1.8.8` e `2.2.8.8` (fontes extraorçamentárias) em
`period_change` dos meses 1 a 12, nos dois exercícios. O relatório PublicSoft devolve um
`totalGeral` por exercício. Esse valor sai das duas linhas. SICONFI não tem a rota.

## Componentes afetados

| Componente | Papel |
|---|---|
| `PublicSoftMSC` | `GET` do relatório, header `x-authorization` já usado na MSC |
| `app/services/bf/quadro_principal.py` | abate o `totalGeral` e propaga para quem soma a linha |
| `app/services/pipeline/apuracao.py` | o invólucro da fonte repassa o método quando a fonte bruta o tem |
| `app/services/pipeline/resultado.py` | publica o estorno na procedência quando houve abatimento |

## Fluxo

```text
apurar BF
  → se a fonte não tem estorno_receita_extra: matriz como hoje
  → senão, por exercício da coluna:
       receita = GET estorno-receita-extra?exercicio={ano}&tipo=sintetico
       despesa = GET estorno-despesa-extra?exercicio={ano}&tipo=sintetico
       L27 −= receita
       L60 −= receita + despesa
       totalizadora que soma a linha −= o abatimento da filha, se a célula já era número
```

## Contratos

Rota do BF inalterada. URL do relatório derivada do host de `PUBLICSOFT_API_URL`:
`/contabilidade-tools/relatorios-gerenciais/estorno-receita-extra`.

Sem `data.totalGeral`, `EstornoIndisponivel` — o resultado não é montado.

## Decisões

### D1 — Só PublicSoft
**Escolhido:** abater apenas se a fonte implementa `estorno_receita_extra`. **Descartado:** flag
por ente ou por exercício. **Porquê:** SICONFI não tem o relatório; o PO fechou isso em 2026-10-05.

### D2 — Um totalGeral por exercício
**Escolhido:** consulta de `{exercicio}` na coluna atual e de `{exercicio}-1` na anterior.
**Descartado:** usar o total de 2025 nas duas colunas.

### D3 — Propagar pela soma
**Escolhido:** subtrair o mesmo valor nas compostas que já tinham número (`L24`, `L33`, `L57`,
`L66`). **Descartado:** recalcular o quadro inteiro.

## Arquivos

| Arquivo | Ação |
|---|---|
| `app/infra/msc/publicsoft.py` | alterar |
| `app/services/bf/quadro_principal.py` | alterar |
| `app/services/pipeline/apuracao.py` | alterar |
| `app/services/pipeline/resultado.py` | alterar |
| `tests/bf/test_estorno_receita_extra.py` | criar |
| `tests/msc/test_estorno_receita_extra.py` | criar |
