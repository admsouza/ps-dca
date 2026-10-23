# Tasks — Contas específicas para L28/L61 por crédito e débito mensal

**Repo:** `ps-dca` · **Não implementar sem aprovação explícita do PO.**
Fatia vertical: ente/exercício de homologação a definir, `L28` e `L61` calculadas e batendo com o
BF publicado.

## 0. Fundação
- [x] 0.1 PO confirma a lista de contas — 15 contas, confirmado em 2026-10-01
- [x] 0.2 PO aprova esta `proposal.md` — aprovado em 2026-10-01
- [x] 0.3 PO confirma a redução de `bf-completar-nao-apuradas-g8` de 6 para 4 linhas (`L22`, `L23`,
      `L55`, `L56`) — confirmado em 2026-10-01
- [x] 0.4 Discriminador: campo novo `apenas_natureza: credito|debito` (D1, confirmado 2026-10-01)

## 1. TEST (antes do código)
- [x] 1.1 Um teste por `#### Scenario:` do delta spec em `tests/bf/test_l28_l61_contas_especificas.py`
- [x] 1.2 Rodado e confirmado que falha antes do código (linhas ainda `review_required`/`None`)

## 2. IMPLEMENT
- [x] 2.1 Nova função de agregação em `app/domain/bo/saldo.py`
      (`soma_da_celula_por_natureza` — soma só crédito ou só débito, sem subtração do lado oposto)
- [x] 2.2 Nova leitura MSC em `app/infra/msc/fonte.py` (`fonte_periodo`; 12 competências,
      `TipoSaldo.PERIODO`, isolada às contas de `L28`/`L61` via `app/services/bf/quadro_principal.py`)
- [x] 2.3 `app/infra/regras/carregador.py`: lê `apenas_natureza` do YAML (`_apenas_natureza`)
- [x] 2.3.1 `knowledge/schemas/rule.json`: propriedade `apenas_natureza` (`enum: credito|debito`).
      Ficou de fora em 2026-10-01 e, como o schema tem `additionalProperties: false`,
      `python -m scripts.validate_rules knowledge` saía com exit 1 em `ingressos.l27`,
      `ingressos.l28`, `dispendios.l60` e `dispendios.l61` — gate da base canônica
      (`openspec/project.md:78`) vermelho para todas as changes. Corrigido em 2026-10-23:
      o comando volta a **exit 0, 0 erros, 226 regras**. Só validação; nenhum valor muda
- [x] 2.4 `knowledge/rules/bf/quadro_principal.yaml`: `accounts` + `apenas_natureza` em `L28`
      (~l.1752) e `L61` (~l.3755); `status: review_required` mantido (ver 4.3)
- [x] 2.5 `app/services/bf/informados.py:24`: `"L28"`, `"L61"` removidos de `CODIGOS_SEM_MAPEAMENTO`
- [x] 2.6 Sem migration

## 3. REVIEW
- [x] 3.1 `git diff` completo: só os arquivos do design.md + testes; sem código morto
- [x] 3.2 `git diff tests/` contém os testes novos (`test_l28_l61_contas_especificas.py`) e ajustes
      justificáveis em `test_apuracao.py`/`test_cenarios_spec.py` (G8 de 6 para 4 linhas)

## 4. VERIFY
- [x] 4.1 `python -m pytest` — suíte completa 100% verde (sem regressão nas outras 64 linhas)
- [x] 4.2 `python -m ruff check .` — limpo
- [x] 4.3 Medido `L28`/`L61` contra o BF publicado de João Pessoa/2025 (API SICONFI real,
      2026-10-01) — **reprovado**: `L28` apurado R$ 15.251,40 × publicado R$ 13.227.595.529,71;
      `L61` apurado R$ 15.005,24 × publicado R$ 12.295.961.584,22. Seis ordens de grandeza de
      diferença — as 15 contas de classe 1 (ativo) da proposal não são a fonte real de L28/L61
      neste ente. Blocker atualizado no YAML, com a pista já registrada antes (`classes 7/8`,
      controle devedor/credor do PCASP) como candidato não testado.
- [ ] 4.4 **Bloqueado por 4.3** — `status` permanece `review_required`; não vira `extracted` até o
      PO revisar a lista de contas e uma nova medição bater com o publicado
- [x] 4.5 Regressão: as outras 64 linhas do BF continuam bit a bit iguais (suíte completa + medição
      real confirmam — divergência isolada a L28/L61)
- [x] 4.6 Cada cenário do delta spec → coberto em `tests/bf/test_l28_l61_contas_especificas.py`

## 5. Arquivamento
- [ ] 5.1 **Bloqueado** — `tasks.md` não pode fechar 100% enquanto 4.4 estiver pendente
- [ ] 5.2 Mesclar deltas em `openspec/specs/dca/balanco-financeiro/spec.md`
- [ ] 5.3 Mover para `openspec/changes/archive/<AAAA-MM-DD>-bf-l28-l61-contas-especificas/`
- [ ] 5.4 Atualizar a tabela "Change ativa" em `openspec/AGENTS.md`
- [ ] 5.5 Confirmar que `bf-completar-nao-apuradas-g8` reflete a whitelist reduzida (4 linhas) antes
      de ela própria ser arquivada
