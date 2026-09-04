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
- [x] 1.2 Design revisado após as decisões 0.7–0.10 e assinado pelo PO em 2026-09-04.
- [x] 1.3 Dependências confirmadas em 2026-09-03: runtime `pyyaml` + `jsonschema`; dev `pymupdf`,
      `pytest`, `ruff`. `pydantic` retirado por não ter uso nesta change.
- [x] 1.4 Esqueleto do repositório criado em 2026-09-04: `pyproject.toml` com as dependências
      acima, `[tool.ruff]` (line-length 100, `E,F,I,UP,B,SIM`) e `[tool.pytest.ini_options]`.
      `python -m ruff check .` → `All checks passed`. Artefatos compartilhados
      (`knowledge/schemas/`, `knowledge/sources/`, `scripts/check_sources.py`) absorvidos da
      change arquivada `knowledge-base-ipc`, conforme decisão do PO de 2026-09-04.

## 2. TEST — antes do código

- [x] 2.1 Os **49** `#### Scenario:` do delta spec traduzidos em 85 testes, escritos em
      2026-09-04. O delta cresceu de 47 para 49 cenários com B6 (`L27`–`L30` e `L51`); a contagem
      antiga desta task era anterior a essa decisão.
      · `tests/test_validador.py` (38) — cenários estruturais, com regras sintéticas
      · `tests/test_fontes_e_indice.py` (15) — hash de fontes, domínio STN, índice
      · `tests/test_base_ipc07.py` (32) — conteúdo real das 69 regras transcritas
- [x] 2.2 `tests/conftest.py` — `REGRA_VALIDA` e os construtores `regra(**alteracoes)` e
      `regra_composta(...)`, a policy mínima e a fixture `base(...)`, que monta uma árvore
      `knowledge/` temporária. Cobre regra válida, inválida e bloqueada por mutação da válida.
- [x] 2.3 Suíte executada em 2026-09-04: **32 failed · 1 passed · 52 errors**, e
      `python -m ruff check .` → `All checks passed!`. Falhas conferidas uma a uma:
      · 52 erros são `ModuleNotFoundError` — `scripts.validate_rules` (44), `check_sources` (3),
        `load_stn_tables` (3), `build_index` (2): o código não existe
      · 32 falhas são `base canônica ausente: knowledge/rules/bo`: a transcrição não existe
      · 1 passa — `test_pdf_nao_e_duplicado_dentro_de_knowledge`, verdadeiro por vacuidade agora e
        que continua valendo depois da transcrição
      Nenhuma falha por erro de escrita do teste.

## 3. IMPLEMENT — código mínimo

- [x] 3.1 `knowledge/sources/ipc07/metadata.yaml` (17 páginas, edição 2020-01, SHA-256 do PDF) e
      `knowledge/sources/stn/metadata.yaml` (as 7 tabelas com hash e contagem de registros). O PDF
      permanece em `docs/referencia/ipc/`; `check_sources.py` falha se for copiado para dentro da
      base.
- [x] 3.2 `knowledge/schemas/rule.json` e `policy.json` (Draft 2020-12), com os enums fechados do
      IPC 07 e `additionalProperties: false` — campo especulativo é rejeitado, não ignorado.
- [x] 3.3 As 69 regras transcritas em 3 arquivos (2.722 + 468 + 426 linhas), a partir de
      `knowledge/sources/ipc07/extracted.md`. Literal do PDF preservado em `evidence.text`,
      inclusive nas divergências (`L-40`, `(VII + IX + X)`, `(-VIII)`, `28.842, - 28.844`).
- [x] 3.4 `knowledge/policies/ipc07.yaml` — as 2 policies do IPC 07 (p. 6, itens 19 e 15).
      Nenhuma inventada: o IPC 07 não traz exclusão de intraorçamentárias, ao contrário do
      IPC 04/05.
- [x] 3.5 `scripts/` implementado na API fixada pelos testes: `validate_rules.py`,
      `check_sources.py`, `build_index.py`, `load_stn_tables.py`, mais `extract_ipc.py`
      (extração geométrica, uso manual) e os auxiliares `_carregar.py` e `_relatorio.py`.
- [x] 3.6 `pyproject.toml` com runtime e dev; `openspec/project.md` com os comandos de validação
      reais.

## 3bis. Medições da base gerada (2026-09-04)

`python -m scripts.validate_rules knowledge` → **exit 0**:

```
Regras por quadro    quadro_principal 51 · rp_nao_processados 9 · rp_processados 9   (total 69)
Regras por status    extracted 69 · review_required 0 · validated 0 · draft 0 · deprecated 0
Exceção B1            1 código / 6 linhas
Exceção B3           16 códigos / 5 linhas
Exceção B2           13 códigos / 13 linhas
Exceção B4           13 códigos / 21 linhas
```

Três divergências em relação ao previsto no `design.md`, todas por contagem e não por conteúdo —
o design foi corrigido:

| | Previsto | Medido | Porquê |
|---|---|---|---|
| **B1** | 9 linhas | **6 linhas** | a conta `5.3.1.3.0.00.00` está nas colunas, e as 3 linhas compostas do RPNP (`L1`, `L5`, `L9`) não declaram colunas próprias |
| **B3** | 8 padrões | **16 grafias** | os 8 padrões aparecem em duas grafias — `2111.00.20` nas exclusões de `L11` e `2111.00.2.0` em `L19`–`L23` (R6). Normalizadas, são os mesmos 8 |
| **B4** | 17 linhas | **21 linhas** | inclui as 4 linhas de amortização detalhada (`L43`, `L44`, `L46`, `L47`), cujos padrões `46.xx.76`/`46.xx.77` têm coringa e não são conferíveis na tabela |

## 4. REVIEW

- [x] 4.1 Diff revisado em 2026-09-04. Escopo: `knowledge/`, `scripts/`, `tests/`,
      `pyproject.toml` e os documentos da própria change — nada fora. Nenhum `print` fora dos
      `main()`, nenhum `TODO`/`FIXME`, nenhum segredo. Uma correção aplicada na revisão:
      `extract_ipc.py` usava `import fitz`, nome deprecado, trocado por `import pymupdf`.
- [x] 4.2 `git status docs/` limpo e `check_sources.py` → `✓ Fontes íntegras`: o PDF e as 7
      tabelas da STN têm o mesmo SHA-256 registrado. Nenhum PDF dentro de `knowledge/`.
- [x] 4.3 Medido: `review_required` **0**, `review.blocker` **0**. `provenance.decision: B6` em
      exatamente 5 regras — `L27`, `L28`, `L29`, `L30` e `L51`; e `L51` tem `columns: {}`.
- [x] 4.4 B1 em 6 regras do RPNP e B3 em 5 do Quadro Principal (`L11`, `L19`, `L20`, `L22`,
      `L23`), cada uma com `provenance.reading.note` explicando a exceção histórica.
      `line_account_override: true` só em `L29` e `L30`; o validador rejeita nos demais
      (teste `test_override_fora_de_l29_e_l30_e_rejeitado`).

## 5. VERIFY

Executado em 2026-09-04.

- [x] 5.1 `python -m pytest` → **89 passed**, 0 failed.
- [x] 5.2 `python -m ruff check .` → **All checks passed!**
- [x] 5.3 `python -m scripts.validate_rules knowledge` → **exit 0**, com
      `quadro_principal 51 · rp_nao_processados 9 · rp_processados 9` (total **69**).
- [x] 5.4 Mesma execução: **0** IDs duplicados, **0** referências quebradas, **0** ciclos,
      **0** páginas fora de 1..17, **0** regras sem `source` e **0** `review_required`.
      `check_sources.py` → `✓ Fontes íntegras`. Índice com 69 entradas, idêntico ao regerado.
- [x] 5.5 Os **49** cenários (não 47 — B6 acrescentou 2) estão cobertos. Em vez de uma tabela
      de-para, a rastreabilidade virou teste: `tests/test_cobertura_spec.py` falha se um cenário
      ficar sem teste que o cite, se um teste não declarar o que cobre, ou se a contagem mudar
      sem decisão registrada. Tabela em markdown envelheceria em silêncio; o teste não.
- [x] 5.6 Migration e espelho `tt/dca` **não se aplicam** a esta change: a base canônica é YAML
      versionado em git, sem banco (`design.md` › Impacto). O espelho contra `tt/dca` pertence às
      changes de anexo; a persistência em banco, à `plataforma-pipeline-dca` (F3).

## 6. Arquivamento

- [x] 6.1 `tasks.md` 100% atualizado — todas as fases com resultado medido, não estimado.
- [x] 6.2 Delta mesclado em `openspec/specs/dca/base-canonica-regras/spec.md` (13 requisitos,
      49 cenários). `tests/test_cobertura_spec.py` passa a apontar para lá.
- [x] 6.3 Change movida para `openspec/changes/archive/2026-09-04-ipc07-bo-regras-canonicas/`.
- [x] 6.4 Tabela "Change ativa" de `openspec/AGENTS.md` atualizada: a change sai das ativas e
      entra nas arquivadas.
