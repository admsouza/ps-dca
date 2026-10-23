# Proposal — DVP, Quadro Principal

**Status:** aprovada pelo PO para abrir a change (2026-10-23). Código só depois do gate TEST.
**Repositório:** `ps-dca`
**Capability:** `dca/demonstracao-variacoes-patrimoniais` (nova)
**Anexo DCA:** `DCA-Anexo I-HI`
**Base normativa:** IPC 05 ed. 2020-01 (`docs/referencia/ipc/IPC05 - DVP atualizacao - 20200117.pdf`), pp. 8–9, item 22
**Fonte da verdade externa:** `tt/dca` e `tt/msc_patrimonial` do SICONFI. Aceite = 1:1 em centavos.

## Why

A DVP não está no pipeline. O `I-HI` publicado já é a soma das classes 3 e 4. Aplicar a coluna Exclusões do IPC 05 tira bilhões que o SICONFI mantém no anexo.

## What Changes

- 19 regras em `knowledge/rules/dvp/quadro_principal.yaml`, no mesmo contrato de BO, BP e BF.
- L2–L8 e L10–L18 somam o 2º nível do PCASP. L1, L9 e L19 só referenciam outras linhas.
- A coluna Exclusões do IPC 05 não entra em `filters`, `exclusion_groups` nem no cálculo.
- Apuração no mesmo motor de BO, BP e BF: `MSCE`, saldo de abertura, classes 3 e 4, duas colunas.
- Conta redutora reduz pela direção da coluna, o que o motor já faz em `saldo_da_celula`.

**Fora de escopo:** os 16 quadros anexos do IPC 05 (item 21); DFC; religar exclusão intra de BP ou BF; coringa de 5º nível = 2. Também fora: o transporte HTTP (change `dvp-no-pipeline`) e o recorte por unidade gestora com escolha da origem do exercício anterior (change `dvp-por-unidade-gestora`).

## Por que a exclusão não entra no cálculo

Medido em 2026-10-23. MSC de encerramento, saldo de abertura, classes 3 e 4, contra `tt/dca` `DCA-Anexo I-HI`. Sem a lista de exclusões, as 16 linhas-base fecham. Com a lista do IPC 05, as transferências intra saem do anexo publicado.

| Ente | Exercício | Leitura | L6 `4.5` | L14 `3.5` |
|---|---|---|---:|---:|
| João Pessoa `2507507` | 2025 | `I-HI` = MSC sem exclusão | 11.722.481.279,59 | 9.199.369.111,48 |
| João Pessoa `2507507` | 2025 | MSC menos a lista do IPC 05 | 3.151.851.371,43 | 628.739.203,32 |

O mesmo fechamento, sem exclusão, em Porto Alegre `4314902` (2025 e 2024) e em João Pessoa 2024. Decisão do PO em 2026-10-23: nenhuma exclusão intra no cálculo. O padrão é o do BP depois de `bp-consolidado-sem-exclusao` e o do item 38 do BF: a lista pode existir no PDF e não reduz o valor que o SICONFI publica.

## Entradas e saídas

| Interface | Entrada | Saída |
|---|---|---|
| Apuração da DVP | MSC `MSCE` / abertura, classes 3 e 4, exercícios N e N−1 | 19 linhas, `exercicio_atual` e `exercicio_anterior` |
| `GET` do anexo, quando a change de pipeline entrar | cache da DVP | a mesma matriz |

O transporte HTTP não é desta change. A DVP entrará pelo `REGISTRY` no anexo `I-HI`, hoje declarado sem serviço (`app/services/pipeline/registry.py:46`), na change `dvp-no-pipeline` — o mesmo recorte que `bf-no-pipeline` fez pelo BF. Enquanto isso, a apuração é verificável pelo CLI, como foi a do BF entre `bf-apuracao-f1` e `bf-no-pipeline`.

## Exemplo concreto

João Pessoa/PB (`2507507`), 2025, `I-HI` = MSC sem exclusão.

| Linha | Conta | Valor |
|---|---|---:|
| L1 VPA | L2+…+L8 | 17.319.103.824,61 |
| L2 | `4.1` | 397.963.739,37 |
| L6 | `4.5` | 11.722.481.279,59 |
| L9 VPD | L10+…+L18 | 17.046.926.343,10 |
| L14 | `3.5` | 9.199.369.111,48 |
| L19 | L1−L9 | 272.177.481,51 |

Porto Alegre/RS (`4314902`), 2025: L1 53.603.764.288,49, L9 54.984.708.163,98, L19 −1.380.943.875,49.

A redutora `4.1.1.2.1.97` em João Pessoa vale 1.052.431,74. Somada na direção dela, L2 fica 2.104.863,48 acima do `I-HI`. Na direção da coluna (classe 4 credora), L2 fecha.

## Critérios de aceite

- [ ] João Pessoa 2025: as 16 linhas-base, L1, L9 e L19 iguais ao `I-HI` em centavos.
- [ ] Porto Alegre 2025: L1, L9 e L19 iguais ao `I-HI` em centavos.
- [ ] João Pessoa e Porto Alegre 2024: coluna do exercício anterior igual ao `I-HI` de 2024.
- [ ] Nenhuma regra da DVP declara `filters` nem `exclusion_groups`.
- [ ] BO, BP e BF permanecem bit a bit iguais.
- [ ] `python -m scripts.validate_rules knowledge` sem nenhum erro `dvp.*` (os 4 erros do BF são pré-existentes — ver `design.md`, Pendências).

## Casos de erro

| Situação | Comportamento esperado |
|---|---|
| Conta do grupo sem natureza no PCASP e sem direção de prefixo | A célula da linha fica não apurada (`None`), com o motivo no diagnóstico. Não vira zero. |
| `L17` sem movimento | 0,00. O `I-HI` pode omitir a linha. |
| Exercício anterior sem MSC | Coluna anterior não apurada, no mesmo contrato do BP/BF. |

## Restrições e riscos

- `4.4.2.5.1.00.00` em Porto Alegre não é folha do `PCASP.md`. A direção do prefixo fecha L5 em 716,56. Sem esse fallback a linha inteira sai não apurada.
- O YAML do GitHub `yaml-dvp-ipc05` aplica `exclusion_groups`. Não é a fonte desta change.

## Gates

| Gate | Artefato | Esta change |
|---|---|---|
| SPEC | `proposal.md` + delta spec | este arquivo e `specs/dca/demonstracao-variacoes-patrimoniais/spec.md` |
| PLAN/ARCH | `design.md` + `tasks.md` | decisões D1–D8 e a lista de arquivos |
| TEST | teste do cenário antes do código | `tasks.md` §2 |
| IMPLEMENT | YAML e apuração mínimos | `tasks.md` §3, só depois do teste falhar pelo motivo esperado |
| REVIEW | `git diff` | `tasks.md` §4 |
| VERIFY | pytest, ruff, cenários medidos | `tasks.md` §5 |

## Aprovação do PO

- [x] PO mandou abrir a change em 2026-10-23, com a DVP no padrão de BO, BP e BF e sem exclusão no cálculo.
