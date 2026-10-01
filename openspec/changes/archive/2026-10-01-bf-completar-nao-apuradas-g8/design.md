# Design — Completar G8 no exercício atual

**Change:** `bf-completar-nao-apuradas-g8` · **Repo:** `ps-dca`

## Decisões

### D1 — Nome do mapa: `valores_sem_mapeamento`
Não usar `valores_atuais`: sugere “manualizar o ano”. O mapa é override das linhas **sem conta no IPC 06**.

### D2 — Desacoplado do Manual do anterior
`origem_exercicio_anterior` e `valores_anteriores` continuam como estão. Um POST pode trazer só G8, só anterior, ou ambos.

### D3 — Whitelist fixa
Códigos: `L22`, `L23`, `L28`, `L55`, `L56`, `L61`. Só quadro principal / `exercicio_atual`. Anexo e outras linhas fora.

### D4 — Persistência
Espelhar o padrão de `valores_anteriores`: campo em `procedencia` na linha de cache já existente. Sem tabela nova.

### D5 — Reaplicar vs limpar
- Body **sem** a chave `valores_sem_mapeamento` → mantém/reaplica o salvo.
- Body com `valores_sem_mapeamento: {}` → limpa.
- Body com mapa não vazio → substitui o salvo pelo informado (merge total do mapa G8, não patch parcial de um código omitido — YAGNI: o front sempre reenvia o conjunto completo das G8 preenchidas).

### D6 — Compostas
Reusar `_aplicar_compostas_manual` (ou extrair helper de coluna) sobre `exercicio_atual` depois do merge, para `L21` / totais refletirem a parcela.

## Arquivos prováveis
- `app/services/bf/quadro_principal.py` — merge + compostas
- `app/services/bf/informados.py` (ou equivalente) — validação whitelist
- Rota / pipeline de `POST /dca/BF/reprocessar` — ler corpo
- Serialização de `procedencia`
- Testes em `tests/bf/` e/ou `tests/pipeline/`

## Não fazer
- Flag de origem do exercício atual
- Editar células que já têm valor MSC (só G8 / null)
- Meter G8 dentro de `valores_anteriores`
