# Entes de homologação do Balanço Financeiro

Uma pasta por ente, com três coisas:

| Arquivo | O que é |
|---|---|
| `*.pdf` | BF publicado pelo SIAFIC do ente, como recebido |
| `gabarito-bf-2025.md` | o PDF extraído em tabela, conferido pelas identidades do próprio demonstrativo |
| `auditoria-bf-2025.md` | **apuração pelo IPC 06 × publicado**, linha e coluna a linha e coluna |

## O que se persegue

A apuração segue o **mapeamento do IPC 06, ed. 2024-06** (`knowledge/rules/bf/quadro_principal.yaml`)
sobre a **matriz de saldos** que o ente envia à MSC, com as contas e os códigos da STN. O BF
publicado pelo ente é **referência de conferência, não alvo**: pode ter sido alterado na publicação
e divergir da matriz. Divergência vira registro de auditoria — nunca ajuste de regra canônica.

A conferência que vale **sem depender do ente** são as identidades do próprio demonstrativo
(`L1 = L2+L3+L11`, `L33 = L1+L15+L21+L24+L29`, …), apuradas sobre a matriz. Elas conferem em
**24 de 24, nos 5 entes**.

## Placar (rodada de 2026-09-18, 66 linhas × 2 colunas = 132 células)

| Ente | Confere | Diverge | Não apurável | Não comparável | Observação |
|---|---|---|---|---|---|
| [Recife/PE](recife/auditoria-bf-2025.md) | **86** | 34 | 12 | 0 | referência: 66 linhas 1:1 com o IPC 06 |
| [Belo Horizonte/MG](belo-horizonte/auditoria-bf-2025.md) | **86** | 26 | 12 | 8 | PDF é OCR; 2 células duvidosas |
| [João Pessoa/PB](joao-pessoa/auditoria-bf-2025.md) | 81 | 39 | 12 | 0 | agrega 4 vinculações; fecha por bloco |
| [Cuitegi/PB](cuitegi/auditoria-bf-2025.md) | 20 | 60 | 12 | 40 | publica 48 das 66 linhas |
| [Porto Alegre/RS](porto-alegre/auditoria-bf-2025.md) | 34 | 86 | 12 | 0 | PDF é da **administração direta**, MSC é consolidada |

"Não apurável" são as 6 linhas sem conta declarada no IPC 06 (`L22`, `L23`, `L28`, `L55`, `L56`,
`L61`), nas duas colunas. "Não comparável" é o que o ente agrega, omite ou não publica.

## Coluna do exercício anterior

Nesta rodada ela foi apurada da **MSCE do exercício anterior**, pelas mesmas regras do IPC 06 — é a
origem padrão. A change `bf-apuracao-f1` prevê uma segunda origem, à escolha de quem apura:
**preenchimento manual**, linha a linha. Ela existe porque o ente pode ter publicado o exercício
anterior com números que a matriz daquele ano não reproduz — em Recife, `L17` e `L50` de 2024 saem
628.456.869,17 da MSC contra 0,00 publicado. A origem usada é declarada na procedência do resultado.

## Terceira fonte: o RREO do próprio ente

Cada relatório traz a conferência contra o **RREO** que o ente publicou no SICONFI — independente do
PDF do BF. O **Anexo 01** cobre `L1`, `L34` e `L25`; o **Anexo 07** cobre `L58`, `L59` e as inscrições
do exercício anterior em `L25` e `L26`.

Em **32 de 34** confrontos o apurado bate em centavos com o RREO. Em **13** deles é o **BF
publicado** que diverge das outras duas fontes — em Cuitegi, todos os 6 confrontos têm
apuração = RREO e BF divergente (89.752.313,29 × 50.723.704,91 na receita). A apuração só diverge em
**2** casos: `L1` e `L34` de Recife, por registro sem fonte de recursos na MSC.

## Limitações conhecidas desta rodada

1. **Item 38** (excluir transferências intraorçamentárias acompanhadas de execução) **não é
   aplicado**, por decisão baseada em medição: a policy não diz quais códigos caracterizam a
   transferência, e a interpretação natural (receita das categorias 7 e 8, despesa com modalidade 91)
   **quebra o que já batia** — em Belo Horizonte e João Pessoa, `L1` e `L34` conferem em centavos sem
   a exclusão e divergem com ela. Volume medido: Recife 4,1%, Porto Alegre 12,9%, Belo Horizonte
   5,7%, João Pessoa 2,2%, Cuitegi 0%.
2. **`L27`/`L60`** pedem movimento **bruto** de depósitos restituíveis, que a MSC não expõe.
3. **Quadro Anexo** não apurado.

Evidência de tudo: `docs/evidencia-bf-medicao-2026-09-18.md`. Decisões pendentes do PO:
`docs/decisoes-bf-para-po-2026-09-18.md`.
