# Design — Apuração do Balanço Financeiro (F1)

**Change:** `openspec/changes/bf-apuracao-f1/` · **Proposal aprovada pelo PO em:** ____

## Contexto

A F1 do BO entregou um núcleo puro que já é genérico em quase tudo: `Linha`, `Coluna`, `Filtro`,
`Registro`, o motor de matriz em três passos (células → agregações → derivadas) e o cálculo de
saldo por direção do PCASP. O que amarra esse núcleo ao BO são três coisas, e só três: o nome do
pacote (`app/domain/bo/`), o tipo `MapaBO` e o caminho fixo `rules/bo` no carregador.

O IPC 06 pede três capacidades novas, todas na borda do núcleo:

| Capacidade | Onde entra | Por que não dá para improvisar |
|---|---|---|
| Fonte de recursos | `saldo._campo` e `saldo._casa` | `fonte_recurso` (regra) × `fonte_recursos` (registro) e prefixo de exercício: hoje o casamento falha **em silêncio**, zerando 22 linhas |
| Saldo em data | porta `FonteSaldos` + adapters MSC | `id_tv` está fixo em `ending_balance` no adapter |
| Sentido do movimento | `saldo.saldo_da_celula` | saldo acumulado não separa crédito de débito |

## Componentes afetados

| Componente | Papel na change |
|---|---|
| `app/domain/nucleo/` (ex-`app/domain/bo/`) | motor único: modelo, saldo, matriz, portas |
| `app/domain/nucleo/saldo.py` | campo `fonte_recurso`, normalização da fonte, filtro por movimento |
| `app/domain/nucleo/portas.py` | `FonteSaldos.registros(..., tipo_valor)` |
| `app/domain/nucleo/modelo.py` | `MapaBO` → `Mapa`; `Coluna.movimento`; `ContaCC.saldo` |
| `app/infra/regras/carregador.py` | `carregar(exercicio, demonstrativo)`; hoje fixo em `rules/bo` |
| `app/infra/msc/siconfi.py`, `publicsoft.py` | `id_tv` parametrizado; classes 1–6 |
| `app/services/bf/quadro_principal.py` | orquestração do BF, espelhando a do BO |
| `app/services/pipeline/resultado.py` | ordem de apresentação do BF (2 quadros, 2 grupos) |
| `app/cli/bf.py` | CLI de verificação sem rota nem banco |

## Fluxo da informação

```text
carregar(exercicio, "bf") ──► Mapa (80 linhas)
                                  │
MSC (classes 1-6, 2 exercícios, 3 tipos de valor) ──► [Registro] ──► apurar() ──► Matriz
                                                                          │
                                                      procedência + diagnóstico + template
```

As leituras da MSC que o BF precisa, por tipo de valor:

| Leitura | Para quê | Classes |
|---|---|---|
| `MSCE`/abertura, exercício apurado | execução orçamentária, transferências, RP, `L63`–`L65` | 1–6 |
| `MSCE`/abertura, **exercício anterior** | `L30`–`L32` (saldo do exercício anterior) | 1, 2 |
| variação do período | `L27` e `L60` (movimento credor/devedor) | 2 |

## Contratos / interfaces

```python
# app/domain/nucleo/portas.py
class FonteSaldos(Protocol):
    def registros(self, ente: int, ano: int, mes: int, classe: int,
                  tipo_valor: str = "final") -> Sequence[Registro]: ...
```

`tipo_valor` é vocabulário do domínio (`inicial` | `final` | `periodo`); cada adapter traduz para o
que sua API usa (`beginning_balance` | `ending_balance` | `period_change` no SICONFI). O domínio
não conhece `id_tv`.

```python
# app/domain/nucleo/modelo.py
class ContaCC(NamedTuple):
    cc: str
    operacao: str = "+"
    saldo: str | None = None        # inicial | final — IPC 06, L30-L32 e L63-L65

class Coluna(NamedTuple):
    ...
    movimento: str | None = None    # credor | devedor — IPC 06, L27 e L60
```

Normalização da fonte (G1):

```python
def codigo_principal(fonte: str) -> str:
    """'1500' -> '500'; '1540000123' -> '540'; '500' -> '' (sem prefixo: não classificada)."""
    digitos = "".join(c for c in fonte if c.isdigit())
    return digitos[1:4] if len(digitos) >= 4 else ""
```

Casamento por **igualdade** do código principal, não por prefixo: `startswith` faria `540` casar
com `5400`, e `500` nunca casar com `1500`.

## Impacto

| Eixo | Impacto |
|---|---|
| Banco / migration | nenhum na F1 |
| Cache | nenhum na F1; o `versao_regras` do BF é próprio. **A chave precisará do mês** (G10) — sem ele, resultado mensal e anual colidem na mesma entrada |
| Filas / worker | nenhum na F1 |
| APIs externas | SICONFI e PublicSoft: 6 classes × até 3 tipos de valor × 2 exercícios — **medido: ~45 s**, maior resposta 6.202 regs. Exige **retry com backoff**: 2 de ~40 chamadas caíram por reset de conexão |
| Regressão | apuração do BO **bit a bit igual**; `import app.domain.bo` deixa de existir e todo teste do BO passa a importar `app.domain.nucleo` |

## Decisões

### D1 — Motor único em `app/domain/nucleo/`, com renomeação mecânica
**Escolhido:** renomear `app/domain/bo/` → `app/domain/nucleo/` e `MapaBO` → `Mapa` ·
**Descartado:** duplicar o motor em `app/domain/bf/`, ou o BF importar de `app/domain/bo/` ·
**Porquê:** duplicar são ~500 linhas que divergem no primeiro bug corrigido de um lado só; importar
`MapaBO` dentro do BF deixa o nome mentindo sobre o que a estrutura é. A renomeação é mecânica e
está coberta pelos 287 testes atuais — se algo quebrar, quebra em vermelho, não em silêncio.

### D2 — `tipo_valor` como vocabulário do domínio, traduzido no adapter
**Escolhido:** `inicial | final | periodo` na porta · **Descartado:** passar `id_tv` cru ·
**Porquê:** `id_tv` é nome da API do SICONFI; a PublicSoft usa outro. Vazar o nome da API para o
domínio obrigaria o núcleo a conhecer a fonte — o oposto do que as portas existem para evitar.

### D3 — Movimento filtrado no cálculo da célula, não no adapter
**Escolhido:** a coluna declara `movimento` e `saldo_da_celula` soma só os registros daquele
sentido · **Descartado:** o adapter devolver dois conjuntos separados · **Porquê:** o sentido é
propriedade da **regra** (IPC 06 L27/L60), não da fonte; decidir na fonte espalharia norma pela
infraestrutura.

### D4a — Direção do saldo por conta no BF (G7)
**Escolhido:** no BF, cada conta declarada é tomada na direção da **própria conta**; o BO mantém a
direção da coluna · **Descartado:** unificar os dois critérios · **Porquê:** medido — com a direção
de coluna, `L1` sai 5.872.854.713,27; por conta, 5.117.875.296,33, que é exatamente o publicado no
I-C. No IPC 07 a redutora não traz sinal na regra e entra subtraindo pela direção do grupo; no IPC
06 o par `6.2.1.2 (+) / 6.2.1.3 (−)` **já traz o sinal**, e aplicar a direção do grupo faria a
dedução somar. O critério passa a ser declarado pela regra, não por convenção global.

### D4 — Código principal casado por igualdade
**Escolhido:** `codigo_principal(registro) == valor da regra` · **Descartado:** `startswith`, como
nas contas contábeis · **Porquê:** contas do PCASP são hierárquicas e o prefixo é a hierarquia;
fontes não são — `540` e `541` são subgrupos distintos dentro de Educação, e `54` não significa
nada. Prefixo faria `500` capturar `5001` se o ente detalhar.

### D4b — Par (matriz, tipo de saldo) é propriedade do demonstrativo (G9, decidido)
**Escolhido:** `MSCE`/abertura para o BF, conforme decisão do PO de 2026-09-14; o par é declarado
pelo demonstrativo e vai na procedência · **Descartado:** parâmetro livre por chamada ·
**Porquê:** o par é norma, não configuração — `MSCE`/encerramento devolve **0 registros** nas
classes 3 e 4, e o BF sairia sem as transferências financeiras (8,57 bi em João Pessoa) mostrando
zero, não erro. Deixar os dois lados soltos permite a combinação errada; amarrá-los ao
demonstrativo torna a combinação errada inexprimível. A tabela por demonstrativo (BO, BF, DVP e DFC
na abertura; BP no encerramento) vive num só lugar, não espalhada pelos adapters.

### D4c — Competência como parâmetro em toda a cadeia (G10)
**Escolhido:** mês parametrizado do serviço à chave de cache, padrão 12 · **Descartado:** manter
`MES_DA_DCA = 12` e tratar mensal depois · **Porquê:** a periodicidade mensal foi confirmada para
**todos os anexos**. Retrofitar o mês depois atravessaria serviço, carregador, chave de cache, job
e rota — e, pior, todo resultado já cacheado com chave sem mês passaria a poder devolver o mês
errado. É a mesma razão pela qual o exercício já é parâmetro no carregador (P8).

### D5 — Linha bloqueada é parcela inexistente no total (G5)
**Escolhido:** o total soma as parcelas apuradas e nomeia as bloqueadas no diagnóstico ·
**Descartado:** propagar `None` até o total · **Porquê:** o motor já distingue três situações na
parcela (não declara / suprimida / não apurada) desde a change `ipc07-c5-c7-linhas-cruzadas`; a
quarta — bloqueada por falta de mapeamento — é do mesmo tipo da primeira. Propagar `None` deixaria
`L33` e `L66` não apuradas e o BF inteiro incomparável ao publicado, por causa de linhas que na
maioria dos entes valem zero.

### D6 — Exercício anterior apurado com o mapa do exercício atual
**Escolhido:** mesma edição de regra nas duas colunas · **Descartado:** carregar a vigência de
`exercicio-1` para a coluna anterior · **Porquê:** a coluna "Exercício Anterior" do demonstrativo é
o exercício passado **relido pela regra vigente**, que é o que o STN publica; misturar edições
faria duas colunas da mesma linha significarem coisas diferentes.

## Arquivos criados / alterados

| Arquivo | Ação |
|---|---|
| `app/domain/bo/*.py` → `app/domain/nucleo/*.py` | mover (git mv) |
| `app/domain/nucleo/modelo.py` | alterar (`Mapa`, `ContaCC.saldo`, `Coluna.movimento`) |
| `app/domain/nucleo/saldo.py` | alterar (fonte de recursos, movimento) |
| `app/domain/nucleo/portas.py` | alterar (`tipo_valor`) |
| `app/infra/regras/carregador.py` | alterar (demonstrativo como parâmetro) |
| `app/infra/msc/siconfi.py`, `app/infra/msc/publicsoft.py`, `app/infra/msc/cache.py` | alterar (`tipo_valor`) |
| `app/services/bf/quadro_principal.py` | criar |
| `app/services/pipeline/resultado.py` | alterar (ordem de apresentação do BF) |
| `app/cli/bf.py` | criar |
| `tests/bf/test_apuracao.py`, `tests/bf/test_fonte_recursos.py`, `tests/bf/test_saldo_em_data.py`, `tests/bf/test_caso_joao_pessoa.py` | criar |
| `docs/validacao-bf-jp-2025.md` | criar |
| imports de `app.domain.bo` em `app/`, `tests/`, `worker.py`, `main.py` | alterar |

## Pendências conhecidas

- As seis linhas bloqueadas (F1/F2 do IPC 06) não se resolvem por conta de controle: **medido** que
  as classes 7 e 8 do ente só trazem controles de disponibilidade e programação financeira. A saída
  provável é G8 — apurar `L22`/`L55` pela variação de `1.1.4` e `1.2.1.3`. Até lá, D5 mantém o
  demonstrativo comparável, com desequilíbrio declarado de −228.702.095,15.
- Rota, job, cache e SSE do BF ficam para `plataforma-pipeline-dca` — que precisa absorver o mês
  na chave de cache, no job e na rota assim que G10 for decidido.
- G9 e G10 alcançam o BO já entregue: decididos de outro modo, o BO é reapurado e revalidado, e a
  decisão C1 do PO (mês 12, MSCC) é revisitada.
- O volume de leitura da MSC no BF é maior que o do BO; se a latência inviabilizar a apuração
  síncrona, a F2 precisará do job antes do que precisou no BO.
