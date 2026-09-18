# Tasks — Vigência publicada por anexo

## 1. TEST (antes do código)
- [x] 1.1 Teste de que `semear()` publica BO **e** BF, cada um no ano da sua edição
- [x] 1.2 Teste de que a completação de apresentação usa a transcrição do anexo carregado
- [x] 1.3 Teste de idempotência: segundo `semear()` não duplica nem falha
- [x] 1.4 Rodar e confirmar que falham pelo motivo esperado

## 2. IMPLEMENT
- [x] 2.1 `semear()` percorre os anexos implementados do registry, com a base canônica de cada um
- [x] 2.2 `_completar_apresentacao` recebe o demonstrativo
- [x] 2.3 `documento` da vigência deixa de ter `"IPC 07"` como padrão fixo
- [x] 2.4 Migration: n/a — a tabela já é por anexo

## 3. REVIEW
- [x] 3.1 `git diff` completo: sem arquivo fora do escopo

## 4. VERIFY
- [x] 4.1 `python -m pytest` — **403 testes, exit 0**
- [x] 4.2 `python -m ruff check .` — sem erro novo
- [x] 4.3 Mapa do BF pelo banco × pelo YAML: mesmas 80 linhas e mesmos códigos (`test_bf_carregado_do_banco_confere_com_o_yaml`)
