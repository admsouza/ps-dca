# Proposal — Completar linhas sem mapeamento IPC 06 (exercício atual)

**Status:** aprovada
**Repositório:** `ps-dca`
**Capability:** `dca/balanco-financeiro` (existente)
**Anexo DCA:** Balanço Financeiro (IPC 06)
**Base normativa:** IPC 06 — seis linhas do quadro principal sem conta declarada (`L22`, `L23`, `L28`, `L55`, `L56`, `L61`)
**Change irmã:** `front-declaracoes` / `bf-completar-nao-apuradas-g8`

## Why

Seis linhas do Quadro Principal não têm conta no IPC 06 e saem `None` (“não apuradas”). Nos entes de homologação, o BF **publicado** traz valores materiais nessas linhas (ordem de bilhões em Recife) que a MSC não produz. Hoje o operador não tem como completar o exercício **atual** nessas células: a spec proíbe preenchimento manual do atual, e o fluxo Manual existe só para a coluna do exercício **anterior**.

A dor não é “modo manual do ano corrente”. É **completar o buraco normativo** onde a regra não mapeou conta — independente da origem MSC/Manual do exercício anterior.

## What Changes

- Aceitar no corpo de `POST /dca/BF/reprocessar` o mapa `valores_sem_mapeamento: { "<código G8>": "<decimal>" }`.
- Esse mapa **não** exige `origem_exercicio_anterior: manual` e **não** se mistura com `valores_anteriores`.
- Após apurar o exercício atual pela MSC: sobrescrever só as células G8 informadas; reaplicar compostas da coluna atual; remover essas células de `diagnostico.nao_apuradas`.
- Gravar o mapa em `procedencia.valores_sem_mapeamento` na linha de cache. Pedido seguinte **sem** o mapa no body SHALL reaplicar o salvo (mesmo padrão do mapa anterior).
- Validação: só os seis códigos G8; código fora da lista ou não decimal → `422`; mapa na query → `400`.
- A frase vigente “a coluna do exercício atual NÃO DEVE aceitar preenchimento manual” SHALL ser **revogada parcialmente**: override pontual só nas G8 via `valores_sem_mapeamento`. O restante do atual continua só da MSC.

**Fora de escopo:** editar o exercício atual inteiro; anexo `*_atual`; unificar com o radio MSC/Manual do anterior; histórico de edições; tabela nova; autosave.

## Entradas e saídas

| Interface | Entrada | Saída |
|---|---|---|
| `POST /dca/BF/reprocessar` | query: `anReferencia`, `id_ente`; corpo `{ "valores_sem_mapeamento": { "L22": "1234567.89" } }` (origem anterior opcional/independente) | `202`; ao fim, `L22.exercicio_atual` = valor; `procedencia.valores_sem_mapeamento` = mapa informado; diagnóstico sem essa célula |
| `GET /dca/BF` | sem mapa | `200` com as G8 completadas iguais à última gravação, quando houver mapa salvo |
| `POST /batch-jobs` / reprocessar sem mapa | — | reaplica `valores_sem_mapeamento` salvo; MSC recalcula o restante do atual |
| Limpar override | corpo `{ "valores_sem_mapeamento": {} }` **ou** omitir e enviar flag explícita — **decisão na implementação:** YAGNI = mapa vazio no body limpa; ausência de chave no body **mantém** o salvo | células voltam a `None` + diagnóstico |

Autorização: a mesma das rotas de anexo.

## Exemplo concreto

| Ente | Exercício | Célula | Valor |
|---|---|---|---|
| 2611606 — Recife | 2025 | `L22` / `exercicio_atual` | `1234567.89` no body → após job e `GET` sem mapa, a célula continua `1234567.89`; `L21` (pai) reflete a composta com essa parcela |

## Critérios de aceite

- [ ] Recife/2025: POST com `L22` = `1234567.89` → célula atual = esse valor; diagnóstico sem `l22.exercicio_atual`.
- [ ] `GET` seguinte sem mapa mantém a célula.
- [ ] Origem do exercício anterior permanece MSC (ou Manual) sem ser alterada por esse POST.
- [ ] Código fora de G8 no mapa → `422`; mapa na query → `400`.
- [ ] Reprocessar/batch sem mapa reaplica o salvo; compostas (`L21`, totais) usam a parcela informada.

## Casos de erro

| Situação | Esperado |
|---|---|
| Código não-G8 | `422`; mapa salvo anterior intacto |
| Decimal inválido | `422` |
| `valores_sem_mapeamento` na query | `400` |

## Restrições

- Change irmã de UI em `front-declaracoes` / `bf-completar-nao-apuradas-g8`.
- Não reabrir o desenho de `valores_anteriores` / MSC explícita do anterior.

## Aprovação do PO

- [x] PO aprovou o framing (completar G8 ≠ modo manual do atual) em 2026-09-24
- [x] PO aprovou esta proposta escrita em 2026-09-24
