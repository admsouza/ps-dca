# <domínio>/<capability> — Delta spec

## Purpose
<Só para capability nova: o que esta capability garante, em uma ou duas frases.>

## ADDED Requirements

### Requirement: <nome do requisito>
O sistema SHALL <comportamento observável obrigatório>.
<Condições de contorno, unidades, arredondamento, o que NÃO deve acontecer.>

#### Scenario: <caso feliz>
- **GIVEN** <estado inicial>
- **WHEN** <ação>
- **THEN** <resultado observável e medível>

#### Scenario: <caso de erro>
- **WHEN** <entrada inválida>
- **THEN** <erro esperado>, sem persistir estado parcial

## MODIFIED Requirements

### Requirement: <nome do requisito existente>
<Texto completo do requisito já com a alteração — não só o diff.>

#### Scenario: <cenário atualizado>
- **WHEN** ...
- **THEN** ...

## REMOVED Requirements

### Requirement: <nome>
**Motivo:** <por que deixa de valer> · **Migração:** <o que substitui>
