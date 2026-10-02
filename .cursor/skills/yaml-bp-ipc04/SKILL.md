---
name: yaml-bp-ipc04
description: >
  Transcreve o IPC 04 (Balanço Patrimonial) para YAML canônico no mesmo contrato
  de BO e BF, pronto para o programador implementar o mapeamento. Use esta skill
  sempre que o pedido for YAML, regras, mapeamento ou transcrição do BP, do
  IPC 04, do balanço patrimonial, ou de docs/referencia/ipc/IPC04 - BP atualizacao - 20200117.pdf,
  mesmo que o usuário não diga "skill" nem "YAML".
---

# YAML do Balanço Patrimonial (IPC 04)

Entrega a base canônica do BP para o programador implementar a apuração no mesmo contrato de BO e BF. O produto é YAML válido em `knowledge/schemas/`. Código Python, schema e validador ficam com o programador.

Os caminhos de arquivo são relativos à raiz do repositório `ps-dca`. Se o workspace atual não for esse repositório, abra-o antes de gravar YAML.

## Fonte oficial da STN, depois o ponto do dado

Nenhuma decisão de mapeamento fecha na leitura do PDF sozinha, nem por analogia com BO ou BF. A ordem é fixa porque o PDF de 2020 cita o PCASP 2019, e a tabela oficial deste repositório é outra edição: código, 5º nível e atributo mudam.

Antes de gravar `pattern`, `sign`, filtro, exclusão, coluna, `status` ou blocker:

1. Leia a página do IPC 04 que declara a linha (`docs/referencia/ipc/IPC04 - BP atualizacao - 20200117.pdf`). O `literal` é a grafia dessa página, inclusive erro de digitação.
2. Consulte a tabela oficial da STN em `docs/contas-stn/` que é dona daquele código. Conta patrimonial → `PCASP.md`. Fonte → `fonte-recursos.md`. Natureza, função e subfunção só entram se a linha do IPC as citar, nas tabelas de mesmo nome.
3. Confirme no ponto do dado, e só então escreva o campo:
   - Conta: a linha folha do `PCASP.md` (`CONTA`, `SUBTÍTULO`, `NATUREZA DO SALDO`, `INDICADOR DO SUPERÁVIT FINANCEIRO`). O prefixo do YAML é o que essa folha sustenta. Máscara com zero à direita no PDF (`1.1.1.0.0.00.00`) não é código exato.
   - Atributo financeiro/permanente: o indicador do plano não basta. 924 contas de ativo e passivo são `Financeiro/Permanente`; o atributo está no registro do fato (`financeiro_permanente` no SICONFI, `financeiroPermanente` no PublicSoft: `1` = F, `2` = P). Sem o registro, a linha não é computável.
   - Fonte: igualdade com o nome em `fonte-recursos.md`. Faixa inventada não entra.
   - Código ausente da tabela: `pattern: null`, `status: review_required`, candidato em `review.candidate` e **fora** de `filters` e `columns`. Corrigir o PDF em silêncio é erro.

Se a tabela e o ponto do dado não sustentam a leitura, a regra nasce `review_required` com `review.blocker`. Não invente campo, enum nem `provenance.decision`.

## O que não fazer

- Não alterar `app/`, `tests/`, `knowledge/schemas/` nem `scripts/validate_rules.py`. O validador só conhece IPC 06 e IPC 07; falha por documento ausente do enum é recado para o programador, não patch desta entrega.
- Não copiar o PDF para dentro de `knowledge/`. `scripts/check_sources.py` recusa PDF na base.
- Não marcar `validated`. Quem valida é gente, depois da apuração.
- Não criar uma regra por fonte no quadro de superávit, nem coringa “todo 5º nível = 2”. Esse coringa, medido no `PCASP.md`, exclui conta que o quadro mantém (em Caixa, `111320101` e `111320102`).

## Ordem de leitura

1. `knowledge/schemas/rule.json` e `knowledge/schemas/policy.json`
2. `references/contrato.md` desta skill
3. Uma regra de cada tipo, não o arquivo inteiro: soma com filtro `not_in` em `knowledge/rules/bo/quadro_principal.yaml` (`bo.quadro_principal.receitas.l11`); subtração de conta irmã em `knowledge/rules/bf/quadro_principal.yaml` (`bf.quadro_principal.ingressos.l2`); linha que só referencia outras (`bo.quadro_principal.receitas.l1`); policy em `knowledge/policies/ipc07.yaml`
4. `docs/source-analysis.md` seções 4, 6 e 11 — pendência já decidida pelo PO não se reabre; pendência aberta (P2) não se resolve aqui
5. O PDF do IPC 04 e o `PCASP.md`, na ordem do gate acima

## Entregáveis

| Arquivo | Conteúdo |
|---|---|
| `knowledge/sources/ipc04/metadata.yaml` | Espelho de `knowledge/sources/ipc07/metadata.yaml`. `sha256` calculado do PDF, não copiado de memória. |
| `knowledge/sources/ipc04/extracted.md` | Texto das páginas de regra (8–18), para a transcrição. Extraia com PyMuPDF (`page.get_text()`). Se o texto sair corrompido, não complete letra faltante: releia a página. |
| `knowledge/policies/ipc04.yaml` | Itens de instrução que valem para o demonstrativo, não o mapa de uma linha. |
| `knowledge/rules/bp/quadro_principal.yaml` | L1–L40 |
| `knowledge/rules/bp/ativos_passivos_financeiros.yaml` | L1–L7 |
| `knowledge/rules/bp/contas_compensacao.yaml` | L1–L10 |
| `knowledge/rules/bp/superavit_deficit.yaml` | Só o total. A abertura por fonte fica em blocker. |

`rule_id` reinicia a numeração por quadro: `bp.quadro_principal.ativo.l1` e `bp.ativos_passivos_financeiros.l1` são regras diferentes. Grupo só quando o quadro tem lado (ativo, passivo).

## Validar antes de entregar

```bash
python -c "import json,yaml,pathlib,jsonschema; s=json.loads(pathlib.Path('knowledge/schemas/rule.json').read_text(encoding='utf-8'));
[jsonschema.validate(r,s) for p in pathlib.Path('knowledge/rules/bp').glob('*.yaml') for r in yaml.safe_load(pathlib.Path(p).read_text(encoding='utf-8'))['rules']]"
python -c "import json,yaml,pathlib,jsonschema; s=json.loads(pathlib.Path('knowledge/schemas/policy.json').read_text(encoding='utf-8'));
[jsonschema.validate(p,s) for p in yaml.safe_load(pathlib.Path('knowledge/policies/ipc04.yaml').read_text(encoding='utf-8'))['policies']]"
python scripts/check_sources.py
```

No relatório final, liste cada `review.blocker` com página do IPC e o que a tabela STN ou o ponto do dado recusou. `scripts/validate_rules.py` pode falhar porque o IPC 04 não está nos enums fechados; registre a falha e não edite o script.

O contrato de cada quadro, coluna, exclusão e blocker está em [references/contrato.md](references/contrato.md). Leia esse arquivo antes de escrever a primeira regra.
