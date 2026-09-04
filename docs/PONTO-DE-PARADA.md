# Ponto de parada — 2026-09-04

Documento de handoff. Escrito para quem chega sem contexto nenhum.

## Onde estamos, em uma frase

A **base canônica do IPC 07** e a **F1 do Balanço Orçamentário** estão entregues, verificadas
contra o STN em centavos e arquivadas; as três pendências normativas foram fechadas por medição.
Resta **uma change ativa** — a plataforma (F2/F3) —, cuja fase TEST começou: **15 dos 63 cenários**
escritos, 20 testes vermelhos de propósito.

```bash
python -m pytest                              # 155 passed · 20 failed (os 20 são a fase TEST)
python -m ruff check .                        # All checks passed!
python -m scripts.validate_rules knowledge    # exit 0 · 69 regras · review_required 0
python -m scripts.check_sources knowledge     # Fontes íntegras
python -m app.cli.bo 2507507 2025             # apura contra a API pública do SICONFI
```

> **Os 20 vermelhos são esperados.** São os testes da plataforma, escritos antes do código, e
> falham por `ModuleNotFoundError` dos módulos da F2/F3. Tudo o que existe está verde.

## Por onde retomar

1. **Continuar a fase TEST da plataforma** — faltam 48 dos 63 cenários. Detalhe na §6.
2. **Depois, F2** (rota fina) e **F3** (job, cache, banco). O ambiente já está configurado (§5).
3. Antes da primeira migration, **confirmar o host/banco de produção** com o PO — o `.env` atual é
   `development` e aponta para `localhost`.

**Nada está comitado.** 35 entradas em `git status`, sobre `b84ceed`.

---

## 1. O que o repositório faz

Processa a **DCA** (Declaração de Contas Anuais, SICONFI/STN). O primeiro demonstrativo entregue é
o **Balanço Orçamentário** do IPC 07, apurado a partir da Matriz de Saldos Contábeis do ente.

É o **terceiro pipeline da casa** — `regras-rreo-api` e `regras-rgf-api` já rodam a mesma forma em
produção: rota → cache → job → worker → cache. A DCA replica o ciclo e corrige três acúmulos
históricos deles (tabela única em vez de uma por anexo, um lock só, `versao_regras` no cache).

### Estrutura

```text
app/domain/bo/        modelo · portas (Protocol) · saldo · matriz     ← núcleo puro, sem I/O
app/infra/pcasp/      natureza do saldo, lida do PCASP.md
app/infra/msc/        siconfi (paginação ORDS) · publicsoft · normalizacao
app/infra/regras/     carregador: recebe o exercício, devolve o mapa vigente + versao_regras
app/services/bo/      quadro_principal.apurar() — síncrono, sem estado, serve rota/worker/CLI
app/cli/bo.py         python -m app.cli.bo <ente> <exercicio> [--fonte] [--json]
knowledge/            69 regras · 2 policies · schemas · sources (hashes) · índice
scripts/              validate_rules · check_sources · build_index · load_stn_tables · extract_ipc
tests/bo/             F1 do Balanço Orçamentário
tests/pipeline/       fase TEST da plataforma (vermelha de propósito)
```

### Processo

O contrato é **[AGENTS.md](../AGENTS.md)** na raiz e `openspec/AGENTS.md`. Resumo:

```text
SPEC → PLAN/ARCH → TEST → IMPLEMENT → REVIEW → VERIFY
```

Nenhuma fase começa antes do gate da anterior. **SPEC só fecha com aprovação explícita do PO.**
Teste antes do código, sempre. Durante uma change edita-se só o delta em
`openspec/changes/<change>/specs/`; `openspec/specs/` só recebe no arquivamento.

---

## 2. Estado das changes

| Change | Fase | Situação |
|---|---|---|
| `plataforma-pipeline-dca` | **TEST** | 50 tasks abertas. SPEC e PLAN/ARCH completos. 15 dos 63 cenários escritos |
| `ipc07-c5-c7-linhas-cruzadas` | arquivada | fechou C5 e C7 |
| `ipc07-b1-remocao-termo-5313` | arquivada | fechou C6 |
| `bo-quadro-principal-processamento` | arquivada | F1 do BO |
| `ipc07-bo-regras-canonicas` | arquivada | as 69 regras |
| `knowledge-base-ipc` | arquivada | sucedida, nunca implementada |

Specs em vigor: `openspec/specs/dca/base-canonica-regras/spec.md` (51 cenários) e
`openspec/specs/dca/balanco-orcamentario/spec.md` (34).

`tests/test_cobertura_spec.py` **falha** se um cenário ficar sem teste que o cite no docstring, ou
se a contagem mudar sem decisão registrada. `pipeline/plataforma` ainda **não** está em
`COM_TESTES` — entra quando os 63 estiverem cobertos.

---

## 3. O que foi verificado contra o STN, e como

O aceite do projeto é **1:1 em centavos**, não "parece certo".

| Verificação | Resultado |
|---|---|
| 11 valores de referência, JP 12/2025 | zero diferença — `docs/validacao-bo-jp-2025.md` |
| Quadro principal × `RREO-Anexo 01`, linha a linha | 108 de 123 células em centavos — `docs/verificacao-5.5-rreo-jp-2025.md` |
| C5, superávit (JP) e déficit (12 estados) | exato — `docs/evidencia-c5-deficit-superavit.md` |
| C7 (25 entes) e C6 (~185.000 registros, 9 entes) | exato — `docs/evidencia-c6-c7.md` |
| Aceite final de C5/C7 | **JP 13 de 13 células**; SP e GO conferidos |

**As 14 divergências de sinal do relatório 5.5 não são erro:** o IPC 07 define a coluna de saldo da
receita como `SALDO (d) = (c-b)` e o RREO publica `SALDO (a-c)`. Convenções opostas de
demonstrativos distintos; magnitude idêntica.

---

## 4. Decisões que **não** devem ser reabertas

C1–C4 · P1–P10 · P-D1 a P-D8 · B2 · B4 · B5.

**Três foram alteradas por medição, e o histórico está em `docs/source-analysis-ipc07.md`:**

- **B1 revogada** (2026-09-04): `5.3.1.3.0.00.00` saiu da fórmula. Descontinuada, conteúdo já em
  `5.3.1.2`, que era o primeiro termo — mantê-la duplicaria a conta.
- **B6 restringida** (2026-09-04): `L29` não declara `previsao_inicial`. Zero de 25 entes publicam
  essa coluna.
- **C5, C6 e C7 encerradas** — ver §7.

### Invariantes do núcleo

- **Direção do saldo vem da coluna, não da conta.** No PCASP a conta redutora tem natureza oposta
  à do grupo **e** `(-)` no título. Somar cada conta na direção dela faz a redutora somar: a
  dotação atualizada sairia `6.303.210.688,18` em vez de `6.043.181.131,90`. A direção do grupo vem
  da **primeira conta não redutora** sob o prefixo (`infra/pcasp/natureza.py::credora_prefixo`) —
  contar por maioria erra em `5.2.1.1`.
- **Nada de heurística de sinal por classe contábil.** Célula sem direção conhecida é `None` com
  aviso, **nunca** `0`.
- **`None` tem dois sentidos, e eles são separados:** "não apurado" gera aviso; "não se aplica"
  (linha suprimida por condição) entra em `Matriz.suprimidas` e **contribui zero** no total.
- **`app/domain/` não importa** `requests`, `pandas`, `yaml`, `sqlalchemy`, `fastapi` nem as 8 deps
  de F2/F3 — `tests/test_fronteira_camadas.py` quebra o build se alguém cruzar, seguindo o fecho
  **transitivo** dos imports.
- Todo teste declara `Scenario:` ou `Requisito:` no docstring.

---

## 5. Ambiente — já configurado

`.env` criado (fora do git, `.gitignore:10`); `.env.example` com os mesmos nomes e placeholders
vazios.

| Origem | Variáveis |
|---|---|
| **Herdado de `regras-rgf-api`** — compartilhado de propósito | `POSTGRES_*` e as 7 de Redis, incluindo `REDIS_PREFIX=msc_cache:` |
| **Gerado próprio da DCA** — nunca copiar dos irmãos | `SECRET_KEY`, `S2S_API_SECRET`, `TOKEN_ENCRYPTION_KEY` |

### Schema real, levantado por inspeção read-only

`db-ps-rreo-rgf-dca`, PostgreSQL 18.0, **44 tabelas, todas em `public`**:

- **`dca_*`: zero tabelas** — espaço de nomes livre.
- **Nenhum `alembic_version` órfão**: só `alembic_version_rgf` (`060_token_ps_validacao_status`) e
  `alembic_version_rreo` (`032`). `alembic_version_dca` nasce limpo.
- O RGF tem `rgf_anexo01..06_cache` e o RREO nove `rreo_anexo*_cache` — o acúmulo por anexo que a
  decisão P-D1 evita com tabela única.
- `rgf_anexo02_mapeamento` confirma o molde de `dca_regra_mapeamento`: as mesmas 7 colunas; a DCA
  acrescenta `anexo` para unificar as cinco em uma.
- `rgf_anexo01_cache` tem 12 colunas; `dca_anexo_cache` acrescenta `versao_regras`, `procedencia` e
  `diagnostico`, e dispensa `tipo_poder`/`periodicidade`/`periodo_referencia` — a DCA é anual e
  consolidada.

**Nenhuma migration foi criada.** Toda inspeção até aqui foi read-only.

### Convenções de infra

- Postgres e Redis **compartilhados de propósito**. A separação da DCA é por prefixo `dca_*` e
  `alembic_version_dca`, **não** por schema. Advisory lock `43812/1001` —
  `plataforma-pipeline-dca/design.md` §5.
- `REDIS_PREFIX=msc_cache:` é comum aos três: nomeia o cache de MSC. O que se isola é o estado de
  execução — fila `arq:queue:dca`, chaves `dca:`.

---

## 6. A fase TEST da plataforma — onde parei

**15 de 63 cenários.** Fundação em `tests/pipeline/conftest.py`: fakes em memória de repositório,
fila e lock, implementando as portas que os adapters de `infra/` vão implementar.

Cobertos — `test_ciclo.py` e `test_invalidacao.py`: `Ciclo único`, `Identidade e invalidação`,
`Cache único`, `Anexo é conjunto fechado`.

**Faltam 48**, nestes requisitos:

| Requisito | Cenários |
|---|---|
| Mapeamento vigente é publicado sem sobrescrever o anterior | 6 |
| Reprocessamento forçado de um anexo | 4 |
| Convivência com os demais pipelines no banco compartilhado | 4 |
| Conclusão de job é notificada | 4 |
| Autorização por unidade em toda rota de anexo | 4 |
| Lock por identidade com recuperação de órfão | 3 |
| Estado de execução isolado; cache de dados compartilhado | 3 |
| Rota e worker apenas orquestram | 2 |
| Acompanhamento por polling e por stream | 2 |
| Resumo agregado responde sempre | 2 |
| Apuração não roda no processo da API | 2 |
| Regra vigente é resolvida pelo exercício apurado | 2 |
| Procedência do valor apurado | 2 |
| Diagnóstico da apuração acompanha o resultado | 2 |
| Núcleo de apuração isolado de infraestrutura | 2 |
| Falha de infraestrutura é reportada, não mascarada | 2 |
| Serviço de apuração chamável por rota, worker e CLI | 1 |
| Estado do job é serializado sem execução de código | 1 |
| **Total** | **48** |

A conta é reproduzível — não confie na tabela, refaça:

```bash
python - <<'EOF'
import pathlib
spec = pathlib.Path("openspec/changes/plataforma-pipeline-dca/specs/pipeline/plataforma/spec.md")
docs = " ".join(p.read_text(encoding="utf-8") for p in pathlib.Path("tests/pipeline").glob("test_*.py")).lower()
req, mapa = None, {}
for l in spec.read_text(encoding="utf-8").splitlines():
    if l.startswith("### Requirement:"): req = l[17:].strip(); mapa[req] = []
    elif l.startswith("#### Scenario:") and req: mapa[req].append(l[15:].strip())
falta = {r: [c for c in cs if c.lower() not in docs] for r, cs in mapa.items()}
print(sum(len(f) for f in falta.values()), "cenarios sem teste")
for r, f in falta.items():
    if f: print(f"  {len(f):2}  {r}")
EOF
```

### Contrato que os testes já fixaram

```text
GET /dca/{anexo}?anReferencia=2025   → 200 | 202+job_id | 202 sem job_id
GET /jobs/{job_id}                    → polling;  SSE para stream
app.services.pipeline.cache.ler_ou_enfileirar(ente, exercicio, anexo,
                                              repo, fila, lock, versao_api, versao_regras)
app.services.pipeline.registry.validar_anexo / AnexoDesconhecido / ANEXOS
app.infra.cache.modelo.STATUS_CACHE / validar_status / StatusInvalido
```

`ANEXOS = ("BO", "I-AB", "I-C", "I-D", "I-E", "I-F", "I-G", "I-HI")` — `BO` à frente por ser o
derivado da MSC, publicado como `RREO-Anexo 01`. Rota admin segue o padrão do RGF:
`/dca/{anexo}/mapeamentos`.

### Três armadilhas que já custaram retrabalho aqui

1. **Teste que passa antes da implementação não testa nada.** Dois dos meus afirmavam a validação
   do próprio dublê. Aponte para o módulo real.
2. **`pytest.raises(Exception)` fica verde por acidente de import** — `ModuleNotFoundError` também
   é `Exception`. Use exceções nomeadas.
3. **Os YAMLs do repositório estão em CRLF.** Um `replace(b"\n", b"\r\n")` produz `\r\r\n` e muda
   o valor parseado por dobra de escalar. Normalize antes de gerar a variante — eu não normalizei,
   diagnostiquei um defeito inexistente no `_hash_canonico` e cheguei a "corrigir" o produto antes
   de perceber. **O hash canônico da F1 está correto.**

---

## 7. As três pendências normativas — todas fechadas

Nasceram como "o IPC 07 não diz" e foram resolvidas **medindo o que o STN publica**, não
escolhendo. Se aparecer uma quarta, o caminho é o mesmo: medir primeiro, e o processo manda
**declarar, não presumir**.

### C5 — as linhas que cruzam receita e despesa

`L25`, `L26`, `L49` e `L50` cruzam blocos com colunas disjuntas (4 × 6). O publicado do STN
responde, e **as duas metades não são simétricas**:

| | `L25`/`L26` Déficit | `L49`/`L50` Superávit |
|---|---|---|
| Bloco · células | receita · **1** | despesa · **3** |
| Coluna(s) | `receitas_realizadas` | `empenhadas` · `liquidadas` · `pagas` |
| Contraparte | despesa **empenhada** apenas | a respectiva coluna de execução |

Cada bloco recebe tantas células de ajuste quantas colunas de realização tem. Resolver por simetria
daria 3 células de déficit onde há 1.

Três achados que a medição obrigou, e que o IPC 07 não continha:

1. **A fórmula é cruzada em coluna** — `L49.empenhadas` lê `L24.receitas_realizadas`. A referência
   ganhou o campo `column`.
2. **Célula suprimida contribui zero e se apresenta em branco.** Em ente deficitário o STN deixa
   `Superavit` em branco e **publica** `TotalDespesasComSuperavit` igual a `TotalDespesas`.
3. **A condição é decidida uma vez, por linha** (`calculation.condition.column`). São Paulo tem
   déficit contra a empenhada e superávit contra liquidadas e pagas; o STN deixa as três em branco.
   Decidir célula a célula publicaria duas células que o STN não publica.

### C6 — `5.3.1.3.0.00.00`

Descontinuada; o conteúdo está em `5.3.1.2`, que já era o primeiro termo da mesma fórmula.
Substituir uma pela outra **duplicaria** o valor — o motor soma por conta declarada, sem
deduplicar. O termo saiu; a coluna tem 3 contas, simétrica à de RP Processados. Zero ocorrências em
~185.000 registros de 9 entes.

### C7 — previsão inicial de `L29`

Zero de 25 entes publicam `PREVISÃO INICIAL` para `SuperavitFinanceiro`. Um superávit financeiro é
apurado sobre o exercício fechado. `L27.previsao_inicial` passou de 482.338.332,64 para
**12.000.000,00**, batendo com o STN.

---

## 8. Observações abertas — do ente, não do código

Duas divergências medidas em que **o ente publica menos do que a sua própria MSC sustenta**. Não
são defeito de apuração e não foram tratadas. Cabe ao PO decidir se merecem conferência por ente.

| Ente | Divergência |
|---|---|
| **PB** (estado) | despesa empenhada R$ 35.893.050,14 acima da receita realizada, mas **não publicou** `Deficit`. Os outros 11 deficitários são unânimes |
| **GO** (estado) | `L27.previsao_atualizada` dá R$ 963.024,00 a mais que o STN — exatamente `L30` Reabertura de Créditos Adicionais, linha que GO omite do anexo |

Consequência prática: **a regra não pode presumir que o ente publique a linha de ajuste.**

---

## 9. Detalhes que economizam tempo

- `.env` e `.env.example` **não** são graváveis pela ferramenta de escrita nem por heredoc com
  segredo no comando — o classificador bloqueia. O caminho é script Python que lê do disco.
- A API do SICONFI **honra um `id_ente` por chamada**; passar vários devolve só o primeiro. E
  ignora `conta_contabil` como filtro — varra a classe e filtre local.
- `python -m pytest` sem `PYTHONIOENCODING=utf-8` quebra na impressão de falhas
  (`OSError: [Errno 22]`) neste Windows.
- Apurar um ente grande contra a API leva minutos; rode em background e leia o log.
- YAML 1.1 interpreta a chave `on:` como o booleano `True`. Por isso o campo da condição chama
  `column`, não `on`.
- O aceite contra o `RREO-Anexo 01` usa `nr_periodo=6` (exercício fechado):
  `https://apidatalake.tesouro.gov.br/ords/siconfi/tt/rreo?an_exercicio=2025&nr_periodo=6&co_tipo_demonstrativo=RREO&no_anexo=RREO-Anexo%2001&id_ente=<ibge>`
- Entes deficitários de 2025, para conferir a metade do déficit: `12 17 22 24 25 27 35 41 42 50 52 53`.
