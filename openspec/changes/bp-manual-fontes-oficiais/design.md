# Design — BP manual com catálogo oficial de fontes

**Change:** `openspec/changes/bp-manual-fontes-oficiais/` · **Proposal aprovada pelo PO em:** 2026-10-15

## Contexto

`app/services/bp/quadro_principal.py` possui um parser privado de
`docs/contas-stn/fonte-recursos.md` para rotular linhas apuradas. Já
`app/services/bp/informados.py` aceita qualquer regex de quatro dígitos. O desenho centraliza leitura,
rótulo e validação sem duplicar a tabela no front ou em constantes Python.

## Componentes afetados

| Componente | Papel na change |
|---|---|
| `app/services/bp/fontes.py` | carregar o catálogo, montar códigos completos, rotular e validar |
| `app/services/bp/quadro_principal.py` | reutilizar o rótulo compartilhado |
| `app/services/bp/informados.py` | validar `S:<fonte>` pelo domínio canônico |
| `app/routes/anexos.py` | expor `GET /dca/fontes-recursos` autenticado |
| `tests/bp/test_fontes_oficiais.py` | catálogo, ordenação, rótulos e domínio |
| `tests/pipeline/test_rota_anterior_por_recorte.py` | `422` antes da fila para fonte inválida |

## Fluxo da informação

```text
fonte-recursos.md → service puro/cacheado → GET catálogo → frontend
                                      └→ validação S:<fonte> antes da fila
                                      └→ rótulo das linhas apuradas
```

## Contratos / interfaces

```json
{
  "fontes": [
    {"codigo": "1500", "nome": "Recursos não Vinculados de Impostos"},
    {"codigo": "2500", "nome": "Recursos não Vinculados de Impostos - Exercícios Anteriores"}
  ]
}
```

O carregador retorna uma coleção imutável/cacheada e falha se encontrar código duplicado,
nomenclatura vazia ou tabela sem registros. A validação recebe o código completo e não depende da
rota, da MSC ou do cache de anexos.

## Impacto

| Eixo | Impacto |
|---|---|
| Banco / migration | nenhum |
| Cache | nenhum; apenas cache em memória do arquivo normativo |
| Filas / worker | nenhum; entrada inválida é recusada antes da fila |
| APIs externas | nenhuma chamada nova |
| Regressão | resultados e rótulos apurados devem permanecer bit a bit iguais |

## Decisões

### D1 — Catálogo servido pelo backend
**Escolhido:** endpoint autenticado derivado do arquivo canônico. · **Descartado:** JSON/constante no
frontend. · **Porquê:** uma única fonte normativa elimina divergência entre validação e interface.

### D2 — Domínio completo gerado por prefixo
**Escolhido:** gerar `1xxx` e `2xxx` para cada código principal `xxx`. · **Descartado:** aceitar
qualquer primeiro dígito. · **Porquê:** são os identificadores de exercício corrente e exercícios
anteriores já usados pelo BP; outros prefixos não têm rótulo normativo nesse fluxo.

### D3 — Falha fechada
**Escolhido:** arquivo ausente/malformado ou código desconhecido interrompe catálogo/validação. ·
**Descartado:** usar o código como rótulo ou aceitar regex. · **Porquê:** fallback silencioso volta a
permitir dado sem vínculo oficial.

### D4 — Rota sem contexto de ente
**Escolhido:** JWT válido, sem `id_ente`, MSC ou autorização por unidade. · **Descartado:** acoplar o
catálogo público a uma apuração. · **Porquê:** a classificação é pública e igual para todos os entes;
o JWT mantém o padrão de acesso da API sem criar IDOR.

## Arquivos criados / alterados

| Arquivo | Ação |
|---|---|
| `app/services/bp/fontes.py` | criar |
| `app/services/bp/quadro_principal.py` | alterar |
| `app/services/bp/informados.py` | alterar |
| `app/routes/anexos.py` | alterar |
| `tests/bp/test_fontes_oficiais.py` | criar |
| `tests/pipeline/test_rota_anterior_por_recorte.py` | alterar |

## Pendências conhecidas

- Catálogos históricos por exercício não entram: o backend hoje possui uma tabela canônica vigente.
  Se versões históricas forem adicionadas, o contrato deverá ganhar `anReferencia` em change própria.
