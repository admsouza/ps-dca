# pipeline/plataforma — Delta spec

## ADDED Requirements

### Requirement: Módulo DCA exigido em toda rota de anexo

Toda rota de anexo SHALL exigir que o módulo `dca` esteja entre os módulos do usuário **naquele
ente**, resolvidos pelo hub a cada requisição. Usuário sem o módulo SHALL receber `403`, sem job e
sem dado do ente. Esconder a opção na interface NÃO DEVE ser tratado como controle de acesso.

#### Scenario: usuário sem o módulo

- **GIVEN** um usuário vinculado ao ente, com poder, mas sem `dca` entre os módulos ali
- **WHEN** ele chama qualquer rota de anexo, direto na API
- **THEN** a resposta é `403`
- **AND** nenhum job é criado

#### Scenario: módulo concedido só em outro ente

- **GIVEN** um usuário com `dca` em um ente e sem `dca` em outro
- **WHEN** ele chama a mesma rota nos dois entes
- **THEN** o primeiro responde normalmente e o segundo responde `403`

#### Scenario: revogação vale na requisição seguinte

- **GIVEN** um usuário com `dca` no ente
- **WHEN** o módulo é removido no cadastro e ele repete a chamada com o mesmo JWT
- **THEN** a resposta é `403`, sem novo login

### Requirement: Recorte por unidade gestora limitado às UGs autorizadas

A visibilidade de recorte SHALL considerar, além do poder, as Unidades Gestoras autorizadas ao
usuário naquele ente. Lista de UGs **vazia** SHALL significar ausência de restrição por UG,
preservando o comportamento por poder.

Com a lista preenchida: as chaves de unidade visíveis SHALL ser apenas as UGs autorizadas; o
recorte consolidado e os recortes de grupo de poder SHALL permanecer visíveis **somente** quando
todas as unidades que eles somam estiverem autorizadas. Duas UGs de um mesmo poder NÃO DEVEM
conceder acesso uma à outra.

Recorte pedido e não visível SHALL responder `403`, sem nenhum valor dele no corpo. Usuário sem
nenhum recorte visível SHALL receber `403`, nunca uma resposta vazia com `200`.

#### Scenario: duas UGs do mesmo poder, contadores diferentes

- **GIVEN** dois usuários com o poder Executivo no mesmo ente, um autorizado na UG do Fundo de
  Saúde e o outro na UG do Fundo de Assistência
- **WHEN** cada um lê os recortes disponíveis
- **THEN** cada um vê apenas a sua UG
- **AND** o recorte da UG do outro responde `403`

#### Scenario: usuário com várias UGs

- **GIVEN** um usuário autorizado em duas das cinco UGs do ente
- **WHEN** ele lê os recortes disponíveis
- **THEN** as duas UGs aparecem, e o consolidado e os grupos de poder não

#### Scenario: usuário com todas as UGs

- **GIVEN** um usuário autorizado em todas as unidades do ente, com poder consolidado
- **WHEN** ele lê os recortes disponíveis
- **THEN** o consolidado, os grupos de poder e as unidades aparecem

#### Scenario: UGs de poderes diferentes

- **GIVEN** um usuário autorizado apenas na UG da Câmara, com poder Legislativo
- **WHEN** ele pede o recorte de uma UG do Executivo
- **THEN** a resposta é `403`

#### Scenario: mesmo usuário, entes diferentes

- **GIVEN** um usuário com UGs autorizadas em um ente e nenhuma no outro
- **WHEN** ele lê os recortes nos dois
- **THEN** no primeiro vê só as UGs autorizadas e no segundo vê o que o poder dele permite

#### Scenario: usuário sem restrição de UG

- **GIVEN** um usuário sem nenhuma UG autorizada no ente
- **WHEN** ele lê os recortes disponíveis
- **THEN** o resultado é idêntico ao anterior a este requisito, filtrado só por poder

#### Scenario: recorte padrão respeita a restrição

- **WHEN** a leitura não informa recorte
- **THEN** o recorte servido é um dos visíveis ao usuário
- **AND** se nenhum for visível, a resposta é `403`

#### Scenario: escolha do exercício anterior em UG não autorizada

- **GIVEN** um usuário autorizado apenas em uma UG
- **WHEN** ele envia `anterior_por_recorte` com a chave de outra UG no reprocessamento
- **THEN** a resposta é `403`
- **AND** nenhuma escolha do pedido é gravada e nenhum job é criado

#### Scenario: fonte da autorização indisponível

- **WHEN** o serviço de autorização não responde
- **THEN** a resposta é `503` e nenhum recorte é servido
