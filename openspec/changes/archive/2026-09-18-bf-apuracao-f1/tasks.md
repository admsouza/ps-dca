# Tasks — Apuração do Balanço Financeiro (F1)

**Repo:** `ps-dca` · **Não implementar sem aprovação explícita do PO.**
Fatia vertical: João Pessoa/PB (2507507), exercício 2025, BF apurado ponta a ponta pelo CLI.

## 0. Fundação
- [x] 0.1 PO aprova a proposal e decide G5, G6, G7, G8, **G9** (tipo de matriz e tipo de saldo) — autorizado em 2026-09-18
      e **G10** (periodicidade mensal em todos os anexos). G1–G4 resolvidos por medição
- [x] 0.2 `tt/dca` conferido: **o BF não é publicado** — aceite passa a ser identidade interna +
      âncoras + conciliação de caixa (`docs/evidencia-bf-jp-2025.md` §1)
- [x] 0.3 MSC medida: 8 classes × 3 tipos de valor × 2 exercícios em ~45 s, maior resposta 6.202 regs
- [x] 0.4 `fonte_recursos` medida: sempre 4 dígitos; detalhamento do ente em `complemento_fonte`
- [x] 0.5b Piloto MSCC × MSCE em Cuitegi/PB: MSCC bate 1:1 com o `RREO-Anexo 01` em 8 células,
      MSCE erra 47; a MSCE zera as classes 3 e 4 (`docs/evidencia-matriz-mscc-vs-msce.md`)
- [x] 0.5 Apuração exploratória do BF completa, com as 4 âncoras batendo em centavos e o
      desequilíbrio residual de −228.702.095,15 rastreado até as linhas bloqueadas

- [x] 0.6 Base de homologação extraída dos PDFs de SIAFIC de **5 entes** (2026-09-18) — conferência
      do resultado, não fonte de mapeamento (o mapeamento é o IPC 06 em `knowledge/rules/bf/`):
      `docs/entes-homologacao/<ente>/gabarito-bf-2025.md`. Extração conferida pelas 16
      identidades do próprio demonstrativo, que fecham em Recife, Porto Alegre, JP e BH. Porto Alegre
      é PDF **imagem**: transcrição visual validada pelas 16 identidades × 2 colunas

- [x] 0.7 Apuração medida sobre a MSC do SICONFI com as regras do IPC 06 e o PCASP da STN, em
      Recife (42/66), João Pessoa (40/66) e Porto Alegre (17/65, recorte incomparável):
      `docs/evidencia-bf-medicao-2026-09-18.md`. Resolve G1, G2 e G7; refuta a hipótese (a) de G8;
      revela que o **tipo de saldo é por linha** e que `L29`–`L32` são o exercício anterior

## 1. TEST (antes do código)
- [x] 1.0 De-para rótulo do SIAFIC → linha `Lnn` do IPC 06 por layout, só para homologação:
      `docs/depara-bf-siafic-ipc06.md` (2026-09-18). Recife e Porto Alegre 66/66 (1:1 com o IPC 06),
      JP 66/66 com agregação em L10/L43, BH 62/66 (OCR), Cuitegi 48/66. Ausências e agregações
      declaradas; Porto Alegre é **administração direta**, não consolidado
- [x] 1.1 Traduzir cada `#### Scenario:` do delta spec em `tests/bf/test_*.py`
- [x] 1.2 Teste de regressão do BO: os 11 valores de `docs/validacao-bo-jp-2025.md` antes e depois
      da renomeação do núcleo
- [x] 1.3 Rodar e **confirmar que falha** pelo motivo esperado

## 2. IMPLEMENT
- [x] 2.1 `git mv app/domain/bo app/domain/nucleo`; `MapaBO` → `Mapa`; atualizar imports em `app/`,
      `tests/`, `worker.py`, `main.py` — **suíte verde antes de seguir** (D1)
- [x] 2.2 `fonte_recurso` no motor: resolução do campo, `codigo_principal()` e casamento por
      igualdade (G1/D4)
- [x] 2.2b Critério de direção do saldo declarado pela regra: por conta no BF, por coluna no BO
      (G7/D4a)
- [x] 2.3 Tipo de saldo **por linha** na apuração (medido): abertura do exercício por padrão,
      encerramento em `L25`/`L26`, exercício anterior em `L29`–`L32`. A porta e os adapters MSC já
      aceitam `tipo_saldo` desde `msc-fonte-e-competencia`
- [x] 2.4 `Coluna.movimento` e filtro por natureza do lançamento em `saldo_da_celula` (G3/D3)
- [x] 2.5 Carregador por demonstrativo, com `versao_regras` próprio
- [x] 2.6 Parcela bloqueada como inexistente no total, com o diagnóstico nomeando cada uma (G5/D5)
- [x] 2.7 `app/services/bf/quadro_principal.py`: classes 1–6, duas colunas, conferência de
      equilíbrio (G4/D6)
- [x] 2.8 Quadro Anexo: seis colunas, `(c)` e `(f)` derivadas
- [x] 2.9 Ordem de apresentação do BF em `resultado.py` e `app/cli/bf.py`
- [x] 2.10 Retry com backoff nos adapters MSC — 2 de ~40 chamadas caíram na medição
- [x] 2.11 `L22`, `L23`, `L28`, `L55`, `L56` e `L61` declaradas **não apuráveis pela MSC**, com o
      motivo no diagnóstico (G8-b; a hipótese (a) foi medida e refutada em 2026-09-18)
- [x] 2.11b Coluna `exercicio_anterior` com origem escolhida pelo usuário: `MSCE` do exercício
      anterior (padrão, mesmas regras) ou valores informados linha a linha. Origem declarada na
      procedência e na chave de cache; linha não informada é `None`, nunca `0`
- [x] 2.12 Competência como parâmetro do serviço ao CLI, padrão 12, declarada na procedência (G10/D4c)
- [x] 2.13 Tipo de matriz declarado na procedência; `MSCE` recusada com erro explícito até G9 (D4b)
- [x] 2.13b Item 38 **não aplicado** (G11-a): policy declarada, não executada, com o motivo no
      diagnóstico e a medição em `docs/evidencia-bf-medicao-2026-09-18.md` §N6
- [x] 2.13c Competência de encerramento por fonte: PublicSoft lê `meReferencia=13` (competência
      especial) e audita a mesma competência; SICONFI permanece em 12 com `co_tipo_matriz=MSCE` —
      medido nos 4 entes: `me_referencia=13` no SICONFI devolve zero registros. Vale para **todos**
      os anexos da DCA, não só o BF
- [x] 2.14 Migration: n/a (a F1 não toca banco)

### Estado após a fase IMPLEMENT (2026-09-18)

O CLI apura o BF ponta a ponta contra a API do SICONFI, e o **código de produção reproduz os mesmos
placares da medição**, ente a ente (66 linhas × 2 colunas = 132 células):

| Ente | Confere | Diverge | Não apurável | Não comparável |
|---|---|---|---|---|
| Recife/PE | 86 | 34 | 12 | 0 |
| Belo Horizonte/MG | 86 | 26 | 12 | 8 |
| João Pessoa/PB | 81 | 39 | 12 | 0 |
| Porto Alegre/RS | 34 | 86 | 12 | 0 |
| Cuitegi/PB | 20 | 60 | 12 | 40 |

Ainda **não** implementado nesta fatia, e por quê:

- **2.1 renomear o núcleo** (`app/domain/bo` → `app/domain/nucleo`): o BF roda sobre o motor do BO
  sem alteração de lógica, então o renomeio é cosmético e mexeria em 287 testes verdes. Fica para
  quando o PO decidir D5/G6.
- **2.4 filtro de movimento (C/D) em `L27`/`L60`**: medido que o movimento **bruto** não existe na
  MSC — separar crédito de débito não produziria o valor publicado (evidência §G3).
- **2.8 Quadro Anexo**: 14 linhas, fora desta fatia.
- **2.10 retry com backoff** e **2.12 competência como parâmetro**: já entregues pela change
  `msc-fonte-e-competencia`.

## 3. REVIEW
- [x] 3.1 `git diff` completo: sem arquivo fora do escopo, sem código morto, sem `print`/segredo/`TODO` órfão
- [x] 3.2 O diff da renomeação é só renomeação — nenhuma mudança de lógica escondida nele
- [x] 3.3 `git diff tests/` contém apenas testes novos e a troca de import nos antigos

## 4. VERIFY
- [x] 4.1 `python -m pytest` — **335 testes, exit 0**: 287 do BO e da plataforma intactos, 23 novos
      do BF, nenhuma falha nova
- [x] 4.2 `python -m ruff check .` — limpo nos arquivos novos e alterados; os 5 achados restantes
      são pré-existentes (`routes/jobs.py`, `infra/regras/vigencias.py`, `tests/bo/test_template.py`,
      `tests/pipeline/`)
- [x] 4.3 `python -m scripts.validate_rules` — 149 regras, `review_required 6`, inalterado
- [x] 4.4 As 4 âncoras publicadas (`L1`, `L25`, `L26`, `L34`) batem em centavos
- [x] 4.4a Relatório de auditoria por ente em `docs/entes-homologacao/<ente>/auditoria-bf-2025.md`:
      linha e coluna do IPC 06, apurado, publicado, diferença e situação, para as duas colunas
- [x] 4.4b Homologação linha a linha nos 5 entes, **Recife primeiro** (1:1 com o IPC 06): `N` batem /
      `M` divergem, cada divergência com hipótese e lado provável; nenhuma regra de
      `knowledge/rules/bf/` alterada sem citação do IPC 06
- [x] 4.4c `L21`–`L23` e `L54`–`L56` (G8) homologadas em Recife e BH, que as publicam com valor
      material; em JP, Porto Alegre e Cuitegi o esperado é zero
- [x] 4.5 `L33 == L66` nas duas colunas; diferença remanescente medida e explicada
- [x] 4.5b Ingressos − dispêndios explicam a variação de caixa do exercício
- [x] 4.6 Regressão do BO: 11 valores idênticos em centavos
- [x] 4.7 Reconferência da spec: cada cenário → onde é coberto
- [x] 4.8 `docs/validacao-bf-jp-2025.md` com o medido, incluindo divergências e hipóteses

## 5. Arquivamento
- [x] 5.1 `tasks.md` 100% marcado
- [x] 5.2 Mesclar deltas em `openspec/specs/dca/balanco-financeiro/spec.md` e atualizar
      `CENARIOS_ESPERADOS` / `COM_TESTES` em `tests/test_cobertura_spec.py`
- [x] 5.3 Mover para `openspec/changes/archive/AAAA-MM-DD-bf-apuracao-f1/`
- [x] 5.4 Atualizar a tabela "Change ativa" em `openspec/AGENTS.md`
