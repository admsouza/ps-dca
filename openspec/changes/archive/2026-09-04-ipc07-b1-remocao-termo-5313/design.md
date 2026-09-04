# Design — remoção do termo `5.3.1.3.0.00.00`

## Componentes afetados

| Arquivo | Alteração |
|---|---|
| `knowledge/rules/bo/rp_nao_processados.yaml` | remove a conta `5.3.1.3` da coluna `inscritos_exerc_anteriores`; reescreve as 6 notas `B1` |
| `tests/bo/test_saldo.py` | substitui `test_excecao_historica_usa_a_natureza_declarada` pelo teste do comportamento novo; corrige a direção das contas `531*` na fixture |
| `docs/source-analysis-ipc07.md` | acrescenta a decisão de 2026-09-04 ao bloco B1, sem apagar a de 2026-08-27 |
| `docs/PONTO-DE-PARADA.md` · `openspec/changes/bo-quadro-principal-processamento/tasks.md` | C6 encerrada |

**Nenhum arquivo de `app/` é alterado.** A mudança é de base canônica: o motor já trata "conta
declarada sem escrituração contribui zero" (`app/domain/bo/saldo.py:105`) e já resolve a direção da
coluna pela tabela. Remover o termo elimina o caminho que produzia `None`, sem tocar no caminho.

## Fluxo da informação

A coluna é composta por `saldo_da_celula` (`app/domain/bo/saldo.py:79`), que itera as contas
declaradas. Hoje, com `5.3.1.3` na lista:

```text
5312 -> casa registros, direção conhecida -> soma
5313 -> se há registro, direcao.credora("531300000") é None
     -> pendência "sem natureza de saldo no PCASP nem na regra"
     -> a função devolve (None, pendencias): a CÉLULA INTEIRA fica não apurada
5316 -> soma        6316 -> subtrai
```

Depois, com 3 contas, o segundo passo desaparece. Registro de `5.3.1.3` não casa com nenhuma conta
declarada e é ignorado — mesmo tratamento de qualquer conta fora da fórmula.

## Contratos e interfaces

`MapaBO`, `Coluna` e a assinatura de `carregar`/`apurar` seguem iguais. `ContaCC` **perde o campo
`natureza_saldo`** (D3, revertida na execução).

## Impacto em banco, cache, filas e APIs externas

- **Banco/filas:** nenhum. Não há migration nesta change.
- **Cache:** o hash canônico `versao_regras` **muda**, porque as regras mudam — é o comportamento
  correto, e é o que a task 1.3 de `plataforma-pipeline-dca` garante. Não há cache em produção
  (a F3 não entrou), então não há invalidação a coordenar.
- **APIs externas:** nenhuma. Nenhuma tabela de `knowledge/sources/` é tocada, então
  `check_sources` segue íntegro.

## Decisões

**D1 — o termo sai, em vez de virar `5.3.1.2`.**
Substituir `5313` por `5312` daria `5312 + 5312 + 5316 (-) 6316`. `saldo_da_celula` soma por conta
declarada e **não deduplica** (`app/domain/bo/saldo.py:103`), então todo registro de `5.3.1.2`
entraria duas vezes — R$ 67.299.876,72 a mais na coluna (a) em João Pessoa 2025, nas 9 linhas.
*Descartado:* declarar `5312` duas vezes e deduplicar no motor — resolveria um problema que só
existe se a regra estiver errada, e mascararia duplicata legítima em outras colunas.

**D2 — o literal de 4 termos do IPC 07 é preservado em `source`/`evidence`.**
A spec de base canônica proíbe apagar o literal normativo. A regra passa a declarar 3 contas, e a
fórmula original continua legível na própria regra e em `docs/source-analysis-ipc07.md`.
*Descartado:* reescrever o `evidence.text` para 3 termos — falsificaria a transcrição do PDF.

**D3 — `ContaCC.natureza_saldo` sai do modelo. REVERTIDA na execução.**

*Decisão original:* manter o campo, inerte — `None` por default, não custa nada, e mexer no domínio
para tirar um campo aumentaria o diff sem fechar nada.

*Por que foi revertida:* ao remover o cenário do delta do BO, a medição mostrou que o mecanismo
**nunca funcionou de ponta a ponta**. `_direcao_da_coluna` consumia `natureza_saldo` para a direção
da **coluna**, mas a checagem por registro em `saldo_da_celula` (`app/domain/bo/saldo.py:109`)
rejeita qualquer registro cuja conta a tabela não resolva — então a célula saía `None` de todo
jeito. Era exatamente por isso que o teste de C6 estava vermelho: o campo não salvava a célula.

Somado a isso: **0 regras declaram o campo**, ele é **ausente do schema** `rule.json`, e nenhum
teste o exercitava. Não era campo inerte — era mecanismo quebrado e sem chamador. Manter seria
manter código morto que aparenta cobrir um caso que não cobre, e o gate de REVIEW proíbe código
morto.

*Consequência:* saíram `ContaCC.natureza_saldo` (`modelo.py`), o ramo em `_direcao_da_coluna`
(`saldo.py`) e o terceiro argumento em `carregador.py`. Junto saiu **`_direcao_da_conta`**, função
de 22 linhas **nunca chamada** — código morto pré-existente que existia só para esse campo.

**D4 — a fixture de direção das contas `531*` é corrigida junto.**
`tests/bo/test_saldo.py` declara `531100000`, `531200000` e `531600000` como **credoras**; no PCASP
as três são **Devedora**. Hoje é latente porque o teste só afirma `is not None`. O teste novo
confere **valor**, então a direção invertida daria sinal errado — corrigir deixou de ser opcional.

## Arquivos criados ou alterados

Previstos no PLAN/ARCH:

```text
knowledge/rules/bo/rp_nao_processados.yaml                     alterado
tests/bo/test_saldo.py                                         alterado
docs/source-analysis-ipc07.md                                  alterado
docs/PONTO-DE-PARADA.md                                        alterado
openspec/changes/bo-quadro-principal-processamento/tasks.md     alterado
openspec/specs/dca/base-canonica-regras/spec.md                mesclado no arquivamento
```

Acrescentados na execução, cada um por uma consequência descoberta:

```text
tests/test_base_ipc07.py                                       1 teste alterado, 1 substituído
app/domain/bo/modelo.py · saldo.py · infra/regras/carregador.py  D3 revertida — código morto
openspec/changes/bo-quadro-principal-processamento/
    specs/dca/balanco-orcamentario/spec.md                     cenário substituído (delta ativo)
```

O delta do BO é editado aqui porque aquela change está **ativa e não mesclada**: o processo manda
editar deltas em `changes/`, e é lá que o requisito de `natureza_saldo` vive. A troca está
registrada nas tasks das duas changes.
