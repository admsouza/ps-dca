# Orientação ao front — DCA: `id_ente` no SSE e "processado em"

Duas mudanças no backend (`ps-dca`). **Nenhuma exige alterar o util de SSE compartilhado.**

## 1. SSE/polling de job — corrigido no backend

Sintoma: `422 {"detail":[{"loc":["query","id_ente"],"msg":"Field required"}]}` ao acompanhar o job
depois de processar/reprocessar. Causa: `src/utils/rreoJobSse.ts` monta `GET /sse/jobs/{id}` sem
`?id_ente=` (manda só `Authorization` + `X-Unidade-Id`), e a DCA exigia o query param.

Agora `id_ente` é opcional em toda rota da DCA e vale o header `X-Unidade-Id` quando ausente.
Regras: nenhum dos dois → `400`; ambos divergentes → `400`.

**Ação no front: nenhuma.** `buildDcaHeaders(idEnte)` já envia `X-Unidade-Id`. Continue mandando
`id_ente` nas chamadas de `dcaBalancoOrcamentarioService.ts` — o comportamento não muda.

## 2. "Processado em" — use `GET /dca/resumo`

Não há `calculado_em` no payload do `GET /dca/BO` (é o demonstrativo, não metadado). O equivalente
ao `GET /cache/BO` do RREO é o resumo, que já existe e cobre os oito anexos numa chamada:

```
GET /dca-api/dca/resumo?anReferencia=2025&id_ente=2507507
Authorization: Bearer <jwt>   |   X-Unidade-Id: 2507507
```

`200` sempre — inclusive sem nenhuma apuração. Nunca dispara cálculo.

```json
[
  {
    "anexo": "BO",
    "status": "ok",                                  // ok | processando | erro | sem_cache
    "calculado_em": "2026-09-09T12:31:04.512+00:00", // ISO 8601 com timezone; null em sem_cache
    "duracao_ms": 8412,
    "versao_api": "1.0.0",
    "versao_regras": "3f2a…",
    "erro_detalhe": null,                            // preenchido só quando status = "erro"
    "implementado": true                             // false = anexo previsto, ainda sem pipeline
  }
]
```

`calculado_em` passou a ser **recarimbado a cada apuração concluída** — antes ficava congelado na
primeira, então após reprocessar o Info mostraria data velha. Requer o backend atualizado.

### Service

```ts
// src/services/dcaBalancoOrcamentarioService.ts
export interface DcaResumoAnexo {
  anexo: string;
  status: 'ok' | 'processando' | 'erro' | 'sem_cache';
  calculado_em: string | null;
  duracao_ms: number | null;
  versao_regras: string | null;
  erro_detalhe: string | null;
}

export async function obterResumoBo(
  anReferencia: number,
  idEnte: string,
  signal?: AbortSignal,
): Promise<DcaResumoAnexo | null> {
  const { data } = await dcaClient.get<DcaResumoAnexo[]>('/dca/resumo', {
    params: { anReferencia, id_ente: idEnte },
    signal,
  });
  return data.find((e) => e.anexo === 'BO') ?? null;
}
```

### Uso na tela

- Buscar no mount da página e **após cada job concluído** (no `onDone`/depois de `acompanharJob`).
- `calculado_em` nulo ou `status: 'sem_cache'` → tooltip "ainda não processado".
- `status: 'erro'` → mostrar `erro_detalhe`.
- Formatar com o timezone local: `new Date(calculado_em).toLocaleString('pt-BR')`. A data vem em
  UTC com offset; não concatenar nem assumir horário de Brasília no cliente.
- Nunca derivar a data no cliente (`Date.now()` ao terminar o job): o job pode ter sido de outro
  usuário (`already_queued`) e o 200 pode vir do cache.

## Contrato de erro (inalterado)

`401` sem JWT · `403` unidade sem acesso · `422` sem regra vigente para o exercício ·
`503` fila ou hub de autorização indisponível.
