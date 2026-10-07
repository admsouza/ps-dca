# Tasks — Notificações do Discord no padrão do RREO e do RGF

**Repo:** `ps-dca` · **Não implementar sem aprovação explícita do PO.**
Fatia vertical: Cuitegi/PB (`2505204`), 2025 — anexo isolado, percurso BO/BF/BP e requisição recebida.

## 0. Fundação
- [x] 0.1 Padrão de referência lido: `regras-rgf-api/worker.py` (por anexo e resumo do pipeline),
      `jobs_rgf_completo.py` (requisição recebida), `discord_notifier.py` (`fmt_duracao`, `label_ente`)
- [x] 0.2 Causa do `DCA — None concluído` localizada: `DiscordNotificador.enviar` formata o dict de
      percurso como se fosse de anexo
- [x] 0.3 Schema confirmado pelo PO: `public.unidade_gestora(cod_ibge, cidade, uf)`, mesmo banco
- [x] 0.4 PO aprova a proposal — 2026-10-07

## 1. TEST (antes do código)
- [x] 1.1 Cenários do delta em `tests/pipeline/test_notificacao_discord.py` (14: embed sobre `http`
      dublê, rotas reais com portas fakes) e em `tests/pipeline/test_pipeline_completo.py`
- [x] 1.2 Falharam pelo motivo esperado: `rotulo` inexistente, módulo `ente` ausente, duração no
      formato antigo, nenhuma notificação de requisição recebida, percurso sem mensagem por anexo.
      `test_leitura_servida_do_cache_nao_notifica` é guarda de regressão e já passava

## 2. IMPLEMENT
- [x] 2.1 `app/infra/notificacao/ente.py` (D2), memória só de acertos
- [x] 2.2 `DiscordNotificador` com os três tipos; `formatar_duracao` com meio para cima (850 ms →
      `0.9s`; o `:.1f` do RGF daria `0.8s`); `de_configuracao` usado pela API e pelo worker
- [x] 2.3 `notificacao.py`: `tipo` nos dicts, `notificar_recebida` e um único `_enviar` tolerante
- [x] 2.4 `completo.py`: mensagem por anexo (inclusive cache) e resumo com e-mail, fonte e duração;
      `a_apurar()` removida, sem uso
- [x] 2.5 Rotas: requisição recebida só no `202` com job novo (D5), em thread; `email_do_solicitante`;
      `worker.py` e fila com `solicitante_email`; porta `notificador` na API
- [x] 2.6 Migration: n/a

## 3. REVIEW
- [x] 3.1 `git diff` completo: só e-mail, ente, exercício, fonte e duração entram na mensagem; nada
      de token, `token_ps` ou segredo
- [x] 3.2 `git diff tests/`: testes novos; cenário do resumo do percurso ajustado; porta
      `notificador` no teste do lifespan

## 4. VERIFY
- [x] 4.1 `python -m pytest` — **559 passed / 0 failed** (antes: 546)
- [x] 4.2 `python -m ruff check .` — 5 achados, todos pré-existentes
- [x] 4.2b SQL real dentro do container `dca_api`: `2505204` → Cuitegi/PB, `2507507` → João
      Pessoa/PB, `2510808` → Patos/PB, `9999999` → nada (cai no IBGE)
- [x] 4.3 — **não executado**: dispensado pelo PO no arquivamento (2026-10-07); envio real ao Discord pendente. Envio real num webhook de teste: anexo, percurso com cache e com falha, requisição recebida
- [x] 4.4 Reconferência da spec — cenário → teste: job concluído →
      `test_anexo_concluido_no_formato_do_rgf` + `test_job_concluido_com_sucesso` · job com erro →
      `test_job_com_erro_tambem_notifica` + `test_anexo_com_falha_traz_o_motivo_truncado` · ente
      ausente → `test_ente_ausente_da_tabela_de_unidades` · banco indisponível →
      `test_banco_indisponivel_ao_resolver_o_ente` · duração → `test_duracao_no_padrao_dos_irmaos` ·
      canal indisponível / não configurada → testes vigentes em `test_transporte.py` · anexo
      enfileirado → `test_anexo_enfileirado` · percurso enfileirado → `test_percurso_enfileirado` ·
      cache não notifica → `test_leitura_servida_do_cache_nao_notifica` · progresso → teste vigente ·
      resumo uma vez → `test_conclusao_do_percurso_e_notificada_uma_vez` +
      `test_resumo_do_percurso_sem_none` · cada anexo → `test_cada_anexo_do_percurso_tambem_notifica`
      · percurso com falha → `test_percurso_com_falha`

## 5. Arquivamento
- [x] 5.1 `tasks.md` 100% marcado
- [x] 5.2 Mesclar deltas em `openspec/specs/pipeline/plataforma` e `pipeline/processamento-completo`;
      atualizar `CENARIOS_ESPERADOS` (plataforma +6 → 89, processamento-completo +2)
- [x] 5.3 Mover para `openspec/changes/archive/AAAA-MM-DD-pipeline-notificacao-discord-padrao/`
- [x] 5.4 Atualizar a tabela "Change ativa" em `openspec/AGENTS.md`
