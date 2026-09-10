# Balanço Orçamentário — delta: o template acompanha o resultado

## ADDED Requirements

### Requirement: O resultado publica o template de apresentação

Todo resultado apurado SHALL trazer, além dos valores, o **template do demonstrativo**: uma
sequência ordenada de linhas com `rule_id`, `codigo`, `rotulo`, `quadro`, `grupo`, `nivel`, `ordem`
e `totalizadora`. Quem renderiza NÃO DEVE precisar declarar rótulo, nível ou ordem por fora.

`nivel` e `ordem` SHALL ser os declarados na transcrição normativa versionada, e NÃO DEVEM ser
derivados da árvore de composição — as duas coisas divergem, e a norma é a que vale.

#### Scenario: template acompanha os valores

- **WHEN** um anexo é apurado
- **THEN** o resultado traz `linhas` com uma entrada por linha do demonstrativo
- **AND** todo `rule_id` de `linhas` existe em `matriz`, e todo `rule_id` de `matriz` existe em
  `linhas`

#### Scenario: nível e ordem são os da norma

- **GIVEN** a transcrição declara `nivel` e `ordem` para cada linha
- **WHEN** o template é publicado
- **THEN** os valores publicados são os declarados na transcrição
- **AND** `Reserva do RPPS` sai com `nivel: 2`, e não com o nível que a composição sugeriria

#### Scenario: linhas saem na ordem de apresentação da norma

- **WHEN** o template é publicado
- **THEN** os quadros aparecem na ordem `QUADRO_PRINCIPAL`, `RP_NAO_PROCESSADOS`,
  `RP_PROCESSADOS`
- **AND** dentro do quadro principal, o grupo `RECEITAS` precede `DESPESAS`
- **AND** dentro de cada grupo, as linhas seguem `ordem` crescente

#### Scenario: ordem é relativa ao grupo

- **GIVEN** que a norma numera receitas de 1 a 30 e despesas de 1 a 21
- **WHEN** o template é publicado
- **THEN** existem duas linhas com `ordem: 1` no quadro principal, distinguidas por `grupo`
- **AND** `grupo` é publicado em cada linha, de modo que a intercalação seja resolúvel

#### Scenario: linha totalizadora é identificável sem reimplementar a regra

- **GIVEN** uma linha composta de outras
- **WHEN** o template é publicado
- **THEN** ela sai com `totalizadora: true`
- **AND** linha de folha e linha de rótulo saem com `totalizadora: false`

#### Scenario: adição não quebra consumidor existente

- **WHEN** o resultado é publicado
- **THEN** `matriz`, `procedencia` e `diagnostico` permanecem com a mesma forma
- **AND** nenhum campo é removido ou renomeado

### Requirement: Vigência publicada sem os metadados de apresentação é completada

Vigência de mapeamento publicada antes desta change NÃO DEVE quebrar a apuração nem publicar
template incompleto. O carregador SHALL completar `nivel` e `ordem` ausentes a partir da
transcrição versionada, registrando o evento em log.

#### Scenario: vigência antiga não tem nível nem ordem

- **GIVEN** uma vigência publicada cujo shape não traz `nivel` e `ordem`
- **WHEN** o mapa é carregado do banco
- **THEN** os dois campos são completados pela transcrição versionada
- **AND** o evento é registrado em log, sem falhar a apuração

#### Scenario: linha do banco sem correspondente na transcrição

- **GIVEN** uma vigência com linha que a transcrição versionada não contém
- **WHEN** o mapa é carregado
- **THEN** a linha permanece no template com a ordem em que aparece na vigência
- **AND** a apuração não falha
