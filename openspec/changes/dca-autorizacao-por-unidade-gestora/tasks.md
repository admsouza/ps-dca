# Tasks — Leitura do DCA restrita às UGs autorizadas

**Repo:** `ps-dca` · **Não implementar sem aprovação explícita do PO.**
Fatia vertical: Cuitegi (`2505204`) 2025, BO/BP/BF, Cenário 01 do PO ponta a ponta.
**Pré-requisito:** `regras-rgf-api` › `CH-49-ug-siafic-no-dca` publicando `ugs` no authorize.

## 0. Fundação
- [x] 0.1 Golden de regressão: payload de BO, BP e BF de Cuitegi 2025 com usuário sem restrição de
      UG, gerado com o código **atual**. Nunca regenerar durante a change
      Registro (revisão): o teste custava **87 s** porque reapurava o fixture 12 vezes (3 anexos ×
      4 conjuntos de poderes) para comparar payloads que não dependem do usuário. `_resultado()`
      apura uma vez por fábrica (BP e BF partem da mesma: 2 apurações no total) e devolve
      `deepcopy`. **87 s → 21,5 s**, com os mesmos 24 payloads comparados bit a bit e o arquivo do
      golden intocado — nenhum conjunto de poderes foi removido.
- [x] 0.2 Dublê do hub nos testes devolvendo `{poderes, modulos, ugs}`

## 1. TEST (antes do código)
- [x] 1.1 `tests/test_autorizacao_por_ug.py`: traduzir cada `#### Scenario:` do delta — duas UGs do
      mesmo poder com contadores diferentes; várias UGs; todas as UGs; poderes diferentes; dois
      entes; sem restrição; recorte padrão; `anterior_por_recorte`; hub fora
- [x] 1.2 `tests/test_guard_modulo_dca.py`: `403` sem `dca`; `403` só no ente sem o módulo;
      revogação na requisição seguinte
- [x] 1.3 Golden: usuário com `ugs` vazio devolve o payload de 0.1 **bit a bit**
- [x] 1.4 Rodar e **confirmar que falham** pelo motivo esperado — registrar o número aqui
      **Registrado: 18 failed / 8 passed** (os 8 que passam são os de comportamento legado: sem
      restrição de UG, hub fora, golden — este último tem de passar antes e depois)

## 2. IMPLEMENT
- [x] 2.1 `app/auth/hub.py`: `Autorizacao(poderes, modulos, ugs)`; campo ausente vira tupla vazia
- [x] 2.2 `app/routes/dependencias.py`: guarda os três em `request.state`; `403` sem `dca`
- [x] 2.3 `app/domain/recorte.py`: `visiveis(..., ugs=())` com a regra de cobertura (D2)
- [x] 2.4 `app/routes/anexos.py` e `app/services/pipeline/resumo.py`: repassar `ugs` em todas as
      chamadas de `visiveis` — nenhuma chamada sem o parâmetro
- [x] 2.5 Migration: não há

## 3. REVIEW
- [x] 3.1 `git diff` completo: sem arquivo fora do escopo, sem código morto, sem `print`/segredo/`TODO` órfão
- [x] 3.2 `git diff tests/` contém apenas testes novos e mudanças justificáveis
- [x] 3.3 `grep -rn "visiveis(" app/` — toda chamada passa `ugs`

## 4. VERIFY
- [x] 4.1 `python -m pytest -q` — reportar `N passed / M failed` — **852 passed / 0 failed**
- [ ] 4.2 `python -m ruff check .` — limpo (5 erros pré-existentes, nenhum desta change:
      vigencias.py I001/E501, test_template.py I001, test_unidade_por_header.py E501/F401)
      Registro (revisão): confirmados os mesmos 5, em 3 arquivos que esta change não toca. Fica como
      falha **pré-existente** declarada; limpá-los é mudança fora do escopo desta change.
      Registro (revisão) de 4.1: reexecutado com `PYTHONUTF8=1` e saída em arquivo — **852 passed /
      0 failed**, exit 0. Sem redirecionamento o pytest morre num `OSError: [Errno 22]` ao escrever a
      linha final no terminal do Windows; é o terminal, não a suíte.
- [x] 4.3 Golden de 1.3 verde
- [ ] 4.4 Medição ao vivo em Cuitegi com os três contadores do Cenário 01: recortes disponíveis de
      cada um, `403` na UG do outro, e o Cenário 02 com todas as UGs marcadas
- [x] 4.5 Reconferência da spec: cada `#### Scenario:` → teste ou medição que o cobre

## 5. Arquivamento
- [ ] 5.1 `tasks.md` 100% marcado
- [ ] 5.2 Mesclar o delta em `openspec/specs/pipeline/plataforma/spec.md`
- [ ] 5.3 Mover para `openspec/changes/archive/AAAA-MM-DD-dca-autorizacao-por-unidade-gestora/`
- [ ] 5.4 Atualizar a tabela "Change ativa" em `openspec/AGENTS.md`

## 6. Gate de deploy
- [ ] 6.1 Apuração de produção do guard de módulo `dca` concluída na CH-49 (task 7.4) — **ninguém
      perde acesso que tenha hoje** antes de subir
- [ ] 6.2 Hub com a CH-49 em produção antes deste deploy
