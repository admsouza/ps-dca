# Tasks — "Intragovernamental": IPC 08 × SIAFIC

## 0. SPEC
- [x] 0.1 Achado A2 medido na auditoria de Cuitegi
- [x] 0.2 Causa identificada: dois conceitos com o mesmo nome, provado pelo BF do mesmo ente
- [x] 0.3 Hipótese "contas de transferência financeira" implementada e **revertida** — quebra as
      amarrações `P.L10 = T.L7` e `P.L15 = T.L15`, e perde a modalidade 91 que o IPC declara
- [x] 0.4 Confirmado que `T.L5` = 0,00 está correto: a receita de categoria 7 do ente é
      contribuição patronal (`7.2.1.5.02.11`), não transferência
- [x] 0.5 PO decidiu **A** em 2026-10-27: manter o IPC 08

## 1. IMPLEMENT
- [x] 1.1 **Nada a implementar.** A decisão A confirma a apuração vigente; A2 e A4 passam a
      divergências registradas do ente, não defeitos.

## 2. Arquivamento
- [x] 2.1 Auditoria de Cuitegi atualizada com a decisão
- [x] 2.2 `openspec/AGENTS.md` atualizado
- [x] 2.3 Movida para `openspec/changes/archive/2026-10-27-dfc-intragovernamentais/`

## Nota de processo

A implementação foi delegada a um subagente com um brief que mandava **substituir** as contas.
O brief estava errado: o conceito do IPC (modalidade 91) e o do ente (transferência financeira)
são somas diferentes, não a mesma coisa escrita de outro jeito. O subagente seguiu o brief,
mediu, viu as amarrações quebrarem e **reportou sem contornar** — foi o relatório dele que
expôs o erro. Lição: num brief de implementação, dizer o que o valor **tem de preservar**
(as amarrações) é tão importante quanto dizer o que ele deve alcançar.
