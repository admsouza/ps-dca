# Design — Notificações do Discord no padrão do RREO e do RGF

**Change:** `openspec/changes/pipeline-notificacao-discord-padrao/` · **Proposal aprovada pelo PO em:** ____

## Contexto

`services/pipeline/notificacao.py` monta dois dicionários (fim de job e fim de percurso), e
`infra/notificacao/discord.py` formata **um** deles. O de percurso cai no formato do de anexo e sai
`None`. O desenho atual (serviço monta o dado, infra formata) está certo e continua; o que muda é que
a infra passa a conhecer os três tipos de mensagem.

## Componentes afetados

| Componente | Papel na change |
|---|---|
| `app/services/pipeline/notificacao.py` | três funções: `notificar_fim`, `notificar_percurso`, `notificar_recebida`; cada dict leva `tipo` |
| `app/infra/notificacao/discord.py` | formata os três tipos no padrão do RGF; `formatar_duracao` no formato dos irmãos |
| `app/infra/notificacao/ente.py` | **novo**: `rotulo_ente(cod_ibge) -> "Cidade - UF"` via `public.unidade_gestora` |
| `app/services/pipeline/completo.py` | notifica cada anexo (inclusive cache) e o resumo com e-mail, fonte e duração por anexo |
| `app/routes/anexos.py` | notifica a requisição recebida quando enfileira (anexo e percurso) |
| `app/routes/dependencias.py` | e-mail do solicitante (`sub`) disponível para a rota |
| `worker.py` | passa `solicitante_email` e `fonte` ao percurso; constrói o notificador com o resolvedor de ente |

## Fluxo da informação

```text
rota (202) ──► notificar_recebida ──► Discord (azul)
worker ─► job.executar ─► notificar_fim ─► Discord (verde/vermelho)
worker ─► completo.executar_percurso ─┬─► notificar_fim por anexo (verde/cinza/vermelho)
                                      └─► notificar_percurso ─► Discord (roxo/laranja)
DiscordNotificador.enviar(dict) ─► rotulo_ente(cod_ibge) ─► SELECT cidade, uf FROM public.unidade_gestora
```

## Contratos / interfaces

```python
# app/services/pipeline/notificacao.py — dicts, sem tipo de framework
{"tipo": "anexo", "ente", "exercicio", "anexo", "duracao_ms", "desfecho": "sucesso"|"erro"|"cache", "erro"}
{"tipo": "percurso", "ente", "exercicio", "duracao_ms", "falhas", "solicitante", "fonte",
 "anexos": [{"anexo", "status", "duracao_ms", "erro_detalhe"}]}
{"tipo": "recebida", "ente", "exercicio", "anexos": [...], "percurso": bool, "forcar": bool,
 "solicitante", "fonte"}

# app/infra/notificacao/ente.py
def rotulo_ente(cod_ibge: str) -> str: ...   # "Cuitegi - PB" | "2505204"
```

```sql
SELECT cidade, uf FROM public.unidade_gestora WHERE cod_ibge = :cod_ibge LIMIT 1
```

## Impacto

| Eixo | Impacto |
|---|---|
| Banco / migration | só leitura de `public.unidade_gestora` (`cod_ibge`, `cidade`, `uf`), confirmado pelo PO; sem migration |
| Cache | nenhum |
| Filas / worker | payload do percurso ganha `solicitante_email` e `fonte` (não sensíveis) |
| APIs externas | webhook do Discord: timeout 5 s, sem retry (já vigente) |
| Regressão | desfecho de job e de percurso inalterado; mudam só texto, cor e quantidade de mensagens |

## Decisões

### D1 — Formatação na infra, dado no serviço
**Escolhido:** o serviço monta dicts com `tipo`; `DiscordNotificador` formata · **Descartado:** o
serviço montar o embed · **Porquê:** é o desenho vigente e testável sem webhook. Trocar o canal
(Slack, e-mail) não toca no pipeline.

### D2 — Rótulo do ente resolvido na infra, com memória por processo
**Escolhido:** `rotulo_ente` com `lru_cache(maxsize=1024)` só para acertos; erro ou ausência devolve o
IBGE sem guardar · **Descartado:** consultar a cada mensagem; levar o rótulo pela fila ·
**Porquê:** cidade/UF não mudam durante a vida do worker, e a fila não deve carregar dado derivado.
Sem guardar a falha: banco que volta passa a responder.

### D3 — Percurso notifica por anexo dentro de `completo`, não em `job.executar`
**Escolhido:** `_apurar_um` devolve o desfecho e `executar_percurso` chama `notificar_fim` com ele
(inclusive `cache`) · **Descartado:** passar o notificador para `job.executar` · **Porquê:** o anexo em
cache nem passa por `executar`, e a ordem das mensagens (anexos, depois resumo) fica num lugar só.

### D4 — E-mail e fonte pela fila, nunca o token
**Escolhido:** `solicitante_email` (o `sub` do JWT) e `fonte` (`siconfi`|`publicsoft`) no payload do
percurso · **Porquê:** o worker não tem o JWT. Rótulo da fonte igual ao do RGF: `SICONFI` ou
`MSC-SIAFIC`.

### D5 — Requisição recebida só quando há job
**Escolhido:** notificar na rota só se a resposta for `202` · **Porquê:** o `200` do cache não
enfileira nada, e o RGF também notifica só o que enfileira.

## Arquivos criados / alterados

| Arquivo | Ação |
|---|---|
| `app/infra/notificacao/ente.py` | criar |
| `app/infra/notificacao/discord.py` | alterar |
| `app/services/pipeline/notificacao.py` | alterar |
| `app/services/pipeline/completo.py` | alterar |
| `app/routes/anexos.py`, `app/routes/dependencias.py` | alterar |
| `worker.py` | alterar |
| `tests/pipeline/test_notificacao_discord.py` | criar |
| `tests/pipeline/test_pipeline_completo.py` | alterar (cenários do resumo e por anexo) |
