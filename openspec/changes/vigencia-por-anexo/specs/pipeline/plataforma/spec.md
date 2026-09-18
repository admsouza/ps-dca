# pipeline/plataforma — Delta spec

## ADDED Requirements

### Requirement: A semente de vigência cobre todos os anexos implementados

A semente de boot SHALL publicar a vigência de **cada anexo com serviço implementado** no registry,
usando a base canônica declarada por ele e o ano da edição correspondente. NÃO DEVE publicar apenas
o Balanço Orçamentário.

Anexo sem serviço SHALL ser ignorado, sem falhar o boot. Base canônica sem edição que cubra o ano
SHALL ser registrada em aviso, e os demais anexos SHALL ser semeados mesmo assim — um anexo sem
transcrição não pode impedir a publicação dos outros.

A semente SHALL continuar idempotente: vigência já publicada é mantida, e a recusa da chave
primária é tratada como "já semeado".

#### Scenario: BO e BF semeados no boot

- **WHEN** a semente roda num banco vazio
- **THEN** a vigência do BO é publicada com a edição do IPC 07
- **AND** a vigência do BF é publicada com a edição do IPC 06
- **AND** cada uma no ano da sua própria edição

#### Scenario: apuração do BF deixa de cair no YAML

- **GIVEN** a semente aplicada
- **WHEN** o worker apura o BF
- **THEN** o mapa vem do banco
- **AND** nenhum aviso de vigência ausente é registrado

#### Scenario: segundo boot não reescreve

- **GIVEN** a semente já aplicada
- **WHEN** o boot roda de novo
- **THEN** nada é publicado
- **AND** o boot conclui sem erro

### Requirement: A completação de apresentação usa a transcrição do próprio anexo

Ao carregar a vigência do banco, a completação de nível, ordem e colunas ausentes SHALL usar a
transcrição **do anexo carregado**, não a do Balanço Orçamentário.

Completar o BF com a transcrição do BO não casa `rule_id` nenhum (`bf.*` contra `bo.*`) e devolve o
mapa inalterado — sem erro e sem efeito, que é a forma mais cara de não fazer nada.

#### Scenario: BF completado pela transcrição do IPC 06

- **GIVEN** uma vigência do BF publicada sem `nivel` em alguma linha
- **WHEN** o mapa é carregado do banco
- **THEN** o nível vem da transcrição do IPC 06
- **AND** o `documento` da vigência é o do próprio anexo
