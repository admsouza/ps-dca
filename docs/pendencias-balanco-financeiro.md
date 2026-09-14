# Pendências do Balanço Financeiro — estado em 2026-09-14

Consolida tudo que falta para o BF. A base canônica está entregue (`ipc06-bf-regras-canonicas`,
arquivada); a **apuração não existe** — não há uma linha de código do BF em `app/`. O que foi
medido veio de scripts de medição, fora do repositório, e está em `docs/evidencia-bf-jp-2025.md`.

## 1. O que já está validado contra dado

| Item | Evidência |
|---|---|
| Mapeamento de fontes por subgrupo (F3) | `L1 = L2+L3+L11` e `L34 = L35+L36+L44` fecham em 0,00; resíduo de fonte **zero** |
| `fonte_recursos` tem 4 dígitos; detalhamento em `complemento_fonte` | medido em todas as classes |
| `beginning_balance`, `ending_balance` e `period_change` respondem | classes 1, 2 e 6 |
| Direção do saldo **por conta** no BF | `L1` = 5.117.875.296,33, igual ao publicado no I-C |
| 4 âncoras publicadas | `L1`, `L25`, `L26`, `L34` — 1:1 em centavos |
| Volume e latência | 8 classes × 3 tipos de valor × 2 exercícios em ~45 s |

**4 linhas de 80** têm conferência contra dado publicado. As outras 76 não têm gabarito possível: o
`tt/dca` não publica o Balanço Financeiro.

## 2. O que não fecha

```
L33 TOTAL (VI)    15.898.515.801,53
L66 TOTAL (XII)   16.875.758.073,28
diferença           −977.242.271,75
```

O BF **não equilibra** — e equilíbrio é a propriedade que define o demonstrativo. Peças
identificadas, todas dentro das seis linhas sem mapeamento:

| Peça | Valor | Onde entraria |
|---|---|---|
| `1.2.1.3` Títulos Públicos, movimento credor no período | 374.780.440,97 | `L22` Resgates |
| `L27`/`L60` sem o filtro de fontes extraorçamentárias | −13.802.518,58 no líquido | `L27`/`L60` |
| restante | ~616.000.000 | `L23`, `L28`, `L55`, `L56`, `L61` e o item 38 |

## 3. Decisões do PO pendentes

| # | Assunto | Situação |
|---|---|---|
| **G5** | Linha bloqueada é parcela inexistente no total, ou propaga `None`? | **pendente** — sem a opção (a), `L21`, `L24`, `L33`, `L54`, `L57` e `L66` saem todas não apuradas e o BF fica em branco por causa de 6 linhas |
| **G6** | Renomear `app/domain/bo/` → `app/domain/nucleo/`, motor único | **pendente** — alternativa é duplicar ~500 linhas |
| **G7** | Direção do saldo por conta no BF, por coluna no BO | **pendente** — medido: por coluna, `L1` erra em 754.979.416,94 |
| **G8** | `L22`/`L55` pela variação de `1.1.4` e `1.2.1.3` | **pendente** — é o que provavelmente fecha os 977 milhões |
| ~~G9~~ | Par (matriz, tipo de saldo) | **decidido** em 2026-09-14: `MSCE`/abertura |
| ~~G10~~ | Periodicidade mensal | **decidido** em 2026-09-14: mensal entra, para entes com prestação de contas mensal |

## 4. O que nunca foi apurado

- **Coluna `exercicio_anterior`** — todas as 80 linhas têm duas colunas; só a do exercício atual foi
  medida.
- **Quadro Anexo** — as 14 linhas foram apuradas na medição, mas **nenhuma** foi conferida contra
  coisa alguma; `(c)` e `(f)` derivadas nunca foram validadas.
- **Item 38** (excluir transferências intraorçamentárias acompanhadas de execução) — a policy existe
  na base e não foi aplicada em nenhuma medição. Medido: receita intra 129.527.844,24 e despesa
  intra 128.361.663,58 em João Pessoa.
- **17 das 60 linhas apuradas valem zero** e não foram investigadas uma a uma. Zero pode ser
  correto (`L7`, `L40` num município sem SPSM) ou filtro que não casou — hoje não há como
  distinguir sem olhar linha por linha.
- **`L27`/`L60`** — o filtro de fontes extraorçamentárias (`860`–`869`) corta de 127.592.727,15
  para 24.347.660,58 no ingresso. O literal do IPC 06 diz `< fontes extraorçamentárias>`, mas isso
  não foi conferido contra nada.
- **Períodos mensais** — nenhuma competência além de 12 foi apurada. Com G10 decidido, o BF terá de
  responder por mês. O par do mensal é outro (`MSCC`/encerramento), e o **critério de identificação
  da MSCE mensal segue pendente** de decisão do PO com um ente real de prestação mensal
  (`docs/pendencias-periodicidade-mensal.md`) — o BF herda essa pendência inteira.

## 5. Bloqueios normativos (F1/F2 do IPC 06)

Seis linhas seguem `review_required`: `L22`, `L23`, `L28`, `L55`, `L56`, `L61`.

Medido em João Pessoa: as classes 7 e 8 do ente só trazem controles de disponibilidade por
destinação e programação financeira — **nenhuma** conta de movimentação de investimento ou bloqueio
de caixa. A saída provável não é achar a conta de controle do ente, e sim G8.

## 6. Implementação — nada feito

Não existe em `app/`:

- `app/services/bf/` — o serviço
- `app/cli/bf.py` — o CLI de verificação
- `tests/bf/` — os testes
- suporte a `fonte_recurso` no motor (hoje o campo da regra é singular e o do registro plural: o
  casamento falharia **em silêncio**, zerando 22 linhas)
- suporte a `saldo` (abertura/encerramento) e a `movimento` (credor/devedor) no cálculo da célula
- carregador de regras por demonstrativo — hoje fixo em `rules/bo`

Tudo isso é a change `bf-apuracao-f1`, que segue em **fase SPEC**, aguardando G5, G6, G7 e G8.

## 7. Ordem sugerida

1. Fechar G5–G8 com o PO.
2. `msc-fonte-e-competencia` (em curso) entrega a fonte por demonstrativo e a competência mensal —
   o BF depende das duas.
3. `bf-apuracao-f1`: motor único, fonte de recursos, saldo em data, movimento, duas colunas.
4. Investigar o desequilíbrio remanescente com o BF já rodando pelo código, não por script.
