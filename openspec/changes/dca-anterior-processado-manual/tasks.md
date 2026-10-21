# Tasks — Exercício anterior somente Processado ou Manual

**Repo:** `ps-dca` · **Aprovado pelo PO em 2026-10-21.**
Fatia vertical: Cuitegi/PB, BF e BP de 2025 com Processado 2024 ou Manual por unidade.

## 0. Fundação
- [x] 0.1 Mapear resolver, rota, cache, callers, testes e contrato do front

## 1. TEST (antes do código)
- [x] 1.1 Atualizar testes: padrão sem N−1 falha, MSCE nova é recusada e Manual permanece válido
- [x] 1.2 Rodar e confirmar falha pelo motivo esperado

## 2. IMPLEMENT
- [x] 2.1 Remover fallback público para MSCE e exigir Processado no padrão
- [x] 2.2 Recusar MSCE em pedidos novos e normalizar escolha legada
- [x] 2.3 Atualizar mensagens HTTP curtas e acionáveis

## 3. REVIEW
- [x] 3.1 Revisar diff completo e regressão do exercício atual/manual

## 4. VERIFY
- [x] 4.1 `python -m pytest` — suíte completa aprovada
- [ ] 4.2 `python -m ruff check .` — bloqueado por 6 violações preexistentes fora do escopo
- [x] 4.3 Não aplicável: nenhuma migration ou alteração de schema
- [x] 4.4 Reconferir cada cenário do delta

## 5. Arquivamento
- [ ] 5.1 Arquivar após a consolidação da change-base ativa `pipeline-anterior-por-recorte`;
      registro incluído em `openspec/AGENTS.md`
