# Contrato do YAML do BP

O schema é `knowledge/schemas/rule.json`. Campo fora dele quebra a carga. O que não couber vai para `review.blocker` e `review.candidate`, sem chave nova.

Edição: `2020-01`. `valid_from` sai da data do PDF (o metadado medido em `docs/source-analysis.md` §1 é 2020-01-20 — confira no arquivo antes de gravar). `valid_until` é `null`. O IPC não declara fim de vigência; data inventada é erro.

`provenance.extraction_method: assisted`. `provenance.decision` só com código que já exista no schema (`B1`, `B3`, `B5`, `B6`, `F3`, `F4`, `F5`). Decisão nova do BP não ganha sigla: fica no `review.blocker`.

`evidence.text` é trecho da página, com o código na grafia do PDF. `source.document: IPC04`, `document_version: 2020-01`, `section` igual ao título da seção na página.

## Colunas de valor

A estrutura (pp. 14–18) tem Nota, Exercício Atual e Exercício Anterior. Nota é layout, não critério: não vira coluna.

As duas colunas de valor seguem o BF (`exercicio_atual` e `exercicio_anterior`), com as **mesmas** contas. O exercício anterior é a mesma regra em outro período, não outro plano de contas. Como o BP é saldo patrimonial e não movimento, cada conta declara `saldo: final`. Ausência de `saldo` significa movimento do período no schema — omitir isso faria o programador apurar fluxo.

Linha que o IPC define só como soma de outras linhas (`L1 = L2 + L9`) não declara `columns`. Declara `calculation.references` com `rule` e `sign`. Subtração de linha, como `Saldo Patrimonial (L1 − L4)`, usa `sign: '-'` na referência. `on` é proibido: o YAML 1.1 lê essa chave como booleano.

## Exclusão de conta

A coluna Exclusões do quadro principal é lista de contas filhas do somatório. Não é o `sign: '-'` do BF: lá `6.2.1.3` é conta irmã de `6.2.1.2`, subtraída no valor. Também não é `exclusion_groups`: esse bloco é combinação de campos diferentes (BO L38), e o motor exclui o grupo pelo casamento, ignorando o operador.

Modelo, o mesmo da L11 do BO:

```yaml
filters:
- field: conta_contabil
  operator: not_in
  values:
  - literal: 1.1.1.1.2.00.00
    pattern: '11112'
columns:
  exercicio_atual:
    label: Exercício Atual
    accounts:
    - literal: 1.1.1.0.0.00.00
      pattern: '111'
      sign: +
      saldo: final
```

`pattern` da exclusão e do somatório só entra depois do gate da skill: a folha no `PCASP.md` tem de começar por esse prefixo. Zero à direita no PDF é máscara, não dígito do prefixo.

O item 9 (deduzir também conta de 5º nível = 2 criada pelo ente) é policy, não filtro. A lista do quadro é o que se aplica. Um coringa de todo subtítulo 2, conferido no `PCASP.md`, pega conta oficial que a coluna Exclusões não lista. Não aplique esse coringa. A policy descreve o item 9 e fica referenciada nas linhas que têm exclusão; o texto deixa claro que o filtro é a lista do quadro, não o universo do 5º nível.

`1.1.3.8.2.000.00` (L4) é erro de digitação do PDF (grupo de três dígitos). Preserve o `literal`. Confira `11382` no `PCASP.md`. Se a folha existir, o candidato vai para `review.candidate` e o `pattern` aplicado continua `null` até decisão — não corrija a grafia dentro de `filters`.

## Quatro quadros

Códigos de quadro: `QUADRO_PRINCIPAL`, `ATIVOS_PASSIVOS_FINANCEIROS`, `CONTAS_COMPENSACAO`, `SUPERAVIT_DEFICIT`. `demonstrativo.codigo: BP`.

| Quadro | O que é executável | O que para em blocker |
|---|---|---|
| Principal, L1–L40, pp. 8–10 | Soma de prefixo PCASP, exclusão `not_in`, agregação de linhas | Código que o `PCASP.md` não sustenta (`pattern: null`) |
| Financeiros e permanentes, L1–L7, p. 11 | L1, L4 e L7, que são só referência de linhas. Contas de classe 6 citadas nominalmente em L5 (`6.2.2.1.3.01.00`, `6.2.2.1.3.05.00`, `6.3.1.1.0.00.00`, `6.3.1.5.0.00.00`), se o `PCASP.md` confirmar a folha | L2, L3, L5 e L6 no que dependem do atributo (F) ou (P). O schema não tem esse campo. Conta nominal entra em `columns`; o atributo fica em `review.blocker`, com o candidato descrevendo registro `1` ou `2`. `status: review_required` |
| Compensação, L1–L10, p. 12 | Conta `8.1.1.x` / `8.1.2.x` que o `PCASP.md` confirmar, nas duas colunas, `saldo: final` | “(somente saldo a executar)”. O IPC item 13 diz que o PCASP não separa executado de a executar (pendência P2). A restrição não entra em `filters` |
| Superávit / déficit, p. 13 | Uma regra de total: conta `8.2.1.1.1.00.00` nas duas colunas, se o `PCASP.md` confirmar | Uma linha por fonte. A cardinalidade é do ente (P7). Não crie `rule_id` com `<código da fonte>` |

Linha com blocker continua no arquivo: o programador precisa ver a conta que já é computável e o que ficou de fora. `review.candidate` guarda a leitura provável e não é aplicado.

## Policies

Arquivo `knowledge/policies/ipc04.yaml`, schema `policy.json`.

- `ipc04.exclusao_intra_so_no_consolidado` — item 8. A exclusão de intra vale para o BP consolidado do ente. Órgão ou unidade isolada não exclui.
- `ipc04.intra_quinto_nivel_criada_pelo_ente` — item 9. A lista da matriz não esgota contas que o ente criar com 5º nível = 2. Não vira `not_in` genérico.

`status: extracted` na policy quando o item está inteiro na página. Não invente `policy_id` para texto institucional (prefácio, objetivo, alcance).

## Identidade da linha

`rule_id` em minúsculas, estável: `bp.<quadro>.<grupo opcional>.l<n>`. `linha.codigo` é `L1` como no PDF. `linha.ordem` segue a aparição no quadro. `linha.nivel` é a indentação da estrutura (pp. 14–18): total do lado = 1, grupo = 2, conta = 3. Rótulo (`linha.descricao`) copia o PDF, inclusive “(-) Ações / Cotas em Tesouraria”.

Âncora YAML (`&`) só quando o bloco de colunas é idêntico ao de outra linha do mesmo arquivo, como o BO faz. Não compartilhe âncora entre arquivos.

Colunas repetidas nas linhas de filtro podem usar a âncora. Linha agregadora não tem `columns` e portanto não usa a âncora.
