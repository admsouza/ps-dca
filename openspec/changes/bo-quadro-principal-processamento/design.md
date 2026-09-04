# Design — Processamento do BO, quadro principal

**Change:** `openspec/changes/bo-quadro-principal-processamento/` · **Aprovada pelo PO em:** 2026-09-04 (Jackson S. da Silva (PO))

## 1. Como as fontes são chamadas

Medido em `regras-rgf-api`. Os dois adapters entregam o **mesmo** conjunto de colunas em
snake_case; quem apura não sabe qual fonte respondeu.

### SICONFI — `app/services/data_sources/siconfi_api.py`

```
GET https://apidatalake.tesouro.gov.br/ords/siconfi/tt/{endpoint}
    ?id_ente=<cod_ibge>&an_referencia=<ano>&me_referencia=<mes>
    &co_tipo_matriz=MSCC&classe_conta=<5|6>&id_tv=ending_balance
    &offset=<n>&limit=5000
```

O endpoint é escolhido pela **classe contábil** (1º dígito da conta) — três matrizes distintas:

| Classes | Endpoint |
|---|---|
| 1, 2, 3, 4 | `msc_patrimonial` |
| **5, 6** | `msc_orcamentaria` |
| 7, 8 | `msc_controle` |

Paginação ORDS obrigatória: blocos de 5.000, seguir `hasMore`/`offset` (entes grandes excedem uma
página). Sem token — API pública.

### PublicSoft — `app/services/data_sources/publicsoft_api.py`

```
GET {PUBLICSOFT_API_URL}/contabilidade-tools/matriz-saldo/base-demonstrativos
    ?anReferencia=<ano>&meReferencia=<mes>&classeConta=<5|6>&idTv=ending_balance
Header: x-authorization: <token do ente>
```

Duas diferenças que o adapter absorve:

1. **Gate de auditoria.** Antes do fetch, `GET …/matriz-saldo/auditorias?exercicio&mesMsc` precisa
   devolver `status == "validado"` **e** `podeGerar == true`. Reprovado → sem dados, não erro.
2. **camelCase.** `codConta`→`conta_contabil`, `naturezaConta`→`natureza_conta`,
   `naturezaReceita`→`natureza_receita`, `poderOrgao`→`poder_orgao`. Resposta em `data[]` ou
   `items[]`.

### Contrato normalizado (o que o apurador consome)

`conta_contabil` · `natureza_conta` (`C`|`D`) · `valor` · `natureza_receita` ·
`natureza_despesa` · `fonte_recursos` · `poder_orgao` · `complemento_fonte`

## 2. Débito, crédito e classe de conta

Três coisas distintas, hoje confundidas com facilidade:

| | O que é | De onde vem |
|---|---|---|
| **`natureza_conta`** do registro | se **aquele lançamento** é C ou D | MSC, por registro |
| **natureza do saldo** da conta | se a conta **acumula** por C ou por D | `PCASP.md`, coluna `NATUREZA DO SALDO`, por conta folha |
| **`operacao`** | como a conta entra na fórmula da célula (`+`/`−`) | IPC 07 |

```
saldo(conta)  = Σ C − Σ D   se a conta é credora
              = Σ D − Σ C   se a conta é devedora
celula        = Σ  operacao × saldo(conta)      (contas da coluna × filtros da linha)
```

`natureza_conta` é a natureza do **saldo do registro**, nunca da conta — derivar a direção dela
inverte sinal (medido em João Pessoa dez/2025: 22 de 323 registros de classe 1 vêm com `C`).

**A direção é resolvida por conta folha, na tabela.** Não pela classe e não pelo prefixo da regra:

| Escopo | Medição no `PCASP.md` | Consequência |
|---|---|---|
| classe 5 | 54 devedoras · **22 credoras** | heurística de classe (RGF) inverte 22 contas |
| classe 6 | 56 credoras · **7 devedoras** | inverte as 7 dedutoras `(-)` |
| prefixo `5.2.1.1` | 4 credoras · 2 devedoras | direção por prefixo declarado inverte 2 |
| prefixo `6.2.1.3` | 1 credora · **5 devedoras** | inverte 5 — são as deduções da receita |

Por isso o algoritmo agrupa os registros pela **conta completa do registro** e resolve cada uma na
tabela. O prefixo do IPC07 serve só para dizer quais contas entram na célula.

Sem natureza na tabela e sem `natureza_saldo` na regra → célula `None` + aviso. Nunca `0`.

**Validado 1:1 em centavos** contra `DCA-Anexo I-C` e `I-D` de João Pessoa 2025 — 8 valores, zero
diferença, incluindo as duas contas dedutoras de classe 6 que a heurística de classe inverteria.
Evidência em [`docs/validacao-bo-jp-2025.md`](../../../docs/validacao-bo-jp-2025.md).

**Casamento de conta é por conta folha declarada, não por prefixo solto.** Medido: o prefixo
`5.2.2.1.3` captura `522139900` (controle paralelo por fonte, bifront) junto com `522130100` (a
conta de `L29`) e infla a coluna em R$ 729.036.483,90.

## 3. `ending_balance` na DCA

Decisão do PO: a DCA lê sempre `id_tv = ending_balance`. O exercício é fechado e todas as colunas
do BO são posição acumulada — previsão, dotação, arrecadado, empenhado, liquidado, pago. Não há
coluna de fluxo do período, então `period_change` não é consultado.

Duas consultas por apuração — classe 5 e classe 6, mesmo mês, mesmo `id_tv`. Ambas caem em
`msc_orcamentaria`.

**Mês 12, `co_tipo_matriz=MSCC`** — decisão do PO em 2026-09-03. Não o mês de encerramento: ali as
contas de controle das classes 5 e 6 são zeradas e o quadro sairia em zero. Confirmado no caso real
de João Pessoa 12/2025 (4.600 registros de classe 5, 4.320 de classe 6, uma página ORDS cada).

## 4. Estrutura

Dependências apontando para dentro. O núcleo não conhece HTTP, pandas nem YAML.

```text
app/
├─ domain/bo/                    # NÚCLEO — puro, sem I/O
│  ├─ modelo.py                  # Registro · ContaCC · Coluna · Linha · MapaBO
│  ├─ portas.py                  # DirecaoSaldo · FonteSaldos          (Protocol)
│  ├─ saldo.py                   # saldo_da_celula(registros, contas, filtros, direcao)
│  └─ matriz.py                  # apurar(mapa, saldos, direcao) -> Matriz   (3 passos, §5)
├─ infra/pcasp/
│  └─ natureza.py                # ADAPTER de DirecaoSaldo: PCASP.md -> {conta: credora|devedora}
├─ infra/msc/
│  ├─ siconfi.py                 # ADAPTER de FonteSaldos: tt/msc_orcamentaria + paginação ORDS
│  ├─ publicsoft.py              # ADAPTER de FonteSaldos: base-demonstrativos + gate auditoria
│  └─ normalizacao.py            # camelCase -> snake_case; contrato único de colunas
├─ infra/regras/
│  └─ carregador.py              # knowledge/rules/bo/*.yaml -> MapaBO
└─ services/bo/
   └─ quadro_principal.py        # ORQUESTRAÇÃO: mapa + fonte + direção -> Matriz
```

Reusado do `regras-rgf-api` sem reescrever: `engine/formula.py` (parser `ast` com whitelist, sem
`eval`) e `engine/dag.py` (ordem topológica). Reescrito: o cálculo de saldo — a regra de direção
muda (§2).

### Contratos

```python
# domain/bo/portas.py
class DirecaoSaldo(Protocol):
    def credora(self, conta: str) -> bool | None: ...   # None = desconhecida -> célula não apurada

class FonteSaldos(Protocol):
    def registros(self, ente: int, ano: int, mes: int, classe: int) -> Sequence[Registro]: ...

# domain/bo/modelo.py
class Registro(NamedTuple):         # já normalizado pelo adapter
    conta: str; natureza: str; valor: Decimal
    natureza_receita: str; natureza_despesa: str; poder_orgao: str; fonte_recursos: str

class ContaCC(NamedTuple):
    cc: str                                    # prefixo do IPC07, sem separadores
    operacao: str = "+"                        # como entra na fórmula
    natureza_saldo: str | None = None          # só p/ exceção histórica fora do PCASP (B1/B3)

class Coluna(NamedTuple):
    id: str; rotulo: str
    contas: tuple[ContaCC, ...] = ()           # coluna lida da matriz
    expressao: str | None = None               # coluna derivada, ex.: saldo = "c - b"

class Linha(NamedTuple):
    id: str; rotulo: str; tipo: str            # expressao_cc | soma_filhas
    filtros: Filtros
    referencias: tuple[Ref, ...] = ()
    contas_da_linha: tuple[ContaCC, ...] = ()  # B5: override em L29/L30 — substitui as da coluna
    colunas: tuple[str, ...] = ()              # B6: vazio = linha sem coluna de valor (L51)
```

## 5. Fluxo

```
services/bo/quadro_principal.apurar(ente, ano, mes, fonte)
  1. MapaBO  <- carregador.carregar(exercicio=ano)     # regra vigente p/ o exercício (P8)
  2. saldos  <- fonte.registros(classe=5) + fonte.registros(classe=6)     # ending_balance
  3. direcao <- natureza.do_pcasp("docs/contas-stn/PCASP.md")             # 1x, em cache
  4. matriz  <- domain.matriz.apurar(mapa, saldos, direcao)
       (a) células = contas da coluna × filtros da linha; override de linha em L29/L30
       (b) agregações `soma_filhas`, coluna a coluna, em ordem topológica
       (c) colunas derivadas por linha (`saldo = c - b`), em ordem topológica
  5. -> Matriz{valores, avisos, nao_apuradas, residuos, procedencia, duracao}   # P9
```

Derivadas **depois** das agregações mantém `saldo = c − b` verdadeira também nos totais, por
construção — não por conferência posterior.

## 6. Decisões

**D1 — Direção do saldo vem da tabela, por conta folha.**
Descartado: heurística por classe (o RGF faz assim); direção declarada por prefixo na regra.
Porquê: medido — a heurística de classe erra 29 contas das classes 5/6, e a direção por prefixo
erra 7 contas só nos prefixos `5.2.1.1` e `6.2.1.3` do exemplo do item 23 do IPC07. A tabela
oficial tem o dado por conta; inferir onde há dado é escolher errar.

**D2 — Núcleo sem pandas.**
Descartado: DataFrame no domínio, como no RGF.
Porquê: o quadro principal agrupa por conta e soma — dois `dict`. A MSC orçamentária de um
município cabe em memória com folga, e o núcleo fica testável com uma lista literal de registros,
sem fixture de DataFrame. `Decimal`, não `float`: o aceite da DCA é 1:1 em centavos.

**D3 — Célula não apurada é `None`, com aviso.**
Descartado: `0` quando a natureza é desconhecida.
Porquê: `0` é um valor legítimo do demonstrativo — usá-lo para "não sei" apaga a diferença entre
conta sem escrituração e conta sem direção conhecida. Herdado do `FiltroInclusaoIndisponivel` do
RGF, onde a mesma escolha já está validada.

**D4 — Um adapter por fonte, atrás da mesma porta.**
Porquê: o gate de auditoria da PublicSoft e a paginação ORDS do SICONFI são detalhes de transporte.
O apurador recebe registros normalizados e não muda quando a fonte muda.

**D5 — Só o quadro principal.**
Porquê: os 3 quadros do IPC07 têm colunas diferentes. O motor matricial é o mesmo; provar com um
quadro é o menor recorte que valida a estrutura inteira.

**D6 — Núcleo antes de infra, mas a DCA nasce para ser pipeline (F1 → F2 → F3).**
A DCA é o **terceiro pipeline** da casa, ao lado do RREO e do RGF: mesma forma final — rota
enfileira job, worker apura, resultado vai para cache em Postgres, registry lista os anexos ativos e
um resumo agregado responde ao front (`app/utils/rgf_pipeline_registry.py` e
`services/cache_rgf/resumo.py` no RGF). F3 não é hipótese: é destino.

O que muda é só a **ordem**, e por uma razão: o aceite desta change são 11 valores em centavos, e
nenhum precisa de fila, banco ou rota — a F1 é verificável por CLI. Adiar a infra encurta o ciclo de
verificação do núcleo; não a dispensa.

Duas consequências que a F1 tem de respeitar desde já, para a F3 não pedir reescrita:

1. `services/bo/quadro_principal.apurar(...)` é **síncrono, puro e sem estado** — a mesma chamada
   serve à rota, ao worker e ao CLI. Nada de `Depends`, sessão de banco ou `await` no service.
2. A identidade do resultado é `(ente, exercício, anexo, versão das regras)` — a mesma chave que
   vira PK da tabela de cache e critério de invalidação na F3. O apurador devolve essa identidade
   junto com a matriz, ainda que ninguém a persista na F1.

Descartado: subir FastAPI + ARQ/Redis + Postgres junto com o núcleo, como está hoje no
`regras-rgf-api`. Fases e o que reusar do RGF em `tasks.md` › "Ordem de execução".

## 7. Pendências

- C1, C2 e C3 **resolvidos** — ver `proposal.md` e a evidência em
  `docs/validacao-bo-jp-2025.md`.
- Depende de `ipc07-bo-regras-canonicas` entregar as 51 regras do quadro principal.
- **C4 — resolvido pelo PO em 2026-09-04: o Balanço Orçamentário fica no `ps-dca`.**
  Levantamento em
  [`docs/anexos-siconfi-inventario.md`](../../../docs/anexos-siconfi-inventario.md): os 7 anexos da
  DCA (o universo completo — 2.002 registros, nenhum oitavo anexo existe) publicam posição e
  execução realizada, nunca previsão ou dotação. O `RREO-Anexo 01` é demonstrativo do **RREO** e
  pertence ao `regras-rreo-api`; aqui ele entra apenas como **gabarito de validação** das colunas
  de previsão e dotação, nunca como escopo de publicação. O quadro principal do IPC 07 é apurado
  neste repositório a partir da MSC.

- Delta spec escrito em `specs/dca/balanco-orcamentario/spec.md` e **aprovado pelo PO em 2026-09-04**
  (task 0.12). Fase SPEC fechada; nenhuma pendência de conteúdo.
