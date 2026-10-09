# Design — Superávit / Déficit Financeiro por fonte

**Change:** `openspec/changes/bp-superavit-por-fonte/` · **Proposal aprovada pelo PO em:** pendente

## Contexto

A regra `bp.superavit_deficit.total` está `review_required` e a apuração devolve `None`. O BP lê as classes 1, 2 e 6. A conta `82111` está na classe 8. O `Registro` não guarda `complemento_fonte`.

Medido em Cuitegi 2025 (SICONFI, MSCE, saldo de encerramento): o total de 2024 com as fontes `2…` incluídas é `13.279.106,25`, igual ao impresso. O PO revogou a exclusão desse prefixo em 2026-10-08.

## Componentes afetados

| Componente | Papel na change |
|---|---|
| `app/infra/msc/fonte.py` | a leitura do BP passa a incluir a classe 8 |
| `app/domain/bo/modelo.py` | `Registro` ganha `complemento_fonte` |
| `app/infra/msc/normalizacao.py` | preenche o complemento (`complemento_fonte`) |
| `app/services/bp/quadro_principal.py` | monta as linhas do quadro e o total |
| `knowledge/rules/bp/superavit_deficit.yaml` | o total deixa de ser blocker; as linhas por fonte não viram uma regra cada |

## Fluxo da informação

```text
MSC classe 8 (ano e ano-1) → saldo C−D de 821110100 e 821110200
→ agrupa por fonte+complemento, inclusive fonte que começa com 2
→ linhas do quadro + Total → as duas visões
```

## Contratos / interfaces

Linha do quadro, além do `Total` já existente:

| Campo | Valor |
|---|---|
| `codigo` | 8 dígitos, `fonte_recursos` + complemento (`0000` se vazio) |
| `rotulo` | nomenclatura STN da fonte; complemento diferente de `0000` acrescenta a nomenclatura do complemento |
| `exercicio_atual` | saldo do ano pedido |
| `exercicio_anterior` | saldo do ano anterior |

Ordem: código crescente, `Total` por último.

## Impacto

| Eixo | Impacto |
|---|---|
| Banco / migration | nenhum |
| Cache | `versao_regras` muda; cache antigo do BP fica desatualizado até reprocessar |
| Filas / worker | o job do BP lê mais a classe 8, nos dois anos |
| APIs externas | `tt/msc_controle`, mesma paginação e timeout já usados |
| Regressão | Quadro Principal, F/P e Compensação saem iguais. Compensação continua `None` |

## Decisões

### D1 — Coluna anterior pela MSC do ano anterior
**Escolhido:** saldo de encerramento de N−1. · **Descartado:** coluna anterior publicada no `I-AB`. · **Porquê:** o `I-AB` não abre este quadro por fonte; o impresso de Cuitegi fecha com a MSC de 2024 nas linhas conferidas.

### D2 — Uma linha por fonte e complemento, não uma regra YAML por fonte
**Escolhido:** gerar as linhas na apuração. · **Descartado:** enumerar fontes no YAML. · **Porquê:** a cardinalidade é do ente (P7). O YAML guarda o total e a conta.

### D3 — Prefixo `2` entra
**Escolhido:** `fonte_recursos` que começa com `2` entra nas duas colunas. · **Descartado:** omitir `25000000`. · **Porquê:** o PO corrigiu em 2026-10-08. Sem essas fontes o total de 2024 não fecha os `13.279.106,25` do impresso.

### D4 — Fonte vazia entra
**Escolhido:** saldo sem fonte vira a linha `00000000`. · **Descartado:** jogar no resíduo e omitir do total. · **Porquê:** em Cuitegi 2025 são 3.840.319,73; omitir mudaria o total sem decisão do PO.

## Arquivos criados / alterados

| Arquivo | Ação |
|---|---|
| `app/domain/bo/modelo.py` | alterar |
| `app/infra/msc/normalizacao.py` | alterar |
| `app/infra/msc/fonte.py` | alterar |
| `app/services/bp/quadro_principal.py` | alterar |
| `knowledge/rules/bp/superavit_deficit.yaml` | alterar |
| `tests/bp/test_superavit_fonte.py` | criar |

## Pendências conhecidas

- O total de 2025 na MSC (48.827.308,73) não é o total impresso (23.325.698,13). O aceite desta change é a MSC com a regra acima. O total de 2024 (`13.279.106,25`) fecha com o impresso.
- `00000000` não aparece no trecho do impresso que foi conferido.
