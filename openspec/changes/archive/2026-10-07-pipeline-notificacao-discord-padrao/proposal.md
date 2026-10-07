# Proposal — Notificações do Discord no padrão do RREO e do RGF

**Status:** arquivada (2026-10-07)
**Repositório:** `ps-dca`
**Capabilities:** `pipeline/plataforma` (existente), `pipeline/processamento-completo` (existente)
**Anexo DCA:** n/a — canal de operação
**Fonte da verdade externa:** `regras-rgf-api/worker.py` (mensagens por anexo e resumo do pipeline),
`regras-rgf-api/app/routes/jobs_rgf_completo.py` (requisição recebida),
`regras-rgf-api/app/utils/discord_notifier.py` (`fmt_duracao`, `label_ente`)

## Why

O canal de operação recebe hoje, do DCA (2026-10-07, ente `2510808`):

```text
DCA — None concluído
Ente: 2510808 | Exercício: 2025
Anexo: None | Duração: 2 min 8 s
```

1. **Bug:** o fim do percurso completo manda uma mensagem sem `anexo`, com a lista de anexos à parte.
   `DiscordNotificador.enviar` só conhece a mensagem de um anexo e imprime `None`. Somem a lista
   de anexos, as falhas e o "com erros", que vira "concluído".
2. **Spec × código:** `pipeline/processamento-completo` diz "não sai uma notificação por anexo", mas
   saem: `job.executar` notifica cada anexo do percurso. Em 2026-10-07 o canal mostrou BO e BF
   individuais seguidos do resumo quebrado.
3. **Padrão divergente:** RREO e RGF usam título `<Relatório> <Anexo> — Concluído ✅`, ente como
   `Cidade - UF`, duração `18.7s` / `1m 13s`, resumo do pipeline com detalhamento por anexo e uma
   mensagem de requisição recebida. O DCA usa outro formato, e quem opera os três sistemas lê dois
   vocabulários no mesmo canal.

## What Changes

- **Mensagem por anexo** no formato do RGF: `DCA BO — Concluído ✅` (verde), `— Cache ✅` (cinza),
  `— Falhou ❌` (vermelho, motivo em bloco de código, até 900 caracteres).
- **Resumo do percurso** no formato do pipeline do RGF: título `✅ Cuitegi - PB  2025 [Anual] —
  usuario@x`, corpo `3 anexo(s) concluído(s) com sucesso.` ou `Fila concluída com 1 falha(s).`,
  campos `Fonte MSC`, `Tempo total`, `Detalhamento` (`BO — 3.3s ✅`, `BF — cache ✅`,
  `BP — 2.0s ❌`) e `Erros`. Cor roxa sem falha, laranja com falha.
- **Percurso notifica por anexo e no fim** (decisão do PO, 2026-10-07): revoga o "não sai uma
  notificação por anexo".
- **Requisição recebida** (azul), ao enfileirar: `DCA BO — Requisição Recebida (Processar) [Anual] —
  usuario@x` e `DCA — Requisição Recebida (Reprocessar) [Anual] — usuario@x` para o percurso.
- **Ente como `Cidade - UF`**, lido de `public.unidade_gestora` (`cod_ibge`, `cidade`, `uf`) no
  banco compartilhado (schema confirmado pelo PO em 2026-10-07). Ente não encontrado ou banco fora:
  o código IBGE, sem falhar a notificação.
- **Duração** no formato dos irmãos: `850ms`→`0.9s`, `18.7s`, `1m 13s`.

**Fora de escopo:** notificação de login (o DCA não tem login próprio); mensagem de cancelamento
(o DCA não cancela job); mudar o canal ou o webhook.

## Entradas e saídas

| Interface | Entrada | Saída no Discord (embed) |
|---|---|---|
| fim de job de anexo | ente, exercício, anexo, duração, desfecho, erro | título, descrição, cor |
| fim de percurso | ente, exercício, solicitante, fonte, duração total, anexos com status/duração/erro | título, descrição, cor, campos `Fonte MSC`, `Tempo total`, `Detalhamento`, `Erros` |
| requisição recebida | ente, exercício, anexo (ou percurso), modo, solicitante, fonte, anexos na fila | título, descrição, cor azul |
| `GET /dca/{anexo}` com cache válido (200) | — | **nada**: não há job |

## Exemplo concreto

Cuitegi/PB (`2505204`), exercício 2025, percurso completo pedido por `jackson@x`, fonte SICONFI. BO
e BP apurados, BF do cache:

```text
DCA BO — Concluído ✅            Cuitegi - PB | 2025 | Tempo: 3.3s
DCA BF — Cache ✅                Cuitegi - PB | 2025 | Dados já em cache
DCA BP — Concluído ✅            Cuitegi - PB | 2025 | Tempo: 4.4s
✅ Cuitegi - PB  2025 [Anual] — jackson@x
3 anexo(s) concluído(s) com sucesso.
Fonte MSC: SICONFI · Tempo total: 7.9s
Detalhamento: BO — 3.3s ✅ / BF — cache ✅ / BP — 4.4s ✅
```

## Critérios de aceite

- [ ] Nenhuma mensagem com `None` no título ou no corpo, em nenhum caminho (anexo, percurso, recebida).
- [ ] Resumo do percurso com uma linha de detalhamento por anexo implementado, na ordem do registry.
- [ ] Percurso de 3 anexos sem cache produz 3 mensagens por anexo + 1 resumo; com 1 em cache, a dele
      sai como `Cache ✅`.
- [ ] Ente presente em `unidade_gestora` sai `Cidade - UF`; ausente, o código IBGE.
- [ ] Banco fora ao resolver o nome: a notificação sai com o código IBGE e o job não muda de desfecho.
- [ ] `formatar_duracao`: `0.9s` (850 ms), `18.7s`, `1m 13s`, `2m 8s`.
- [ ] Regressão: os cenários de canal indisponível e não configurado continuam passando.
- [ ] `python -m pytest` e `python -m ruff check .` sem falha nova.

## Casos de erro

| Situação | Comportamento esperado |
|---|---|
| Webhook fora do ar | log de aviso; resultado e estado do job inalterados (já vigente) |
| Webhook não configurado | nada é enviado (já vigente) |
| `unidade_gestora` sem o `cod_ibge` | rótulo = código IBGE |
| Banco indisponível ao consultar o rótulo | rótulo = código IBGE; falha logada em `debug`, sem stack no canal |
| Erro maior que 900 caracteres | truncado em 900, como no RGF |
| Solicitante sem e-mail no token | título termina em `— desconhecido`, como no RGF |

## Restrições e riscos

- O e-mail do solicitante vai ao canal de operação, como já fazem RREO e RGF. Token, `token_ps` e
  segredo nunca entram na mensagem.
- `unidade_gestora` é do RGF. O DCA só lê `cod_ibge`, `cidade` e `uf`, sem migration nem escrita.
- O resumo do percurso precisa do e-mail e da fonte no payload do job do percurso. Os dois são
  dados não sensíveis e entram junto do `solicitado_por` que já vai.

## Aprovação do PO

- [x] PO pediu a change e decidiu, em 2026-10-07: mensagens por anexo + resumo; ente `Cidade - UF`
      via `public.unidade_gestora` no mesmo banco; mensagem de requisição recebida
- [x] PO aprovou a proposal em 2026-10-07
