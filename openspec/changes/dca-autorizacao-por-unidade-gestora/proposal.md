# Proposal — Leitura do DCA restrita às Unidades Gestoras autorizadas, e guard do módulo

**Status:** proposta
**Repositório:** `ps-dca`
**Capability:** `pipeline/plataforma` (ADDED)
**Anexo DCA:** BO, BP e BF (os recortáveis)
**Base normativa:** n/a (autorização; não muda número)
**Change irmã (pré-requisito):** `regras-rgf-api` › `CH-49-ug-siafic-no-dca` — publica `ugs` no
`POST /internal/authorize`

## Why

Dois defeitos de autorização, ambos **A01 Broken Access Control**:

1. **Toda UG do poder do usuário é visível.** `recortes.visiveis` (`app/domain/recorte.py:76-86`)
   libera cada chave `ug:` cujo `poder_orgao` case com um poder do usuário. Em Cuitegi, o contador
   do Fundo de Assistência enxerga o Fundo de Saúde e o Fundo de Previdência — todos Executivo — e
   o consolidado do ente. Não há cadastro que separe os três.
2. **O módulo `dca` não é verificado.** `AutorizadorHub.autorizar` (`app/auth/hub.py:85`) lê só
   `poderes` e descarta `modulos`, que o hub devolve desde a CH-47. Tirar o DCA de um usuário no
   cadastro esconde o menu no front e **não** impede a chamada HTTP. É o mesmo buraco que a CH-47
   fechou para RGF e importação.

## What Changes

- `AutorizadorHub.autorizar` passa a devolver poderes, módulos e UGs autorizadas; a rota guarda os
  três em `request.state`.
- Toda rota de anexo responde `403` quando `dca` não está nos módulos do usuário naquele ente.
- `recortes.visiveis` passa a receber as UGs autorizadas:
  - lista **vazia** → comportamento atual, por poder (usuário legado, `adm_sistema`, ente sem UG);
  - lista preenchida → as chaves `ug:` ficam limitadas à interseção;
  - `consolidado` e os grupos `poder:` só permanecem visíveis se as UGs autorizadas cobrirem
    **todas** as unidades que aquele recorte soma. É o que atende "o mesmo contador em todas as
    UGs" sem wildcard, e o que impede o consolidado de vazar a UG não autorizada.
- A regra vale também na **escrita**: a chave de `anterior_por_recorte` no
  `POST /dca/{BF|BP}/reprocessar` passa pelo mesmo filtro, como já faz com o poder
  (`pipeline-anterior-autorizacao-por-poder`).

**Fora de escopo:** recortes `po:` (ente sem SIAFIC não tem UG — segue só por poder); outros
módulos; cadastro de UG (vive no hub); `audite_ps`.

## Entradas e saídas

| Interface | Entrada | Saída |
|---|---|---|
| `POST /internal/authorize` (consumido) | `{sub, cod_ibge}` | `{poderes, modulos, ugs}` — `ugs` novo |
| `GET /dca/{anexo}?recorte=ug:<id>` | JWT + `id_ente` | `200` só se `<id>` autorizado; `403` senão |
| `GET /dca/{anexo}` (sem `recorte`) | JWT + `id_ente` | recorte padrão **entre os visíveis**; `403` se nenhum |
| qualquer rota de anexo | JWT + `id_ente` | `403` sem o módulo `dca` naquele ente |
| `POST /dca/{BF|BP}/reprocessar` | `anterior_por_recorte` | `403` em chave de UG não autorizada, sem job |

## Exemplo concreto

Cuitegi (`2505204`), exercício 2025. UGs: `1` Prefeitura, `3` Fundo de Saúde, `4` Fundo de
Assistência, `5` Fundo de Previdência, `7` Câmara.

| usuário | `poderes` / `ugs` do hub | `recortesDisponiveis` |
|---|---|---|
| Contador A | `[executivo]` / `["3","5"]` | `ug:3`, `ug:5` |
| Contador B | `[executivo]` / `["4"]` | `ug:4` |
| Contador C | `[legislativo]` / `["7"]` | `ug:7` |
| Contador único | `[consolidado]` / `["1","3","4","5","7"]` | `consolidado`, grupos e as 5 UGs |
| legado | `[executivo]` / `[]` | como hoje: `poder:executivo` + todas as UGs do Executivo |

## Critérios de aceite

- [ ] Contador A: `GET /dca/BO?recorte=ug:4` → `403`; `ug:3` e `ug:5` → `200`.
- [ ] Contador B: `recortesDisponiveis` tem exatamente um item (`ug:4`), sem `consolidado` e sem
      `poder:executivo` — duas UGs do mesmo poder deixam de se conceder acesso.
- [ ] Contador C (Legislativo) não vê nenhuma UG do Executivo, e vice-versa.
- [ ] Contador único (todas as UGs) vê `consolidado` e os grupos.
- [ ] Usuário com `ugs: []` responde **bit a bit igual** ao de hoje (golden do payload de BO/BP/BF
      de Cuitegi 2025, antes e depois).
- [ ] Usuário sem `dca` nos módulos recebe `403` em toda rota de anexo, inclusive chamando a API
      direto, sem passar pelo front.
- [ ] O mesmo usuário com UGs diferentes em dois entes recebe recortes diferentes em cada um.
- [ ] `reprocessar` com `anterior_por_recorte` de UG não autorizada → `403`, sem job e sem gravar
      nenhuma escolha do pedido.

## Casos de erro

| Situação | Comportamento esperado |
|---|---|
| `recorte=ug:<id>` não autorizado | `403`, sem corpo do recorte |
| Nenhum recorte visível ao usuário | `403` (`sem acesso a este recorte`), nunca `200` vazio |
| Hub sem o campo `ugs` (anterior à CH-49) | tratado como `[]` — comportamento atual |
| Hub indisponível | `503`, como hoje (fail closed) |
| Usuário sem `dca` | `403` em toda rota de anexo |
| Modo local (sem hub configurado) | segue `consolidado` sem restrição — só `development/test/local` |

## Restrições e riscos

- **O guard de módulo é bloqueio novo.** Quem usa o DCA hoje sem `dca` gravado passa a receber
  `403`. Exige a apuração em produção da CH-49 (task 7.4) **antes** do deploy, nos moldes do que a
  CH-47 fez com RGF/importação.
- **`ugs: []` é fail-open por desenho** — é o único modo de não revogar acesso de usuário legado
  (decisão do PO). A restrição nasce quando o admin edita a permissão.
- **Ordem de deploy:** hub primeiro. `ps-dca` antes do hub só veria `ugs` ausente, que é o legado.
- **Ente sem SIAFIC** emite por `po:` e não tem UG: a restrição não o alcança, e o `avisoRecorte`
  já explica por quê.

## Aprovação do PO

- [x] PO definiu os dois cenários e o escopo exclusivo do DCA (2026-10-20)
- [x] PO incluiu o guard de módulo `dca` no escopo (2026-10-20)
- [x] PO aprovou esta proposta e o `design.md` (2026-10-20) — gate liberado
