# Proposal — Estorno extra também na fonte SICONFI; auditoria do exercício anterior desligada

**Status:** em implementação — **aguardando aprovação do PO** (decisão do dev em 2026-10-06)
**Repositório:** `ps-dca`
**Capability:** `dca/balanco-financeiro` e `dca/fonte-msc` (existentes)
**Anexo DCA:** Balanço Financeiro (IPC 06), Quadro Principal

## Why

Com `use_siconfi=true`, `L27` e `L60` saíam brutas (movimento da MSC), e o mesmo ente publicava
dois BFs diferentes conforme a fonte marcada na tela. O estorno de receita/despesa extra não
depende da MSC: vem do relatório gerencial da PublicSoft, que está disponível para o ente com
`token_ps` qualquer que seja a fonte da matriz.

Em produção (2026-10-06), o BF pela PublicSoft caía por dois erros de contrato com a
`contabilidade-tools-api`:
- `401` no pré-check `GET /matriz-saldo/auditorias`. Esse endpoint exige o JWT do usuário, e o
  worker só tem o `token_ps`. RREO e RGF não fazem esse pré-check.
- `400` em `base-demonstrativos` por causa de `tipoMatriz`, que não está no DTO (o pipe usa
  `forbidNonWhitelisted`).

## What Changes

- **SICONFI abate o estorno.** A rota resolve o `token_ps` no hub também com `use_siconfi=true`.
  Com token, o BF abate `L27` e `L60` igual à PublicSoft (D1–D3 de `bf-estorno-receita-extra`).
  Sem token (ente só SICONFI ou hub fora), o BF sai sem abater e a procedência fica sem
  `estorno_*`. Sem acesso à unidade continua `403`.
- **Auditoria: o DCA não faz pré-check.** A auditoria é verificada no servidor:
  `base-demonstrativos` responde `409` quando a competência não foi auditada, e o adapter trata
  esse 409 como **sem dados**.
- **Auditoria do exercício anterior desligada temporariamente, aguardando o PO.** Se o exercício
  anterior responder `409`, o BF do exercício atual é publicado mesmo assim, e o anterior não
  bloqueia: as colunas anteriores ficam sem dados (`sem_dados_exercicio_anterior=true`) e o
  estorno **não** é abatido sobre o zero (sem isso `L27`/`L60` anteriores sairiam negativas).
  O exercício atual continua dependendo da própria auditoria.
- `base-demonstrativos` recebe só os parâmetros do DTO: `anReferencia`, `meReferencia`,
  `classeConta` e `idTv`.

**Fora de escopo:** o percurso completo (`POST /batch-jobs`), que não recebe `use_siconfi` nem
token e segue sem estorno.

## Exemplo concreto

PM Cuitegi/PB (`2505204`), 2025, `use_siconfi=true` com `token_ps`: `L27` = 4486188.21 e `L60` =
4479755.61, iguais aos de `use_siconfi=false`.

## Casos de erro

| Situação | Comportamento esperado |
|---|---|
| SICONFI, ente sem `token_ps` / hub fora | `202`; BF sem abatimento, procedência sem `estorno_*` |
| SICONFI, usuário sem acesso à unidade | `403`, sem job |
| Exercício anterior com auditoria pendente (`409`) | anterior sem dados, sem abatimento; atual publicado |
| `base-demonstrativos` com 401/5xx | a apuração falha (não vira demonstrativo vazio) |

## Pendências para o PO

1. Confirmar que o SICONFI deve publicar `L27`/`L60` líquidas. Isso revoga D1 de
   `bf-estorno-receita-extra` ("Só PublicSoft"), aprovada em 2026-10-05.
2. **Auditoria do exercício anterior:** manter desligada (o anterior não bloqueia) ou exigir
   auditoria nos dois exercícios?
3. Percurso completo: deve resolver token e abater?

## Aprovação do PO

- [ ] PO aprovou esta proposta em <data>
