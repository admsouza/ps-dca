# dca/fonte-msc — Delta spec

## ADDED Requirements

### Requirement: A competência da matriz de encerramento é traduzida por adapter

O domínio SHALL expressar a leitura como **competência (1–12) mais matriz**. O número que cada API
usa para chegar à matriz de encerramento SHALL ser traduzido pelo adapter da fonte, nunca pelo
serviço.

| Fonte | Tradução |
|---|---|
| SICONFI | competência 12 com `co_tipo_matriz=MSCE` — medido: `me_referencia=13` devolve zero registros nos 4 entes de homologação |
| PublicSoft | competência especial **13** (`mesMsc=13` / `meReferencia=13`); 12 é dezembro |

O gate de auditoria da PublicSoft SHALL ser consultado na **mesma** competência que será lida.
Auditar dezembro e ler o encerramento liberaria uma competência com base na validação de outra.

#### Scenario: encerramento na PublicSoft

- **WHEN** a matriz de encerramento é pedida à PublicSoft para a competência 12 do domínio
- **THEN** a consulta de saldos usa `meReferencia=13`
- **AND** a auditoria é consultada com `mesMsc=13`

#### Scenario: consolidada mantém o mês pedido

- **WHEN** a matriz consolidada é pedida para as competências 1, 6 ou 12
- **THEN** a consulta usa o próprio mês
- **AND** 12 significa dezembro

#### Scenario: encerramento no SICONFI

- **WHEN** a matriz de encerramento é pedida ao SICONFI
- **THEN** a consulta usa `me_referencia=12` e `co_tipo_matriz=MSCE`
- **AND** a competência 13 NÃO é pedida a esta fonte
