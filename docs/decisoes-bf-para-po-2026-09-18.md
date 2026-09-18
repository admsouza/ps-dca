# Balanço Financeiro — decisões para o PO

**Data:** 2026-09-18 · **Change:** `openspec/changes/bf-apuracao-f1`
**Evidência completa:** `docs/evidencia-bf-medicao-2026-09-18.md`
**Gabaritos:** `docs/entes-homologacao/<ente>/gabarito-bf-2025.md` · de-para em
`docs/depara-bf-siafic-ipc06.md`

Tudo abaixo foi **medido**: regras do IPC 06 sobre a MSC da API do SICONFI, direção do saldo pelo
PCASP da STN, confrontado com o BF publicado pelos SIAFIC de 5 entes. Nenhuma regra canônica foi
alterada para fazer número fechar.

---

## Onde estamos

| Ente | Linhas que batem em centavos | Divergem | Não apuráveis |
|---|---|---|---|
| **Recife/PE** | **42 de 66** | 18 — das quais **12 são só propagação** de uma filha | 6 |
| João Pessoa/PB | 40 de 66 | 20 | 6 |
| Porto Alegre/RS | 17 de 65 | 43 — recorte incomparável (ver D6) | 5 |

Em Recife, o demonstrativo apurado fecha consigo mesmo com **18.025.391,58** de resíduo em 22,3
bilhões (0,08%). As causas-raiz de tudo que não fecha são **seis**, e quatro delas são as decisões
abaixo.

---

## D1 · G8 — as 6 linhas sem conta no IPC 06

**Em jogo:** `L22`, `L23`, `L28`, `L55`, `L56`, `L61`. Recife publica **4,13 bilhões** nelas.

**Medido:** procuramos esses valores na MSC em **7 combinações** (MSCE e MSCC × abertura,
encerramento e período × exercício e anterior), em **todos os prefixos de conta de 3 a 9 dígitos**,
como saldo, como soma de créditos e como soma de débitos:

| Linha | Publicado por Recife | Existe na MSC? |
|---|---|---|
| `L22` Resgates de Investimentos | 370.110.128,29 | **não** |
| `L55` Transferências para Investimentos | 690.544.116,24 | **não** |
| `L28` Outros Recebimentos Extraorçamentários | 1.629.640.087,52 | **não** |
| `L61` Outros Pagamentos Extraorçamentários | 1.640.655.129,62 | **não** |

A busca foi validada por **controle**: a mesma rotina acha `L16` (10.938.332.536,31 → conta
`3.5.1.1.2.02.00`) e `L25` (74.205.408,29 → conta `5.3.1.7`). "Não achar" aqui é resultado, não
falha do método.

A hipótese anterior — apurar `L22`/`L55` pela variação de `1.1.4` e `1.2.1.3` — **não se sustenta**:
em Recife `1.1.4` varia +710.419.938,88 no exercício, `1.1.2.1` varia −57.745.528,96 e `1.2.1.3` não
tem movimento nenhum. Nenhuma combinação chega aos valores publicados.

> **Recomendação: opção (b)** — manter `review_required` e declarar as 6 linhas como **não apuráveis
> pela MSC**, com o motivo no diagnóstico. O BF sai com o buraco **declarado**, não estimado.
>
> **Se decidir (a)** (apurar por variação patrimonial): entregaríamos número que a medição mostra
> estar errado, com aparência de certo — o pior resultado possível num demonstrativo contábil.

---

## D2 · G5 — o que uma linha não apurável faz com o total

**Em jogo:** `L21`, `L24`, `L33`, `L54`, `L57` e `L66` têm parcela entre as 6 linhas de D1.

**Medido:** com a opção (a), Recife entrega 42 linhas certas e os totais saem. Com a opção (b)
(propagar `None`), **nenhum total sai** — o BF inteiro fica em branco por causa de 6 linhas, mesmo
com 42 corretas.

> **Recomendação: opção (a)** — parcela inexistente contribui zero, e o diagnóstico nomeia cada
> linha que faltou. É o mesmo tratamento que o BO já dá à célula suprimida.

---

## D3 · G9 refinado — o tipo de saldo é **por linha**, não por demonstrativo

A decisão de 2026-09-14 (MSCE, saldo de abertura) está certa para a maior parte, mas não para tudo.
Três origens cobrem o demonstrativo inteiro, e as três foram medidas contra o publicado:

| Origem | Linhas | Prova |
|---|---|---|
| MSCE/abertura do exercício | fluxos e saldo final (`L62`–`L65`) | `L63` = 1.279.005.988,75, igual ao publicado |
| MSCE/**encerramento** | `L25`, `L26` | contas `5.3.1.7` e `5.3.2.7` **não existem na abertura**; no encerramento valem 74.205.408,29 e 106.062.740,96 — exatamente o publicado |
| MSCE/abertura do **exercício anterior** | `L29`–`L32` | 802.570.332,31 (`1.1.1` de 2024) + 717.721,98 (`1.1.3.5.1`) = **803.288.054,29**, o publicado |

Descoberta que explica o resto: **MSCE/abertura do exercício é a posição final**, não a de 1º de
janeiro. Em Recife ela devolve 1.308.763.064,41 — que é `L63 + L64` publicados. A mesma regra, lida
em exercícios diferentes, produz `L29` e `L62`.

> **Recomendação:** manter MSCE e declarar o tipo de saldo **por linha** na base canônica, com a
> procedência dizendo qual origem cada linha usou. Sem isso, `L25`, `L26` e `L29`–`L32` saem zeradas
> ou erradas **sem erro nenhum aparecer**.

---

## D4 · G7 e G1 — confirmados, sem contraparte

- **G7 (direção do saldo por conta):** com ela, as 22 linhas por fonte fecham em centavos. A regra do
  IPC já traz o sinal do par redutor (`6.2.1.2 (+)` / `6.2.1.3 (−)`), então a direção da coluna
  deixa de ser necessária. **Nenhum efeito no BO**, que continua com direção de coluna.
- **G1 (fonte de recursos):** descartar o 1º dígito (exercício da vinculação) e casar os 3 seguintes
  por igualdade. Confirmado nos 3 entes medidos.

> **Recomendação:** aprovar as duas como estão. Não há alternativa que produza os números publicados.

---

## D5 · G6 — núcleo único (`app/domain/bo/` → `app/domain/nucleo/`)

**Medido, sem querer:** a apuração do BF inteiro rodou **sobre o motor do BO sem alterar uma linha
dele** — carregador de regras, filtros, matriz, agregação, condições, resíduos. A única coisa
trocada foi a função de saldo da célula (D4). O motor **já é genérico**; o nome é que não é.

> **Recomendação: opção (a)** — renomear nesta change, antes de o BF importar `MapaBO`. A alternativa
> é duplicar ~500 linhas ou conviver com um BF que importa "BO" para sempre.

---

## D6 · Base de homologação — o que cada ente pode provar

| Ente | Serve para | Ressalva |
|---|---|---|
| **Recife/PE** | homologação principal | nenhuma — 66 linhas 1:1 com o IPC 06 |
| **Belo Horizonte/MG** | 2ª referência | PDF é OCR; 2 células duvidosas marcadas |
| **João Pessoa/PB** | robustez com agregação | não é 1:1 por linha; **por bloco fecha em 0,00**: `L8+L9+L10` = 580.159.482,56 e `L41+L42+L43` = 529.816.473,72 |
| **Cuitegi/PB** | robustez com omissão | publica 48 das 66 linhas |
| **Porto Alegre/RS** | **não homologa hoje** | PDF é da **administração direta**, MSC é consolidada: `L11`–`L14` saem 2,27 bi contra zero publicado |

> **Decisão pedida:** aceitar Recife como caso de referência do aceite (no lugar de João Pessoa) e
> tratar Porto Alegre como fora da homologação enquanto não houver recorte equivalente.

---

## D7 · Duas divergências que **não** são nossas

1. **`L9`/`L42` em Recife** — 450.202.814,72 de receita e 260.723.445,80 de despesa vêm de 2
   registros na conta sintética `6.2.1.2.0.00.00` **sem fonte de recursos na MSC**. O ente os
   classificou em "Demais Vinculações Legais"; nós não temos como saber a fonte. Vira **resíduo no
   diagnóstico** — nunca zero silencioso, nunca rateio por conta própria.
2. **`L27`/`L60`** — o movimento **bruto** de depósitos restituíveis não existe na API. Saldo de
   `2.1.8.8`: 132.890.609,07 (2024) → 176.421.602,57 (2025), variação +43.530.993,50; `period_change`
   da MSCC dá −6.107.254,33; o publicado implica +123.944.269,55. Três números, nenhum igual: o que
   o ente chama de depósitos não é `2.1.8.8 + 2.2.8.8`.

> **Recomendação:** ambas entram como divergência **declarada** no resultado, com valor e hipótese.
> Não são motivo para alterar a regra canônica.

---

## D8 · G11 — item 38 (intraorçamentárias)

**Em jogo:** a policy `ipc06.exclusao_de_intraorcamentarias` declara o conceito e **não diz quais
códigos** caracterizam a transferência intra acompanhada de execução.

**Medido:** aplicada pela interpretação natural — excluir receita das categorias 7 e 8 e despesa com
modalidade de aplicação 91 — ela **quebra o que já batia**:

| Ente | `L1` sem item 38 | `L1` com item 38 | `L1` publicado | Efeito |
|---|---|---|---|---|
| Belo Horizonte | **20.523.952.374,89** | 19.261.638.788,12 | 20.523.952.374,89 | afasta (batia em centavos) |
| João Pessoa | **5.117.875.296,33** | 4.988.347.452,09 | 5.117.875.296,33 | afasta (batia em centavos) |
| Recife | 9.939.848.008,46 | 9.471.717.975,89 | 10.390.050.823,18 | afasta |
| Cuitegi | 89.752.313,29 | 89.752.313,29 | 50.723.704,91 | neutro — não há intra no ente |

> **Recomendação: (a) não aplicar**, com a policy declarada e não executada e a medição anexa. A
> alternativa é quebrar 4 linhas que conferem, sem nenhum ente onde melhore de forma inequívoca.
> Definir o escopo com o STN é o caminho correto no longo prazo, mas depende de terceiro.

---

## D9 · Coluna do exercício anterior — duas origens

**Requisito do PO, 2026-09-18.** A coluna do exercício anterior **SHALL** aceitar duas origens, à
escolha de quem apura:

1. **MSCE do exercício anterior** (padrão) — apurada pelas mesmas regras do IPC 06. É o que os
   relatórios de auditoria já trazem.
2. **Preenchimento manual**, linha a linha — porque o ente pode ter publicado o exercício anterior
   com números que a matriz daquele ano não reproduz: em Recife, `L17` e `L50` de 2024 saem
   628.456.869,17 da MSC contra **0,00** publicado.

A procedência declara a origem; linha não informada é `None`, nunca `0`; as identidades do IPC 06
continuam exigidas sobre o que for informado. Já está na proposal e na `tasks.md` (2.11b).

> **Decisão pedida:** confirmar o padrão (`MSCE` do exercício anterior) e se o modo manual entra
> nesta change ou em change própria.

---

## D10 · Registro sem fonte de recursos no total da receita e da despesa

**Medido:** o RREO Anexo 01 do próprio ente é uma terceira fonte, independente do PDF. Em **13 de 15**
confrontos o apurado bate em centavos com ele. A única exceção é Recife, e a causa é de composição:

| | valor |
|---|---|
| Receita apurada **direto das contas** `6.2.1.2 (+)` / `6.2.1.3 (−)` | **10.390.050.823,18** (= RREO = BF) |
| `L1` composta pelo IPC 06 (`L2 + L3 + L11`, todas por fonte) | 9.939.848.008,46 |
| Diferença: 2 registros na conta sintética `6.2.1.2.0.00.00` **sem fonte na MSC** | 450.202.814,72 |

| Opção | Consequência |
|---|---|
| (a) manter a composição do IPC 06 e **declarar o resíduo** no diagnóstico **(recomendado)** | fiel à regra; o total sai menor que o publicado, com a causa nomeada e o valor exato |
| (b) apurar `L1`/`L34` direto das contas | bate com RREO e BF, mas **contraria o IPC 06**, que define a linha como soma das filhas |
| (c) ratear o registro sem fonte entre as linhas por fonte | inventa classificação que o ente não declarou |

> **Recomendação: (a)**, com o total direto publicado no diagnóstico como conferência — assim o
> usuário vê o valor pela regra, o valor direto e a diferença, sem que nenhum dos dois seja escondido.

---

## O que acontece depois do aceite

Com D1–D5 aprovados, a implementação é a fatia já desenhada em `tasks.md`: renomear o núcleo,
`fonte_recurso` no motor, tipo de saldo por linha, serviço `app/services/bf/` e CLI — e o aceite
passa a ser **42 de 66 linhas em centavos em Recife**, com as 6 de D1 declaradas e as 18 restantes
explicadas uma a uma.

**Ainda sem resposta** (não bloqueiam o gate): o resíduo de −972.846.807,25 em João Pessoa, a coluna
do exercício anterior e o Quadro Anexo, nenhum deles medido até aqui.

---

### Decisões pedidas

- [ ] **D1 (G8)** — (b) declarar não apurável **[recomendado]** ou (a) apurar por variação patrimonial
- [ ] **D2 (G5)** — (a) parcela inexistente **[recomendado]** ou (b) propagar `None`
- [ ] **D3 (G9)** — tipo de saldo por linha **[recomendado]**
- [ ] **D4 (G7/G1)** — aprovar como medido **[recomendado]**
- [ ] **D5 (G6)** — renomear o núcleo nesta change **[recomendado]**
- [ ] **D6** — Recife como caso de referência; Porto Alegre fora da homologação
- [ ] **D8 (G11)** — (a) não aplicar o item 38 **[recomendado]** ou (b) aplicar por categoria 7/8 e modalidade 91
- [ ] **D10** — registro sem fonte: (a) declarar resíduo **[recomendado]**, (b) total direto, (c) ratear
- [ ] **D9** — coluna do exercício anterior: confirmar padrão `MSCE` e se o modo manual entra nesta change
