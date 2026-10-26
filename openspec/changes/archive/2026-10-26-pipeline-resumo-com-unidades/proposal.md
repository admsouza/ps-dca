# Proposal — Resumo da DCA com as unidades de BF e BP

**Status:** implementação autorizada pelo dev em 2026-10-15; aprovação formal do PO pendente
**Repositório:** `ps-dca` (front: `front-declaracoes` `dca-dados-exercicio-anterior`)
**Capability:** `pipeline/plataforma` (MODIFIED: resumo agregado)
**Anexo DCA:** BF e BP (só metadados)
**Base normativa:** n/a (não muda número)

## Why

O front precisa da lista de unidades de BF/BP, de N e de N−1, para mostrar a configuração da coluna
anterior. Hoje ele a obtém com `GET /dca/BF` (`DcaDialog.tsx:286`), e isso traz dois problemas:

- **Abrir o diálogo enfileira processamento.** Sem cache em N, a leitura cai em `ler_ou_enfileirar`
  (`app/routes/anexos.py:342`) e dispara um job do BF que ninguém pediu.
- **Ler o resultado inteiro para listar unidades.** Megabytes para obter `chave`/`rotulo`.

O resumo (`GET /dca/resumo`) já é leitura pura do cache e não inicia cálculo. Falta só ele trazer as
unidades.

## What Changes

- A entrada de **BF** e **BP** no resumo passa a trazer `recortes: [{chave, tipo, rotulo}]` com as
  unidades (`ug:`/`po:`) gravadas no resultado `ok`. Grupos e consolidado ficam de fora. Sem
  resultado `ok`, o campo vem como `[]`.
- As unidades obedecem à mesma visibilidade por poder da leitura do anexo (fail closed).
- Os demais anexos e campos não mudam.

O front chama o resumo de N e de N−1. Com isso calcula as unidades, a disponibilidade do Processado
(chave presente em N−1) e a falta de correspondência UG × PO (prefixo da chave em N−1 diferente do
tipo de recorte da fonte atual). Não é preciso endpoint novo.

**Fora de escopo** (revisado em 2026-10-15 por excesso de engenharia):
- **Endpoint de configuração lendo a MSC de N antes de processar.** Exigiria ler a MSC só para
  listar unidades. Uma unidade nova em N não tem Processado, e o Manual se digita na página, que
  exige N processado. Portanto o padrão (MSC) é o que valeria de qualquer forma.
- **Corpo `anterior` no `/batch-jobs`.** O front já envia as escolhas pelo `reprocessar` antes do
  percurso, e as gravadas são reaplicadas. Basta passar a enviá-las também no Processar (só no front).
- **`anterior_vs_unidades` no consolidado e Processado de PO como soma de UGs.** Os dois dependem
  de decisão contábil (D1/D2 abaixo). Sem a decisão, não há código.
- Rótulos com fonte e Manual incompleto: só front.

## Decisões do PO (sem código nesta change)

| # | Pergunta | Estado |
|---|---|---|
| D1 | Como a coluna anterior do consolidado reflete as escolhas das unidades? (origem própria × derivar da soma + parcela sem unidade) | aberta. Até decidir, a tela informa que o consolidado usa a origem própria |
| D2 | Ao trocar SIAFIC (`ug`) por SICONFI (`po`), o Processado do PO pode ser a soma das UGs de N−1? | aberta. Até decidir, aparece indisponível com o motivo |

## Entradas e saídas

| Interface | Entrada | Saída |
|---|---|---|
| `GET /dca/resumo` | sem mudança | entradas `BF`/`BP` ganham `recortes: [{"chave": "ug:12", "tipo": "ug", "rotulo": "Câmara Municipal de Cuitegi"}]` |

## Exemplo concreto

Cuitegi/PB (`2505204`), resumo de 2024 com BF `ok` por SIAFIC: `recortes` lista as 4 UGs (Prefeitura,
FMAS, FMS, Câmara). Resumo de 2025 sem cache: `recortes = []` e nenhum job enfileirado.

## Critérios de aceite

- [ ] Resumo com BF/BP `ok` com recortes: 1 item por unidade, sem grupo e sem consolidado.
- [ ] Usuário sem o poder Legislativo: a Câmara não aparece.
- [ ] Resumo sem cache: `recortes = []` e zero jobs.
- [ ] Demais campos e anexos: bit a bit iguais.

## Casos de erro

| Situação | Comportamento esperado |
|---|---|
| BF/BP em `erro` ou `processando` | `recortes = []` |
| Resultado gravado antes dos recortes | `recortes = []` |

## Restrições e riscos

- O resumo cresce com uma linha curta por unidade (dezenas, não megabytes).

## Aprovação do PO

- [ ] PO aprovou esta proposta em <data> — **gate para a fase PLAN/ARCH** (implementação autorizada pelo dev em 2026-10-15; aprovação formal do PO pendente)
