# Ponto de parada — 2026-09-03

Estado do repositório ao fim da sessão. Fase de **spec**: nenhum código foi escrito.

## Onde paramos

Duas changes ativas. A primeira está pronta e só aguarda assinatura; a segunda tem uma decisão de
escopo aberta que precisa vir antes do delta spec.

### 1. `ipc07-bo-regras-canonicas` — pronta, aguarda aprovação

Todas as pendências de conteúdo foram fechadas hoje:

| # | Decisão |
|---|---|
| **B6** | `L27`–`L30` têm as 4 colunas de receita; `L51` não tem coluna de valor |
| **B2 / B4** | exceção declarada — as tabelas de `docs/contas-stn/` não são completadas nesta change |
| **0.7** | exemplo com ente/exercício/valor fora de escopo — pertence à change de ligação DCA |
| **1.3** | `pydantic` retirado; runtime fica `pyyaml` + `jsonschema` |

Resultado: **0** regras `review_required` (antes eram 5), as 69 linhas transcritíveis.

**Único item aberto: task 0.11** — aprovação formal do PO em `proposal.md` e no delta spec, com
data. É o gate para PLAN/ARCH. Nada mais bloqueia.

### 2. `bo-quadro-principal-processamento` — nova, criada hoje

Proposal e design escritos: contrato das duas fontes MSC, regra de débito/crédito, `ending_balance`
na DCA e a estrutura de apuração (Clean Architecture, núcleo sem I/O).

C1, C2 e C3 resolvidos. **C4 está aberta e bloqueia o delta spec** (task 0.10).

## A decisão que falta — C4

Os 7 anexos da DCA (universo completo, medido) publicam **posição** e **execução realizada**.
Nenhum publica previsão da receita ou dotação. O Balanço Orçamentário do IPC 07 é o
**`RREO-Anexo 01`**, cujas 12 colunas correspondem uma a uma à matriz do IPC.

**Pergunta ao PO:** este demonstrativo pertence ao `ps-dca` ou ao `regras-rreo-api`?

A resposta muda o repositório de destino, não o desenho: a estrutura e a regra de saldo valem nos
dois casos.

## O que ficou provado com dado real

João Pessoa `2507507`, 12/2025, `MSCC`, `ending_balance`, classes 5 e 6 (4.600 + 4.320 registros)
contra `DCA-Anexo I-C`, `I-D` e `RREO-Anexo 01`: **11 valores, zero diferença em centavos.**

A regra validada:

```
saldo(conta) = Σ C − Σ D   se a conta é credora no PCASP
             = Σ D − Σ C   se a conta é devedora no PCASP
```

Direção resolvida **por conta folha de 9 dígitos** na tabela `PCASP.md`, pela conta do registro —
nunca pela classe contábil, nunca pelo prefixo declarado na regra.

Três coisas que a medição decidiu e que não devem ser reabertas sem nova medição:

1. **A heurística de classe do `regras-rgf-api` não serve.** `621310100` e `621390000` são classe 6
   e devedoras; tratadas como credoras saem com sinal invertido contra o STN.
2. **`522139900` não pode entrar por prefixo.** É irmã de `522130100` (a conta de `L29`); o prefixo
   `5.2.2.1.3` a captura e infla a coluna em R$ 729.036.483,90.
3. **O resíduo tem de ser medido.** Os R$ 12.000.000,00 de natureza `9.9.9.0.00.0.0` não pertencem
   ao total das receitas — vão para a linha de saldos de exercícios anteriores. Isso confirmou B5 e
   B6 contra o publicado.

## Por onde retomar

1. Assinar a task 0.11 de `ipc07-bo-regras-canonicas` (ou apontar o que falta) — libera PLAN/ARCH.
2. Responder C4 — libera o delta spec de `bo-quadro-principal-processamento`.
3. Com as duas respostas: escrever o delta spec e só então a fase TEST.

## Artefatos desta sessão

| Arquivo | Conteúdo |
|---|---|
| `docs/validacao-bo-jp-2025.md` | os 11 valores conferidos, com as contas e a reprodução |
| `docs/anexos-siconfi-inventario.md` | o que cada anexo publica; onde está o gabarito do BO |
| `openspec/changes/bo-quadro-principal-processamento/` | proposal · design · tasks |
| `openspec/changes/ipc07-bo-regras-canonicas/` | B6, B2/B4, 0.7 e 1.3 registrados |
| `docs/source-analysis-ipc07.md` | §B6, §5.1–5.4 atualizados com as decisões |
| `openspec/AGENTS.md` | tabela "Change ativa" com as duas changes |

Nada foi comitado. `git status` mostra os arquivos novos e modificados.
