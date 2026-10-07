# Design — BP: coluna do exercício anterior pela DCA publicada no SICONFI

**Change:** `openspec/changes/bp-anterior-publicado-siconfi/` · **Proposal aprovada pelo PO em:** 2026-10-07

## Contexto

O serviço do BP apura cada coluna com `_apurar_exercicio(..., registros)` sobre `Registro`s da MSC. A
origem publicado só precisa entregar **outros registros** para a coluna anterior: as contas folha do
`I-AB` convertidas em `Registro`. O motor, as regras e as exclusões são os mesmos. O quadro F/P é a
exceção: o `I-AB` não traz o atributo por conta, só os totais F/P.

## Componentes afetados

| Componente | Papel |
|---|---|
| `app/infra/siconfi/dca.py` (novo) | lê `tt/dca` (`an_exercicio`, `no_anexo=DCA-Anexo I-AB`, `id_ente`), com timeout e retry dos adapters MSC |
| `app/services/bp/publicado.py` (novo) | folhas do `I-AB` → `Registro`; totais F/P |
| `app/services/bp/quadro_principal.py` | `Anterior` (`PUBLICADO` \| `MSCE`), padrão `PUBLICADO`; coluna anterior pela origem; F/P publicado; diagnóstico |
| `app/routes/anexos.py` | `origem_exercicio_anterior` aceito no BP (`publicado_siconfi` \| `msce_exercicio_anterior`), sempre preenchido |
| `app/services/pipeline/completo.py` | pedido do percurso com a origem padrão do BP |

## Fluxo

```text
coluna atual    → MSCE/encerramento (ano)        → regras IPC 04 → matriz
coluna anterior ─┬ msce:      MSCE/encerramento (ano−1) → regras IPC 04
                 └ publicado: tt/dca I-AB (ano−1) → folhas → Registro → regras IPC 04
                                                 └ AtivoFinanceiro… → F/P L2, L3, L5, L6
```

## Contratos

```python
class Anterior(StrEnum):
    PUBLICADO = "publicado_siconfi"
    MSCE = "msce_exercicio_anterior"

def registros_publicados(itens: list[dict]) -> list[Registro]:
    """Folhas `P*` do I-AB: `cod_conta` sem filha publicada, convertida em 9 dígitos;
    valor com sinal → natureza pela direção da conta (`_DirecaoDoBP`), valor absoluto."""
```

## Decisões

### D1 — Publicado pelas regras do IPC 04, sobre as folhas (decisão do PO)
**Descartado:** valor do grupo como publicado · **Porquê:** a coluna anterior fica comparável à
atual, com as mesmas exclusões. Folha evita a dupla contagem da hierarquia.

### D2 — Identidade sempre com a origem explícita
**Escolhido:** a rota e o percurso preenchem `origem_exercicio_anterior` do BP mesmo quando omitido
(padrão `publicado_siconfi`) · **Porquê:** `identidade_do_pedido` usa `origem_anterior or "-"`. Sem
isso, o mesmo resultado teria duas identidades (`-` e `publicado_siconfi`), e a leitura marcaria
`pedido` sem motivo.

### D3 — Sem queda silenciosa para a MSC
**Porquê:** é a regra do BF (`Anterior.MANUAL` nunca escolhido por omissão). Sem publicação, a coluna
sai `None` e o diagnóstico diz o motivo; o usuário escolhe a MSC na engrenagem.

### D4 — `tt/dca` lido sempre do SICONFI, qualquer que seja a fonte da MSC
**Porquê:** a DCA publicada só existe no SICONFI. A fonte da MSC (SICONFI ou PublicSoft) continua
valendo para a coluna atual.

## Impacto

| Eixo | Impacto |
|---|---|
| Banco | nenhum |
| Cache | origem na identidade; resultados atuais sem origem passam a `desatualizado` (`pedido`) na leitura, sem reprocessar |
| APIs externas | +1 chamada ao `tt/dca` por apuração do BP pelo publicado |
| Regressão | `msce_exercicio_anterior` bit a bit igual ao BP de hoje; BO e BF intactos |

## Arquivos

| Arquivo | Ação |
|---|---|
| `app/infra/siconfi/dca.py`, `app/services/bp/publicado.py` | criar |
| `app/services/bp/quadro_principal.py`, `app/routes/anexos.py`, `app/services/pipeline/completo.py`, `worker.py` | alterar |
| `tests/bp/test_anterior_publicado.py` | criar |
| `docs/evidencia-bp-publicado-2024.md` | criar (medição de folhas × grupo em Cuitegi e JP) |
