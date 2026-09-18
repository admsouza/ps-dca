# Tasks — Balanço Financeiro servido pelo pipeline

**Repo:** `ps-dca` · Fatia vertical: `GET /anexos/BF` devolvendo o demonstrativo completo, com o
mesmo JSON do CLI.

## 0. Fundação
- [x] 0.1 Apuração do BF implementada e verificada (`bf-apuracao-f1`): 66 linhas × 2 colunas, 24
      identidades fechando nos 5 entes
- [x] 0.2 Plataforma F2/F3 implementada e verde (74 testes em `tests/pipeline/`)
- [x] 0.3 Gaps levantados no código, não supostos: `_ComCache.registros` sem `matriz`/`tipo_saldo`
      (`apuracao.py:47`), `ORDEM_GRUPOS` sem `INGRESSOS`/`DISPENDIOS` (`resultado.py`), chave de
      cache sem a origem da coluna anterior
- [x] 0.4 PO aprova a proposal — autorizado em 2026-09-18

## 1. TEST (antes do código)
- [x] 1.1 Teste de que o envelope de cache **repassa** `matriz` e `tipo_saldo` à fonte — asserção
      sobre os parâmetros, não sobre o valor: o defeito é silencioso
- [x] 1.2 Teste de ordem de apresentação do BF: ingressos antes de dispêndios, `ordem` relativa ao
      grupo, quadro anexo depois do principal
- [x] 1.3 Teste de que a chave de cache separa as duas origens da coluna anterior
- [x] 1.4 Teste de contrato: JSON da rota idêntico ao do CLI para o mesmo pedido
- [x] 1.5 Regressão: template e ordem do BO inalterados
- [x] 1.6 Rodar e confirmar que falham pelo motivo esperado

## 2. IMPLEMENT
- [x] 2.1 `_ComCache.registros` repassa `matriz` e `tipo_saldo` (`apuracao.py`)
- [x] 2.2 `BF` no `REGISTRY`, apontando `app.services.bf.quadro_principal:apurar`
- [x] 2.3 Ordem de apresentação declarada pelo demonstrativo, em vez de constante do serializador
- [x] 2.4 Serialização de `origens_por_linha`, `origem_exercicio_anterior`,
      `policies_nao_aplicadas` e `sem_dados_exercicio_anterior`
- [x] 2.5 Chave de cache com a origem da coluna anterior e, no modo manual, a identidade do
      conjunto informado
- [x] 2.6a **Defeito encontrado e corrigido:** a fábrica do apurador importava o serviço do BO de
      forma fixa e o carregador vinha sem demonstrativo — o BF seria apurado pelas regras do IPC 07
      sobre as classes do BO, sem erro nenhum. O serviço e a base canônica passam a vir do registry
- [x] 2.6b Job `apurar_anexo` com competência e origem da coluna anterior no payload: os
      parâmetros entram na identidade do cache, viajam no enfileiramento e chegam ao serviço —
      filtrados pela assinatura dele, para que um job só sirva a anexos com parâmetros diferentes
- [x] 2.7 Migration: n/a — o registro de cache já é genérico por anexo

## 3. REVIEW
- [x] 3.1 `git diff` completo: sem arquivo fora do escopo, sem código morto
- [x] 3.2 Nenhuma alteração no comportamento da apuração — esta change só transporta

## 4. VERIFY
- [x] 4.1 `python -m pytest` — **353 testes, exit 0**
- [x] 4.2 `python -m ruff check .` — limpo nos arquivos tocados; 6 achados pré-existentes
- [x] 4.3 CLI e serialização da rota são **a mesma função** (`resultado.para_dados`), com teste de
      igualdade; falta o teste end-to-end pela rota HTTP
- [x] 4.3b `GET /dca/BF` contra a app, com portas fakes: 200 com as 80 linhas, `L1` primeiro e grupo `INGRESSOS` (`tests/pipeline/test_rota_bf.py`)
- [x] 4.4 Apuração pela plataforma reproduz a do CLI nos 5 entes (mesmos placares por ente)
- [x] 4.5 Regressão do BO: suíte inteira verde, contrato da rota inalterado

## 5. Arquivamento
- [x] 5.1 `tasks.md` 100% marcado
- [x] 5.2 Mesclar deltas em `openspec/specs/` e atualizar `CENARIOS_ESPERADOS`
- [x] 5.3 Mover para `openspec/changes/archive/AAAA-MM-DD-bf-no-pipeline/`
- [x] 5.4 Atualizar a tabela "Change ativa" em `openspec/AGENTS.md`
