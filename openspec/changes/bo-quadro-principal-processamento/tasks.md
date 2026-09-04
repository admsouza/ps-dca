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
- [ ] 1.2 Confirmar as dependências da F1: runtime `pyyaml` + `requests`; dev `pytest`, `ruff`. Sem
      pandas no núcleo (D2). FastAPI é F2; `arq`, `redis`, `sqlmodel` e `alembic` são F3.
- [ ] 1.3 Esqueleto mínimo da F1: `docker-compose.yml` com o app na rede externa `ps-infra`,
      `.env.example`, `ruff.toml`, `pytest.ini`. Sem serviço de banco e sem worker.

## 2. TEST — antes do código

- [ ] 2.1 Traduzir cada cenário do delta spec em teste de comportamento.
- [ ] 2.2 Fixture do exemplo documental do IPC07 p. 8 (`L2` — Impostos, Taxas e Contribuições de
      Melhoria) com registros literais, cobrindo conta credora, conta devedora e coluna derivada.
- [ ] 2.3 Teste que falha se a direção do saldo passar a ser inferida da classe ou do prefixo —
      ancorado em `621310100`/`621390000`, que a heurística de classe inverte.
- [ ] 2.4 Teste que falha se `522139900` entrar na coluna de `L29` por casamento de prefixo.
- [ ] 2.5 Teste de vigência: o carregador recebe o exercício; exercício sem vigência falha
      nomeando as disponíveis.
- [ ] 2.6 Teste de procedência e diagnóstico: o resultado identifica edição do IPC, versão das
      tabelas STN e as células não apuradas.
- [ ] 2.7 Rodar e confirmar que falham pelo motivo esperado.

## 3. IMPLEMENT — F1 (núcleo)

- [ ] 3.1 `domain/bo/modelo.py` e `portas.py` — contratos, sem I/O.
- [ ] 3.2 `infra/pcasp/natureza.py` — direção por conta folha, lida da tabela.
- [ ] 3.3 `domain/bo/saldo.py` — saldo da célula com direção injetada.
- [ ] 3.4 `domain/bo/matriz.py` — os 3 passos, reusando `formula` e `dag` do RGF.
- [ ] 3.5 `infra/msc/` — os dois adapters e a normalização de colunas.
- [ ] 3.6 `infra/regras/carregador.py` — recebe o **exercício** e devolve o mapa vigente (P8 da
      change de plataforma). Na F1 a implementação é de YAML; na F3 entra a de banco
      (`dca_regra_mapeamento`, P10) atrás da mesma porta, e o YAML fica como seed e fixture. E
      `services/bo/quadro_principal.py`, que devolve matriz + procedência + diagnóstico (P9).
- [ ] 3.7 CLI `python -m app.cli.bo <ente> <ano>` — apura e imprime a matriz. É o que roda a
      verificação 5.3–5.5 sem depender de rota nem de banco.

## 4. REVIEW

- [ ] 4.1 Nenhuma heurística de sinal por classe ou prefixo no diff.
- [ ] 4.2 Nenhum `0` no lugar de célula não apurada.
- [ ] 4.3 Núcleo sem import de `requests`, `pandas` ou `yaml`.
- [ ] 4.4 Nenhuma conta ou regra fora do que a change `ipc07-bo-regras-canonicas` entregou.
- [ ] 4.5 Nenhuma chamada que carregue regra sem receber o exercício.
- [ ] 4.6 A apuração devolve procedência e diagnóstico — não só valores.

## 5. VERIFY

- [ ] 5.1 `python -m pytest` — reportar `N passed / M failed`.
- [ ] 5.2 `python -m ruff check .` — reportar resultado real.
- [ ] 5.3 Apurar o quadro principal de JP 12/2025 e reportar quantas células saíram `None`, com o
      motivo de cada uma.
- [ ] 5.4 Reconferir os 11 valores de `docs/validacao-bo-jp-2025.md` pelo código, não por script
      de análise.
- [ ] 5.5 Apurar o quadro principal completo e conferir contra `RREO-Anexo 01` de JP 2025, linha a
      linha, reportando cada divergência.

## 6. F2 e F3 — changes próprias

- [ ] 6.0 F2 e F3 são implementadas conforme a change `plataforma-pipeline-dca`, que especifica o
      ciclo, a infra e a organização em camadas. Não desenhar pipeline aqui.
- [ ] 6.1 Ao fim da F1, confirmar que `services/bo/quadro_principal.apurar(...)` satisfaz o
      requisito "serviço chamável por rota, worker e CLI" daquele delta spec — é o que evita
      reescrita na F2.

## 7. Arquivamento

- [ ] 7.1 `tasks.md` 100% atualizado.
- [ ] 7.2 Mesclar o delta em `openspec/specs/dca/balanco-orcamentario/spec.md`.
- [ ] 7.3 Mover para `openspec/changes/archive/AAAA-MM-DD-bo-quadro-principal-processamento/`.
- [ ] 7.4 Atualizar a tabela "Change ativa" em `openspec/AGENTS.md`.
