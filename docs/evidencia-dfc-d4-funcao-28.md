# Evidência — D4: Função 28 / subfunções 841–844 é filtro de inclusão

**Change:** `ipc08-dfc-regras-canonicas` · **Medição:** 2026-10-26 · **Fonte:** API SICONFI
(`tt/msc_*`, pública), MSCE competência 12, saldo de abertura, classe 6, exercício 2025.

## A dúvida

No IPC 08, `L32` (p. 11) e `L3` do quadro de juros (p. 16) grafam `Função: 28 Subfunção: 841, 842,
843 e 844` **depois** da coluna Exclusões, visualmente sobrecarregada. Duas leituras possíveis:

| | Leitura | Efeito em `L32` |
|---|---|---|
| **A** | filtro de **inclusão** — só o que está na função 28 / subfunções 84x | adotada na transcrição, igual a `L14` |
| **B** | filtro de **exclusão** — tudo menos a função 28 / subfunções 84x | o oposto |

## O que foi medido

Soma das contas `6.2.2.1.3.04.00 + 6.3.1.4.0.00.00 + 6.3.2.2.0.00.00` (pago + RP não processados
pagos + RP processados pagos), com as naturezas de despesa de cada linha, **particionada** entre
`função = 28 e subfunção ∈ {841, 842, 843, 844}` e o restante.

| Ente | Linha | Em 28/84x | Fora | % fora |
|---|---|---:|---:|---:|
| Porto Alegre/RS (4314902) | L32 | 4.278.384,37 | 0,00 | 0,00% |
| Porto Alegre/RS | L14 | 115.727.775,84 | 0,00 | 0,00% |
| Recife/PE (2611606) | L32 | 10.993.370,04 | 0,00 | 0,00% |
| Recife/PE | L14 | 321.239.463,44 | 3.328.107,36 | 1,03% |
| João Pessoa/PB (2507507) | L32 | 0,00 | 0,00 | — |
| João Pessoa/PB | L14 | 84.442.510,78 | 5.082,43 | 0,01% |
| Belo Horizonte/MG (3106200) | L32 | 0,00 | 0,00 | — |
| Belo Horizonte/MG | L14 | 385.461.974,64 | 0,00 | 0,00% |
| Cuitegi/PB (2505204) | L32 | 0,00 | 0,00 | — |
| Cuitegi/PB | L14 | 0,00 | 0,00 | — |

## Conclusão — D4 é inclusão

**A leitura B zera a linha.** Entre 98,97% e 100% do pagamento de amortização e de juros está
classificado na função 28 com subfunção 84x, nos cinco entes. Excluir essas funções produziria
`L32 = 0` e `L14 ≈ 0` em todos — contra 4.242.326,51 e 115.201.049,07 que **Porto Alegre publica**
(`docs/entes-homologacao/porto-alegre/gabarito-dfc-2025.md`). A leitura B está refutada.

A transcrição já adotava a leitura A: **nenhum YAML muda**. O que muda é o status da decisão — de
interpretação visual para leitura medida.

Em consequência, o filtro de função é **inócuo na prática** nestes entes (A = universo sem filtro,
porque não há amortização nem juros fora da função 28). Ele vale como guarda contra ente que
classifique fora do padrão, e os 1,03% de Recife mostram que esse ente existe.

## Conferência contra o publicado

Nas duas linhas com alvo conhecido, o apurado pela leitura A fica **acima** do publicado:

| Linha | Apurado (A) | Publicado | Diferença |
|---|---:|---:|---:|
| L32 | 4.278.384,37 | 4.242.326,51 | +36.057,86 (0,85%) |
| L14 | 115.727.775,84 | 115.201.049,07 | +0,46% |

Diferença compatível com a **ressalva de recorte** já registrada no BF do mesmo ente: o PDF é da
**administração direta**, a MSC é **consolidada**. Não é teste de D4 — nas duas leituras o recorte
é o mesmo —, mas confirma que o mapa de contas e naturezas de `L32` e `L14` está na ordem de
grandeza certa, o que não se sabia antes desta medição.

## Achado colateral — quadro de juros não reproduz a abertura publicada

Pendência para a change de apuração, não para D4:

1. **Interna × externa por subfunção não bate.** Pela regra (`841, 843` = interna; `842, 844` =
   externa), Porto Alegre sai 59.461.280,32 / 35.313.289,58 contra 74.425.391,92 / 40.775.657,15
   publicados. O total fecha; a partição, não — o ente aparentemente não usa a subfunção para
   separar dívida interna de externa.
2. **`J.L3` Outros Encargos.** A regra manda ~20,9 milhões (naturezas `3.2.90.22`, `3.2.90.24` e
   demais `3.2.xx`) para `J.L3`, que o ente publica **zerada**, somando tudo em `J.L1`/`J.L2`.
   Por isso `J.L1 + J.L2 = 115.201.049,07 = L14` no publicado, enquanto a regra dá 94.774.569,90.

## Reprodução

`SiconfiMSC().registros(<ente>, 2025, 12, 6, Matriz.ENCERRAMENTO, TipoSaldo.ABERTURA)`, filtrando
`conta` por `6221304|6314|6322`, `natureza_despesa` pelos prefixos de cada linha (em `L32`, `46`
menos `4690.71`…`4690.77`) e particionando por `funcao == "28" and subfuncao in {841,842,843,844}`.
