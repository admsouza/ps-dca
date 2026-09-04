# Tasks — Processamento do BO, quadro principal

**Não implementar sem aprovação explícita do PO.** Fatia: apuração das 51 linhas do quadro
principal a partir da MSC. Os quadros de RP e a ligação com o anexo DCA são changes posteriores.

## Ordem de execução

Núcleo primeiro; infra pesada só quando houver o que cachear. Decidido em 2026-09-04, com base no
fluxo já em produção no `regras-rgf-api`.

| Fase | Entrega | Infra necessária |
|---|---|---|
| **F1 — Núcleo** | `domain/bo/` + adapters (PCASP, MSC) + carregador de regras + service + CLI que apura JP 12/2025 | nenhuma — sem FastAPI, sem Postgres, sem Redis |
| **F2 — Transporte** | FastAPI; rota fina que só chama o service | nenhuma |
| **F3 — Pipeline** | job ARQ/Redis + tabela de cache no Postgres + alembic | Redis (`ps-infra`) + Postgres |

F1 fecha as seções 2 a 5 deste arquivo: o aceite são os 11 valores em centavos, e ele não depende de
banco. **A DCA é o terceiro pipeline da casa, ao lado do RREO e do RGF** — a F3 é destino certo, não
hipótese; adiá-la só encurta o ciclo de verificação do núcleo (D6). Por isso a F1 já entrega o
service síncrono, puro e sem estado, e a identidade `(ente, exercício, anexo, versão das regras)` —
a mesma chave que vira PK do cache na F3.

**Do `regras-rgf-api`, reusar:** `engine/formula.py` (parser `ast` com whitelist, sem `eval`),
`engine/dag.py` (ordem topológica), a paginação ORDS e o gate de auditoria dos `data_sources`, e —
na F3 — o padrão de job + cache de `routes/anexo_01/jobs_rgf_anexo_01.py`.

**Não reusar:** `_CLASSES_CREDORAS` (D1 — medida errada em 29 contas); pandas no domínio (D2);
regra e `ThreadPoolExecutor` dentro da rota (`routes/anexo_01/completo.py`); cache replicado por
anexo — na DCA é um service parametrizado.

## 0. SPEC

- [x] 0.1 Levantar em `regras-rgf-api` como SICONFI e PublicSoft são chamadas, e registrar o
      contrato normalizado de colunas (`design.md` §1).
- [x] 0.2 Medir no `PCASP.md` a natureza do saldo por classe e por prefixo do BO; concluir que a
      direção é resolvida por conta folha (`design.md` §2, D1).
- [x] 0.3 Registrar a decisão do PO de que a DCA lê sempre `ending_balance` (`design.md` §3).
- [x] 0.4 Escrever `proposal.md` e o rascunho de `design.md` com a estrutura.
- [x] 0.5 C1 decidido pelo PO em 2026-09-03: mês **12**, `co_tipo_matriz=MSCC`.
- [x] 0.6 C3 resolvido por medição: nenhuma conta da MSC de JP 12/2025 está fora do PCASP atual;
      `natureza_saldo` na regra fica como precaução para exercícios antigos.
- [x] 0.7 C2 resolvido por medição: das 4 bifront só 2 têm movimento e nenhuma compõe as colunas —
      ficam fora, e o casamento de conta não pode capturá-las por prefixo.
- [x] 0.8 Validar a regra de saldo contra caso real (JP 12/2025 × `DCA-Anexo I-C` e `I-D`):
      espelho 1:1 em centavos nos 8 valores. Registrado em `docs/validacao-bo-jp-2025.md`.
- [x] 0.9 Inventariar onde cada informação é publicada no SICONFI e localizar o gabarito das
      colunas de previsão/dotação. Registrado em `docs/anexos-siconfi-inventario.md`.
- [x] 0.10 C4 decidido pelo PO em 2026-09-04: o Balanço Orçamentário fica no `ps-dca`. O
      `RREO-Anexo 01` é do RREO (`regras-rreo-api`) e aqui serve só como gabarito de validação.
- [x] 0.11 Delta `specs/dca/balanco-orcamentario/spec.md` escrito: 13 requisitos, 29 cenários,
      ancorados nos valores medidos de JP 12/2025.
- [x] 0.12 PO aprovou `proposal.md`, `design.md` e o delta spec em 2026-09-04 (Jackson S. da Silva (PO)). **Fase SPEC
      fechada** — PLAN/ARCH liberada.

## 1. PLAN/ARCH

- [x] 1.1 `design.md` revisado após C1–C4 e assinado pelo PO em 2026-09-04.
- [x] 1.2 Dependências da F1 fixadas em `pyproject.toml` (2026-09-04): runtime `pyyaml`,
      `jsonschema` e `requests`; dev `pytest`, `ruff`, `pymupdf`. Sem pandas (D2). FastAPI é F2;
      `arq`, `redis`, `sqlmodel` e `alembic` são F3.
- [x] 1.3 Esqueleto da F1: `.env.example` criado; `ruff` e `pytest` configurados no
      `pyproject.toml` — **um arquivo em vez de três**, ao contrário do `ruff.toml` + `pytest.ini`
      separados do RGF.
      **`docker-compose.yml` adiado para a F2, deliberadamente.** A F1 não tem processo servido:
      é núcleo mais CLI, roda com `python -m`. Um compose agora declararia serviço sem nada para
      servir — scaffolding para depois, que a F2 cria junto com a API que o justifica. A rede
      externa `ps-infra` e o Redis continuam previstos em `plataforma-pipeline-dca` § 5.

## 2. TEST — antes do código

- [x] 2.1 Os **33** cenários do delta spec traduzidos em 45 testes, escritos em 2026-09-04:
      · `tests/bo/test_saldo.py` — direção do saldo, composição da célula, casamento de conta
      · `tests/bo/test_apuracao.py` — leitura da MSC, adapters, ordem de apuração, vigência,
        procedência e diagnóstico
      · `tests/bo/test_caso_joao_pessoa.py` — os 11 valores do caso de referência
      A cobertura é verificada por `tests/test_cobertura_spec.py`, agora parametrizado por
      capability: falha se um cenário ficar sem teste ou se a contagem mudar sem decisão.
- [x] 2.2 `tests/bo/conftest.py` — fixture `exemplo_l2` com os registros do item 23 do IPC 07
      (p. 8), cobrindo numa só passagem conta credora (`521110000`, `621200000`), conta devedora
      (`621310100`) e coluna derivada (`saldo = c − b`). Mais os dublês `FonteFake`,
      `FonteVazia` e `DirecaoFake` das duas portas do domínio.
- [x] 2.3 `test_heuristica_de_classe_e_rejeitada` falha se o módulo de saldo passar a conhecer
      conjunto de classes credoras; `test_contas_de_mesmo_prefixo_com_direcoes_opostas` e
      `test_deducoes_de_classe_6_sao_devedoras_no_pcasp` ancoram em `621310100`/`621390000`.
- [x] 2.4 `test_conta_irma_de_controle_paralelo_nao_entra` — falha se `522139900` inflar a
      coluna de `L29` em R$ 729.036.483,90.
- [x] 2.5 `test_exercicio_e_parametro_da_carga_de_regras` e `test_exercicio_descoberto`, que
      exige a falha nomeando o exercício e as vigências disponíveis.
- [x] 2.6 `test_divergencia_explicavel_pelo_resultado` (edição, documento, `versao_regras`,
      hashes das tabelas STN e regras aplicadas) e
      `test_apuracao_sem_pendencia_declara_diagnostico_vazio`.
- [x] 2.7 Suíte executada em 2026-09-04: **93 passed · 4 failed · 41 errors**, e
      `ruff check .` → `All checks passed!`. Os 45 vermelhos são todos
      `ModuleNotFoundError: No module named 'app'` — o pacote da F1 não existe. Nenhuma falha
      por erro de escrita do teste. Os 93 verdes são a base canônica, já entregue.

## 3. IMPLEMENT — F1 (núcleo)

- [x] 3.1 `domain/bo/modelo.py` (Registro · ContaCC · Filtro · Coluna · Linha · MapaBO ·
      Matriz · NaoApurada · Residuo) e `portas.py` (`DirecaoSaldo`, `FonteSaldos`).
- [x] 3.2 `infra/pcasp/natureza.py` — direção por conta folha e por grupo, lida do `PCASP.md`
      (6.053 contas com natureza declarada).
- [x] 3.3 `domain/bo/saldo.py` — saldo da conta, casamento por prefixo com coringa, filtros,
      grupos de exclusão e saldo da célula com direção injetada.
- [x] 3.4 `domain/bo/matriz.py` — os 3 passos e o detector de ciclo. O parser de fórmula do RGF
      **não** foi reusado: as expressões do BO são listas de referências com sinal, já
      estruturadas no YAML — não há texto de fórmula para interpretar, e um parser `ast` aqui
      seria complexidade sem uso.
- [x] 3.5 `infra/msc/` — `siconfi.py` (paginação ORDS), `publicsoft.py` (gate de auditoria) e
      `normalizacao.py` (contrato único, camelCase e latin-1).
- [x] 3.6 `infra/regras/carregador.py` — recebe o **exercício**, resolve a vigência e devolve o
      mapa com `versao_regras` (hash canônico, P-D7) e os hashes das tabelas STN. E
      `services/bo/quadro_principal.py`, síncrono e sem estado, devolvendo matriz + procedência
      + diagnóstico (P9).
- [x] 3.7 CLI `python -m app.cli.bo <ente> <exercicio> [--fonte] [--json]`. Executado contra a
      API real do SICONFI em 2026-09-04.

## 3bis. Verificação com dados reais (2026-09-04)

`python -m app.cli.bo 2507507 2025` — API pública do SICONFI, sem mock. **Todos os valores do
gabarito conferem em centavos**, apurados pelo código e não por script de análise:

| Linha | Coluna | Apurado | Gabarito |
|---|---|---|---|
| `L40` SUBTOTAL DAS DESPESAS | dotação inicial | 5.314.144.648,00 | ✓ |
| | dotação atualizada | 6.043.181.131,90 | ✓ |
| | empenhadas | 4.850.356.845,30 | ✓ |
| | liquidadas | 4.569.049.735,78 | ✓ |
| | pagas | 4.529.794.533,11 | ✓ |
| `L16` SUBTOTAL DAS RECEITAS | previsão inicial | 5.301.644.648,00 | ✓ |
| | previsão atualizada | 5.560.342.799,26 | ✓ |
| `L27` Saldos de Exerc. Anteriores | previsão atualizada | 482.338.332,64 | ✓ |
| `L28` Recursos Arrecadados | previsão inicial | 12.000.000,00 | ✓ |
| `L29` Superávit Financeiro | previsão atualizada | 470.338.332,64 | ✓ |
| `L51` Reserva do RPPS | — | sem coluna de valor | ✓ |

Os R$ 12.000.000,00 de natureza `9.9.9.0.00.0.0` ficam **fora** do total (`L16`) e dentro de
`L28`, exatamente como o STN publica — confirmando B5 e B6 pelo código.

### Descoberta que mudou o desenho

O saldo de cada conta é tomado **na direção da coluna**, não na da própria conta. No PCASP a
conta redutora tem natureza oposta à do grupo e `(-)` no título — `522190400 (-) CANCELAMENTO DE
DOTAÇÕES` é credora entre devedoras; `621310100 (-) FUNDEB` é devedora entre credoras. Somar cada
uma na direção dela devolveria a redutora positiva e inflaria a coluna: a dotação atualizada sairia
6.303.210.688,18 em vez de 6.043.181.131,90, e a receita realizada viria bruta em vez de líquida.

A direção do grupo vem da primeira conta **não redutora** sob o prefixo — o marcador `(-)` é dado
da tabela, não heurística. Contar por maioria erraria em `5.2.1.1`, onde há mais contas de dedução
do que de previsão.

## 3ter. Pendências abertas — decisão do PO

| # | Pendência | Efeito hoje |
|---|---|---|
| ~~**C5**~~ | **ENCERRADA em 2026-09-04** pela change `ipc07-c5-c7-linhas-cruzadas`. As 4 linhas são apuradas: superávit em 3 colunas de execução, déficit em 1, contra a empenhada — assimétricas, medido. | Fechou os 3 testes vermelhos. Aceite em JP: 13 de 13 células em centavos. |
| ~~**C7**~~ | **ENCERRADA em 2026-09-04** pela mesma change. `L29` não declara `previsao_inicial` — zero de 25 entes publicam essa coluna. B6 restringida. | `L27.previsao_inicial` = 12.000.000,00, batendo com o STN. |
| ~~**C6**~~ | **ENCERRADA em 2026-09-04** pela change `ipc07-b1-remocao-termo-5313`. O PO decidiu que `5.3.1.3.0.00.00` foi descontinuada e o conteúdo está em `5.3.1.2`, já primeiro termo da mesma fórmula — o termo saiu da regra e não há mais conta ausente do PCASP em coluna de valor. **Não foi preciso alterar o schema.** `natureza_saldo` perdeu o único caso de uso e saiu do domínio: o mecanismo nunca funcionava de ponta a ponta, porque `saldo.py:109` rejeitava o registro mesmo com a direção declarada. | Fechou `test_excecao_historica_usa_a_natureza_declarada` — a suíte foi de 4 para 3 vermelhos. |

## 4. REVIEW

- [x] 4.1 Nenhuma heurística de sinal por classe ou prefixo no diff.
- [x] 4.2 Nenhum `0` no lugar de célula não apurada.
- [x] 4.3 Núcleo sem import de `requests`, `pandas` ou `yaml`.
- [x] 4.4 Nenhuma conta ou regra fora do que a change `ipc07-bo-regras-canonicas` entregou.
- [x] 4.5 Nenhuma chamada que carregue regra sem receber o exercício.
- [x] 4.6 A apuração devolve procedência e diagnóstico — não só valores.

Verificado em 2026-09-04: núcleo sem `requests`/`pandas`/`yaml`/`sqlalchemy`/`fastapi`; direção do
saldo vem do marcador `(-)` do PCASP, não de classe contábil; os únicos literais `0` em
`domain/bo/` são estados do DFS de `matriz.py`, não células; `carregador.carregar(exercicio, ...)`
exige o exercício na assinatura; a saída traz `procedencia` (documento, edição, `versao_regras`,
hashes das 7 tabelas STN) e `diagnostico` (`nao_apuradas` com motivo, `residuos`, `duracao_ms`,
`sem_dados`).

## 5. VERIFY

- [x] 5.1 `python -m pytest` → **134 passed / 4 failed**. As 4 falhas são C5 (3) e C6 (1).
- [x] 5.2 `python -m ruff check .` → **All checks passed!**
- [x] 5.3 JP 12/2025 apurado em 4.448 ms: **0 células `None`** e **0 resíduos**. As 4 linhas de C5
      (`L25`, `L26`, `L49`, `L50`) saem **sem coluna alguma**, cada uma em `nao_apuradas` com o
      motivo "referências sem coluna em comum … (pendência C5)".
- [x] 5.4 Os 11 valores conferidos pelo código, via `python -m app.cli.bo 2507507 2025 --json`
      contra a API pública: zero diferença. `L40` = 5.314.144.648,00 · 6.043.181.131,90 ·
      4.850.356.845,30 · 4.569.049.735,78 · 4.529.794.533,11; `L16` = 5.301.644.648,00 ·
      5.560.342.799,26; `L27`/`L28`/`L29` previsão atualizada = 482.338.332,64 · 12.000.000,00 ·
      470.338.332,64. A escrituração real de JP em `522130900` compõe a dotação atualizada sem
      ajuste — a ressalva de `tests/bo/test_caso_joao_pessoa.py` está resolvida.
- [x] 5.5 Feito — relatório em `docs/verificacao-5.5-rreo-jp-2025.md`. **123 células comparáveis:
      108 conferem em centavos, 14 divergem só no sinal por convenção do próprio IPC 07, 1
      divergência real de valor** (`L27.previsao_inicial`, registrada como **C7** em § 3ter).

## 6. F2 e F3 — changes próprias

- [x] 6.0 Confirmado e **transferido**: F2 e F3 são trabalho da change `plataforma-pipeline-dca`,
      que especifica ciclo, infra e camadas. Nada de pipeline foi desenhado aqui, e nada nesta
      change bloqueia aquela. Não é tarefa pendente desta change.
- [x] 6.1 Confirmado. `apurar(ente, exercicio, fonte, direcao=None, mapa=None)` é síncrona, sem
      estado e sem I/O próprio: a fonte de MSC, a direção do PCASP e o mapa de regras entram por
      parâmetro (`fonte` é `Protocol`, os outros dois têm default carregado). Devolve `Resultado`
      com `matriz`, `procedencia` e `diagnostico` — serializável. `app/cli/bo.py` já é o terceiro
      chamador, ao lado de rota e worker previstos na F2/F3. Sem reescrita à vista.

## 7. Arquivamento

- [x] 7.1 Atualizado. As três pendências normativas — C5, C6 e C7 — foram encerradas por duas
      changes próprias, e a suíte está verde.
- [x] 7.2 Mesclado: 15 requisitos / **34 cenários** (era 33; `exceção histórica usa a natureza
      declarada` deu lugar a `escrituração em conta descontinuada não apaga a célula`, e
      `exercício deficitário` entrou com a C5).
- [x] 7.3 Movida para `openspec/changes/archive/2026-09-04-bo-quadro-principal-processamento/`.
- [x] 7.4 Atualizada — sai das ativas, entra nas arquivadas.
