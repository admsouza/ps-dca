"""Validação da base canônica de regras — gate de CI.

Verifica, nesta ordem: schema, identificadores, referências e ciclos, rastreabilidade,
enums fechados, decisões do PO com escopo fechado, coerência de status, códigos contra as
tabelas da STN e sincronia do índice.

Princípio que atravessa o arquivo: **nada é presumido**. Código ausente da tabela oficial não é
corrigido nem ignorado — ou é exceção de domínio declarada (B2/B4), ou é decisão histórica do PO
(B1/B3), ou a regra tem de estar `review_required`. Qualquer outro caminho é erro.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

from scripts import load_stn_tables
from scripts._carregar import carregar_policies, carregar_regras
from scripts._relatorio import Relatorio, configurar_saida

# ─── conjuntos fechados do IPC 07 (design › "Enums fechados") ────────────────

CAMPOS = {"conta_contabil", "natureza_receita", "natureza_despesa", "funcao", "subfuncao"}
OPERADORES = {"in", "not_in"}
SINAIS = {"+", "-"}
CONDICOES = {"result_positive", "result_negative"}
STATUS = {"draft", "extracted", "review_required", "validated", "deprecated"}
METODOS = {"automated", "assisted", "manual"}
DECISOES = {"B1", "B3", "B5", "B6"}
OVERRIDE_PERMITIDO = {
    "bo.quadro_principal.receitas.l29",
    "bo.quadro_principal.receitas.l30",
}

# Exceções de domínio medidas na descoberta: faixas que as tabelas do repositório
# comprovadamente não cobrem. Não viram `review_required`, mas são reportadas à parte —
# "exceção declarada" e "código inexistente" são coisas diferentes no relatório.
GRUPO_ND_COBERTO = "31"          # B4 — `natureza_despesa.md` traz 172 códigos, todos do grupo 3.1
CATEGORIAS_RECEITA_INTRA = ("7", "8")  # B2 — intraorçamentárias, 0 códigos na tabela

# As tabelas da STN são do repositório, não da árvore validada: `base` pode ser uma árvore de
# teste, e o domínio de conferência continua sendo o oficial.
RAIZ_REPO = Path(__file__).resolve().parent.parent
CONTAS_STN = RAIZ_REPO / "docs" / "contas-stn"

CAMPO_POR_DOMINIO = {
    "conta_contabil": "conta_contabil",
    "natureza_receita": "natureza_receita",
    "natureza_despesa": "natureza_despesa",
    "funcao": "funcao",
    "subfuncao": "subfuncao",
}


def validar(base: Path, raiz_docs: Path | None = None) -> Relatorio:
    rel = Relatorio()
    regras = list(carregar_regras(base))
    policies = list(carregar_policies(base))

    paginas = _paginas_por_documento(base)
    codigos_stn = load_stn_tables.carregar(raiz_docs or CONTAS_STN)
    schemas = _carregar_schemas(base)

    ids: dict[str, tuple[Path, int]] = {}
    excecoes: list[dict] = []

    for regra, arquivo, linha in regras:
        contexto = (regra.get("rule_id"), str(arquivo), linha)
        _validar_schema(rel, regra, schemas, *contexto)
        _validar_identificador(rel, regra, ids, arquivo, linha)
        _validar_source(rel, regra, paginas, *contexto)
        _validar_filtros(rel, regra, codigos_stn, excecoes, *contexto)
        _validar_colunas(rel, regra, codigos_stn, excecoes, *contexto)
        _validar_status(rel, regra, *contexto)
        _validar_override(rel, regra, *contexto)
        _validar_versao(rel, regra, *contexto)
        _validar_condicao(rel, regra, *contexto)

    _validar_referencias(rel, regras)
    _validar_policies(rel, policies, schemas)
    _validar_indice(rel, base, regras)

    rel.contagens = _contar(regras, excecoes)
    return rel


# ─── schema ──────────────────────────────────────────────────────────────────

def _carregar_schemas(base: Path) -> dict[str, dict]:
    diretorio = base / "schemas"
    if not diretorio.is_dir():
        return {}
    return {
        arquivo.stem: json.loads(arquivo.read_text(encoding="utf-8"))
        for arquivo in sorted(diretorio.glob("*.json"))
    }


def _validar_schema(rel, regra, schemas, rule_id, arquivo, linha) -> None:
    schema = schemas.get("rule")
    if not schema:
        rel.erro("schema de regra ausente em knowledge/schemas/rule.json",
                 rule_id=rule_id, arquivo=arquivo, linha=linha)
        return
    import jsonschema

    validador = jsonschema.Draft202012Validator(schema)
    for falha in sorted(validador.iter_errors(regra), key=lambda e: list(e.path)):
        caminho = ".".join(str(p) for p in falha.path) or "(raiz)"
        rel.erro(f"schema: {caminho}: {falha.message}",
                 rule_id=rule_id, arquivo=arquivo, linha=linha)


# ─── identificador ───────────────────────────────────────────────────────────

def _validar_identificador(rel, regra, ids, arquivo, linha) -> None:
    rule_id = regra.get("rule_id")
    if not rule_id:
        rel.erro("rule_id ausente", arquivo=str(arquivo), linha=linha)
        return
    if rule_id != rule_id.lower():
        rel.erro(f"rule_id deve ser minúsculo: {rule_id}",
                 rule_id=rule_id, arquivo=str(arquivo), linha=linha)
    anterior = ids.get(rule_id)
    if anterior:
        antes, antes_linha = anterior
        rel.erro(
            f"rule_id duplicado: {rule_id} — também em {antes}:{antes_linha}",
            rule_id=rule_id, arquivo=str(arquivo), linha=linha,
        )
    else:
        ids[rule_id] = (arquivo, linha)


# ─── rastreabilidade ─────────────────────────────────────────────────────────

OBRIGATORIOS_SOURCE = ("document", "document_version", "page", "section", "table", "row")


def _paginas_por_documento(base: Path) -> dict[str, int]:
    paginas: dict[str, int] = {}
    for meta in sorted((base / "sources").glob("*/metadata.yaml")):
        dados = yaml.safe_load(meta.read_text(encoding="utf-8")) or {}
        if "document" in dados and "pages" in dados:
            paginas[dados["document"]] = int(dados["pages"])
    return paginas


def _validar_source(rel, regra, paginas, rule_id, arquivo, linha) -> None:
    source = regra.get("source")
    if not source:
        rel.erro("regra sem bloco source", rule_id=rule_id, arquivo=arquivo, linha=linha)
        return
    for campo in OBRIGATORIOS_SOURCE:
        if source.get(campo) in (None, ""):
            rel.erro(f"source.{campo} ausente", rule_id=rule_id, arquivo=arquivo, linha=linha)

    pagina = source.get("page")
    total = paginas.get(source.get("document", ""))
    if pagina is None:
        return
    if not isinstance(pagina, int) or pagina < 1 or (total and pagina > total):
        limite = f"1..{total}" if total else "1..N"
        rel.erro(f"source.page inválida: {pagina} — esperado {limite}",
                 rule_id=rule_id, arquivo=arquivo, linha=linha)


# ─── filtros e códigos ───────────────────────────────────────────────────────

def _grupos_de_filtro(regra: dict) -> list[list[dict]]:
    grupos = [regra.get("filters") or []]
    grupos.extend(regra.get("exclusion_groups") or [])
    return [g for g in grupos if g]


def _excecao_de_dominio(campo: str, padrao: str) -> str | None:
    """Motivo da exceção de domínio, ou None se o código deveria mesmo estar na tabela."""
    if campo == "natureza_receita" and padrao.startswith(CATEGORIAS_RECEITA_INTRA):
        return "B2 — naturezas intraorçamentárias ausentes da tabela do repositório"
    if campo == "natureza_despesa" and not padrao.startswith(GRUPO_ND_COBERTO):
        return "B4 — a tabela de natureza de despesa cobre apenas o grupo 3.1"
    return None


def _validar_filtros(rel, regra, codigos_stn, excecoes, rule_id, arquivo, linha) -> None:
    review_required = regra.get("status") == "review_required"
    decisao = (regra.get("provenance") or {}).get("decision")

    for grupo in _grupos_de_filtro(regra):
        for filtro in grupo:
            campo = filtro.get("field")
            operador = filtro.get("operator")
            if campo not in CAMPOS:
                rel.erro(f"campo de filtro não suportado para o IPC07: {campo}",
                         rule_id=rule_id, arquivo=arquivo, linha=linha)
                continue
            if operador not in OPERADORES:
                rel.erro(f"operador inválido: {operador}",
                         rule_id=rule_id, arquivo=arquivo, linha=linha)

            for valor in filtro.get("values") or []:
                _validar_valor(rel, valor, campo, codigos_stn, excecoes,
                               review_required, decisao, rule_id, arquivo, linha)


def _validar_valor(rel, valor, campo, codigos_stn, excecoes,
                   review_required, decisao, rule_id, arquivo, linha) -> None:
    literal = valor.get("literal")
    padrao = valor.get("pattern")

    if not literal:
        rel.erro(f"valor de filtro sem literal em {campo}",
                 rule_id=rule_id, arquivo=arquivo, linha=linha)
        return
    if padrao is None:
        # Normalização indeterminável: o delta spec manda declarar, não escolher.
        if not review_required:
            rel.erro(f"pattern nulo em {literal} exige status review_required",
                     rule_id=rule_id, arquivo=arquivo, linha=linha)
        return

    dominio = codigos_stn.get(CAMPO_POR_DOMINIO[campo], set())
    padrao_digitos = load_stn_tables.normalizar(padrao)
    coringa = "x" in padrao.lower()

    if not coringa and any(codigo.startswith(padrao_digitos) for codigo in dominio):
        return

    motivo = _excecao_de_dominio(campo, padrao_digitos)
    if not motivo and coringa:
        # Coringa não é conferível contra a tabela — o casamento por prefixo acontece no motor
        # de cálculo. Registrar como exceção, nunca deixar passar em silêncio.
        motivo = "padrão com coringa — conferido no casamento por prefixo, não na tabela"
    if motivo:
        excecoes.append({"rule_id": rule_id, "field": campo, "literal": literal,
                         "pattern": padrao_digitos, "motivo": motivo})
        return
    if decisao in {"B1", "B3"}:
        excecoes.append({"rule_id": rule_id, "field": campo, "literal": literal,
                         "pattern": padrao_digitos,
                         "motivo": f"exceção histórica {decisao} decidida pelo PO"})
        return
    if not review_required:
        rel.erro(
            f"código ausente da tabela oficial ({campo}): {literal} — "
            f"a regra deve ficar review_required, ou declarar exceção",
            rule_id=rule_id, arquivo=arquivo, linha=linha,
        )


# ─── colunas ─────────────────────────────────────────────────────────────────

def _validar_colunas(rel, regra, codigos_stn, excecoes, rule_id, arquivo, linha) -> None:
    colunas = regra.get("columns")
    if colunas is None:
        return  # linha composta; cobertura em _validar_referencias
    review_required = regra.get("status") == "review_required"
    decisao = (regra.get("provenance") or {}).get("decision")

    for nome, coluna in colunas.items():
        for conta in coluna.get("accounts") or []:
            if conta.get("sign") not in SINAIS:
                rel.erro(f"sinal inválido em columns.{nome}: {conta.get('sign')}",
                         rule_id=rule_id, arquivo=arquivo, linha=linha)
            # A conta da coluna é código do PCASP como qualquer outro: confere igual.
            _validar_valor(rel, conta, "conta_contabil", codigos_stn, excecoes,
                           review_required, decisao, rule_id, arquivo, linha)
        referencias = (coluna.get("calculation") or {}).get("references") or []
        for referencia in referencias:
            alvo = referencia.get("column")
            if alvo and alvo not in colunas:
                rel.erro(f"columns.{nome} referencia coluna inexistente: {alvo}",
                         rule_id=rule_id, arquivo=arquivo, linha=linha)
            if referencia.get("sign") not in SINAIS:
                rel.erro(f"sinal inválido em columns.{nome}.calculation",
                         rule_id=rule_id, arquivo=arquivo, linha=linha)


# ─── status, override, versão, condição ──────────────────────────────────────

def _validar_status(rel, regra, rule_id, arquivo, linha) -> None:
    status = regra.get("status")
    review = regra.get("review") or {}
    if status not in STATUS:
        rel.erro(f"status inválido: {status}", rule_id=rule_id, arquivo=arquivo, linha=linha)
    if status == "validated" and review.get("required"):
        rel.erro("status validated com review.required: true",
                 rule_id=rule_id, arquivo=arquivo, linha=linha)

    proveniencia = regra.get("provenance") or {}
    metodo = proveniencia.get("extraction_method")
    if metodo not in METODOS:
        rel.erro(f"provenance.extraction_method inválido: {metodo}",
                 rule_id=rule_id, arquivo=arquivo, linha=linha)
    if metodo in {"automated", "assisted"} and status == "validated":
        rel.erro("regra extraída automaticamente não pode nascer validated",
                 rule_id=rule_id, arquivo=arquivo, linha=linha)

    decisao = proveniencia.get("decision")
    if decisao is not None and decisao not in DECISOES:
        rel.erro(f"provenance.decision fora do conjunto: {decisao}",
                 rule_id=rule_id, arquivo=arquivo, linha=linha)

    if review.get("blocker"):
        rel.erro(
            f"bloqueio documental remanescente: review.blocker={review['blocker']} — "
            f"B1, B3, B5 e B6 já foram decididos pelo PO",
            rule_id=rule_id, arquivo=arquivo, linha=linha,
        )


def _validar_override(rel, regra, rule_id, arquivo, linha) -> None:
    if not regra.get("line_account_override"):
        return
    if rule_id not in OVERRIDE_PERMITIDO:
        permitidos = ", ".join(sorted(OVERRIDE_PERMITIDO))
        rel.erro(
            f"line_account_override não permitido para este rule_id\n"
            f"  Permitido somente em: {permitidos}",
            rule_id=rule_id, arquivo=arquivo, linha=linha,
        )


def _validar_versao(rel, regra, rule_id, arquivo, linha) -> None:
    versao = regra.get("version") or {}
    if not versao.get("valid_from"):
        rel.erro("version.valid_from ausente", rule_id=rule_id, arquivo=arquivo, linha=linha)
    if versao.get("valid_until") is not None:
        rel.erro(
            f"version.valid_until deve ser null — o IPC07 não declara fim de vigência "
            f"(obtido: {versao['valid_until']})",
            rule_id=rule_id, arquivo=arquivo, linha=linha,
        )


def _validar_condicao(rel, regra, rule_id, arquivo, linha) -> None:
    condicao = ((regra.get("calculation") or {}).get("condition") or {}).get("when")
    if condicao is not None and condicao not in CONDICOES:
        rel.erro(
            f"calculation.condition.when fora do conjunto fechado: {condicao!r} — "
            f"esperado {sorted(CONDICOES)}",
            rule_id=rule_id, arquivo=arquivo, linha=linha,
        )


# ─── referências e ciclos ────────────────────────────────────────────────────

def _colunas_efetivas(regras) -> dict[str, set[str] | None]:
    """Colunas que cada linha apresenta, resolvidas como o motor resolve.

    Linha que declara `columns` apresenta essas. Linha composta que não declara herda a
    **interseção** das colunas das linhas que referencia — o mesmo critério de
    `app/domain/bo/matriz.py::_colunas_das_filhas`. Sem resolver transitivamente, uma referência
    que nomeia coluna de linha composta (`L24`, `L48`) não teria como ser conferida, e é
    exatamente esse o caso das linhas cruzadas.

    Devolve `None` para linha cujas colunas não puderam ser resolvidas — aí a conferência é
    omitida, em vez de acusar erro que pode não existir.
    """
    por_id = {r.get("rule_id"): r for r, _a, _l in regras}
    memo: dict[str, set[str] | None] = {}

    def resolver(rule_id: str, visitando: frozenset[str]) -> set[str] | None:
        if rule_id in memo:
            return memo[rule_id]
        if rule_id in visitando:
            return None                     # ciclo: reportado à parte, não aqui
        regra = por_id.get(rule_id)
        if regra is None:
            return None
        declaradas = regra.get("columns")
        if declaradas is not None:
            memo[rule_id] = set(declaradas)
            return memo[rule_id]
        alvos = [
            ref.get("rule")
            for ref in ((regra.get("calculation") or {}).get("references") or [])
            if ref.get("rule")
        ]
        conjuntos = [resolver(a, visitando | {rule_id}) for a in alvos]
        if not conjuntos or any(c is None for c in conjuntos):
            memo[rule_id] = None
            return None
        comuns = set(conjuntos[0])
        for c in conjuntos[1:]:
            comuns &= c
        memo[rule_id] = comuns
        return comuns

    return {rule_id: resolver(rule_id, frozenset()) for rule_id in por_id}


def _validar_referencias(rel, regras) -> None:
    conhecidos = {r.get("rule_id") for r, _a, _l in regras}
    colunas_de = _colunas_efetivas(regras)
    grafo: dict[str, list[str]] = {}
    posicao: dict[str, tuple[str, int]] = {}

    for regra, arquivo, linha in regras:
        rule_id = regra.get("rule_id")
        posicao[rule_id] = (str(arquivo), linha)
        alvos = []
        for referencia in ((regra.get("calculation") or {}).get("references") or []):
            alvo = referencia.get("rule")
            if not alvo:
                continue
            alvos.append(alvo)
            if referencia.get("sign") not in SINAIS:
                rel.erro(f"sinal inválido na referência a {alvo}",
                         rule_id=rule_id, arquivo=str(arquivo), linha=linha)
            if alvo not in conhecidos:
                rel.erro(
                    f"referência a rule_id inexistente: {alvo}",
                    rule_id=rule_id, arquivo=str(arquivo), linha=linha,
                )
                continue
            # Coluna nomeada tem de existir na linha referenciada. Sem isso, a parcela seria
            # tratada como inexistente e o total sairia com uma parcela a menos, sem aviso.
            pedida = referencia.get("column")
            disponiveis_alvo = colunas_de.get(alvo)
            if pedida and disponiveis_alvo is not None and pedida not in disponiveis_alvo:
                disponiveis = sorted(disponiveis_alvo or {"<nenhuma>"})
                rel.erro(
                    f"referência a {alvo} nomeia coluna inexistente: {pedida} — "
                    f"disponíveis: {', '.join(disponiveis)}",
                    rule_id=rule_id, arquivo=str(arquivo), linha=linha,
                )
        grafo[rule_id] = alvos

    for caminho in _ciclos(grafo):
        origem = caminho[0]
        arquivo, linha = posicao.get(origem, (None, None))
        rel.erro("dependência circular: " + " → ".join(caminho),
                 rule_id=origem, arquivo=arquivo, linha=linha)


def _ciclos(grafo: dict[str, list[str]]) -> list[list[str]]:
    """Busca em profundidade devolvendo o caminho completo de cada ciclo encontrado."""
    encontrados: list[list[str]] = []
    estado: dict[str, int] = {}   # 0 = não visto, 1 = na pilha, 2 = fechado
    pilha: list[str] = []

    def visitar(no: str) -> None:
        estado[no] = 1
        pilha.append(no)
        for vizinho in grafo.get(no, []):
            if vizinho not in grafo:
                continue
            if estado.get(vizinho, 0) == 1:
                inicio = pilha.index(vizinho)
                encontrados.append([*pilha[inicio:], vizinho])
            elif estado.get(vizinho, 0) == 0:
                visitar(vizinho)
        pilha.pop()
        estado[no] = 2

    for no in grafo:
        if estado.get(no, 0) == 0:
            visitar(no)
    return encontrados


# ─── policies e índice ───────────────────────────────────────────────────────

def _validar_policies(rel, policies, schemas) -> None:
    schema = schemas.get("policy")
    for policy, arquivo, linha in policies:
        if not policy.get("policy_id"):
            rel.erro("policy sem policy_id", arquivo=str(arquivo), linha=linha)
        if not policy.get("source"):
            rel.erro("policy sem bloco source",
                     rule_id=policy.get("policy_id"), arquivo=str(arquivo), linha=linha)
        if not schema:
            continue
        import jsonschema

        for falha in jsonschema.Draft202012Validator(schema).iter_errors(policy):
            rel.erro(f"schema: {falha.message}",
                     rule_id=policy.get("policy_id"), arquivo=str(arquivo), linha=linha)


def _validar_indice(rel, base, regras) -> None:
    caminho = base / "indexes" / "rules_index.json"
    if not caminho.is_file():
        return  # ainda não gerado; `build_index.py` cria
    from scripts import build_index

    gravado = json.loads(caminho.read_text(encoding="utf-8"))
    esperado = build_index.construir(base)
    faltando = sorted(set(esperado) - set(gravado))
    sobrando = sorted(set(gravado) - set(esperado))
    if faltando or sobrando:
        rel.erro(
            "índice desatualizado — "
            + (f"ausentes: {', '.join(faltando)}. " if faltando else "")
            + (f"obsoletos: {', '.join(sobrando)}." if sobrando else ""),
            arquivo=str(caminho),
        )


# ─── contagens ───────────────────────────────────────────────────────────────

def _contar(regras, excecoes) -> dict:
    por_quadro: dict[str, int] = {}
    por_status = dict.fromkeys(STATUS, 0)
    rule_ids: list[str] = []
    valid_until: list = []

    for regra, arquivo, _linha in regras:
        rule_ids.append(regra.get("rule_id"))
        por_quadro[arquivo.stem] = por_quadro.get(arquivo.stem, 0) + 1
        status = regra.get("status")
        if status in por_status:
            por_status[status] += 1
        valid_until.append((regra.get("version") or {}).get("valid_until"))

    return {
        "rule_ids": rule_ids,
        "por_quadro": por_quadro,
        "por_status": por_status,
        "valid_until": valid_until,
        "excecoes_dominio": excecoes,
        "total": len(rule_ids),
    }


def main() -> int:
    configurar_saida()
    base = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("knowledge")
    rel = validar(base)
    for erro in rel.erros:
        print(erro)
        print()
    contagens = rel.contagens
    quadros = " · ".join(f"{k} {v}" for k, v in sorted(contagens["por_quadro"].items()))
    status = " · ".join(f"{k} {v}" for k, v in sorted(contagens["por_status"].items()))
    print(f"Regras por quadro    {quadros}   (total {contagens['total']})")
    print(f"Regras por status    {status}")
    for rotulo, marca in (("B1", "B1"), ("B3", "B3"), ("B2", "B2"), ("B4", "B4")):
        itens = [e for e in contagens["excecoes_dominio"] if marca in e["motivo"]]
        if itens:
            codigos = len({e["literal"] for e in itens})
            linhas = len({e["rule_id"] for e in itens})
            print(f"Exceção {rotulo}            {codigos} código(s) / {linhas} linha(s)")
    return rel.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
