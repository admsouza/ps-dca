# Proposal — Coluna do exercício anterior editada na célula

**Status:** implementação autorizada pelo dev em 2026-10-19; aprovação formal do PO pendente
**Repositório:** `ps-dca` (front: `front-declaracoes`)
**Capability:** `pipeline/plataforma` (MODIFIED: resumo agregado)
**Anexo DCA:** BF e BP (só metadados; nenhum número muda)
**Base normativa:** n/a (não muda número)

## Why

Digitar o saldo anterior exigia um ritual: escolher Manual no diálogo, voltar, abrir o anexo,
digitar e apurar. Entre a escolha e a digitação a unidade ficava "Manual incompleto", o que
bloqueava o percurso, e a coluna conceitualmente zerava — o que não fosse digitado saía em branco.

Além disso, a origem exibida no diálogo vinha do `sessionStorage` (`DcaDialog.tsx:419`), que some
entre sessões e não existe em outro navegador: a tela dizia "Automática" enquanto a apuração
aplicava o Manual gravado na procedência. Dois estados para o mesmo fato, e o errado era o visível.

## What Changes

- **Front:** a coluna anterior nasce da origem automática e é editável célula a célula na unidade.
  Editar é o que torna a origem `manual` — Manual deixa de ser opção do painel e do lote. A faixa
  "Coluna de N−1 ajustada · Desfazer ajustes" mostra o estado e devolve a unidade ao padrão com
  `{origem: "padrao"}`. Some o estado "Manual incompleto" e o bloqueio de percurso que ele causava.
- **Backend:** a entrada de BF/BP no resumo passa a trazer, por unidade com escolha gravada,
  `anterior: {origem, manual}` — a origem que a apuração aplica, para a tela não contradizê-la.

Sem mudança no contrato de `POST /dca/{anexo}/reprocessar`: o front já envia a coluna inteira em
`anterior_por_recorte`, e `padrao` já era aceito por `validar_escolhas`.

## Entradas e saídas

| Interface | Entrada | Saída |
|---|---|---|
| `GET /dca/resumo` | sem mudança | unidade com escolha gravada ganha `anterior: {"origem": "manual", "manual": true}` |

## Critérios de aceite

- [ ] Unidade com manual gravado: o resumo traz `anterior.manual = true`, e o diálogo mostra a
      origem real mesmo com o `sessionStorage` vazio.
- [ ] Unidade sem escolha: a chave `anterior` não aparece (automática).
- [ ] Demais campos e anexos do resumo: bit a bit iguais.

## Casos de erro

| Situação | Comportamento esperado |
|---|---|
| BF/BP em `erro` ou `processando` | `recortes = []`, sem `anterior` |
| Resultado gravado antes das escolhas por unidade | unidades sem `anterior` |

## Aprovação do PO

- [ ] PO aprovou esta proposta em <data> (implementação autorizada pelo dev em 2026-10-19)
