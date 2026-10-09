# Proposal — DCA processada com todas as unidades, emitida por UG ou por PO

**Status:** aprovada pelo PO (2026-10-09)
**Repositório:** `ps-dca` (fonte: `ps-erp` change `pca-dados-por-unidade-gestora`; hub: `regras-rgf-api` CH-46; front: `front-declaracoes` `dca-recorte-unidade-gestora`)
**Capability:** `pipeline/unidade-gestora` (nova) · `dca/balanco-orcamentario` (existente: contrato da fonte)
**Anexo DCA:** BO (quadro principal e RP) · BP / `DCA-Anexo I-AB` (todos os quadros)
**Base normativa:** MCASP · IPC 04 item 8 (levantamento de unidade específica) · IPC 07 · tabela de Poder/Órgão da STN (`docs/contas-stn/poder-orgao.md`)

## Why

A DCA é uma das peças da PCA/Balanços do município, e a PCA é prestada por **unidade gestora** (UG)
além do ente consolidado: Prefeitura, fundos, Câmara, RPPS. Hoje o `ps-dca` só conhece o ente
(`cod_ibge`), e o usuário não consegue emitir BO ou BP de uma parte do ente.

O `ps-erp` já entrega a base de demonstrativos com a UG em cada item
(`GET /matriz-saldo/base-demonstrativos/unidades-gestoras`). A soma das UGs bate com o consolidado,
validado em produção pelo PO em 2026-10-09. Os entes sem UG na fonte também precisam ser recortados.
São os que importam a MSC por CSV e os processados pelo SICONFI. Nesses casos o recorte possível é o
**poder/órgão (PO)**, informação complementar que a MSC traz em todo registro.

Cada recorte é apurado como uma apuração completa sobre os registros dele: o consolidado, cada
grupo de poder e cada unidade. Somar matrizes finais erraria o Déficit e o Superávit do BO, que
dependem do sinal do conjunto.

## What Changes

**Processamento** — um job serve todas as emissões
- O job do BO e do BP apura, além do consolidado de hoje:
  - um resultado por grupo de poder: Executivo (`10131` + `10132`), Legislativo (`20231`) e
    Executivo + Legislativo;
  - um resultado por unidade: **UG** quando a fonte a informa (PublicSoft com base por UG), **PO**
    quando não informa (SICONFI, ou ente que importa CSV, cuja base por UG responde `422`).
- Cada recorte é o mesmo serviço de apuração de hoje sobre os registros filtrados. A MSC já lida no
  job é reaproveitada, sem nova chamada à fonte.

**Emissão**
- `GET /dca/{BO|BP}?recorte=consolidado|poder:executivo|ug:3|po:20231` serve o recorte do cache e
  **não enfileira job**.
- Sem `recorte`, serve o padrão do poder do usuário.
- A resposta traz `recorte` (a chave servida) e `recortesDisponiveis` (os recortes visíveis, com
  rótulo).

**BP**
- Fora do consolidado, a coluna do exercício anterior vem da **MSC de encerramento do ano anterior**
  com os registros do recorte. A DCA publicada só existe consolidada.
- A conferência contra o `I-AB` publicado só aparece no consolidado.

**Visibilidade pelo poder do usuário no hub** (`usuario_poder`)

| Poder | Vê | Padrão |
|---|---|---|
| `consolidado` | tudo | consolidado do ente |
| `executivo` | grupo Executivo e unidades `10131`/`10132` | grupo Executivo |
| `legislativo` | grupo Legislativo e unidades `20231` | grupo Legislativo |
| ambos | os dois, mais o grupo Executivo + Legislativo | grupo Executivo + Legislativo |

**Dependência no hub**
- Hoje o JWT só leva `sub` e o `POST /internal/authorize` só responde `{authorized: true}`. A
  resposta passa a trazer `poderes` na change `CH-46-poderes-no-authorize` do `regras-rgf-api`.

**Fora de escopo:**
- Combinação arbitrária de unidades, por exemplo Prefeitura + Fundo de Saúde sem os demais fundos.
  O PO decidiu em 2026-10-09 que as peças são consolidado, poder ou uma unidade.
- BF, que fica em standby: os estornos de receita e despesa extra são relatórios do ente, sem UG.
- `I-C` a `I-HI`, DVP e DFC. Cada um nasce com recorte na própria change.
- Filtro por poder no BF e nos demais anexos.
- PDF e XLSX.
- Exclusão intra-OFSS, que segue a decisão de 2026-10-08: o processamento inclui tudo.

## Entradas e saídas

| Interface | Entrada | Saída |
|---|---|---|
| Job BO/BP, PublicSoft | `base-demonstrativos/unidades-gestoras` sem filtro de UG; se `422`, a base oficial de hoje. BP: também o ano anterior pela MSC | Cache com o consolidado (como hoje) + `recortes: {chave: resultado}` |
| Job BO/BP, SICONFI | `tt/msc_*` de hoje (BP: também o ano anterior pela MSC) | Consolidado + `recortes` por grupo e por `po:` |
| `GET /dca/BO`, `GET /dca/BP` | params de hoje + `recorte` (opcional) | corpo do recorte (`linhas`, `matriz`, `procedencia`, `diagnostico`) + `recorte` + `recortesDisponiveis: [{chave, tipo, rotulo, poderOrgao?}]` |
| `POST /dca/{anexo}/reprocessar`, `/batch-jobs` | sem mudança (não recebem `recorte`) | sem mudança |
| Hub `POST /internal/authorize` (CH-46) | `{sub, cod_ibge}` (igual) | `{authorized: true, poderes: [...]}` |

## Exemplo concreto

Cuitegi/PB (`2505204`), 2025, MSC de encerramento. UGs: Prefeitura, Fundo Municipal de Assistência
Social, Fundo Municipal de Saúde e Câmara.

| Emissão | Anexo | Célula | Valor esperado |
|---|---|---|---|
| `consolidado` (PublicSoft) | BP | `L1` ATIVO, atual | 76.314.331,92 (igual a hoje) |
| cada `ug:<id>` | BP | `L1` atual | a medir; Σ das 4 = 76.314.331,92 (o `L1` não tem condição) |
| `poder:executivo` + `poder:legislativo` | BP | `L1` atual | Σ = 76.314.331,92, se todo registro tem PO de Executivo ou Legislativo |
| `po:20231` (SICONFI) | BP | `L1` atual | a medir; comparar com `ug:<Câmara>` |

## Critérios de aceite

- [ ] Cuitegi 2025, recorte `consolidado`, pelas duas fontes: BO e BP iguais bit a bit ao resultado anterior à change.
- [ ] Cuitegi 2025: Σ do `L1` do BP nas 4 UGs = consolidado, com diferença 0,00; a partição dos registros cobre cada registro uma vez (teste).
- [ ] Trocar o `recorte` responde `200` do cache, sem job (zero `enqueue` medido no teste) e sem chamada à fonte.
- [ ] A fonte bruta é chamada no job o mesmo número de vezes que hoje, mais o ano anterior do BP quando a origem é `publicado_siconfi`.
- [ ] `L1`, `L15` e equilíbrio do BP e totais do BO de Cuitegi registrados por UG, por PO e por grupo.
- [ ] Tempo do job e tamanho do `resultado` medidos em Cuitegi e em João Pessoa.
- [ ] `python -m pytest`, `python -m ruff check .` e o validador de regras limpos.

## Casos de erro

| Situação | Comportamento esperado |
|---|---|
| `recorte` malformado (sem prefixo conhecido) | `422` |
| `recorte` em anexo fora de BO/BP | `422` |
| `recorte` inexistente no cache | `404` |
| `recorte` não visível ao usuário (inclusive `consolidado` sem esse poder) | `403`, sem valor no corpo |
| Usuário só com `judiciario`, ou sem poder | `403` |
| Hub sem resposta na consulta de poderes | `503` (fail closed) |
| Cache anterior à change, com `recorte` ≠ `consolidado` ou usuário sem `consolidado` | `409` "reprocesse o anexo" |
| `unidades-gestoras` responde `422` | consolidado pela base oficial, como hoje; unidades por PO |
| `unidades-gestoras` responde `409` (auditoria não liberada) | igual a hoje: conjunto vazio, ausência de dados |

## Restrições e riscos

- **Desempenho:** o `ps-erp` recalcula a matriz de todas as UGs a cada pedido (síncrono). O BP passa
  a ler 2 exercícios × 4 classes. Medir o tempo do job em Cuitegi e em João Pessoa antes de liberar.
- **Identidade da UG** é o `ID_INSTITUICAO` do ERP do ente. A coluna anterior por UG pressupõe que
  ele é estável entre exercícios. A UG que existe em só um dos anos aparece com a outra coluna zerada.
- **Qualidade do PO** é a declarada pelo ente na MSC. Registro sem PO forma a unidade `po:` sem código, que só
  `consolidado` vê. Se o ente não classifica o PO, os grupos Executivo e Legislativo saem incompletos.
  Medir o valor sem PO em Cuitegi e registrar na auditoria.
- A UG técnica `0` ("Sem unidade gestora identificada") só `consolidado` vê, salvo se o ps-erp lhe atribuir PO.
- O id da UG só tem sentido dentro do `id_ente`.
- **Mudança de comportamento para usuários atuais:** quem tem só `executivo`, que é o poder padrão do
  cadastro no hub, deixa de ver o BO/BP consolidado do ente e passa a ver o grupo Executivo.
  Antes de liberar, conceder `consolidado` no hub a quem precisa.
- A change não sobe para produção antes da CH-46 do hub.
- A change `bp-superavit-por-fonte` está ativa no mesmo serviço do BP. Esta change parte do código
  dela. Arquivar aquela antes do merge desta.

## Aprovação do PO

- [x] Escopo BO + BP, BF em standby (PO 2026-10-09)
- [x] Anterior do BP por unidade = MSCE do ano anterior (PO 2026-10-09)
- [x] Emissão por consolidado, grupo de poder ou uma unidade; sem combinação arbitrária (PO 2026-10-09, revisão de engenharia)
- [x] Unidades visíveis conforme o poder do usuário no hub: legislativo, executivo ou consolidado (PO 2026-10-09)
- [x] RPPS (`10132`) fica com o Executivo (PO 2026-10-09)
- [x] Ente sem UG (CSV ou SICONFI) é recortado por PO (PO 2026-10-09)
- [x] PO aprovou esta proposta em 2026-10-09 — **gate para a fase PLAN/ARCH**
