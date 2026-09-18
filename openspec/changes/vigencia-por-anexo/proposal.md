# Proposal — Vigência publicada por anexo, não só do BO

**Status:** proposta
**Repositório:** `ps-dca`
**Capability:** `pipeline/plataforma` (delta)
**Origem:** log do worker em 2026-09-18, apurando o BF do ente 2505204

## Why

O BF apura e responde, mas o worker avisa a cada job:

```
WARNING [app.services.pipeline.apuracao] sem vigência publicada para BF/2025
        — caindo no YAML versionado (semente)
```

Duas vezes por apuração (exercício e exercício anterior). O aviso está certo: a semente publica
**apenas o Balanço Orçamentário**. `semear()` chama `publicar(anexo=ANEXO_BO, ...)` com o mapa do
YAML do BO, e nenhum outro anexo entra — nem o BF, que já tem base canônica versionada.

Hoje isso é ruído com fallback correto. Passa a ser defeito quando alguém publicar uma correção de
regra do BF pela via administrativa: a vigência do banco existiria para o BO e não para o BF, e os
dois anexos passariam a ter **origens de regra diferentes** sem que nada declarasse isso.

Há um segundo ponto no mesmo caminho: `_completar_apresentacao` completa nível, ordem e colunas
ausentes com a transcrição do **BO**, qualquer que seja o anexo carregado do banco. Para o BF,
nenhum `rule_id` casa (`bf.*` contra `bo.*`), e a completação não faz nada — silenciosamente.

## What Changes

- `semear()` passa a publicar a vigência de **todos os anexos implementados** do registry, cada um
  com a sua base canônica (`bo` → IPC 07, `bf` → IPC 06) e o ano da edição correspondente.
- `_completar_apresentacao` passa a receber o demonstrativo e completar com a transcrição **daquele**
  anexo.
- O `documento` padrão da vigência deixa de ser `"IPC 07"` fixo.

**Fora de escopo:** publicar vigência por via administrativa; alterar o formato do jsonb.

## Critérios de aceite

- [ ] Após o boot, `BF/2024` está publicado no banco, com origem `seed-yaml`.
- [ ] O worker apura o BF sem o aviso de vigência ausente.
- [ ] A apuração do BF pelo banco produz os mesmos valores da apuração pelo YAML, em centavos.
- [ ] A semente continua idempotente: segundo boot não reescreve nem falha.
- [ ] Regressão do BO: mesma vigência, mesmo `versao_regras`, suíte verde.

## Casos de erro

| Situação | Comportamento esperado |
|---|---|
| Anexo do registry sem serviço implementado | não é semeado, e não falha o boot |
| Base canônica sem edição que cubra o ano | anexo pulado com aviso, os demais são semeados |
| Vigência já publicada | mantida — `PRIMARY KEY` recusa e a recusa é "já semeado", não erro |

## Aprovação do PO

- [ ] PO aprovou esta proposta em ______
