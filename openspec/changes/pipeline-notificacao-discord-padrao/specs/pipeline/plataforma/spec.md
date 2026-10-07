# pipeline/plataforma — Delta spec

## MODIFIED Requirements

### Requirement: Conclusão de job é notificada

O fim de um job SHALL ser notificado no canal de operação configurado, no mesmo padrão do RREO e do
RGF: título `DCA <anexo> — Concluído ✅` (verde) ou `DCA <anexo> — Falhou ❌` (vermelho), e corpo com
o ente, o exercício e a duração. O ente SHALL aparecer como `Cidade - UF`, lido de
`public.unidade_gestora` pelo `cod_ibge`. Ente ausente da tabela, ou consulta que falhe, SHALL cair
no código IBGE sem impedir a notificação. A duração SHALL seguir o formato dos irmãos: segundos com
uma casa abaixo de um minuto (`18.7s`) e minutos com segundos inteiros acima (`1m 13s`).

Nenhum campo da mensagem SHALL sair como `None`. A notificação NÃO DEVE alterar o desfecho do job:
falha ao notificar é registrada em log e o resultado permanece gravado.

#### Scenario: job concluído com sucesso

- **GIVEN** o BF de Cuitegi (`2505204`), exercício 2025, apurado em 18.700 ms
- **AND** `unidade_gestora` com `cod_ibge = 2505204`, `cidade = Cuitegi`, `uf = PB`
- **WHEN** o job termina e grava o resultado
- **THEN** o título é `DCA BF — Concluído ✅` e a cor é verde
- **AND** o corpo é `**Cuitegi - PB** | 2025 | Tempo: 18.7s`

#### Scenario: job com erro também notifica

- **WHEN** um job termina em erro
- **THEN** o título é `DCA <anexo> — Falhou ❌` e a cor é vermelha
- **AND** o corpo traz o ente, o exercício e o motivo em bloco de código, truncado em 900 caracteres

#### Scenario: ente ausente da tabela de unidades

- **GIVEN** um `cod_ibge` que não está em `unidade_gestora`
- **WHEN** a notificação é montada
- **THEN** o ente aparece como o código IBGE

#### Scenario: banco indisponível ao resolver o ente

- **GIVEN** o banco fora do ar no momento da notificação
- **WHEN** um job termina
- **THEN** a notificação sai com o código IBGE
- **AND** o desfecho do job não muda

#### Scenario: duração no padrão dos irmãos

- **WHEN** a duração é 850 ms, 18.700 ms, 73.000 ms e 128.000 ms
- **THEN** ela é exibida como `0.9s`, `18.7s`, `1m 13s` e `2m 8s`

#### Scenario: canal de notificação indisponível

- **GIVEN** o canal de notificação fora do ar
- **WHEN** um job termina
- **THEN** o resultado permanece gravado no cache
- **AND** a falha de notificação é registrada em log, sem alterar o estado do job

#### Scenario: notificação não configurada

- **WHEN** nenhum canal está configurado
- **THEN** o job roda normalmente e nada é notificado

## ADDED Requirements

### Requirement: Requisição recebida é notificada

Todo pedido que enfileira job SHALL ser notificado no canal de operação ao ser aceito, em azul, com
o título `DCA <anexo> — Requisição Recebida (<modo>) [Anual] — <e-mail>` para um anexo e
`DCA — Requisição Recebida (<modo>) [Anual] — <e-mail>` para o percurso completo. `<modo>` é
`Processar` ou `Reprocessar`. O corpo SHALL trazer o ente (`Cidade - UF`), o exercício, a fonte MSC
(`SICONFI` ou `MSC-SIAFIC`) e a fila (`Fila => BO, BF, BP`). Pedido respondido do cache, sem job, NÃO
DEVE notificar. Falha ao notificar NÃO DEVE mudar a resposta do pedido.

#### Scenario: anexo enfileirado

- **GIVEN** `POST /dca/BP/reprocessar` de `jackson@x` para Cuitegi 2025, fonte SICONFI
- **WHEN** o job é enfileirado
- **THEN** sai `DCA BP — Requisição Recebida (Reprocessar) [Anual] — jackson@x`, em azul
- **AND** o corpo traz `Cuitegi - PB`, `2025`, `Fonte MSC: SICONFI` e `Fila => BP`

#### Scenario: percurso enfileirado

- **WHEN** `POST /batch-jobs` enfileira BO, BF e BP
- **THEN** sai `DCA — Requisição Recebida (Processar) [Anual] — <e-mail>`
- **AND** o corpo traz `Fila => BO, BF, BP`, só com os anexos que serão apurados

#### Scenario: leitura servida do cache não notifica

- **WHEN** `GET /dca/{anexo}` responde `200` do cache
- **THEN** nenhuma mensagem de requisição recebida é enviada
