# Análise da fonte — IPC 06 (Balanço Financeiro), edição 2024-06

Insumo da change `ipc06-bf-regras-canonicas`. Registra o que o PDF **não** resolve sozinho e
como cada ponto foi decidido. O literal divergente nunca é apagado: fica em `evidence.text` da
regra correspondente.

- **PDF:** `docs/referencia/ipc/IPC06 - Balanço Financeiro_2024- 2.pdf` — 19 páginas,
  sha256 `e663ffe5ee0376fd03e7cd340e79a9f6a4a8e265e9e4863098f7f1773dc1d097`
- **Extração:** `python -m scripts.extract_ipc ipc06` → `knowledge/sources/ipc06/extracted.md`
- **Regras:** pp. 10–13 (Quadro Principal, 66 linhas) e pp. 14–15 (Quadro Anexo, 14 linhas)
- **Estrutura de publicação:** pp. 16–19 — não gera regra executável

Nenhuma página do IPC 06 é paisagem rotacionada. As pp. 14–15 são landscape com rotação 0, e a
ordem de leitura já entrega as células corretas — por isso `rotated_pages: []` no metadata, e o
agrupamento geométrico usado no IPC 07 fica desligado aqui.

## Decisões do PO — 2026-09-14

### F1 — `<conta de controle>` em L22, L23, L55 e L56
As quatro linhas do grupo "Outras Movimentações Financeiras" mapeiam para `<conta de controle>`
(itens 31–33, p. 9). O item 20 (e), p. 7, diz apenas que são contas das **classes 7 e 8**; a conta
concreta é criada por cada ente. **Decidido:** `status: review_required`, com o candidato
(classes 7 e 8) registrado em `review.candidate` e **não** aplicado em `columns`. O bloqueio sai
quando o plano de contas do ente for consultado — não é bloqueio da entrega da base.

### F2 — `<contas sob demanda>` em L28 e L61
"Outros Recebimentos/Pagamentos Extraorçamentários" contemplam situações não previstas no
mapeamento, "cabendo a cada ente adaptá-los" (item 29, p. 9). **Decidido:** mesmo tratamento de
F1. São, com as quatro de F1, as **6 únicas** linhas `review_required` da base do BF.

### F3 — "nas fontes aplicáveis"
Onze linhas de ingresso e onze de dispêndio compartilham o mesmo mapeamento contábil e só se
distinguem pela fonte de recursos (itens 22–24, pp. 8–9). **Decidido:** os subgrupos do IPC 06
correspondem aos blocos do Anexo I da Portaria STN nº 710/2021, atualizado até a Portaria STN/MF
nº 2.897/2025 — `docs/contas-stn/fontes-recursos-stn-2026.xlsx`, registrado com SHA-256 em
`knowledge/sources/stn/metadata.yaml`.

| Linha (ingresso / dispêndio) | Bloco do Anexo I | Fontes |
|---|---|---|
| L2 / L35 | RECURSOS LIVRES (NÃO VINCULADOS) | `500`–`503` |
| L4 / L37 | RECURSOS VINCULADOS À EDUCAÇÃO | `540`–`599` (20 códigos) |
| L5 / L38 | RECURSOS VINCULADOS À SAUDE *(sem acento no Anexo)* | `600`–`659` (15) |
| L6 / L39 | RECURSOS VINCULADOS À ASSISTÊNCIA SOCIAL | `660`–`669` (5) |
| L7 / L40 | RECURSOS VINCULADOS À PREVIDÊNCIA SOCIAL, menos o RPPS | `803`, `804` |
| L8 / L41 | DEMAIS VINCULAÇÕES DECORRENTES DE TRANSFERÊNCIAS | `700`–`749` (26) |
| L9 / L42 | DEMAIS VINCULAÇÕES LEGAIS | `750`–`799` (15) |
| L10 / L43 | OUTRAS VINCULAÇÕES | `880`, `898`, `899` |
| L12 / L45 | RPPS — Fundo em Capitalização | `800` |
| L13 / L46 | RPPS — Fundo em Repartição | `801` |
| L14 / L47 | RPPS — Taxa de Administração | `802` |
| L27 / L60 | RECURSOS EXTRAORÇAMENTÁRIOS | `860`–`869` (5) |

Duas consequências que valem registro:

- `803 Sistema de Proteção Social dos Militares` e `804 Demais Recursos Previdenciários` caem em
  L7/L40 exatamente como o **item 25**, p. 8, descreve: SPSM e benefícios previdenciários mantidos
  pelo ente e não incorporados ao RPPS.
- O valor da fonte na regra é o **código principal de 3 dígitos**. O prefixo de exercício
  (`1` corrente, `2` anteriores, `9` condicionados, p. 10 do Anexo) não separa subgrupo; incluí-lo
  triplicaria cada lista sem mudar o recorte. O bloco `000`–`499` é da União, que não entrega DCA.

### F4 — sentido do movimento em L27 e L60
As duas linhas declaram as mesmas contas — `2.1.8.8.0.00.00 + 2.2.8.8.0.00.00` — e o que as separa
é `<movimento credor>` (p. 11) contra `<movimento devedor>` (p. 13). **Decidido:** campo próprio
`movimento` na coluna. Usar `sign: -` estava descartado porque L60 **soma** positivamente no
TOTAL (XII): o sinal faria o total subtrair o que deveria somar.

### F5 — posição de L33 no PDF
A p. 12 imprime `L33 TOTAL (VI)` depois do bloco de dispêndios, ao pé da página. A linha é de
ingressos: `L33 = (L1 + L15 + L21 + L24 + L29)` só agrega linhas de ingresso, e o numeral
`(VI) = (I+II+III+IV+V)` fecha exatamente o bloco. **Decidido:** `grupo: INGRESSOS`, `ordem: 33`,
com a posição física registrada em `evidence.text` e `provenance.reading`.

## Divergências internas do documento

### Conta de caixa grafada com um dígito a menos
A p. 11 grafa, em L30, `1.1.1.0.0.00.0` — oito dígitos, um a menos que o padrão do PCASP. A p. 13
grafa, na linha homóloga L63, `1.1.1.0.0.00.00`. Adotada a grafia da p. 13, que é a conta do
PCASP; `provenance.reading.adopted_from_page: 13` registra a leitura, e o literal completo fica no
YAML. O padrão normalizado é `111` — o grupo Caixa e Equivalentes de Caixa inteiro, do qual a
regra subtrai `1.1.1.1.1.06.00` (Conta Única RPPS) e `1.1.1.3.0.00.00` (valores restituíveis e
vinculados), como o próprio literal manda.

### Rótulos assimétricos entre ingressos e dispêndios
Os dispêndios grafam "Recursos **Destinados** à Educação" (L37) e "Recursos **Destinados** à
Saúde" (L38), enquanto L39 a L43 voltam a "Recursos **Vinculados**". Nos ingressos, as homólogas
L4 e L5 são "Vinculados". A transcrição preserva cada rótulo como está no PDF: é rótulo de
apresentação, não muda mapeamento.

### Autorreferência deslocada no item 36
O item 36, p. 10, diz "Quem adotar o procedimento relatado no **item 34**…", mas o procedimento de
reconhecer a despesa orçamentária na saída de caixa para investimento está descrito no **item 35**.
Não afeta regra nenhuma — o item 36 é orientação, não mapeamento. Registrado para não ser
"descoberto" de novo.

### Numeração do Quadro Anexo reinicia
O Quadro Anexo tem suas próprias `L1`–`L14`, que não têm relação com as linhas de mesmo código do
Quadro Principal. Daí o `rule_id` carregar o quadro: `bf.quadro_anexo.l1` × 
`bf.quadro_principal.ingressos.l1`.

### Líquido no Quadro Principal, aberto no Quadro Anexo
O Quadro Principal traz a receita já líquida (`6.2.1.2.0.00.00 - 6.2.1.3.0.00.00`, item 27). O
Quadro Anexo abre os dois termos em colunas próprias — `(a)` receita e `(b)` deduções — e calcula
`(c) = (a - b)`. Não é divergência: é o detalhamento que o item 27 promete.

## O que o IPC 06 não tem

Nenhuma linha do BF usa classificação funcional, natureza de receita ou natureza de despesa, e não
existe coluna de exclusões. Por isso a base do BF não declara `exclusion_groups`, e o conjunto de
`field` do IPC 06 é `{ conta_contabil, fonte_recurso }` — validado por documento, nunca por um enum
global que aceitaria campo de um IPC na regra do outro.
