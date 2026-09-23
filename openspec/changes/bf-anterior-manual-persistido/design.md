# Design — Exercício anterior manual persiste na unidade

**Change:** `openspec/changes/bf-anterior-manual-persistido/` · **Proposal aprovada pelo PO em:** pendente

## Contexto

O BF já apura a coluna anterior no modo manual quando o pedido traz `anterior` e `valores_anteriores`. A identidade disso entra em `versao_regras`, mas a tabela `dca_anexo_cache` tem uma linha por `(id_ente, an_referencia, anexo)`. O pedido seguinte sem o mapa grava a MSC por cima.

O front manda o mapa na query. Isso vaza em log e se perde com a aba.

## Componentes afetados

| Componente | Papel na change |
|---|---|
| `app/routes/anexos.py` | `POST` lê o corpo; query com `valores_anteriores` responde `400`; pedido sem origem completa os parâmetros a partir da linha de cache |
| `app/services/bf/quadro_principal.py` | grava o mapa em `procedencia.valores_anteriores` |
| `app/services/pipeline/resultado.py` | publica esse campo |
| `app/services/pipeline/job.py` | erro de job não zera a procedência já gravada |
| `worker.py` | o percurso completo usa o mesmo completamento de parâmetros antes de apurar o BF |

## Fluxo da informação

```text
POST /dca/BF/reprocessar  corpo {manual, valores}
  → 400 se valores_anteriores veio na query
  → 422 se código ou decimal é inválido (linha intacta)
  → job → apurar → procedencia.valores_anteriores na mesma linha de cache

GET /dca/BF | POST reprocessar sem corpo | POST /batch-jobs
  → sem origem: lê procedencia.valores_anteriores e reaplica
  → origem msce explícita: apaga o mapa e apura pela MSC
```

## Contratos / interfaces

Corpo do `POST` que grava:

```json
{
  "origem_exercicio_anterior": "manual",
  "valores_anteriores": { "L17": "628456869.17", "A:L1:receita": "100.00" }
}
```

Quadro principal: chave = código da linha. Quadro anexo: `A:<código>:receita` e `A:<código>:deducoes`, como o serviço já aceita.

`procedencia` do resultado passa a poder trazer `valores_anteriores` com o mesmo mapa. Some quando a origem gravada é `msce_exercicio_anterior`.

Um helper só, chamado pela rota e pelo worker: parâmetros efetivos = corpo, ou o mapa da linha quando a origem foi omitida, ou vazio quando a origem explícita é MSC.

## Impacto

| Eixo | Impacto |
|---|---|
| Banco / migration | nenhum. JSONB `procedencia` já existe |
| Cache | a mesma linha. O sufixo de `versao_regras` continua distinguindo o mapa; a rota tem de calculá-lo também quando o mapa veio da linha, não só quando veio no pedido |
| Filas / worker | o job do percurso completa os parâmetros do BF antes de `apurador` |
| APIs externas | nenhuma |
| Regressão | BF sem mapa salvo segue saindo da MSC. BO não lê esse campo |

## Decisões

### D1 — O mapa mora na procedência da linha de cache
**Escolhido:** campo `valores_anteriores` em `procedencia`. **Descartado:** tabela nova de preferência. **Porquê:** a autorização e a linha já existem; outro recurso com a mesma regra de acesso não protege mais.

### D2 — Omisso reaplica; MSC só explícita
**Escolhido:** ausência de origem reaplica o mapa salvo. **Descartado:** ausência continua significando MSC. **Porquê:** é a ausência que hoje apaga a coluna no reprocessar e no percurso.

### D3 — Gravação no corpo do POST
**Escolhido:** `POST /dca/BF/reprocessar` com JSON. **Descartado:** manter `valores_anteriores` na query. **Porquê:** query cai em log, histórico e `Referer`. A query com esse nome passa a `400`.

### D4 — Erro de job não limpa a procedência
**Escolhido:** `_gravar_erro` deixa `procedencia` como está. **Descartado:** zerar o resultado e a procedência juntos. **Porquê:** o mapa mora na procedência; zerá-la no erro apaga o preenchimento.

## Arquivos criados / alterados

| Arquivo | Ação |
|---|---|
| `app/services/bf/quadro_principal.py` | alterar |
| `app/services/pipeline/resultado.py` | alterar |
| `app/services/pipeline/cache.py` | alterar — helper dos parâmetros efetivos |
| `app/routes/anexos.py` | alterar |
| `app/services/pipeline/job.py` | alterar — erro conserva procedência |
| `worker.py` | alterar — percurso usa o helper |
| `tests/bf/test_apuracao.py` | alterar |
| `tests/pipeline/test_rota_bf.py` | alterar |
| `tests/pipeline/test_pipeline_completo.py` | alterar |

## Pendências conhecidas

- O front em produção ainda manda o mapa na query. Até a change irmã subir, esse caminho responde `400`. As duas changes sobem juntas.
