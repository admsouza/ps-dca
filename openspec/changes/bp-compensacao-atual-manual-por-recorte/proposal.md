# Proposal — BP · Compensação atual manual por recorte

**Status:** proposta e SPEC aprovadas pelo PO em 2026-10-21; implementação concluída, em VERIFY
**Repositório:** `ps-dca`
**Capability:** `dca/balanco-patrimonial` (existente)
**Anexo DCA:** `DCA-Anexo I-AB`
**Base normativa:** MCASP · IPC 04, itens 12–13 (`docs/referencia/ipc/IPC04.pdf`) · layout SICONFI
**Frontend coordenado:** `front-declaracoes/dca-bp-compensacao-atual-manual-por-recorte`

## Why

As dez linhas do Quadro das Contas de Compensação não são apuradas pela matriz. Hoje as duas
colunas saem `None`; o frontend permite o preenchimento manual apenas da coluna anterior de uma
unidade. A coluna do exercício atual também precisa ser informada em cada recorte individual.

O consolidado e os grupos de poder já são derivados das unidades para a coluna anterior. Permitir
valor próprio nesses agregados criaria duas fontes de verdade e possibilitaria divergência entre
os individuais e o total exibido.

## What Changes

- `POST /dca/BP/reprocessar` aceita `valores_atuais_por_recorte` para recortes individuais
  `ug:<id>` ou `po:<codigo>`.
- Somente folhas `C:<codigo>` de `CONTAS_COMPENSACAO` podem ser informadas; totalizadoras são
  calculadas pelo mapa vigente.
- Grupos `poder:*` e `consolidado` não aceitam edição própria: a coluna atual de Compensação é a
  soma dos resultados individuais.
- O mapa efetivo é validado, autorizado, identificado no pedido, persistido na procedência e
  reaplicado quando o campo for omitido. Mapa vazio limpa o recorte.
- A coluna anterior continua independente e pode ser enviada no mesmo pedido por
  `anterior_por_recorte`.

**Fora de escopo:** apurar Compensação pela MSC; ratear valores; alterar outros quadros do BP;
alterar BF/BO; criar tabela, migration, endpoint ou dependência; editar grupo ou consolidado.

## Entradas e saídas

| Interface | Entrada | Saída |
|---|---|---|
| `POST /dca/BP/reprocessar` | `valores_atuais_por_recorte: {"ug:<id>"|"po:<codigo>": {"C:<folha>": "<decimal>"}}` | `202` e job; depois, matriz por recorte com `exercicio_atual` informado |
| `GET /dca/BP?recorte=<individual>` | recorte autorizado | folhas e totalizadoras atuais daquele recorte |
| `GET /dca/BP?recorte=<grupo|consolidado>` | recorte autorizado | Compensação atual derivada da soma dos individuais |

## Exemplo concreto

Cuitegi/PB (`2505204`), exercício 2025, usa os recortes reais `po:10131` (Prefeitura), `po:10132`
(RPPS) e `po:20231` (Câmara). O publicado do ente traz as dez linhas de Compensação zeradas. Com
`C:L2 = 0,00` informado nos três POs, cada individual e o consolidado devem publicar `0,00`, e não
`None`. Em cenário controlado de teste, `100,00 + 50,00 + 0,00` deve produzir exatamente `150,00`
no consolidado.

## Critérios de aceite

- [ ] As oito folhas de Compensação são editáveis somente em `ug:`/`po:`; `L1` e `L6` são
  totalizadoras somente leitura.
- [ ] Grupo e consolidado têm `0` valores próprios e reproduzem, célula a célula, a soma dos
  individuais com diferença `0,00`.
- [ ] `0,00` informado permanece zero; campo não informado permanece `None`.
- [ ] Omissão reaplica o mapa salvo e mapa vazio limpa somente o recorte indicado.
- [ ] Entrada inválida ou não autorizada cria `0` jobs e não altera o cache.
- [ ] A coluna anterior sai bit a bit igual quando não houver alteração em `anterior_por_recorte`.

## Casos de erro

| Situação | Comportamento esperado |
|---|---|
| chave `consolidado` ou `poder:*` | `422`, sem job |
| chave fora de `ug:*`/`po:*` | `422`, sem job |
| linha inexistente ou totalizadora (`C:L1`/`C:L6`) | `422`, sem job |
| prefixo diferente de `C:` ou valor não decimal | `422`, sem job |
| recorte individual sem autorização | `403` para o pedido inteiro, sem job |
| campo em anexo diferente de BP | `422`, sem job |

## Restrições e riscos

- Célula `None` em qualquer individual participante deixa a célula agregada `None`; ela não pode
  ser silenciosamente tratada como zero.
- A gravação deve sobreviver a uma tentativa posterior que termine em erro, como os demais mapas
  manuais persistidos.
- A change ativa `bp-superavit-por-fonte` também altera o BP; o delta final deve ser reconciliado
  após seu arquivamento sem reabrir o escopo de Superávit/Déficit.
- O frontend deve ser publicado junto ou depois do backend.

## Aprovação do PO

- [x] PO autorizou criar esta change em 2026-10-21.
- [ ] PO aprovou `proposal.md` e o delta spec — **gate para PLAN/ARCH e TEST**.
