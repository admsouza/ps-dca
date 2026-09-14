# Tasks — Apuração do Balanço Financeiro (F1)

**Repo:** `ps-dca` · **Não implementar sem aprovação explícita do PO.**
Fatia vertical: João Pessoa/PB (2507507), exercício 2025, BF apurado ponta a ponta pelo CLI.

## 0. Fundação
- [ ] 0.1 PO aprova a proposal e decide G5, G6, G7, G8, **G9** (tipo de matriz e tipo de saldo)
      e **G10** (periodicidade mensal em todos os anexos). G1–G4 resolvidos por medição
- [x] 0.2 `tt/dca` conferido: **o BF não é publicado** — aceite passa a ser identidade interna +
      âncoras + conciliação de caixa (`docs/evidencia-bf-jp-2025.md` §1)
- [x] 0.3 MSC medida: 8 classes × 3 tipos de valor × 2 exercícios em ~45 s, maior resposta 6.202 regs
- [x] 0.4 `fonte_recursos` medida: sempre 4 dígitos; detalhamento do ente em `complemento_fonte`
- [x] 0.5b Piloto MSCC × MSCE em Cuitegi/PB: MSCC bate 1:1 com o `RREO-Anexo 01` em 8 células,
      MSCE erra 47; a MSCE zera as classes 3 e 4 (`docs/evidencia-matriz-mscc-vs-msce.md`)
- [x] 0.5 Apuração exploratória do BF completa, com as 4 âncoras batendo em centavos e o
      desequilíbrio residual de −228.702.095,15 rastreado até as linhas bloqueadas

## 1. TEST (antes do código)
- [ ] 1.1 Traduzir cada `#### Scenario:` do delta spec em `tests/bf/test_*.py`
- [ ] 1.2 Teste de regressão do BO: os 11 valores de `docs/validacao-bo-jp-2025.md` antes e depois
      da renomeação do núcleo
- [ ] 1.3 Rodar e **confirmar que falha** pelo motivo esperado

## 2. IMPLEMENT
- [ ] 2.1 `git mv app/domain/bo app/domain/nucleo`; `MapaBO` → `Mapa`; atualizar imports em `app/`,
      `tests/`, `worker.py`, `main.py` — **suíte verde antes de seguir** (D1)
- [ ] 2.2 `fonte_recurso` no motor: resolução do campo, `codigo_principal()` e casamento por
      igualdade (G1/D4)
- [ ] 2.2b Critério de direção do saldo declarado pela regra: por conta no BF, por coluna no BO
      (G7/D4a)
- [ ] 2.3 `ContaCC.saldo` e `tipo_valor` na porta + adapters MSC (G2/D2)
- [ ] 2.4 `Coluna.movimento` e filtro por natureza do lançamento em `saldo_da_celula` (G3/D3)
- [ ] 2.5 Carregador por demonstrativo, com `versao_regras` próprio
- [ ] 2.6 Parcela bloqueada como inexistente no total, com o diagnóstico nomeando cada uma (G5/D5)
- [ ] 2.7 `app/services/bf/quadro_principal.py`: classes 1–6, duas colunas, conferência de
      equilíbrio (G4/D6)
- [ ] 2.8 Quadro Anexo: seis colunas, `(c)` e `(f)` derivadas
- [ ] 2.9 Ordem de apresentação do BF em `resultado.py` e `app/cli/bf.py`
- [ ] 2.10 Retry com backoff nos adapters MSC — 2 de ~40 chamadas caíram na medição
- [ ] 2.11 `L22`/`L55` pela variação de `1.1.4` e `1.2.1.3`, se o PO aprovar G8
- [ ] 2.12 Competência como parâmetro do serviço ao CLI, padrão 12, declarada na procedência (G10/D4c)
- [ ] 2.13 Tipo de matriz declarado na procedência; `MSCE` recusada com erro explícito até G9 (D4b)
- [ ] 2.14 Migration: n/a (a F1 não toca banco)

## 3. REVIEW
- [ ] 3.1 `git diff` completo: sem arquivo fora do escopo, sem código morto, sem `print`/segredo/`TODO` órfão
- [ ] 3.2 O diff da renomeação é só renomeação — nenhuma mudança de lógica escondida nele
- [ ] 3.3 `git diff tests/` contém apenas testes novos e a troca de import nos antigos

## 4. VERIFY
- [ ] 4.1 `python -m pytest` — reportar `N passed / M failed`
- [ ] 4.2 `python -m ruff check .` — sem erro novo
- [ ] 4.3 `python -m scripts.validate_rules` — 149 regras, `review_required 6`
- [ ] 4.4 As 4 âncoras publicadas (`L1`, `L25`, `L26`, `L34`) batem em centavos
- [ ] 4.5 `L33 == L66` nas duas colunas; diferença remanescente medida e explicada
- [ ] 4.5b Ingressos − dispêndios explicam a variação de caixa do exercício
- [ ] 4.6 Regressão do BO: 11 valores idênticos em centavos
- [ ] 4.7 Reconferência da spec: cada cenário → onde é coberto
- [ ] 4.8 `docs/validacao-bf-jp-2025.md` com o medido, incluindo divergências e hipóteses

## 5. Arquivamento
- [ ] 5.1 `tasks.md` 100% marcado
- [ ] 5.2 Mesclar deltas em `openspec/specs/dca/balanco-financeiro/spec.md` e atualizar
      `CENARIOS_ESPERADOS` / `COM_TESTES` em `tests/test_cobertura_spec.py`
- [ ] 5.3 Mover para `openspec/changes/archive/AAAA-MM-DD-bf-apuracao-f1/`
- [ ] 5.4 Atualizar a tabela "Change ativa" em `openspec/AGENTS.md`
