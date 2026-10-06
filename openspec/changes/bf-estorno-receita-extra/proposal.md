# Proposal — Estorno de receita extra no BF (PublicSoft)

**Status:** aprovada pelo PO em 2026-10-05
**Repositório:** `ps-dca`
**Capability:** `dca/balanco-financeiro` (existente)
**Anexo DCA:** Balanço Financeiro (IPC 06), Quadro Principal

## Why

Na PublicSoft, o movimento de `L27` e `L60` vem bruto da MSC. O relatório gerencial de estorno de
receita extra isola o valor que deve sair dessas duas linhas para o número publicado ser líquido.

Na fonte SICONFI o relatório não existe. `L27` e `L60` permanecem o movimento da MSC.

## What Changes

- Com fonte PublicSoft, `L27` é movimento MSC − `totalGeral` de `estorno-receita-extra`.
  `L60` é movimento MSC − esse mesmo total − `totalGeral` de `estorno-despesa-extra`.
  Cada coluna usa o exercício dela.
- `L24`, `L33`, `L57` e `L66` acompanham a parcela, porque somam essas linhas.
- Fonte sem o relatório (SICONFI) não chama a rota e não altera valor.

## Entradas e saídas

| Interface | Entrada | Saída |
|---|---|---|
| Relatório | `GET .../contabilidade-tools/relatorios-gerenciais/estorno-receita-extra?exercicio={ano}&tipo=sintetico`, header `x-authorization` | `data.totalGeral` |
| Célula | movimento MSC da coluna | líquido = movimento − `totalGeral` daquele exercício |

## Exemplo concreto

Ente: PM Cuitegi/PB (`2505204`), exercício 2025. Relatório sintético de 2025: `totalGeral` = 115679.40.

| Célula | Bruto | Líquido |
|---|---:|---:|
| `L27` exercício atual | 4601867.61 | 4486188.21 |
| `L60` exercício atual | 4595435.01 | 4479755.61 (receita 115679.40 + despesa 0.00) |

O exercício anterior usa o `totalGeral` de `exercicio=2024` na mesma rota.

## Critérios de aceite

- [ ] PublicSoft: as duas colunas de `L27` e de `L60` saem líquidas, em centavos.
- [ ] `L24` e `L57` caem pelo mesmo valor abatido na filha.
- [ ] SICONFI: `L27` e `L60` iguais ao movimento da MSC.
- [ ] Resposta sem `totalGeral` não devolve o bruto como se fosse líquido.

## Casos de erro

| Situação | Comportamento esperado |
|---|---|
| `data.totalGeral` ausente | a apuração falha; o bruto não é publicado |
| Fonte SICONFI | nenhum HTTP de estorno; valor inalterado |
