# Tasks — Fonte MSC por demonstrativo e competência mensal

**Repo:** `ps-dca` · **Concluída e arquivada em 2026-09-14.**
Fatia vertical: o BO de Cuitegi/PB e de João Pessoa/PB apurados sobre `MSCE`/abertura, com
regressão célula a célula contra a apuração atual.

## 0. Fundação
- [x] 0.1 PO decidiu o par por demonstrativo em 2026-09-14
- [x] 0.2 Equivalência medida em dois entes: 337 células cada, **zero** divergências
      (`docs/evidencia-matriz-mscc-vs-msce.md`)
- [x] 0.3 PO aprovou a proposta e determinou a inclusão do processamento mensal em 2026-09-14
- [x] 0.4 Medido: a `MSCE` **não existe** nas competências 1, 3, 6, 9 e 11 em João Pessoa e Cuitegi;
      o BO mensal apura sobre `MSCC`/encerramento com acumulados monotônicos

## 1. TEST (antes do código)
- [x] 1.1 Traduzir cada `#### Scenario:` dos dois deltas em `tests/msc/` e `tests/bo/`
- [x] 1.2 Teste de regressão: 337 células × 2 entes, comparando a apuração atual com a nova —
      fixtures gravadas, sem rede na suíte
- [x] 1.3 Rodar e **confirmar que falha** pelo motivo esperado

## 2. IMPLEMENT
- [x] 2.1 `app/infra/msc/fonte.py` com a tabela por demonstrativo e a regra de competência (D1/D1b/D3)
- [x] 2.2 Enums `Matriz` e `TipoSaldo` no domínio; porta `FonteSaldos` recebe o par (D2)
- [x] 2.3 Adapters traduzem o par; `MSCC`/`MSCE` e `id_tv` deixam de ser constantes
- [x] 2.4 Retry com backoff nos adapters, com erro nomeando classe e offset (D4)
- [x] 2.5 Serviço do BO pede o par pelo demonstrativo
- [x] 2.6 Procedência com matriz, tipo de saldo, competência e classes
- [x] 2.7 Competência como parâmetro: serviço, CLI e procedência; `MES_DA_DCA` deixa de ser constante
- [x] 2.8 Migration: n/a

## 3. REVIEW
- [x] 3.1 `git diff` completo: sem arquivo fora do escopo, sem código morto, sem `print`/segredo/`TODO` órfão
- [x] 3.2 Nenhum módulo de `app/domain/` menciona `id_tv`, `MSCC` ou `MSCE`
- [x] 3.3 Não existe caminho de chamada que leia `MSCE`/encerramento fora do BP

## 4. VERIFY
- [x] 4.1 `python -m pytest` — **310 passed / 0 failed** (eram 287)
- [x] 4.2 `python -m ruff check .` — 5 erros, os mesmos pré-existentes; nenhum novo
- [x] 4.3 Regressão medida com o código novo: 337 células × 2 entes, **zero** divergências
- [x] 4.3b BO mensal: competências 3, 6, 9 e 12 de Cuitegi com acumulados monotônicos e a
      procedência declarando o par de cada uma
- [x] 4.4 Os 11 valores de `docs/validacao-bo-jp-2025.md` batendo com o publicado, em centavos
- [x] 4.5 Reconferência da spec: cada cenário → onde é coberto
- [x] 4.6 `docs/validacao-bo-jp-2025.md` atualizado com a troca de origem e a medição

## 5. Arquivamento
- [x] 5.1 `tasks.md` 100% marcado
- [x] 5.2 Mesclar deltas em `openspec/specs/dca/fonte-msc/` e `openspec/specs/dca/balanco-orcamentario/`;
      atualizar `CENARIOS_ESPERADOS` / `COM_TESTES` em `tests/test_cobertura_spec.py`
- [x] 5.3 Mover para `openspec/changes/archive/2026-09-14-msc-fonte-e-competencia/`
- [x] 5.4 Atualizar a tabela "Change ativa" em `openspec/AGENTS.md`
