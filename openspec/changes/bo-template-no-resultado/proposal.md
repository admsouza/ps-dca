# O template do demonstrativo acompanha o resultado

## Por que

Hoje o resultado apurado é `{rule_id: {coluna: valor}}` e nada mais. Quem renderiza precisa saber,
por fora, o rótulo de cada uma das 69 linhas, em que quadro ela está, seu nível de indentação e sua
posição na ordem de apresentação — e nada disso está no payload.

A consequência apareceu ao escrever a spec da UI (`front-declaracoes`,
`openspec/changes/dca-anexo01-bo-ui/`): o front teria de **declarar as 69 linhas** com rótulo, nível
e ordem. Isso cria uma **segunda fonte da verdade** para a transcrição normativa, que já está
verificada aqui — e que divergiria na primeira correção de rótulo feita só de um lado.

Pior: enquanto essa spec era escrita, o nível foi **derivado da árvore de composição** por não estar
no payload, e o resultado saiu errado em duas das três amostras conferidas — `Reserva do RPPS` ficou
no nível 1 quando a norma diz 2, e `Mobiliária` no 2 quando a norma diz 3. O dado correto existia
desde a transcrição, em `knowledge/rules/bo/*.yaml`; só não era publicado.

## O que muda

O resultado passa a trazer, além de `matriz`, `procedencia` e `diagnostico`, uma seção **`linhas`**:
o template de apresentação do demonstrativo, na ordem da norma.

```jsonc
{
  "linhas": [
    { "rule_id": "bo.quadro_principal.receitas.l1", "codigo": "L1",
      "rotulo": "Receitas Correntes (I)", "quadro": "QUADRO_PRINCIPAL",
      "grupo": "RECEITAS", "nivel": 1, "ordem": 1, "totalizadora": true },
    { "rule_id": "bo.quadro_principal.despesas.l51", "codigo": "L51",
      "rotulo": "Reserva do RPPS", "quadro": "QUADRO_PRINCIPAL",
      "grupo": "DESPESAS", "nivel": 2, "ordem": 21, "totalizadora": false }
  ],
  "matriz": { … }, "procedencia": { … }, "diagnostico": { … }
}
```

`nivel` e `ordem` **já existem** na base canônica, transcritos do PDF do IPC 07, e hoje são lidos e
descartados pelo carregador. Esta change os leva ao domínio e ao resultado.

## Decisões

1. **`linhas` é ordenada, `matriz` é indexada.** A ordem de apresentação vive em `linhas`; a `matriz`
   continua um mapa por `rule_id`. Quem renderiza itera `linhas` e busca em `matriz` — e nenhuma das
   duas passa a depender da ordem de chaves de um objeto JSON.
2. **`ordem` é relativa ao grupo**, como a norma declara: receitas 1–30 e despesas 1–21, ambas
   começando em 1. Isto é publicado como está, com `grupo` no mesmo objeto — resolver a intercalação
   é de quem apresenta, e sem `grupo` seria impossível.
3. **A ordem dos quadros é a da norma:** `QUADRO_PRINCIPAL` (p. 8–11), `RP_NAO_PROCESSADOS` (p. 12),
   `RP_PROCESSADOS` (p. 13). A ordem alfabética e a de inserção das chaves são as duas a inversa
   entre os dois quadros de Restos a Pagar; `linhas` sai na ordem normativa.
4. **`nivel` e `ordem` vêm da transcrição versionada** (`knowledge/rules/bo/`), não do banco de
   vigências — a mesma decisão já tomada para `tabelas_stn`. Motivo prático: a vigência publicada é
   INSERT-only e a atual não carrega esses campos; motivo de fundo: são metadados **da norma**, que
   mudam com a edição do IPC 07 e não com uma correção administrativa de mapeamento.
5. **`totalizadora`** é derivada (`bool(referencias)`) e publicada, porque é o que decide o destaque
   visual da linha. Quem renderiza não deve reimplementar a regra de "esta linha soma outras".
6. **Nada sai do payload.** `matriz`, `procedencia` e `diagnostico` seguem idênticos: é adição, e
   nenhum consumidor existente quebra.

## Impacto

| Onde | O que |
|---|---|
| `app/domain/bo/modelo.py` | `Linha` ganha `nivel: int = 0` e `ordem: int = 0` |
| `app/infra/regras/carregador.py` | passa a ler `linha.nivel` e `linha.ordem` do YAML |
| `app/infra/regras/vigencias.py` | shape achatado transporta os dois campos; vigência antiga sem eles é completada pela transcrição, com log |
| `app/services/pipeline/resultado.py` | `para_dados` publica `linhas` |
| CLI | passa a imprimir a matriz na ordem da norma, e não na de inserção |

Sem migration: o jsonb `linhas` de `dca_regra_mapeamento` ganha dois campos por objeto, e a coluna
não muda de tipo.
