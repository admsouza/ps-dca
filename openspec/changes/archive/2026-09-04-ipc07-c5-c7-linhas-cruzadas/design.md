# Design — C5 e C7

## Componentes afetados

| Arquivo | Alteração |
|---|---|
| `knowledge/schemas/rule.json` | `calculation.references[]` ganha `column` opcional |
| `knowledge/rules/bo/quadro_principal.yaml` | `L25`, `L26`, `L49`, `L50` declaram colunas e referência cruzada; `L29` perde `previsao_inicial` |
| `app/domain/bo/modelo.py` | `RefLinha` ganha `coluna`; `Matriz` ganha `suprimidas` |
| `app/domain/bo/matriz.py` | `_agregar` separa os 3 casos da parcela; condição aplicada em ordem topológica |
| `scripts/validate_rules.py` | rejeita referência que nomeie coluna ausente |
| `app/infra/regras/carregador.py` | lê `column` da referência |
| `tests/` | cenários novos e os 3 vermelhos de C5 |
| `docs/source-analysis-ipc07.md` | restrição de B6 registrada |

## Fluxo da informação

O passo (b) da apuração agrega linha composta coluna a coluna, em ordem topológica. Duas mudanças:

```text
antes:  (a) células → (b) agregações → (c) derivadas → (d) condições
depois: (a) células → (b) agregações + condição por linha, na ordem topológica → (c) derivadas
```

A condição passa a ser aplicada **dentro** do laço topológico, logo após a linha ser calculada.
Sem isso, `L26` somaria o valor cru de `L25` — que em ente superavitário é negativo — em vez da
parcela zero que o STN publica.

Na agregação, a parcela deixa de ser lida com `dict.get` e passa a distinguir:

```python
valores = matriz.valores.get(referencia.regra) or {}
lida = referencia.coluna or coluna          # referência cruzada em coluna
if lida not in valores:
    continue                                 # não declara: a parcela não existe
parcela = valores[lida]
if parcela is None:
    if (referencia.regra, lida) in matriz.suprimidas:
        continue                             # suprimida pela condição: contribui zero
    indeterminada = True                     # não apurada: propaga
```

`continue` e `indeterminada` eram o mesmo caminho antes; é essa fusão que fazia
`L27.previsao_inicial` sair `None` assim que `L29` perdesse a coluna.

## Contratos e interfaces

- `RefLinha(regra, sinal, coluna=None)` — `coluna` opcional preserva todo chamador atual.
- `Matriz.suprimidas: set[tuple[str, str]]` — `(rule_id, coluna)` das células que a condição
  suprimiu. É o que separa "não se aplica" de "não apurado" no contrato de saída, sem inventar um
  sentinela novo em `valores`, que segue com `None` para os dois e é desambiguado por este conjunto.
- `calculation.references[].column` no schema — `additionalProperties: false` obriga declarar.

## Impacto em banco, cache, filas e APIs externas

- **Cache:** `versao_regras` muda. Sem cache em produção (F3 não entrou), nada a invalidar.
- **Banco, filas, APIs:** nenhum. Nenhuma tabela de `knowledge/sources/` é tocada.

## Decisões

**D1 — `column` na referência, não coluna-alvo na linha.**
A alternativa era declarar em `L49` um mapa "minha coluna X lê a coluna Y da linha Z". Fica
redundante: o sinal e o `rule_id` já estão na referência, e o mapa duplicaria os dois. Com `column`
na própria referência, `L49` declara **uma** lista de referências que serve às três colunas — a de
`L24` fixa em `receitas_realizadas`, a de `L48` seguindo a coluna calculada.
*Descartado:* repetir o bloco de referências por coluna — 3× o YAML para a mesma informação.

**D2 — `suprimidas` como conjunto na `Matriz`, não sentinela em `valores`.**
`valores` é o que o consumidor serializa; trocar `None` por um sentinela quebraria todo leitor e
obrigaria o JSON a representá-lo. O conjunto é aditivo: quem não souber dele lê `None` e apresenta
em branco, que é o certo.
*Descartado:* `Decimal(0)` em `valores` com a supressão só no conjunto — faria a célula suprimida
aparecer como zero em qualquer leitor que ignorasse o conjunto, e zero é valor legítimo do
demonstrativo.

**D3 — condição na ordem topológica, não num passo próprio depois.**
O passo (d) separado só funciona se ninguém agregar a linha condicional. `L26` e `L50` agregam.
Mover para dentro do laço mantém um invariante simples: quando uma linha é lida por um dependente,
ela já está no estado final.
*Descartado:* manter (d) e fazer `L26`/`L50` recalcularem — dois lugares aplicando a mesma condição.

**D4 — as colunas das 4 linhas são declaradas, não derivadas da interseção.**
A interseção é vazia por construção, e a união traria coluna com uma parcela só. As colunas vêm do
publicado do STN, medido, e ficam explícitas na regra — auditáveis contra a evidência.

## Arquivos criados ou alterados

```text
knowledge/schemas/rule.json                          alterado
knowledge/rules/bo/quadro_principal.yaml             alterado
app/domain/bo/modelo.py · matriz.py                  alterado
app/infra/regras/carregador.py                       alterado
scripts/validate_rules.py                            alterado
tests/bo/test_apuracao.py · tests/test_base_ipc07.py alterado
tests/test_cobertura_spec.py                         contagem 49→51 e 33→34
docs/source-analysis-ipc07.md                        alterado
openspec/changes/bo-quadro-principal-processamento/
    specs/dca/balanco-orcamentario/spec.md           delta ativo, 1 cenário alterado + 1 novo
openspec/specs/dca/base-canonica-regras/spec.md      mesclado no arquivamento
```
