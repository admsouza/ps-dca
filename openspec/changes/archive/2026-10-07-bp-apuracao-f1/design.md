# Design — Apuração do Balanço Patrimonial (F1)

**Change:** `openspec/changes/bp-apuracao-f1/` · **Proposal aprovada pelo PO em:** 2026-10-07

## Contexto

O BF já percorreu tudo o que o BP precisa: carregador por demonstrativo, `base_canonica` no
registry, job único `apurar_anexo`, rota `/dca/{anexo}`, cache, template no resultado e tipo de
saldo por coluna. `fonte_de("BP")` já devolve `MSCE`/encerramento. O BP é, portanto, **mais simples**
que o BF: sem fonte de recursos, sem movimento C/D, sem coluna manual, sem estorno.

O que falta é só o que o IPC 04 traz de novo — o atributo F/P — e a plumbing de mais um anexo.

## Componentes afetados

| Componente | Papel na change |
|---|---|
| `app/domain/bo/modelo.py` | `Registro.financeiro_permanente: str = ""` |
| `app/domain/bo/saldo.py` | resolve o campo de filtro `financeiro_permanente` |
| `app/infra/msc/normalizacao.py` | `CAMPOS["financeiro_permanente"]`, `1`→`F`, `2`→`P`, outro → `""` |
| `app/infra/msc/fonte.py` | `BP`: classes `(1, 2, 6)` (D3) |
| `app/infra/regras/carregador.py` | aceita `demonstrativo="bp"` (já parametrizado) |
| `knowledge/schemas/rule.json`, `scripts/validate_rules.py` | `IPC04` no enum; campos e colunas por documento |
| `knowledge/indexes/rules_index.json` | regenerado (`python -m scripts.build_index knowledge`) |
| `knowledge/rules/bp/*.yaml` | filtros F/P em `ativos_passivos_financeiros` L2/L3/L5/L6 (após P4); `L4`/`L34` conforme P2/P3 |
| `app/services/bp/quadro_principal.py` | **criar** — orquestração, duas colunas, equilíbrio |
| `app/cli/bp.py` | **criar** |
| `app/services/pipeline/registry.py` | `Anexo("BP", "app.services.bp.quadro_principal:apurar", base_canonica="bp")` |
| `app/services/pipeline/apuracao.py` | `services/bp` na lista de pacotes |
| `app/services/pipeline/resultado.py` | ordem de apresentação dos quadros do BP |
| semente de vigência (`vigencia-por-anexo`) | publica a vigência do IPC 04 |

## Fluxo da informação

```text
POST /dca/BP/jobs ─► job apurar_anexo ─► registry("BP") ─► bp.quadro_principal.apurar
                                                              │
carregar(exercicio, "bp") ─► Mapa (58 linhas) ────────────────┤
MSCE/encerramento, comp. 12, classes 1,2,6, ano e ano−1 ─► [Registro] ─► motor ─► Matriz
                                                              │
                         template + procedência + diagnóstico (equilíbrio, resíduos F/P) ─► cache
```

## Contratos / interfaces

```python
# app/domain/bo/modelo.py
class Registro(NamedTuple):
    ...
    fonte_recursos: str = ""
    financeiro_permanente: str = ""   # "F" | "P" | "" — do fato, nunca do PCASP

# app/services/bp/quadro_principal.py
def apurar(ente: int, exercicio: int, fonte, direcao=None, mapa: MapaBO | None = None,
           competencia: int = 12) -> Resultado: ...
```

Termo qualificado no YAML (IPC 04 p. 10, `L5`):

```yaml
accounts:
- {literal: 2.1.0.0.0.00.00, pattern: '21', sign: +, saldo: final, financeiro_permanente: F}
- {literal: 2.2.0.0.0.00.00, pattern: '22', sign: +, saldo: final, financeiro_permanente: F}
- {literal: 6.3.1.1.0.00.00, pattern: '6311', sign: +, saldo: final}
```

`Resultado`, `Procedencia` e `Diagnostico` reutilizados do BF. `Diagnostico` ganha
`sem_atributo_fp: bool`.

## Impacto

| Eixo | Impacto |
|---|---|
| Banco / migration | nenhum — cache por anexo já é genérico |
| Cache | chave nova só pelo anexo `BP`; `versao_regras` próprio do IPC 04 |
| Filas / worker | nenhum job novo |
| APIs externas | +classe 6 na leitura do BP; 2 exercícios × 3 classes. Adapters já têm retry |
| Regressão | BO e BF bit a bit: `Registro` ganha campo com default `""`, nenhuma regra BO/BF filtra por ele |

## Decisões

### D1 — Reusar o motor e o serviço do BF como molde, sem núcleo novo
**Escolhido:** `app/services/bp/` importando de `app/domain/bo/` como o BF faz ·
**Descartado:** renomear para `app/domain/nucleo/` agora · **Porquê:** o BF já adiou o renomeio
(2.1 de `bf-apuracao-f1`); fazê-lo aqui misturaria refatoração com feature num mesmo diff.

### D2 — F/P como qualificador do termo de conta
**Escolhido:** `financeiro_permanente` no `Registro` e no termo de conta (`ContaCC`, `conta` do
schema), só para IPC 04 · **Descartado:** (1) derivar F/P do `INDICADOR DO SUPERÁVIT FINANCEIRO` do
PCASP; (2) filtro de linha. **Porquê:** 924 contas são `F/P` no plano, e o atributo só existe no fato
(`docs/source-analysis.md` §11.2); medido em Cuitegi, Ativo Financeiro = Ativo Circulante em 2025 e
≠ em 2024. O filtro de linha vale para todas as contas da linha, e `L5` mistura `2.1`/`2.2` com F e
contas da classe 6, que vêm **sem** atributo (medido: 1.272 registros em Cuitegi 2025). O IPC 04
escreve o atributo no termo, e o modelo segue o texto. Mesmo precedente de `ContaCC.saldo` no BF.

### D2b — Linha `review_required` carrega o bloqueio
**Escolhido:** `Linha.bloqueio` = `review.blocker` quando `status: review_required`. O serviço do BP
apura a linha sem contas (parcela inexistente no total), devolve `None` e põe o bloqueio no
diagnóstico. Total cujas parcelas são **todas** bloqueadas também sai `None` (compensação) ·
**Descartado:** apagar as contas de `L34` no YAML · **Porquê:** a transcrição continua íntegra, e o
BO e o BF não leem o campo, que só é serializado quando preenchido. `_achatar`/`_linha` levam os dois
campos novos ao banco: sem isso o worker, que lê a vigência publicada, perderia o atributo **sem
erro**.

### D2c — Direção do saldo pela coluna (critério do BO), não por conta
**Escolhido:** `por_conta=False` · **Porquê:** no BP as redutoras ficam **dentro** do grupo (depreciação
`1.2.3.8`, credora, dentro de `1.2.3`). Pela direção da conta, elas somariam. Medido: o total da classe 1
de Cuitegi com D − C em todas as folhas é 76.314.331,92, igual ao publicado. Teto conhecido: `L40 (-)
Ações/Cotas em Tesouraria` (`2.3.9`, devedora) sai positiva e soma no PL. Saldo 0,00 nos entes
medidos; vira sinal `−` na regra quando algum ente tiver saldo.

### D3 — Classes 1, 2 e 6 no BP
**Escolhido:** ampliar `fonte_de("BP").classes` · **Descartado:** segunda leitura ad hoc no serviço ·
**Porquê:** `L5` Passivo Financeiro do quadro F/P declara contas `6.2.2.1.3` e `6.3.1`; a tabela de
fonte é o lugar único do par (matriz, saldo, classes) — `fonte-msc` muda um cenário.

### D4 — Espelho `I-AB` só na conferência
**Escolhido:** de-para fixo de 8 âncoras em `docs/` e no teste de homologação · **Descartado:**
apurar o BP por `cod_conta` do `tt/dca` · **Porquê:** o aceite é medir a apuração **contra** o
publicado; apurar a partir do publicado tornaria o aceite tautológico.

### D5 — Linha bloqueada é parcela inexistente
Igual ao D5 do BF (G5): total soma as parcelas apuradas, diagnóstico nomeia as bloqueadas.

### D6 — Coluna anterior só por MSCE
**Escolhido:** encerramento do exercício − 1, mesmo mapa · **Descartado:** modo manual do BF ·
**Porquê:** nenhum ente medido precisa; o modo manual custou 3 changes no BF. Entra quando houver
caso.

## Arquivos criados / alterados

| Arquivo | Ação |
|---|---|
| `app/domain/bo/modelo.py`, `app/domain/bo/saldo.py` | alterar |
| `app/infra/msc/normalizacao.py`, `app/infra/msc/fonte.py` | alterar |
| `knowledge/schemas/rule.json`, `scripts/validate_rules.py` | alterar |
| `knowledge/rules/bp/ativos_passivos_financeiros.yaml`, `quadro_principal.yaml` | alterar (após P2–P4) |
| `knowledge/indexes/rules_index.json` | regenerar |
| `app/services/bp/__init__.py`, `app/services/bp/quadro_principal.py` | criar |
| `app/cli/bp.py` | criar |
| `app/services/pipeline/registry.py`, `apuracao.py`, `resultado.py` | alterar |
| `app/infra/regras/vigencias.py` | alterar (ida e volta do atributo e do bloqueio) |
| `app/infra/pcasp/natureza.py` | alterar (`mista()`: contas `Credora/Devedora` do PCASP) |
| `tests/bp/` (`conftest.py`, `test_apuracao.py`), `tests/test_regras_bp.py`, `tests/pipeline/test_bp_no_pipeline.py` | criar |
| `tests/msc/test_fonte_por_demonstrativo.py`, `tests/pipeline/test_pipeline_completo.py`, `tests/test_regras_bf.py` | alterar (classes do BP; BP no percurso; 3 documentos) |
| `docs/evidencia-bp-fp-2025.md`, `docs/depara-bp-iab-ipc04.md`, `docs/entes-homologacao/cuitegi/auditoria-bp-2025.md` | criar |

## Pendências conhecidas

- P4 depende de **medição**: se SICONFI ou PublicSoft não trouxer o atributo na `MSCE`, o quadro F/P
  dessa fonte sai `None` (cenário "fonte sem o atributo").
- Compensação e superávit por fonte ficam para change própria, quando houver detalhamento de ente.
