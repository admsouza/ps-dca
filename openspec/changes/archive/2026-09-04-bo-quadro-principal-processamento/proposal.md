# Proposal — Processamento do Balanço Orçamentário (quadro principal)

**Status:** proposta
**Capability:** `dca/balanco-orcamentario` (nova)
**Depende de:** `ipc07-bo-regras-canonicas` (as 51 regras do quadro principal como dado de entrada)
**Repositórios analisados:** `regras-rgf-api` (fontes MSC, engine de saldo, motor matricial)

## Why

A change `ipc07-bo-regras-canonicas` entrega a **regra** (69 linhas em YAML, rastreáveis ao PDF).
Falta o que **executa** a regra: buscar a MSC do ente, resolver débito/crédito por conta e apurar a
matriz linha × coluna. Sem essa camada a base canônica é documentação.

Três achados medidos no `regras-rgf-api` e no `PCASP.md` deste repositório determinam o desenho:

1. **A direção do saldo não pode ser inferida da classe contábil.** O engine do RGF
   (`app/services/rgf/engine/saldo.py`) usa `_CLASSES_CREDORAS = {"2","6","8"}` — classe 5 cai em
   `D−C` e classe 6 em `C−D`. Medido no `PCASP.md`: a classe **5** tem 54 contas devedoras e **22
   credoras**; a classe **6** tem 56 credoras e **7 devedoras**. A heurística inverte o sinal
   dessas 29 contas.
2. **A direção também não pode ser inferida do prefixo do IPC07.** As fórmulas do BO casam por
   prefixo de 4 níveis, e dentro do mesmo prefixo a natureza se mistura: `5.2.1.1` tem 4 credoras +
   2 devedoras; `6.2.1.3` tem 1 credora + **5 devedoras** (as deduções `(-)`). Aplicar uma direção
   por prefixo declarado erra o sinal das dedutoras.
3. **A tabela oficial já traz a resposta.** `docs/contas-stn/PCASP.md` tem a coluna
   `NATUREZA DO SALDO` por conta folha de 9 dígitos. A direção é **dado**, não heurística: resolvida
   por conta do registro, não pelo prefixo da regra nem pela classe.

## What Changes

- Passa a existir `dca/balanco-orcamentario`: apuração do **quadro principal** (51 linhas,
  4 colunas de receita + 6 de despesa) a partir da MSC.
- A direção do saldo passa a ser resolvida na tabela PCASP, por conta folha do registro.
  `natureza_saldo` declarada na regra só existe para as exceções históricas de B1/B3, ausentes da
  tabela atual.
- Passam a existir dois adapters de fonte MSC com o mesmo contrato: SICONFI
  (`tt/msc_orcamentaria`) e PublicSoft (`base-demonstrativos`, com gate de auditoria).
- Na DCA a leitura é sempre `id_tv = ending_balance`, classes **5** e **6**, exercício fechado
  (decisão do PO).

**Fora de escopo:** RP Processados e RP Não Processados (os outros 2 quadros do IPC07); ligação
IPC07 → anexo DCA e espelho `tt/dca`; rota HTTP, worker, cache e banco; IPC04/05/06/08.

## Restrições

- **Nada de heurística de sinal.** Conta sem natureza na tabela e sem `natureza_saldo` declarado na
  regra → célula não apurada (`None`) e aviso. Nunca `0`, nunca direção presumida.
- Reuso, não reescrita: o parser de fórmula (`ast` com whitelist), a ordenação topológica e o
  formato de mapa do `regras-rgf-api` são adotados como estão. O cálculo de saldo é reescrito
  porque a regra de direção muda (achados 1 e 2).

## Validação com caso real

A regra foi medida contra João Pessoa (`2507507`) 12/2025 e os gabaritos oficiais `DCA-Anexo I-C`,
`DCA-Anexo I-D` e `RREO-Anexo 01`: **espelho 1:1 em centavos nos 11 valores conferidos**, zero
diferença — as 5 colunas de despesa executada, as 3 de receita realizada, a dotação inicial, a
dotação atualizada e a previsão atualizada. Evidência completa em
[`docs/validacao-bo-jp-2025.md`](../../../docs/validacao-bo-jp-2025.md) e o inventário de anexos em
[`docs/anexos-siconfi-inventario.md`](../../../docs/anexos-siconfi-inventario.md).

A medição também mostra a heurística de classe falhando no caso real: as duas contas de dedução da
receita (`621310100`, `621390000`) são de classe 6 e **devedoras**; tratadas como credoras sairiam
com sinal invertido em relação ao STN.

## Decisões

| # | Assunto | Decisão |
|---|---|---|
| **C1** | mês de referência | mês **12**, `co_tipo_matriz=MSCC` (PO, 2026-09-03). Confirmado no caso real: 4.600 registros de classe 5 e 4.320 de classe 6 |
| **C2** | contas bifront | resolvida pela medição: das 4, só `621100000` e `522139900` têm movimento, e **nenhuma das duas compõe as colunas** — a dotação atualizada e a receita realizada fecham exatamente sem elas. Ficam **fora** das colunas, e o casamento de conta não pode capturá-las por prefixo |
| **C4** | repositório de destino | o Balanço Orçamentário fica no **`ps-dca`** (PO, 2026-09-04). O `RREO-Anexo 01` é demonstrativo do RREO e pertence ao `regras-rreo-api`; aqui entra só como gabarito de validação das colunas de previsão e dotação |
| **C3** | exceções históricas | resolvida pela medição: **nenhuma** conta da MSC de JP 12/2025 está ausente do PCASP atual; `5.3.1.3` e os padrões de B3 não têm escrituração. `natureza_saldo` na regra permanece como precaução para exercícios antigos |

**Risco medido, que a implementação tem de barrar:** `522139900` é irmã de `522130100` (a conta que
`L29` declara). Casar o prefixo `5.2.2.1.3` por prefixo solto a captura e infla a coluna em
**R$ 729.036.483,90**.

## Aprovação do PO

- [x] PO aprovou esta proposta em **2026-09-04** — Jackson S. da Silva (PO). Gate da fase SPEC fechado; PLAN/ARCH liberada.
      Aprovação cobre a proposta, o `design.md` e o delta `specs/dca/balanco-orcamentario/spec.md`.
