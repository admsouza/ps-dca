# Proposal — Regra da célula no demonstrativo

**Status:** em implementação
**Repositório:** `ps-dca`
**Capability:** `dca/regra-da-celula` (nova)
**Anexo DCA:** BF primeiro; o contrato vale para qualquer anexo com projeção
**Base normativa:** IPC 06, ed. 2024-06, item 39

## Why

O auditor vê o valor e não vê a regra que o produziu. O Anexo 08 do RREO já abre essa regra no clique, só para `auditor_mapeamentos` ou `adm_sistema` no hub. Sem o mesmo no BF, a conferência de L27, L28, L60 e L61 depende de ler o YAML.

## What Changes

- `GET /dca/{anexo}/regra` devolve contas, fontes, natureza, origem do saldo e filhas da célula.
- A origem é a mesma função que a apuração declara em `origens_por_linha`.
- Quem não tem a flag do hub recebe `403`. Anexo sem projeção, linha ou coluna inexistente: `404`.
- O front do BF abre o diálogo no clique da célula de valor.

**Fora de escopo:** lançamentos da MSC que compuseram o número; BO até registrar a própria origem.

## Entradas e saídas

| Interface | Entrada | Saída |
|---|---|---|
| `GET /dca/{anexo}/regra` | `anReferencia`, `linha`, `coluna`, `quadro` opcional. Header `Authorization` | `codigo`, `coluna`, `rotulo`, `tipo` (`contas`\|`soma`), `origem`, `meses`, `natureza`, `contas`, `fontes`, `filhas` |

## Exemplo concreto

| Ente | Exercício | Anexo | Célula | Regra esperada |
|---|---|---|---|---|
| Cuitegi `2505204` | 2025 | BF | `L27` / `exercicio_atual` | `period_change` meses 1–12, crédito, contas `2188` e `2288`, fontes `860`, `861`, `862`, `863`, `869` |

## Critérios de aceite

- [ ] `L27` nas duas colunas responde `period_change` com as 5 fontes.
- [ ] `L28` no exercício anterior responde `abertura`.
- [ ] `L24` responde `soma` com filhas `L25`–`L28`.
- [ ] Perfil sem flag: `403`. Linha inexistente: `404`.

## Casos de erro

| Situação | Comportamento esperado |
|---|---|
| Sem JWT | `401`, sem contas no corpo |
| Autenticado sem `auditor_mapeamentos` nem `adm_sistema` | `403` "Acesso negado." |
| Hub fora | `503`, acesso não liberado |
| Anexo, linha ou coluna fora do catálogo | `404` "Consulta indisponível." |
