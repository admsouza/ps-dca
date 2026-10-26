# Design — Regra da célula

## D1 — Uma projeção da `Linha`, origem por anexo

A projeção (`contas`, `fontes`, `natureza`, `filhas`, `tipo`) lê o modelo que a apuração já usa. A origem do saldo é uma função registrada por base canônica. Hoje só `bf` registra. BO e os anexos sem serviço respondem `404` até registrar a sua. Alternativa descartada: embutir a regra no JSON do demonstrativo — iria para todo usuário e inchava o cache.

## D2 — A apuração e a consulta compartilham a origem

`origem_da_celula` fica em `app/services/bf/origem.py`, sem importar a MSC, e `_origens` a chama. Coluna que termina em `_anterior` usa o conjunto do exercício anterior; a outra usa o do exercício atual. Assim L28 anterior continua `abertura`. A rota não alcança `app.infra.msc`.

## D3 — Perfil no hub, não no JWT

O token só traz `sub`. A rota chama `GET {AUTH_API_URL}/usuarios/me` com timeout de 5s e guarda o booleano por 60s, chaveado pelo hash do token. Fail closed se o hub não responde.

## Arquivos

| Arquivo | Papel |
|---|---|
| `app/domain/bo/regra_celula.py` | projeção pura |
| `app/services/bf/origem.py` | `origem_da_celula` e os conjuntos por linha |
| `app/services/bf/quadro_principal.py` | `_origens` usa a mesma função |
| `app/services/regra_celula.py` | consulta por anexo |
| `app/auth/perfil.py` | flag do hub |
| `app/routes/anexos.py` | `GET /dca/{anexo}/regra` |
| `front-declaracoes` | diálogo e predicado `podeConsultarMapeamento` |
