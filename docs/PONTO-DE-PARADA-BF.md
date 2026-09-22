# Ponto de parada — Balanço Financeiro (2026-09-18)

Documento de handoff. Escrito para quem chega sem contexto nenhum. O handoff do Balanço
Orçamentário e da plataforma continua em `docs/PONTO-DE-PARADA.md`; este cobre o BF.

## Onde estamos, em uma frase

O **Balanço Financeiro do IPC 06 está concluído no backend** — apurado da MSC, servido por
`GET /dca/BF`, homologado em 5 entes e com as quatro changes arquivadas. O front tem a spec escrita
e já começou a implementar.

```bash
python -m pytest                                  # 403 passed, exit 0
python -m ruff check .                            # limpo, salvo 2 achados pré-existentes
python -m app.cli.bf 2611606 2025                 # apura Recife contra a API do SICONFI
python -m app.cli.bf 2611606 2025 --quadro anexo  # só o quadro anexo
python -m app.cli.bf 2611606 2025 --json          # mesmo JSON que a rota serve
```

## Por onde retomar

1. **Nada bloqueia o front.** A rota responde e o contrato está estável.
2. A única change ativa do BF é `openspec/changes/vigencia-por-anexo/` — implementada e verde,
   aguardando aprovação e arquivamento.
3. As decisões do PO em `docs/decisoes-bf-para-po-2026-09-18.md` foram **adotadas conforme a
   recomendação medida** e continuam sujeitas a confirmação na auditoria final.

## 1. O que foi entregue

| Camada | Onde |
|---|---|
| Apuração | `app/services/bf/quadro_principal.py` — os dois quadros, 80 linhas |
| Motor | `app/domain/bo/` — **o mesmo do BO**, sem duplicação |
| CLI | `app/cli/bf.py` |
| Rota | `GET /dca/BF`, `POST /dca/BF/reprocessar` — registry, cache, job |
| Regras | `knowledge/rules/bf/` (66 + 14 linhas, IPC 06 ed. 2024-06) |
| Spec | `openspec/specs/dca/balanco-financeiro/spec.md` — 49 cenários, todos com teste |

### Changes arquivadas em 2026-09-18

| Change | O que entregou |
|---|---|
| `2026-09-18-bf-apuracao-f1` | núcleo, serviço e CLI do quadro principal |
| `2026-09-18-bf-quadro-anexo` | 14 linhas × 6 colunas, com as derivadas |
| `2026-09-18-msc-competencia-de-encerramento` | competência 13 na PublicSoft, 12 no SICONFI |
| `2026-09-18-bf-no-pipeline` | `GET /dca/BF` e o que a plataforma precisou aprender |

## 2. As quatro coisas que o BF ensinou, e que não devem ser reaprendidas

### 2.1 A origem do saldo é por **linha**, não por demonstrativo

Três origens cobrem o quadro principal, e cada uma foi medida contra o publicado:

| Origem | Linhas | Por quê |
|---|---|---|
| MSCE/abertura do exercício | as demais, inclusive `L62`–`L65` | é a **posição final** do exercício |
| MSCE/**encerramento** | `L25`, `L26` | `5.3.1.7` e `5.3.2.7` **não existem** na abertura |
| MSCE/abertura do **ano anterior** | `L29`–`L32` | o saldo do exercício anterior é o do ano−1 |

Ler tudo de uma origem só devolve `L25`/`L26` **zeradas sem erro**. Está em
`DO_ENCERRAMENTO` e `DO_EXERCICIO_ANTERIOR`, no serviço.

### 2.2 Direção do saldo **por conta** (G7)

No BF, cada conta entra na direção dela — `saldo_da_celula_por_conta`. A regra do IPC 06 já traz o
sinal do par redutor. Com a direção da coluna, `L1` de Recife erra em 754 milhões. O BO continua
com direção de coluna; os dois critérios convivem no mesmo motor.

### 2.3 A fonte de recursos casa por **igualdade** de 3 dígitos

A MSC entrega 4 dígitos e o 1º é o exercício da vinculação (`1500` é a fonte `500`). O campo da
regra é `fonte_recurso` (singular) e o do registro é `fonte_recursos` — religados em
`saldo._campo`. Sem isso, **nenhuma** das 22 linhas por fonte casaria, e sairiam zeradas sem erro.

### 2.4 Seis linhas não têm conta no IPC 06

`L22`, `L23`, `L28`, `L55`, `L56`, `L61`. Saem **não apuradas**, nunca zero, e contribuem como
parcela inexistente no total. A busca reversa (7 combinações de matriz × tipo de saldo, todos os
prefixos de conta, saldo/créditos/débitos) **não achou** os valores publicados em nenhuma delas —
e o método foi validado por controle, achando `L16` e `L25`.

## 3. O que foi verificado, e como

### 3.1 Identidades do IPC 06 — a garantia que não depende de ente

As 24 identidades (`L1 = L2+L3+L11`, `L33 = L1+L15+L21+L24+L29`, …) fecham em centavos nos **5
entes**, nas duas colunas. É isto que prova fidelidade ao mapeamento, e não a comparação com o PDF.

### 3.2 Conferência cruzada com o RREO do próprio ente

Terceira fonte, independente do PDF: **32 de 34** confrontos batem em centavos. Em 13 deles é o
**BF publicado** que diverge das outras duas fontes.

| Ente | Confere com o RREO | Observação |
|---|---|---|
| Belo Horizonte, João Pessoa | 7/7 | as três fontes concordam |
| Porto Alegre | 7/7 | o PDF é da administração direta; a MSC é consolidada |
| **Cuitegi** | 6/6 | **o BF publicado diverge do próprio RREO do ente** |
| Recife | 5/7 | `L1` e `L34`: registro sem fonte de recursos (ver 4.1) |

### 3.3 Relatórios de auditoria por ente

`docs/entes-homologacao/<ente>/auditoria-bf-2025.md` — 132 células (66 linhas × 2 colunas), com
divergências linha e coluna a linha e coluna, identidades, conferência com o RREO e o quadro anexo.
Gerados pelo **código de produção**.

## 4. Divergências conhecidas — para a auditoria final, não para o código

### 4.1 Recife: 450.202.814,72 sem fonte de recursos

Dois registros na conta sintética de receita orçamentária, **sem fonte na MSC**. O IPC 06 compõe
`L1` como soma das linhas por fonte, então o total perde esse valor. A receita apurada **direto das
contas** dá 10.390.050.823,18 — igual ao RREO e ao BF do ente. Hoje o valor aparece como **resíduo
declarado** no diagnóstico. Decisão D10 do documento do PO.

### 4.2 `L27`/`L60`: a MSC não tem o movimento bruto

Saldo de `2.1.8.8`: 132.890.609,07 (2024) → 176.421.602,57 (2025), variação +43.530.993,50; o
`period_change` da MSCC dá −6.107.254,33; o publicado implica +123.944.269,55. Três números, nenhum
igual. Não há o que apurar além do saldo.

### 4.3 Item 38 (intraorçamentárias): declarado e **não aplicado**

A policy não diz quais códigos caracterizam a transferência. A interpretação natural (receita das
categorias 7/8, despesa de modalidade 91) foi medida e **quebra `L1` e `L34` em BH e JP**, que
conferem sem ela. Fica no diagnóstico como policy declarada e não executada.

### 4.4 Porto Alegre não homologa no recorte atual

O PDF é da **administração direta** e a MSC é consolidada: `L11`–`L14` saem 2,27 bi contra zero
publicado. Não é erro de apuração.

## 5. O que está aberto

| Item | Onde | Bloqueia? |
|---|---|---|
| Change `vigencia-por-anexo` — implementada, a arquivar | `openspec/changes/` | não |
| 10 decisões do PO, adotadas conforme recomendação | `docs/decisoes-bf-para-po-2026-09-18.md` | não |
| Divergências de 4.1 a 4.4 | relatórios de auditoria | não |
| MSC de encerramento na periodicidade **mensal** | `docs/pendencias-periodicidade-mensal.md` | não |
| Front: implementação da UI | `front-declaracoes`, change `dca-balanco-financeiro` | — |

## 6. Detalhes que economizam tempo

- **A competência de encerramento não tem o mesmo número nas duas APIs.** SICONFI: competência 12
  com `co_tipo_matriz=MSCE` (pedir 13 devolve **zero registros**, medido nos 4 entes). PublicSoft:
  competência especial **13** (`mesMsc=13`). A tradução mora no adapter; o domínio fala 1–12.
- **Conta contábil não pode aparecer no código** — nem em docstring. `test_nenhuma_conta_literal_no_apurador`
  varre `app/` e quebra. A conta vem sempre da base canônica.
- **O `tt/dca` não publica o BF.** Não procure gabarito lá: 2.002 registros, 7 anexos, nenhum é o BF.
- **Os PDFs dos entes** estão em `docs/entes-homologacao/<ente>/`, com o gabarito extraído ao lado.
  Porto Alegre é **imagem pura** — foi transcrito visualmente e validado pelas identidades.
- **Scripts de medição** ficaram no scratchpad da sessão, não no repo. O que precisa ser
  reproduzível está nos relatórios de auditoria e na evidência.

## 7. Documentos do BF

| Documento | O que traz |
|---|---|
| `docs/evidencia-bf-medicao-2026-09-18.md` | a medição completa, com os números de cada achado |
| `docs/decisoes-bf-para-po-2026-09-18.md` | as 10 decisões, com a evidência de cada uma |
| `docs/entes-homologacao/README.md` | placar dos 5 entes e a regra de ouro da homologação |
| `docs/entes-homologacao/<ente>/auditoria-bf-2025.md` | divergências por linha e coluna |
| `docs/depara-bf-siafic-ipc06.md` | rótulo do SIAFIC → linha do IPC 06, por ente |
