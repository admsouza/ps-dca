# Proposal — Fonte de dados escolhida por pedido (`use_siconfi`)

**Status:** aprovada pelo PO em 2026-10-06
**Repositório:** `ps-dca`
**Capability:** `pipeline/plataforma` (existente)
**Anexo DCA:** n/a (vale para todo anexo apurado pelo pipeline; medido no BF)
**Referência de comportamento:** `regras-rreo-api` — `use_siconfi` + `get_publicsoft_token`

## Why

O front (`front-declaracoes`, `DcaDialog`) já envia `use_siconfi` em todo `GET /dca/{anexo}` e
`POST /dca/{anexo}/reprocessar`, como faz no RREO e no RGF. A DCA ignora o parâmetro: a fonte sai
do `DATA_SOURCE` do processo worker. Em produção, em 2026-10-06, o worker subiu com
`fonte=siconfi`. Com SIAFIC marcado na tela, o BF de Cuitegi/2025 saiu da SICONFI, sem o estorno
de receita extra que a change `bf-estorno-receita-extra` aplica só na PublicSoft.

Há uma segunda lacuna no mesmo caminho: a DCA nunca entrega o token PublicSoft ao worker. A rota
recusa `x-authorization` vindo do browser, o que está correto, mas não o resolve no servidor como o
RREO faz. Mesmo com `DATA_SOURCE=publicsoft`, a MSC e os relatórios de estorno seriam consultados
sem credencial.

O custo de não resolver: o usuário escolhe a fonte e recebe outra, sem aviso. A troca de
`DATA_SOURCE` muda a fonte de todos os entes ao mesmo tempo.

## What Changes

- `GET /dca/{anexo}` e `POST /dca/{anexo}/reprocessar` aceitam `use_siconfi` (booleano, query).
  `true` apura pela SICONFI. `false` apura pela PublicSoft (SIAFIC).
- Sem `use_siconfi`, vale `false` (PublicSoft), como no RREO e no RGF.
- Com PublicSoft, a API resolve o `token_ps` do ente no hub (`POST /internal/resolve-tenant`, o
  mesmo contrato do RREO) e o guarda cifrado para o job, com expiração junto do job. O token nunca
  vem do browser nem vai em claro no payload da fila.
- A fonte entra na identidade do resultado em cache. Um resultado apurado por uma fonte não é
  servido a quem pediu a outra; a troca de fonte reapura o anexo.
- O log de boot do worker já mostra `fonte` e `versao_api`. Esta change não o altera.

**Fora de escopo:** `POST /batch-jobs` (percurso completo), que o front não chama na DCA; seletor
"Matriz CSV" do RREO; qualquer mudança no front.

## Entradas e saídas

| Interface | Entrada | Saída |
|---|---|---|
| `GET /dca/{anexo}` | `anReferencia`, `id_ente`, `use_siconfi` (opcional) | `200` com o resultado da fonte pedida, ou `202` com job |
| `POST /dca/{anexo}/reprocessar` | idem | `202` com job, apurado na fonte pedida |
| Hub `POST /internal/resolve-tenant` | `{sub, cod_ibge}` + `X-Internal-Secret` | `token_ps` |
| Cache `dca_anexo_cache.versao_regras` | — | sufixo da identidade passa a incluir a fonte, quando pedida |

## Exemplo concreto

Ente Cuitegi/PB (`id_ente=2505204`, o enviado pelo front), exercício 2025, anexo BF:

| Pedido | Fonte apurada | `L27` exercício atual | `L60` exercício atual | `procedencia.estorno_receita_extra` |
|---|---|---:|---:|---|
| `use_siconfi=false` | PublicSoft | 4486188.21 | 4479755.61 | `{"2025": "115679.40"}` |
| `use_siconfi=true` | SICONFI | movimento MSC (4601867.61) | movimento MSC (4595435.01) | ausente |

## Critérios de aceite

- [ ] `use_siconfi=false`: o job apura pela PublicSoft, com o token do ente, mesmo com
      `DATA_SOURCE=siconfi` no worker. Cuitegi/2025 sai com os valores da tabela, em centavos.
- [ ] `use_siconfi=true`: o job apura pela SICONFI e nenhum token é resolvido.
- [ ] Sem `use_siconfi`: a apuração usa a PublicSoft, como no RREO e no RGF.
- [ ] Depois de apurar com uma fonte, `GET` com a outra fonte responde `202`, não o cache.
- [ ] O token não aparece no payload do job nem em log.

## Casos de erro

| Situação | Comportamento esperado |
|---|---|
| `use_siconfi` não booleano | `422` |
| Ente sem `token_ps` no hub (PublicSoft) | `409`, nenhum job criado |
| Ente inexistente no hub (PublicSoft) | `404`, nenhum job criado |
| Usuário sem acesso ao ente no hub | `403`, nenhum job criado |
| Hub indisponível ao resolver o token | `503`, nenhum job criado |
| `x-authorization` enviado pelo browser | `400`, como hoje |

## Restrições e riscos

- A primeira leitura de cada anexo depois do deploy reapura uma vez: a fonte entra na identidade
  e o hash de `versao_api` muda com o código desta change.
- Depende de `AUTH_API_URL`, `S2S_API_SECRET` e `TOKEN_ENCRYPTION_KEY` na API e no worker.
- Desenho de autenticação igual ao de `regras-rgf-api` (`resolve_publicsoft_auth`); token em
  `x-authorization`, como no RREO.

## Aprovação do PO

- [x] PO aprovou esta proposta em 2026-10-06 — seguir o desenho de RREO/RGF, `x-authorization`,
      Cuitegi = `2505204`
