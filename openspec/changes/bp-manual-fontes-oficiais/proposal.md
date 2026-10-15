# Proposal — BP manual com catálogo oficial de fontes

**Status:** aprovada pelo PO em 2026-10-15
**Repositório:** `ps-dca`
**Capability:** `dca/balanco-patrimonial` (existente)
**Anexo DCA:** `DCA-Anexo I-AB`
**Base normativa:** IPC 04 · Anexo I da Portaria STN nº 710/2021, atualizado pela Portaria STN/MF nº 2.897/2025 · `docs/contas-stn/fonte-recursos.md`
**Front pareado:** `C:\Projetos\front-declaracoes\openspec\changes\dca-bp-fontes-oficiais-manual\`

## Why

O modo Manual do BP aceita chaves `S:<fonte>` para o Quadro do Superávit / Déficit Financeiro. Hoje
o backend verifica apenas se a fonte tem quatro dígitos. Assim, `S:1999` passa pela borda mesmo sem o
código principal `999` existir no catálogo canônico da STN.

O próprio backend já mantém a tabela oficial e a usa para nomear as linhas apuradas. O catálogo e a
validação manual devem compartilhar essa fonte da verdade. O frontend precisa consultar o catálogo,
sem copiar a tabela normativa para seu bundle.

## What Changes

- `GET /dca/fontes-recursos` publica os códigos completos de quatro dígitos e suas nomenclaturas.
- Para cada código principal oficial de três dígitos, a resposta oferece os prefixos `1` (exercício
  corrente) e `2` (exercícios anteriores), na mesma regra usada pelo quadro apurado.
- A validação de `S:<fonte>` exige prefixo `1` ou `2` e código principal existente no catálogo.
- A geração de rótulos das linhas apuradas e o endpoint usam um único carregador do catálogo.
- Código manual inválido responde `422` antes de enfileirar qualquer job.

**Fora de escopo:** alterar a apuração do quadro; validar complemento de fonte; banco ou migration;
consulta externa à STN em tempo de requisição; modificar a change ativa `bp-superavit-por-fonte`.

## Entradas e saídas

| Interface | Entrada | Saída |
|---|---|---|
| `GET /dca/fontes-recursos` | JWT válido | `200 {"fontes": [{"codigo": "1500", "nome": "Recursos não Vinculados de Impostos"}, ...]}` |
| `POST /dca/BP/reprocessar` | manual com `S:<fonte>` | `202` se oficial; `422` se código ausente no catálogo |

O catálogo SHALL ser ordenado por `codigo`, sem duplicidade. A rota não lê MSC, não consulta serviço
externo e não enfileira job.

## Exemplo concreto

| Ente | Exercício | Anexo | Entrada | Valor esperado |
|---|---|---|---|---|
| `2505204 — Cuitegi/PB` | 2025 | I-AB | `S:1621 = 20000.00` | aceito; nome `Transferências Fundo a Fundo de Recursos do SUS provenientes do Governo Estadual` |
| `2505204 — Cuitegi/PB` | 2025 | I-AB | `S:1999 = 20000.00` | `422`; zero jobs enfileirados |

## Critérios de aceite

- [x] Para `N` códigos principais válidos no arquivo canônico, a rota devolve exatamente `2 × N` opções únicas.
- [x] `1621` e `2621` usam a nomenclatura oficial de `621`; `2621` acrescenta ` - Exercícios Anteriores`.
- [x] 100% dos códigos devolvidos pela rota são aceitos pela validação de `S:<fonte>`.
- [x] 100% dos códigos ausentes do domínio são recusados com `422` antes da fila.
- [x] A apuração do BP e os valores do quadro permanecem bit a bit iguais.

## Casos de erro

| Situação | Comportamento esperado |
|---|---|
| Sem JWT ou JWT inválido | `401`, sem expor detalhes internos |
| `S:1999` ou outro código principal inexistente | `422`, sem job |
| `S:3621`, prefixo diferente de `1`/`2` | `422`, sem job |
| Arquivo canônico ausente ou malformado no boot/teste | falha explícita; não publicar catálogo parcial |

## Restrições e riscos

- O arquivo canônico continua sendo atualizado por change normativa e protegido pelos checksums já
  existentes; a rota não baixa tabelas em runtime.
- A rota expõe somente classificação pública da STN, sem dados de ente, usuário ou credencial.
- O repositório contém alterações locais não relacionadas; a implementação deverá preservar esse
  working tree e limitar o diff aos arquivos declarados no design.

## Aprovação do PO

- [x] PO aprovou esta proposta em 2026-10-15 — gate para a fase PLAN/ARCH
