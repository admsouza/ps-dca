# Design — BP · Compensação atual manual por recorte

**Change:** `openspec/changes/bp-compensacao-atual-manual-por-recorte/`
**Proposal:** aprovada pelo PO em 2026-10-21

## Contexto

O BP já aceita manual anterior por unidade com chaves `C:<codigo>`, possui `_totalizar()` para
folhas e tem recortes `ug:`/`po:`. O pipeline já soma colunas prontas com propagação de `None` para
grupos e consolidado. Falta transportar, validar, persistir e aplicar um mapa independente para a
coluna atual da Compensação.

## Componentes afetados

| Componente | Papel na change |
|---|---|
| `app/routes/anexos.py` | contrato, validação e autorização antes do job |
| `app/services/bp/informados.py` | aceitar somente folhas `C:*` e decimais válidos |
| `app/services/bp/quadro_principal.py` | aplicar folhas atuais, totalizar e ajustar diagnóstico |
| `app/services/pipeline/apuracao.py` | aplicar por individual e derivar grupos/consolidado |
| `app/services/pipeline/cache.py` | identidade, reaplicação, limpeza e persistência do mapa |
| `app/services/pipeline/resultado.py` | serializar a procedência manual |

## Fluxo da informação

```text
POST /dca/BP/reprocessar
→ validar forma + folhas + decimais + autorização
→ mesclar pedido com mapas gravados
→ job BP
→ apurar cada ug:/po: com seu mapa atual
→ somar resultados individuais para poder:* e consolidado
→ gravar resultado + procedência + identidade
→ GET serve o recorte escolhido
```

## Contratos / interfaces

```json
{
  "valores_atuais_por_recorte": {
    "po:10131": {"C:L2": "50.00"}
  }
}
```

Um job usa um tipo individual (`ug:` ou `po:`), conforme os recortes que a API expõe. O mapa
efetivamente aplicado fica na procedência por recorte e no rastro de topo necessário para
reaplicação após erro.

## Impacto

| Eixo | Impacto |
|---|---|
| Banco / migration | nenhum; JSONB existente |
| Cache | novo mapa por recorte na identidade e procedência; vazio remove uma entrada |
| Filas / worker | mesmo job e lock; apenas novo parâmetro validado |
| APIs externas | nenhuma chamada nova |
| Segurança | mesmas regras A01 de `anterior_por_recorte`; validação tudo ou nada |
| Regressão | outros quadros e a coluna anterior devem sair bit a bit iguais |

## Decisões

### D1 — Contrato separado da coluna anterior

**Escolhido:** `valores_atuais_por_recorte` no corpo. · **Descartado:** colocar os valores em
`anterior_por_recorte`. · **Por quê:** origem e valor anterior não podem mudar quando apenas o atual
é editado.

### D2 — Agregados derivados

**Escolhido:** `poder:*` e `consolidado` somam os individuais. · **Descartado:** mapa manual próprio
ou rateio. · **Por quê:** há uma única fonte de verdade e o consolidado já segue essa regra no
anterior.

### D3 — Reutilizar soma existente

**Escolhido:** converter os resultados individuais em colunas prontas e usar
`pipeline.anterior.somar`, aplicando ao agregado somente `CONTAS_COMPENSACAO.exercicio_atual`. ·
**Descartado:** novo motor genérico de agregação. · **Por quê:** a soma existente já preserva
ausência e `None` corretamente.

### D4 — Ausente não é zero

**Escolhido:** `None` em qualquer individual propaga `None`; `"0.00"` é zero informado. ·
**Descartado:** transformar vazio em zero ou somar parcialmente. · **Por quê:** mantém o contrato de
“não apurada” e evita publicar total incompleto.

### D5 — Sem schema novo

**Escolhido:** cache e procedência JSONB existentes. · **Descartado:** tabela de valores manuais. ·
**Por quê:** o ciclo de vida é o mesmo do resultado por ente/exercício/anexo.

## Arquivos criados / alterados

| Arquivo | Ação |
|---|---|
| `openspec/changes/bp-compensacao-atual-manual-por-recorte/**` | criar |
| `app/routes/anexos.py` | alterar |
| `app/services/bp/informados.py` | alterar |
| `app/services/bp/quadro_principal.py` | alterar |
| `app/services/pipeline/apuracao.py` | alterar |
| `app/services/pipeline/cache.py` | alterar |
| `app/services/pipeline/resultado.py` | alterar |
| `tests/bp/test_compensacao_atual_manual.py` | criar |
| `tests/pipeline/test_compensacao_atual_por_recorte.py` | criar |

## Pendências conhecidas

- Reconciliar o requisito vigente após o arquivamento de `bp-superavit-por-fonte`.
- Medição viva usará os POs reais de Cuitegi; os valores não nulos de soma são fixtures controladas.
