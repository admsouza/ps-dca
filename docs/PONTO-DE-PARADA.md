# Ponto de parada — 2026-09-04 (sessão 2)

Estado ao fim da sessão. A fase de spec fechou, a base canônica do IPC 07 foi entregue e o núcleo
de apuração do Balanço Orçamentário **já reproduz o gabarito do STN com dados reais**.

## Onde paramos, em uma frase

A F1 do BO está implementada, **REVIEW e VERIFY fechados** (tasks 4.1–4.6, 5.1–5.5 e 6.1), e a
conferência linha a linha contra o `RREO-Anexo 01` fecha **108 de 123 células em centavos**;
o que resta são **três pendências normativas — C5, C6 e a nova C7 —** que dependem de decisão do
PO, não de código. As 17 tasks abertas da change do BO caíram para 5 (a 6.0 e o arquivamento).

## Verificação real, reproduzível agora

```bash
python -m pytest                              # 134 passed · 4 failed (as pendências abaixo)
python -m ruff check .                        # All checks passed!
python -m scripts.validate_rules knowledge    # exit 0 · 51 · 9 · 9 = 69 regras
python -m scripts.check_sources knowledge     # ✓ Fontes íntegras
python -m app.cli.bo 2507507 2025             # apura contra a API pública do SICONFI
```

O CLI bate **em centavos** com o gabarito, apurado pelo código e não por script de análise:

| Linha | Coluna | Valor |
|---|---|---|
| `L40` Subtotal das Despesas | dotação inicial · atualizada | 5.314.144.648,00 · 6.043.181.131,90 |
| | empenhadas · liquidadas · pagas | 4.850.356.845,30 · 4.569.049.735,78 · 4.529.794.533,11 |
| `L16` Subtotal das Receitas | previsão inicial · atualizada | 5.301.644.648,00 · 5.560.342.799,26 |
| `L27` · `L28` · `L29` | previsão | 482.338.332,64 · 12.000.000,00 · 470.338.332,64 |
| `L51` Reserva do RPPS | — | sem coluna de valor |

Os R$ 12.000.000,00 de natureza `9.9.9.0.00.0.0` ficam fora do total e dentro de `L28` — B5 e B6
confirmados pelo código.

## Verificação 5.5 — contra o `RREO-Anexo 01`, feita nesta sessão

Relatório completo em `docs/verificacao-5.5-rreo-jp-2025.md`.

| | |
|---|---|
| Células comparáveis | **123** |
| Conferem em centavos | **108** |
| Divergem só no sinal, por convenção do IPC 07 | **14** |
| Divergência real de valor | **1** → pendência **C7** |

As 14 de sinal **não são erro**: o IPC 07 define a coluna de saldo da receita como
`SALDO (d) = (c-b)` (realizada − previsão) e o RREO publica `SALDO (a-c)` (previsão − realizada).
Magnitude idêntica em centavos nas 14. A coluna de despesa não sofre disso e confere.

## As três pendências que dependem do PO

| # | Pendência | Efeito | Onde |
|---|---|---|---|
| **C5** | `L25`, `L26`, `L49` e `L50` cruzam receita e despesa, e os blocos não têm coluna em comum (4 × 6). O IPC 07 não diz em qual coluna essas linhas são apresentadas. | As 4 linhas saem **não apuradas**, com aviso. Nada é presumido. Derruba `test_exercicio_superavitario`, `test_recursos_arrecadados_em_exercicios_anteriores` e `test_apuracao_sem_pendencia_declara_diagnostico_vazio`. | `tasks.md` § 3ter |
| **C7** | `L29` Superávit Financeiro sai com previsão inicial de R$ 470.338.332,64 (saldo inicial de `5.2.2.1.3.01.00`, a conta que B5 mandou declarar) e por `L27 = L28 + L29 + L30` leva `L27` a 482.338.332,64. O STN **não publica** `PREVISÃO INICIAL` para `SuperavitFinanceiro`, e publica `L27` PREVISÃO INICIAL = 12.000.000,00 — só `L28`. O IPC 07 não diz se a coluna se aplica a `L29`. | Única divergência de valor em 123 células. Leitura plausível: superávit financeiro só é conhecido com o exercício fechado, logo não cabe em previsão inicial — **não aplicada**, é interpretação normativa. Nenhum teste vermelho. | `docs/verificacao-5.5-rreo-jp-2025.md` |
| **C6** | O schema `knowledge/schemas/rule.json` não tem `natureza_saldo` na conta, então a exceção B1 (`5.3.1.3.0.00.00`, fora do PCASP atual) não pode ser declarada. | Só afeta exercícios com escrituração em `5.3.1.3` — JP 2025 não tem. Derruba `test_excecao_historica_usa_a_natureza_declarada`. Fechar exige change pequena na base canônica, que está arquivada. | idem |

**Não resolver essas três por conta própria.** São interpretação normativa; o processo manda
declarar, não escolher.

## A descoberta que mudou o desenho, e não deve ser revertida

O saldo de cada conta é tomado **na direção da coluna**, não na direção da própria conta. No PCASP
a conta redutora tem natureza oposta à do grupo **e** `(-)` no título:

```
522110100  Devedora   CREDITO INICIAL
522190400  Credora    (-) CANCELAMENTO DE DOTAÇÕES
621200000  Credora    RECEITA REALIZADA
621310100  Devedora   (-) FUNDEB
```

Somar cada conta na direção dela faz a redutora somar em vez de reduzir: a dotação atualizada sai
`6.303.210.688,18` em vez de `6.043.181.131,90`, e a receita vem bruta em vez de líquida.

A direção do grupo vem da **primeira conta não redutora** sob o prefixo
(`infra/pcasp/natureza.py::credora_prefixo`). Contar por maioria erra em `5.2.1.1`, que tem mais
contas de dedução do que de previsão. O marcador `(-)` é dado da tabela, não heurística.

Duas formulações equivalentes existem — (a) saldo na direção da coluna, implementada; (b) saldo na
direção da conta com sinal negativo explícito nas contas `(-)`. O PO foi consultado em 2026-09-04 e
**não escolheu**; a troca é pequena e dá o mesmo número.

## O que existe no repositório

```text
app/domain/bo/        modelo · portas (Protocol) · saldo · matriz     ← núcleo puro, sem I/O
app/infra/pcasp/      natureza do saldo, lida do PCASP.md
app/infra/msc/        siconfi (paginação ORDS) · publicsoft (gate de auditoria) · normalizacao
app/infra/regras/     carregador: recebe o exercício, devolve o mapa vigente + versao_regras
app/services/bo/      quadro_principal.apurar() — síncrono, sem estado, serve rota/worker/CLI
app/cli/bo.py         python -m app.cli.bo <ente> <exercicio> [--fonte] [--json]
knowledge/            69 regras · 2 policies · schemas · sources (hashes) · índice
scripts/              validate_rules · check_sources · build_index · load_stn_tables · extract_ipc
tests/                138 testes; tests/bo/ é a F1
```

## Changes

| Change | Fase | Situação |
|---|---|---|
| `ipc07-bo-regras-canonicas` | **arquivada** | `openspec/changes/archive/2026-09-04-…`; spec em `openspec/specs/dca/base-canonica-regras/spec.md` |
| `bo-quadro-principal-processamento` | IMPLEMENT | F1 entregue; REVIEW/VERIFY/6.1 fechados. **5 tasks abertas**: 6.0 e arquivamento 7.1–7.4, que aguardam C5/C6/C7 |
| `plataforma-pipeline-dca` | PLAN/ARCH | SPEC aprovada; 59 tasks abertas. Fase TEST não começou — por isso `test_cobertura_spec.py` só confere a contagem dela |

Decisões já tomadas pelo PO e que **não** devem ser reabertas: C1–C4, P1–P10, P-D1 a P-D8, B1/B3/B5/B6.

## Por onde retomar

1. **Levar C5, C6 e C7 ao PO.** É o único bloqueio real. Com C5 respondida, 3 testes fecham; C7 não
   derruba teste, mas é a última divergência contra o STN.
2. Com as três respondidas, fechar o **arquivamento** (tasks 7.1–7.4) — merge do delta em
   `openspec/specs/dca/balanco-orcamentario/spec.md` e mover para `archive/`.
3. Só então **F2** (FastAPI, rota fina) e **F3** (job ARQ, cache, mapeamento em banco), ambas
   especificadas em `plataforma-pipeline-dca`.

## Convenções que o próximo agente precisa respeitar

- **Antes de qualquer migration ou escrita em banco, pedir o schema real ao PO.** O Postgres
  `db-ps-rreo-rgf-dca` é compartilhado com RREO e RGF; separação por prefixo `dca_*` e
  `alembic_version_dca`, **não** por schema. Advisory lock `43812/1001` — conferir em
  `plataforma-pipeline-dca/design.md` § 5.
- `REDIS_PREFIX=msc_cache:` é **compartilhado** de propósito (cache de MSC serve os três
  pipelines). O que se isola é o estado de execução: fila `arq:queue:dca`, chaves `dca:`.
- Núcleo (`app/domain/`) não importa `requests`, `pandas`, `yaml`, `sqlalchemy` nem `fastapi`.
- Nada de heurística de sinal por classe contábil. Célula sem direção conhecida é `None` com aviso,
  nunca `0`.
- Todo teste declara no docstring `Scenario:` ou `Requisito:` — `tests/test_cobertura_spec.py`
  falha caso contrário.
- `.env.example` só é gravável por shell (regra de permissão bloqueia a ferramenta de escrita).

## Estado do git

Tudo comitado até `7b51ac5`. Esta sessão alterou apenas documentação e o `tasks.md` da change:
`openspec/changes/bo-quadro-principal-processamento/tasks.md`,
`docs/verificacao-5.5-rreo-jp-2025.md` (novo) e este arquivo. Nenhuma linha de `app/` foi tocada —
`134 passed / 4 failed` e `ruff` limpo seguem valendo. **Não comitado**, aguardando o PO.
