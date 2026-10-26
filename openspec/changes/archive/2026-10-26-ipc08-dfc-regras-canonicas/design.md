# Design — Regras canônicas da DFC (IPC 08)

**Change:** `openspec/changes/ipc08-dfc-regras-canonicas/` · **Proposal:** aguardando PO

## Contexto

BO, BF, BP e DVP já apuram uma linha por regra YAML. A DFC entra pela mesma porta, só YAML
nesta change. Fonte MSC já fechada: `MSCE`, abertura, classes 1–6.

## Componentes afetados

| Componente | Papel |
|---|---|
| `knowledge/rules/dfc/*.yaml` | 84 regras, contrato de `rule.json` |
| `knowledge/policies/ipc08.yaml` | itens 13–17 |
| `knowledge/sources/ipc08/` | metadado e extração; PDF permanece em `docs/referencia/ipc/` |
| `knowledge/indexes/rules_index.json` | regenerado por `build_index` |
| `app/` | nenhum |
| `scripts/validate_rules.py` | nenhum patch; IPC08 usa o default de `CAMPOS` |

## Fluxo da informação

```text
IPC 08 PDF (pp. 7–16, rotacionadas)
  → extract_ipc.py → knowledge/sources/ipc08/extracted.md
  → transcrição visual das 14 linhas de lista longa
  → PCASP.md / natureza-receita.md / natureza_despesa.md / funcao-subfuncao.md
  → YAML em knowledge/rules/dfc/
  → jsonschema + check_sources + validate_rules
```

A apuração (MSC → `saldo_da_celula` → matriz) fica para a change de implementação.

## Contratos / interfaces

`rule_id`: `dfc.<quadro>.<grupo?>.l<n>`.

| Quadro | Código | Grupos | Linhas |
|---|---|---|---|
| Principal | `QUADRO_PRINCIPAL` | OPERACIONAIS, INVESTIMENTO, FINANCIAMENTO, CAIXA | L1–L36 |
| Transferências | `TRANSFERENCIAS_RECEBIDAS_CONCEDIDAS` | RECEBIDAS, CONCEDIDAS | L1–L15 |
| Pessoal por função | `DESEMBOLSOS_PESSOAL_POR_FUNCAO` | — | L1–L29 |
| Juros | `JUROS_ENCARGOS_DIVIDA` | — | L1–L4 |

Colunas: `exercicio_atual`, `exercicio_anterior`. Contas recorrentes: `6212` / `6213` (receita
realizada − dedução), `6221304` + `6314` + `6322` (pago + RP não processados pagos + RP
processados pagos), `111` saldo inicial em L35.

## Impacto

| Eixo | Impacto |
|---|---|
| Banco / migration | nenhum |
| Cache / filas | nenhum |
| APIs externas | nenhum |
| Regressão | BO, BF, BP e DVP bit a bit iguais; índice ganha 84 chaves `dfc.*` |
| Teste herdado | `test_dois_documentos_integros` passa de 4 para 5 PDFs |

## Decisões

### D1 — Quatro quadros na mesma change de conhecimento
**Escolhido:** 84 regras de uma vez, sem Python. **Descartado:** só o Quadro Principal, no corte
da DVP. **Porquê:** o pedido é deixar o dev pronto para codar; fatiar a transcrição espalha as
14 linhas de risco.

### D2 — Exclusões entram no cálculo
**Escolhido:** `filters` `not_in`. **Descartado:** deixar a coluna só na evidência (DVP).
**Porquê:** a DVP mediu o I-HI sem exclusão; a DFC não tem anexo `tt/dca` equivalente. O PDF
lista exclusões de natureza, não de intra-OFSS de 5º nível. Executar ou não na apuração é
decisão da change de código.

### D3 — Outros sem conta ficam sem columns
**Escolhido:** L16, L21 e L30 `review_required`, sem `columns`. **Descartado:** inventar conta
de controle. **Porquê:** item 17 — situações não previstas, o ente adapta. L11/L25/L33 têm
lista no quadro e executam.

### D4 — Função na coluna Exclusões é filtro de inclusão (**medida em 2026-10-26**)
**Escolhido:** L32 e L3 do quadro de juros filtram Função 28 + subfunções 841–844 como `in`,
igual L14. **Descartado:** `not_in` dessas funções. **Porquê:** medido na MSC de 5 entes
(`docs/evidencia-dfc-d4-funcao-28.md`) — 98,97% a 100% do pagamento de amortização e de juros está
na função 28 com subfunção 84x, então a leitura `not_in` zeraria `L32` e `L14` em todos eles,
contra 4.242.326,51 e 115.201.049,07 que Porto Alegre publica. Leitura refutada por medição, não
por interpretação. Nenhum YAML mudou: a transcrição já adotava `in`; mudou o status da decisão,
registrado em `review.reason` de `L32` e de `J.L3`.

### D5 — Código do anexo é DFC
**Escolhido:** `demonstrativo.codigo: DFC`. **Descartado:** `I-E`. **Porquê:** `docs/anexos-siconfi-inventario.md` — I-E é despesa por função. A DFC é demonstrativo derivado, como BO/BF.

### D6 — Sem patch no validador
**Escolhido:** não editar `validate_rules.py` nem o schema. **Descartado:** acrescentar `IPC08`
em `CAMPOS_POR_DOCUMENTO`. **Porquê:** o default já é o conjunto de natureza/função. Falha por
enum ausente seria recado para o programador; aqui não houve.

### D7 — L36 é cálculo, não saldo final
**Escolhido:** L36 = L34 + L35. **Descartado:** `saldo: final` de `1.1.1`. **Porquê:** o PDF
escreve a fórmula de linhas e exige correspondência com o saldo final na policy, não no mapa
da linha.

### D8 — N5 não se corrige
**Escolhido:** literal `45.80.66`, `4.4..22.xx.xx`, `7.3.21.00.31.x`. **Descartado:** gravar
`4.5.80.66`. **Porquê:** regra do projeto — PDF prevalece; correção só com decisão registrada.

## Arquivos criados / alterados

| Arquivo | Ação |
|---|---|
| `knowledge/sources/ipc08/metadata.yaml` | criar |
| `knowledge/sources/ipc08/extracted.md` | criar |
| `knowledge/policies/ipc08.yaml` | criar |
| `knowledge/rules/dfc/quadro_principal.yaml` | criar |
| `knowledge/rules/dfc/transferencias_recebidas_concedidas.yaml` | criar |
| `knowledge/rules/dfc/desembolsos_pessoal_por_funcao.yaml` | criar |
| `knowledge/rules/dfc/juros_encargos_divida.yaml` | criar |
| `knowledge/indexes/rules_index.json` | regenerar |
| `tests/test_regras_bf.py` | 4 → 5 documentos |
| `tests/test_regras_dfc.py` | criar (fumaça da transcrição) |
| `openspec/changes/ipc08-dfc-regras-canonicas/**` | criar |
| `openspec/AGENTS.md` | registrar change ativa |
| `docs/entes-homologacao/porto-alegre/gabarito-dfc-2025.md` | criar (homologação estrutural) |
| `app/` | nenhum |

## Pendências conhecidas

- Aprovação formal do PO desta proposal (gate da change de apuração).
- 4 linhas `review_required`: L11 (2.9.40.00.1.1 e 2.9.90.00.1.1 ausentes da tabela NR), L16,
  L21, L30 (item 17).
- D4 decidido por medição: filtro de inclusão. Pendência nova da apuração — o quadro de juros do
  ente não reproduz a abertura interna/externa por subfunção e publica `J.L3` zerada
  (`docs/evidencia-dfc-d4-funcao-28.md`, achado colateral).
- D2 (executar exclusões) — confirmar com o PO na change de apuração, com medição.
- D9 decidido: `L27` soma `L30`, divergindo do literal. Aplicado no YAML e travado em teste.
- D10 decidido: L16/L21/L30 viram campos informados na apuração (padrão do BF). Não altera as
  84 regras; é escopo da change de apuração.
- `scripts/validate_rules.py` continua sem `IPC08` nos enums fechados; o default cobre os campos.

## Homologação estrutural — Porto Alegre/RS 2025 (2026-10-26)

`docs/entes-homologacao/porto-alegre/gabarito-dfc-2025.md`. DFC publicada pela administração
direta, PDF imagem pura, transcrita e conferida por **43 identidades do próprio demonstrativo —
todas fecham em centavos nas duas colunas**, incluindo as quatro amarrações entre quadros
(`P.L10 = T.L7`, `P.L13 = F.L29`, `P.L14 = J.L4`, `P.L15 = T.L15`).

Estrutura confirmada: 36 + **14** + 29 + 4 publicados contra 36 + 15 + 29 + 4 transcritos. A única
ausência é `T.L12` (a Consórcios Públicos), omissão do ente. Diferenças de forma, não de estrutura:
o ente inverte a ordem de L10/L11 e rotula L3 como *Receita Tributária*.

Três achados que a transcrição não revelava e que **pesam na change de apuração**:

### D9 (decidida pelo PO, 2026-10-26) — `L27` soma `L30`, divergindo do literal
**Escolhido:** `L27 = L28 + L29 + L30`, com a divergência registrada em `review.reason` e o literal
do PDF intacto em `evidence.text`. **Descartado:** seguir `L27 Ingressos (L28 + L29)` como grafado.
**Porquê:** é a única agregadora do quadro que não soma a própria linha "Outros" — `L2` inclui
`L11`, `L12` inclui `L16`, `L18` inclui `L21`, `L22` inclui `L25`, `L31` inclui `L33`. Com D10
tornando `L30` digitável, seguir o literal deixaria fora da soma um valor que o contador acabou de
informar. Porto Alegre não desempata (L30 vazia nas duas colunas), mas confirma o padrão das outras
cinco agregadoras, inclusive `L12 = L13+…+L16` fechando em centavos com `L16` valendo 12,4 bi.

Esta é a primeira divergência deliberada do literal na base — D8 exige decisão registrada, e esta é
a decisão. Travada por `tests/test_regras_dfc.py::test_agregadora_soma_a_propria_linha_outros`, que
cobre as seis agregadoras do quadro, não só `L27`.

### D10 (decidido pelo PO, 2026-10-26) — linha sem conta é campo informado
**Escolhido:** `L16`, `L21` e `L30` seguem sem `columns` e, na apuração, ficam **abertas para
digitação do contador** — o mesmo mecanismo já em produção no BF
(`app/services/bf/informados.py`, `CODIGOS_SEM_MAPEAMENTO = {"L22","L23","L55","L56"}`: whitelist
validada na rota, antes de enfileirar o job). **Descartado:** inventar conta de controle; apurar
por complemento. **Porquê:** o IPC 08 item 17 manda o ente adaptar; quem conhece o que caiu em
"Outros" é o contador do ente, não a regra canônica.

**Consequência:** D3 está confirmado e **as 84 regras não mudam** nesta change. O trabalho é todo
da change de apuração: `app/services/dfc/informados.py` com
`CODIGOS_SEM_MAPEAMENTO = {"L16", "L21", "L30"}`, recusa de código fora da whitelist e de valor
não-decimal antes do job, espelhando BF/BP.

**Forçou D9:** com `L30` digitável, o contador pode preenchê-la — e `L27 Ingressos (L28 + L29)`,
literal do PDF, deixaria o valor de fora. Em Porto Alegre L30 é vazia e o erro não aparece; com
campo aberto, apareceria. Decidido somar L30 (ver D9).

**`L11` não entra na whitelist:** tem contas declaradas, só com duas naturezas ausentes da tabela
STN. Apura e mede primeiro, como L28/L61 do BF — se a medição reprovar, aí vira campo informado.

### Peso real das linhas frágeis
`L16` concentra **62,6%** dos desembolsos operacionais (12.455.111.116,11 de 19.894.596.631,09) e
`L11`, **58,4%** dos ingressos (11.878.057.845,81 de 20.339.004.451,07). Com `L16` sem `columns`
(D3), `L12` apurado sai 7.439.485.514,98 — erro que propaga para `L1`, `L34` e `L36` e **quebra a
policy `ipc08.soma_fluxos_igual_variacao_caixa`**. D3 deixa de ser detalhe de borda: sem decisão do
PO sobre como preencher `L16` (resto por complemento, mapa do ente ou célula vazia assumida), a DFC
apurada não reproduz o demonstrativo.

### A DFC publicada não é só orçamentária
Ingressos operacionais de 20,3 bi contra receita orçamentária de 8,7 bi no BF do mesmo ente e
exercício. Mapear `L11`/`L16` apenas por natureza de receita/despesa orçamentária não alcança o
publicado — a change de apuração precisa medir o que compõe a diferença antes de fechar o mapa.
