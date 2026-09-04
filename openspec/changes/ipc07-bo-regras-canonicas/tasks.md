# Tasks — Regras canônicas do Balanço Orçamentário (IPC 07)

**Repo:** `ps-dca` · **Não implementar sem aprovação explícita do PO.**
Fatia desta change: representação canônica das 69 linhas dos três quadros do IPC 07. A ligação
com anexo DCA, ente, exercício e espelho `tt/dca` pertence a uma change posterior.

## 0. SPEC — descoberta e artefatos

- [x] 0.1 Reconstruir por geometria as 69 linhas das páginas 8–13 e registrar a análise em
      `docs/source-analysis-ipc07.md`.
- [x] 0.2 Isolar as ambiguidades R1–R11 e os bloqueios/lacunas B1–B6 sem escolher interpretação
      não sustentada pelo documento.
- [x] 0.3 Conferir os códigos localizáveis nas tabelas de `docs/contas-stn/` e registrar as
      lacunas B2 e B4.
- [x] 0.4 Escrever `proposal.md` restrita ao IPC 07.
- [x] 0.5 Escrever o delta `specs/dca/base-canonica-regras/spec.md`, com 17 requisitos e 47
      cenários observáveis.
- [x] 0.6 Registrar esta change na tabela "Change ativa" de `openspec/AGENTS.md` e deixar
      `knowledge-base-ipc` explicitamente suspensa.
- [x] 0.7 Exemplo com anexo DCA, ente, exercício e valor medido **fora de escopo** por decisão do
      PO em 2026-09-03: nada é calculado nesta change; o exemplo pertence à change de ligação
      IPC07 → DCA. Os exemplos da `proposal.md` permanecem documentais.
- [x] 0.8 Registrar as decisões do PO sobre B1, B3 e B5: conta histórica 531 preservada, B3 no
      domínio PCASP e override de conta restrito a L29/L30.
- [x] 0.9 Registrar a decisão do PO sobre B6 (2026-09-03): `L27`–`L30` têm as 4 colunas de
      receita; `L51` não tem coluna de valor. Nenhuma regra permanece `review_required`.
- [x] 0.10 Decisão do PO em 2026-09-03: B2 e B4 são **exceções declaradas**. As tabelas de
      `docs/contas-stn/` não são completadas nesta change.
- [x] 0.11 PO aprovou formalmente `proposal.md` e o delta spec em 2026-09-04 (Jackson S. da Silva (PO)). **Fase SPEC
      fechada** — PLAN/ARCH liberada.

## 1. PLAN/ARCH — somente após aprovação da SPEC

- [x] 1.1 Rascunhar `design.md`, incluindo componentes, fluxo, contratos, impacto, 14 decisões
      arquiteturais e lista de arquivos. Este rascunho não representa avanço do gate.
- [ ] 1.2 Revisar o design após as decisões 0.7–0.10 e registrar a data de aprovação do PO.
- [x] 1.3 Dependências confirmadas em 2026-09-03: runtime `pyyaml` + `jsonschema`; dev `pymupdf`,
      `pytest`, `ruff`. `pydantic` retirado por não ter uso nesta change.

## 2. TEST — antes do código

- [ ] 2.1 Traduzir cada um dos 47 `#### Scenario:` do delta spec em teste de comportamento.
- [ ] 2.2 Criar fixtures mínimas para regras válidas, bloqueadas e inválidas.
- [ ] 2.3 Rodar os testes e confirmar que falham pelo motivo esperado antes da implementação.

## 3. IMPLEMENT — código mínimo

- [ ] 3.1 Criar metadados e hashes das fontes IPC07/STN sem duplicar ou alterar os documentos.
- [ ] 3.2 Criar os schemas mínimos exigidos pelos cenários aprovados.
- [ ] 3.3 Transcrever as 69 regras em três arquivos, preservando literal, proveniência e status.
- [ ] 3.4 Criar as policies estritamente presentes no IPC07.
- [ ] 3.5 Implementar validação, verificação de fontes e geração determinística dos índices.
- [ ] 3.6 Atualizar documentação e marcar cada item no momento em que for concluído.

## 4. REVIEW

- [ ] 4.1 Revisar o diff completo: nenhum arquivo fora do escopo, regra inventada, código morto,
      segredo, `print` ou `TODO` órfão.
- [ ] 4.2 Reconferir que as tabelas de `docs/contas-stn/` e o PDF original não foram alterados.
- [ ] 4.3 Confirmar `0` regras `review_required` por bloqueio documental e que `L27`–`L30` e
      `L51` carregam `provenance.decision: B6`.
- [ ] 4.4 Confirmar B1/B3 como exceções históricas auditáveis e rejeitar override de conta fora
      de L29/L30.

## 5. VERIFY

- [ ] 5.1 `python -m pytest` — reportar `N passed / M failed`.
- [ ] 5.2 `python -m ruff check .` — reportar resultado real.
- [ ] 5.3 Validar 69 regras: `51` do Quadro Principal, `9` de RP Não Processados e `9` de RP
      Processados.
- [ ] 5.4 Validar `0` IDs duplicados, referências quebradas, ciclos, fontes ausentes, páginas
      fora do intervalo e regras `review_required`.
- [ ] 5.5 Percorrer os 47 cenários e apontar o teste ou a medição que cobre cada um.
- [ ] 5.6 Registrar que migration e espelho `tt/dca` não se aplicam a esta change, conforme escopo
      aprovado.

## 6. Arquivamento

- [ ] 6.1 Garantir `tasks.md` 100% atualizado.
- [ ] 6.2 Mesclar o delta em `openspec/specs/dca/base-canonica-regras/spec.md`.
- [ ] 6.3 Mover a change para `openspec/changes/archive/AAAA-MM-DD-ipc07-bo-regras-canonicas/`.
- [ ] 6.4 Atualizar a tabela "Change ativa" em `openspec/AGENTS.md`.
