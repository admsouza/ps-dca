# Tasks — Processar e reprocessar a DCA inteira numa chamada

**Repo:** `ps-dca` · **Não implementar sem aprovação explícita do PO.**
Fatia vertical: João Pessoa (2507507), exercício 2025, anexos `BO` e `BF` ponta a ponta.

## 0. Fundação
- [x] 0.1 Confirmar com o PO as duas perguntas abertas da proposal (rota única no contrato de
      batch job — D6; notificação consolidada — D5)
- [x] 0.2 Fixtures: registry com anexo implementado e não implementado; fonte-dublê que conta
      consultas por recorte (base do critério das 18 consultas)

## 1. TEST (antes do código)
- [x] 1.1 `tests/pipeline/test_pipeline_completo.py` — um teste por `#### Scenario:` do delta,
      docstring começando em `Scenario: <nome exato>`
- [x] 1.2 Teste de contagem: 18 consultas no percurso contra 20 em jobs separados
- [x] 1.3 Teste do contrato de batch job: status terminal sempre em `done | error`, nunca fora do
      conjunto que o front encerra
- [x] 1.4 Teste de regressão: `GET /dca/{anexo}` e `POST /dca/{anexo}/reprocessar` inalterados
- [x] 1.5 Rodar e confirmar que falham pelo motivo esperado (rota e job inexistentes)

## 2. IMPLEMENT
- [x] 2.1 `completo.montar_percurso` — classificação em `a_apurar | em_cache | already_queued |
      nao_implementado`
- [x] 2.2 ~~`job.executar` devolvendo desfecho estruturado~~ — dispensado (D8): o desfecho
      é lido do registro que ele já grava, e o caminho do job individual fica intocado
- [x] 2.3 `completo.executar_percurso` — série, lock por anexo, falha isolada
- [x] 2.4 Job `apurar_completo` no worker, com uma memória de execução da MSC
- [x] 2.5 Progresso e desfecho por anexo no `job_manager`; evento SSE por anexo
- [x] 2.6 Rota `POST /batch-jobs` (+ polling e SSE do percurso), com a autorização de unidade
- [x] 2.7 Notificação consolidada (D5)
- [x] 2.8 Sem migration — confirmar que nenhuma tabela muda

## 3. REVIEW
- [x] 3.1 `git diff` completo: nada em `app/domain/`, `app/services/bo/`, `app/services/bf/`,
      `knowledge/`
- [x] 3.2 Sem código morto, sem abstração de uso único, sem `print`/segredo/`TODO` órfão

## 4. VERIFY
- [x] 4.1 `python -m pytest` — reportar `N passed / M failed`
- [x] 4.2 `python -m ruff check .` — limpo
- [x] 4.3 Medição real em João Pessoa/2025 (SICONFI, 2026-09-23): percurso `done`, falhas 0, cache `BO` e `BF` em `ok`
- [x] 4.4 Valores idênticos aos dos jobs individuais: 337 células do BO e 216 do BF (66 × 2 do quadro principal + 14 × 6 do quadro anexo), zero divergências. Consultas à fonte: 32 nos jobs separados, 30 no percurso — as 2 do BO saem das leituras que o BF já faz, inclusive do exercício anterior
- [x] 4.5 Reconferência da spec: cada cenário → onde é coberto

## 5. Arquivamento
- [ ] 5.1 `tasks.md` 100% marcado
- [ ] 5.2 Mesclar o delta em `openspec/specs/pipeline/processamento-completo/`
- [x] 5.3 Registrar a capability em `CENARIOS_ESPERADOS` e `COM_TESTES` de
      `tests/test_cobertura_spec.py` (contagem: 11 cenários)
- [ ] 5.4 Mover para `openspec/changes/archive/AAAA-MM-DD-pipeline-completo-dca/`
- [ ] 5.5 Atualizar a tabela "Change ativa" em `openspec/AGENTS.md`
