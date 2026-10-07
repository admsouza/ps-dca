# pipeline/processamento-completo — Delta spec

## MODIFIED Requirements

### Requirement: Progresso do percurso é acompanhável

O estado do job completo SHALL trazer, além do status, o progresso (`concluidos` de `total`) e o
desfecho por anexo — anexo, status e detalhe de erro quando houver. O stream SHALL emitir um evento
a cada anexo concluído e um evento final de desfecho, no mesmo vocabulário que o front já consome
para o job por anexo.

No canal de operação, o percurso SHALL notificar como o pipeline do RGF: **uma mensagem por anexo**,
quando ele termina (`Concluído ✅`, `Falhou ❌`) ou quando vem do cache (`Cache ✅`, cinza, `Dados já
em cache`), e **um resumo** ao fim. O resumo SHALL ter o título `✅ <Cidade - UF>  <exercício>
[Anual] — <e-mail>` (`⚠️` com falha), o corpo `<n> anexo(s) concluído(s) com sucesso.` ou `Fila
concluída com <n> falha(s).`, e os campos `Fonte MSC`, `Tempo total`, `Detalhamento` (uma linha por
anexo implementado, na ordem do registry) e, havendo falha, `Erros`. A cor SHALL ser roxa sem falha e
laranja com falha. Anexo pulado por já estar em voo NÃO DEVE gerar mensagem própria.

#### Scenario: progresso é legível durante a execução

- **GIVEN** um percurso de dois anexos com o primeiro já concluído
- **WHEN** o estado do job é consultado
- **THEN** o progresso indica 1 de 2
- **AND** o desfecho do anexo concluído já aparece, com seu status

#### Scenario: conclusão do percurso é notificada uma vez

- **GIVEN** um percurso concluído, com ou sem erros
- **WHEN** o canal de operação está configurado
- **THEN** sai **um** resumo, com uma linha de detalhamento por anexo e a duração total
- **AND** nenhum campo do resumo sai como `None`

#### Scenario: cada anexo do percurso também notifica

- **GIVEN** um percurso de BO, BF e BP, com o BF em cache
- **WHEN** o percurso termina
- **THEN** saem `DCA BO — Concluído ✅`, `DCA BF — Cache ✅` e `DCA BP — Concluído ✅`, nesta ordem
- **AND** depois deles, o resumo, com `BF — cache ✅` no detalhamento

#### Scenario: percurso com falha

- **GIVEN** um percurso em que o BF falhou com `fonte fora do ar`
- **WHEN** o resumo é enviado
- **THEN** o título começa com `⚠️`, o corpo é `Fila concluída com 1 falha(s).` e a cor é laranja
- **AND** o campo `Erros` traz `**BF:** fonte fora do ar`
