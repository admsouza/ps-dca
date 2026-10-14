# dca/balanco-patrimonial — Delta spec

## ADDED Requirements

### Requirement: Coluna anterior manual do BP por unidade

O BP SHALL aceitar `anterior=manual` para uma unidade (`ug:`/`po:`), com os valores da coluna do
exercício anterior informados por linha folha:

| Chave | Linha |
|---|---|
| `P:<codigo>` | folha do Quadro Principal (`QUADRO_PRINCIPAL`) |
| `FP:<codigo>` | folha do quadro de ativos e passivos financeiros e permanentes (`ATIVOS_PASSIVOS_FINANCEIROS`) |
| `C:<codigo>` | folha das contas de compensação (`CONTAS_COMPENSACAO`) |
| `S:<fonte>` | uma linha do Superávit/Déficit por fonte, com a fonte em 4 dígitos |

As totalizadoras e o `Total` do Superávit SHALL sair da soma das folhas, pela calculation e pelas
referências que o motor já usa. Uma folha não informada SHALL ficar **não apurada**, nunca 0,00.

No Superávit, as linhas SHALL ser a união das fontes apuradas em N com as fontes informadas. A fonte
informada que não existe em N SHALL ter atual 0,00. A procedência da unidade SHALL declarar
`origem_exercicio_anterior = manual` e os `valores_anteriores` usados.

Validação, antes do job (`422`):
- chave sem prefixo conhecido;
- código inexistente no quadro;
- linha totalizadora;
- fonte que não tem 4 dígitos;
- valor não decimal.

O manual NÃO DEVE valer para o consolidado do BP.

Base normativa: IPC 04, coluna "Exercício Anterior".

#### Scenario: Câmara digitada
- **GIVEN** Cuitegi 2025, `ug:<Câmara>` em manual com `P:L3 = 100.00`, `P:L4 = 50.00` e `S:1500 = 20.00`
- **THEN** a coluna anterior da Câmara traz `L3` (Caixa e Equivalentes) = 100,00 e `L4` (Créditos a Curto Prazo) = 50,00, e a totalizadora `L2` (Ativo Circulante) sai pela calculation
- **AND** o Superávit traz a linha `1500` com anterior 20,00, e `Total` anterior = Σ das fontes informadas

#### Scenario: folha não informada
- **GIVEN** um manual sem `P:L5`
- **THEN** `L5` anterior fica não apurada, com o motivo "não informado"

#### Scenario: manual no consolidado
- **WHEN** chega `origem_exercicio_anterior=manual` para o consolidado do BP
- **THEN** `422`

#### Scenario: totalizadora informada
- **WHEN** o manual traz `P:<codigo de totalizadora>`
- **THEN** `422`, sem job
