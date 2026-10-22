# Design — O exercício anterior não bloqueia a apuração

**Change:** `openspec/changes/dca-anterior-nao-bloqueia-apuracao/` · **Proposal aprovada pelo PO em:** 2026-10-22

## Contexto

`anterior.resolver` (`anterior.py:94`) levanta `ProcessadoSemAnterior` quando a origem resolvida é
Processado e N−1 não tem o recorte; `_exigir_n1` (`anexos.py:323`) tenta antecipar isso na rota com
`409`. As duas travas nasceram da change `dca-anterior-processado-manual`, cujo alvo real era outro:
impedir que a MSC de N−1 preenchesse a coluna com números não conferidos.

`0,00` escolhido e marcado no diagnóstico não é número não conferido disfarçado de dado — é a
ausência declarada. Com a apuração sempre concluindo, o impasse desaparece e a lista de unidades —
que só existe dentro do job (`_Observada`, `apuracao.py:145`) — volta pelo próprio resultado, que é
o que o front já consome.

Esta change é majoritariamente **remoção**.

## Componentes afetados

| Componente | Papel na change |
|---|---|
| `app/services/pipeline/anterior.py` | `resolver` devolve `SEM_ANTERIOR` em vez de levantar; `exigir`/`faltam_processado`/`ProcessadoSemAnterior` saem |
| `app/routes/anexos.py` | `_exigir_n1` e `_unidades_gravadas` saem, com as chamadas |
| `app/services/pipeline/apuracao.py` | `da_unidade` pede a coluna anterior zerada e marca o diagnóstico |
| `app/services/bp/quadro_principal.py` | `zero_sem_anterior` passa a valer no ramo da coluna pronta |
| `app/services/bf/quadro_principal.py` | equivalente no ramo `PROCESSADO` |

## Fluxo da informação

```text
POST/GET /dca/{anexo} → (sem validação de N−1) → job
  → com_recortes → por unidade: Processado | Manual | sem_anterior (0,00 + marca)
  → soma dos grupos e do consolidado → cache ok
GET /dca/{anexo} → resultado + diagnostico.sem_dados_exercicio_anterior por recorte
```

## Contratos / interfaces

`OrigemAnterior.SEM_ANTERIOR = "sem_anterior"`. Não é entrada pública: é **resultado** da resolução,
gravado em `procedencia.origem_exercicio_anterior` da unidade. `anterior_por_recorte` continua
aceitando `padrao`, `processado_exercicio_anterior` e `manual` — nada muda no corpo do pedido.

Na apuração: `anterior=PROCESSADO`, `anterior_pronto` com matriz vazia e o flag de coluna zerada. Os
serviços hoje tratam célula ausente da coluna pronta como `NaoApurada` (`SEM_LINHA_ANTERIOR`); com o
flag, ela vira `0,00` e nenhuma `NaoApurada` é registrada — a ausência já está dita uma vez, no
diagnóstico.

Diagnóstico: **nenhum campo novo**. `sem_dados_exercicio_anterior` (já existe, já é propagado a
grupos e consolidado em `apuracao.py:323,343` e já sai em `resultado.py:130`) passa a valer também
para a unidade que caiu em zero; `avisos_anterior` registra o motivo quando N−1 existe mas não
serve. Como cada recorte publica o próprio diagnóstico, o front já identifica a unidade.

## Impacto

| Eixo | Impacto |
|---|---|
| Banco / migration | nenhum |
| Cache | identidade do pedido inalterada; resultados `ok` existentes continuam válidos |
| Filas / worker | nenhum job novo; some uma classe inteira de falha de job |
| APIs externas | nenhuma chamada a mais |
| Regressão | BF/BP com Processado ou Manual devem sair bit a bit iguais; suíte atual é o gate |

## Decisões

### D1 — Zero automático, não escolha do usuário
**Escolhido:** `sem_anterior` é o que sobra quando não há Processado nem Manual ·
**Descartado:** terceira opção explícita no pedido, com diálogo antes de processar ·
**Porquê:** o usuário quer conferir o atual; obrigá-lo a decidir sobre o anterior para ver qualquer
número é a trava que esta change remove. Quem quiser o anterior informa Manual e reprocessa.
PO 2026-10-22.

### D2 — Sem consulta de preparação de unidades
**Escolhido:** o front lê as unidades do próprio resultado · **Descartado:** `GET /dca/{anexo}/anterior`
listando unidades por uma leitura de MSC · **Porquê:** com a apuração sempre concluindo, o resultado
já traz todas as unidades com rótulo. Uma rota a mais e uma chamada a mais à PublicSoft resolveriam
um problema que deixou de existir.

### D3 — Emissão não é travada aqui
**Escolhido:** o diagnóstico informa, a homologação decide · **Descartado:** `emissao_bloqueada` no
resultado · **Porquê:** a DCA vai ganhar módulo de homologação (em auditoria / homologado), como o
RREO. Duas travas para a mesma regra divergem. PO 2026-10-22.

### D4 — Coluna em `0,00`, não em branco
**Escolhido:** célula zerada · **Descartado:** célula não apurada
**Porquê:** o anexo precisa sair com a coluna preenchida, e célula sem valor em qualquer parcela
propaga ausência na soma (`_somar_celulas`, `anterior.py:176`) — uma UG nova apagaria a coluna
anterior do consolidado inteiro, inclusive o Manual já informado nas outras. Com `0,00`, grupo e
consolidado somam sem tratamento especial, e o diagnóstico não ganha uma `NaoApurada` por linha.
Custo: ~2 linhas em cada serviço. PO 2026-10-22.

### D5 — Sem campo novo no diagnóstico
**Escolhido:** reusar `sem_dados_exercicio_anterior` · **Descartado:** `unidades_sem_anterior` ·
**Porquê:** o campo já existe, já propaga a grupo e consolidado e já é publicado por recorte. Lista
nova diria a mesma coisa num segundo lugar, com um segundo caminho de propagação para manter.

### D6 — MSCE continua fora
**Escolhido:** manter a decisão de `dca-anterior-processado-manual` · **Porquê:** o alvo daquela
change era o número não conferido, e ele continua proibido. Esta change só desfaz a recusa, não o
fallback.

## Arquivos criados / alterados

| Arquivo | Ação |
|---|---|
| `app/services/pipeline/anterior.py` | alterar (remover exceção e helpers de recusa; `SEM_ANTERIOR`) |
| `app/routes/anexos.py` | alterar (remover `_exigir_n1`, `_unidades_gravadas` e chamadas) |
| `app/services/pipeline/apuracao.py` | alterar (`da_unidade`: coluna zerada + marca) |
| `app/services/bp/quadro_principal.py` | alterar (~2 linhas: `zero_sem_anterior` no ramo pronto) |
| `app/services/bf/quadro_principal.py` | alterar (~2 linhas: célula ausente = `0,00`) |
| `tests/pipeline/test_rota_anterior_por_recorte.py` | alterar (cenários de `409` saem) |
| `tests/recorte/test_anterior_por_recorte.py` | alterar |

## O que o código já dá de graça

- `sem_dados_exercicio_anterior`: campo, propagação e publicação prontos.
- `avisos_anterior`: o aviso por unidade já existe e já é publicado.
- `zero_sem_anterior` no BP (`quadro_principal.py:150`): o modo "coluna anterior zerada" já existe,
  hoje restrito ao ramo MSCE. Basta valer no ramo da coluna pronta.
- `_somar_celulas` soma `0,00` como qualquer valor: grupo e consolidado não mudam.
- `exigir_processado=repo is not None` (`apuracao.py:282`) existia só para a CLI não quebrar com a
  exceção. Sem a exceção, o parâmetro sai inteiro.

## Pendências conhecidas

- Módulo de homologação da DCA: change própria. A pergunta a fechar lá — homologar exige anterior
  resolvido (Processado ou Manual) em todas as unidades? Enquanto não existir, nada impede emitir um
  BP com anterior em `0,00`.
- **Cache não reage ao N−1 que chega depois.** A identidade do pedido (`cache.versao_do_pedido`)
  não considera a existência de N−1, então um N apurado em `sem_anterior` continua servido do cache
  mesmo depois de N−1 ser processado: só sai por reprocessamento explícito. Antes da change o caso
  não existia, porque o 409 impedia o primeiro resultado. Decidir com o PO se o Processado que chega
  depois deve invalidar o cache de N ou se o botão Reprocessar basta.
- **`zero_sem_anterior` no ramo MSCE do BP ficou sem chamador no pipeline**, já que `resolver` nunca
  mais devolve MSCE. Só sobrevive em chamada direta de `apurar`. Candidato a remoção numa change
  futura, junto com o resto do caminho MSCE.
- `dca-anterior-processado-manual` está em VERIFY e é parcialmente desfeita por esta change. Ao
  arquivar as duas, o delta mesclado em `openspec/specs/` deve refletir **esta** redação.
