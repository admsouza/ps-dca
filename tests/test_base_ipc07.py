"""Cenários normativos — o conteúdo real das 69 regras do IPC 07.

Diferente de `test_validador.py`, que exercita o validador com regras sintéticas, aqui a
asserção é sobre a base transcrita em `knowledge/rules/bo/`. Cada teste cita a página do
IPC 07 de onde a regra vem.

Enquanto a transcrição (tasks 3.3 e 3.4) não existir, todos falham por ausência da base —
é o vermelho esperado da fase TEST.
"""
from __future__ import annotations

import functools

import pytest
import yaml

from tests.conftest import KNOWLEDGE

QUADROS = ("quadro_principal", "rp_nao_processados", "rp_processados")


@functools.lru_cache(maxsize=1)
def _base() -> dict[str, dict]:
    diretorio = KNOWLEDGE / "rules" / "bo"
    assert diretorio.is_dir(), f"base canônica ausente: {diretorio}"
    regras: dict[str, dict] = {}
    for quadro in QUADROS:
        arquivo = diretorio / f"{quadro}.yaml"
        assert arquivo.is_file(), f"quadro ausente: {arquivo}"
        dados = yaml.safe_load(arquivo.read_text(encoding="utf-8")) or {}
        for r in dados.get("rules", []):
            regras[r["rule_id"]] = r
    return regras


def rule(rule_id: str) -> dict:
    base = _base()
    assert rule_id in base, f"regra ausente na base: {rule_id}"
    return base[rule_id]


def contas(regra: dict, coluna: str) -> list[str]:
    return [c["pattern"] for c in regra["columns"][coluna]["accounts"]]


def sinais(regra: dict, coluna: str) -> dict[str, str]:
    return {c["pattern"]: c["sign"] for c in regra["columns"][coluna]["accounts"]}


def filtro(regra: dict, campo: str) -> dict:
    achados = [f for f in regra.get("filters", []) if f["field"] == campo]
    assert achados, f"{regra['rule_id']} não filtra por {campo}"
    return achados[0]


# ─── Regra por linha, com o mapa de colunas do quadro ────────────────────────

def test_linha_de_receita_com_quatro_colunas():
    """Scenario: linha de receita com quatro colunas (IPC07 p. 8, L2)."""
    r = rule("bo.quadro_principal.receitas.l2")
    assert set(r["columns"]) == {
        "previsao_inicial", "previsao_atualizada", "receitas_realizadas", "saldo"
    }
    assert set(v["pattern"] for v in filtro(r, "natureza_receita")["values"]) == {"11", "71"}
    assert sinais(r, "previsao_atualizada") == {"5211": "+", "5212": "+"}
    referencias = r["columns"]["saldo"]["calculation"]["references"]
    assert referencias == [
        {"column": "receitas_realizadas", "sign": "+"},
        {"column": "previsao_atualizada", "sign": "-"},
    ]


def test_linha_de_despesa_com_seis_colunas():
    """Scenario: linha de despesa com seis colunas (IPC07 p. 10, L32)."""
    r = rule("bo.quadro_principal.despesas.l32")
    assert set(r["columns"]) == {
        "dotacao_inicial", "dotacao_atualizada", "empenhadas", "liquidadas", "pagas",
        "saldo_dotacao",
    }
    assert [v["pattern"] for v in filtro(r, "natureza_despesa")["values"]] == ["31"]
    assert len(contas(r, "empenhadas")) == 7
    assert r["columns"]["saldo_dotacao"]["calculation"]["references"] == [
        {"column": "dotacao_atualizada", "sign": "+"},
        {"column": "empenhadas", "sign": "-"},
    ]


def test_coluna_com_contas_de_sinal_negativo():
    """Scenario: coluna com contas de sinal negativo (IPC07 p. 12, RPNP coluna (a)).

    Ancorado em `L2`, e não em `L1`: as colunas do quadro só existem nas linhas de filtro —
    `L1`, `L5` e `L9` são compostas por referência e não declaram contas próprias.
    """
    r = rule("bo.rp_nao_processados.l2")
    mapa = sinais(r, "inscritos_exerc_anteriores")
    assert mapa["5312"] == "+" and mapa["5316"] == "+"
    assert mapa["6316"] == "-"
    # `5.3.1.3` está no literal do IPC 07, mas foi descontinuada e o conteúdo está em `5.3.1.2`,
    # que já é o primeiro termo — declarar as duas duplicaria a conta.
    assert "5313" not in mapa
    assert len(mapa) == 3


@pytest.mark.parametrize("quadro", ["rp_nao_processados", "rp_processados"])
def test_quadro_sem_coluna_de_exclusoes(quadro):
    """Scenario: quadro sem coluna de exclusões — as 18 regras não declaram exclusão."""
    regras = [r for rid, r in _base().items() if rid.startswith(f"bo.{quadro}.")]
    assert len(regras) == 9
    for r in regras:
        assert not [f for f in r.get("filters", []) if f["operator"] == "not_in"]
        assert "exclusion_groups" not in r


# ─── Filtros ─────────────────────────────────────────────────────────────────

def test_exclusao_por_padroes_de_conta_pcasp():
    """Scenario: exclusão por padrões de conta PCASP (IPC07 p. 9, L11 — 8 códigos)."""
    r = rule("bo.quadro_principal.receitas.l11")
    assert set(v["pattern"] for v in filtro(r, "natureza_receita")["values"]) == {"21", "81"}
    exclusoes = [f for f in r["filters"] if f["field"] == "conta_contabil"
                 and f["operator"] == "not_in"]
    assert len(exclusoes) == 1
    assert len(exclusoes[0]["values"]) == 8


def test_funcao_e_subfuncao_como_filtros_separados():
    """Scenario: função e subfunção como filtros separados (IPC07 p. 10, L38)."""
    r = rule("bo.quadro_principal.despesas.l38")
    literais = str(r)
    assert "28.841" in literais, "literal concatenado do PDF deve ser preservado"
    grupos = r["exclusion_groups"]
    campos = {f["field"] for grupo in grupos for f in grupo}
    assert "funcao" in campos and "subfuncao" in campos


def test_duas_exclusoes_independentes_em_l38():
    """Scenario: exclusões de L38 — dois grupos, não uma lista achatada."""
    r = rule("bo.quadro_principal.despesas.l38")
    grupos = r["exclusion_groups"]
    assert len(grupos) == 2

    def sub(grupo):
        alvo = [f for f in grupo if f["field"] == "subfuncao"][0]
        return {v["pattern"] for v in alvo["values"]}

    def nd(grupo):
        alvo = [f for f in grupo if f["field"] == "natureza_despesa"][0]
        return {v["literal"] for v in alvo["values"]}

    por_nd = {next(iter(nd(g))): sub(g) for g in grupos}
    assert por_nd["46.xx.76"] == {"841", "842", "843", "844"}
    assert por_nd["46.xx.77"] == {"841", "842", "843", "844", "846"}


def test_duas_grafias_do_mesmo_codigo_normalizam_igual():
    """Scenario: duas grafias do mesmo código (p. 9 `2111.00.20` × `2111.00.2.0`)."""
    l11 = rule("bo.quadro_principal.receitas.l11")
    l19 = rule("bo.quadro_principal.receitas.l19")

    def padroes(r):
        return {v["pattern"] for f in r["filters"] if f["field"] == "conta_contabil"
                for v in f["values"]}

    assert padroes(l11) & padroes(l19), "as grafias devem normalizar para os mesmos dígitos"


# ─── Cálculo e guardas ───────────────────────────────────────────────────────

def test_soma_de_linhas_em_l1():
    """Scenario: soma de linhas (IPC07 p. 8, L1 = L2+…+L9)."""
    r = rule("bo.quadro_principal.receitas.l1")
    referencias = r["calculation"]["references"]
    assert len(referencias) == 8
    assert all(ref["sign"] == "+" for ref in referencias)
    assert "columns" not in r and "filters" not in r


def test_referencia_entre_grupos_em_l25():
    """Scenario: referência do bloco de receitas para o de despesas (p. 9, L25 = L48 - L24)."""
    r = rule("bo.quadro_principal.receitas.l25")
    referencias = {ref["rule"]: ref["sign"] for ref in r["calculation"]["references"]}
    assert referencias == {
        "bo.quadro_principal.despesas.l48": "+",
        "bo.quadro_principal.receitas.l24": "-",
    }


def test_deficit_orcamentario_tem_condicao():
    """Scenario: déficit orçamentário (p. 9, L25 — somente quando deficitário)."""
    r = rule("bo.quadro_principal.receitas.l25")
    assert r["calculation"]["condition"]["when"] == "result_positive"
    assert "deficitário" in r["evidence"]["text"].lower()


def test_superavit_orcamentario_e_simetrico():
    """Scenario: superávit orçamentário (p. 11, L49 = L24 - L48)."""
    r = rule("bo.quadro_principal.despesas.l49")
    referencias = {ref["rule"]: ref["sign"] for ref in r["calculation"]["references"]}
    assert referencias == {
        "bo.quadro_principal.receitas.l24": "+",
        "bo.quadro_principal.despesas.l48": "-",
    }
    assert r["calculation"]["condition"]["when"] == "result_positive"


def test_leitura_cega_de_linha_composta():
    """Scenario: leitura cega de uma linha composta (L48 = L40 + L41, p. 11)."""
    r = rule("bo.quadro_principal.despesas.l48")
    assert r["quadro"]["codigo"] == "QUADRO_PRINCIPAL"
    assert r["grupo"]["codigo"] == "DESPESAS"
    assert r["linha"]["codigo"] == "L48"
    assert {ref["rule"] for ref in r["calculation"]["references"]} == {
        "bo.quadro_principal.despesas.l40", "bo.quadro_principal.despesas.l41",
    }
    assert r["source"]["document"] == "IPC07" and r["source"]["page"] == 11


# ─── Ambiguidade documental resolvida por evidência ──────────────────────────

def test_rotulo_com_hifen_espurio():
    """Scenario: rótulo com hífen espúrio (p. 10 grafa `L-40`)."""
    r = rule("bo.quadro_principal.despesas.l40")
    assert r["source"]["row"] == "L-40"
    assert "L-40" in r["evidence"]["text"]


def test_numeral_romano_inconsistente_no_subtotal():
    """Scenario: numeral romano inconsistente no subtotal das despesas (L40)."""
    r = rule("bo.quadro_principal.despesas.l40")
    referencias = r["calculation"]["references"]
    assert {ref["rule"] for ref in referencias} == {
        "bo.quadro_principal.despesas.l31",
        "bo.quadro_principal.despesas.l35",
        "bo.quadro_principal.despesas.l39",
    }
    assert all(ref["sign"] == "+" for ref in referencias)
    assert len(referencias) == 3, "não existe quarto componente"
    assert "(VII + IX + X)" in r["evidence"]["text"]
    assert r["provenance"]["reading"]["adopted_from_page"] == 15


def test_sinal_espurio_no_rotulo_de_despesas_correntes():
    """Scenario: sinal espúrio no rótulo de Despesas Correntes (p. 10 `(-VIII)`)."""
    r = rule("bo.quadro_principal.despesas.l31")
    assert "-VIII" not in r["linha"]["descricao"]
    assert "-VIII" in r["evidence"]["text"]


def test_sinal_espurio_em_lista_de_subfuncoes():
    """Scenario: sinal espúrio em lista de subfunções (p. 11, L47)."""
    r = rule("bo.quadro_principal.despesas.l47")
    subfuncoes = {v["pattern"] for f in r["filters"] if f["field"] == "subfuncao"
                  for v in f["values"]}
    assert subfuncoes == {"842", "844", "846"}


# ─── Decisões do PO com escopo fechado ───────────────────────────────────────

def test_refinanciamento_usa_padroes_de_conta_pcasp():
    """Scenario: refinanciamento usa padrões de conta PCASP (B3, 8 códigos em 5 regras)."""
    ids = [
        "bo.quadro_principal.receitas.l11",
        "bo.quadro_principal.receitas.l19",
        "bo.quadro_principal.receitas.l20",
        "bo.quadro_principal.receitas.l22",
        "bo.quadro_principal.receitas.l23",
    ]
    for rid in ids:
        r = rule(rid)
        assert [f for f in r["filters"] if f["field"] == "conta_contabil"]
        assert r["provenance"].get("decision") == "B3"
        assert r["status"] != "review_required"


def test_conta_531_descontinuada_nao_e_declarada():
    """Scenario: a fórmula fica simétrica à do quadro de RP Processados.

    Substitui `test_conta_531_historica_e_preservada`: a decisão B1 de 2026-08-27 foi revogada em
    2026-09-04, e `5.3.1.3` deixou de ser declarada. O literal de 4 termos segue registrado na
    nota de proveniência da regra.
    """
    regras = [r for rid, r in _base().items() if rid.startswith("bo.rp_nao_processados.")]
    assert len(regras) == 9
    for r in regras:
        for coluna in (r.get("columns") or {}).values():
            padroes = [a.get("pattern") for a in (coluna.get("accounts") or [])]
            assert "5313" not in padroes, "5.3.1.3 não é mais declarada em coluna"
        assert (r.get("provenance") or {}).get("decision") != "B1"
        assert r["status"] != "review_required"
    # O literal normativo não foi apagado.
    notas = " ".join(str((r.get("provenance") or {}).get("reading", "")) for r in regras)
    assert "5.3.1.3.0.00.00" in notas


@pytest.mark.parametrize("rule_id", [
    "bo.quadro_principal.receitas.l29", "bo.quadro_principal.receitas.l30",
])
def test_override_de_conta_em_l29_e_l30(rule_id):
    """Scenario: conta da linha substitui contas das colunas em L29 e L30 (B5)."""
    r = rule(rule_id)
    assert r["line_account_override"] is True
    assert r["status"] != "review_required"


def test_override_nao_aparece_em_nenhuma_outra_regra():
    """Scenario: override de conta fora de L29 e L30 é rejeitado — na base real, ausente."""
    permitidos = {"bo.quadro_principal.receitas.l29", "bo.quadro_principal.receitas.l30"}
    com_override = {rid for rid, r in _base().items() if r.get("line_account_override")}
    assert com_override <= permitidos


@pytest.mark.parametrize("rule_id", [
    "bo.quadro_principal.receitas.l27", "bo.quadro_principal.receitas.l28",
    "bo.quadro_principal.receitas.l30",
])
def test_l27_l28_l30_tem_as_quatro_colunas_de_receita(rule_id):
    """Scenario: L27, L28 e L30 têm as quatro colunas de receita, e L29 tem três."""
    r = rule(rule_id)
    assert set(r["columns"]) == {
        "previsao_inicial", "previsao_atualizada", "receitas_realizadas", "saldo"
    }
    assert r["provenance"].get("decision") == "B6"
    assert r["status"] != "review_required"


def test_l29_nao_declara_previsao_inicial():
    """Scenario: L27, L28 e L30 têm as quatro colunas de receita, e L29 tem três.

    B6 restringida em 2026-09-04: zero de 25 entes publicam `PREVISÃO INICIAL` para
    `SuperavitFinanceiro`. Um superávit financeiro é apurado sobre o exercício fechado.
    """
    r = rule("bo.quadro_principal.receitas.l29")
    assert set(r["columns"]) == {"previsao_atualizada", "receitas_realizadas", "saldo"}
    assert "previsao_inicial" not in r["columns"]
    assert r["provenance"].get("decision") == "B6"
    assert r["status"] != "review_required"


def test_l27_soma_l28_l29_l30():
    """Scenario: L27 a L30 — L27 = L28 + L29 + L30 em cada coluna."""
    r = rule("bo.quadro_principal.receitas.l27")
    alvos = {ref["rule"] for ref in r["calculation"]["references"]}
    assert alvos == {
        "bo.quadro_principal.receitas.l28",
        "bo.quadro_principal.receitas.l29",
        "bo.quadro_principal.receitas.l30",
    }


def test_l51_tem_as_seis_colunas_da_l39():
    """Scenario: L51 Reserva do RPPS usa o mapeamento de despesa da L39.

    Scenario: L51 fica fora do TOTAL (XV)
    """
    r = rule("bo.quadro_principal.despesas.l51")
    l39 = rule("bo.quadro_principal.despesas.l39")
    assert set(r["columns"]) == set(l39["columns"])
    assert len(r["columns"]) == 6
    assert contas(r, "pagas") == contas(l39, "pagas")
    assert [v["pattern"] for v in filtro(r, "natureza_despesa")["values"]] == ["99"]
    assert [v["pattern"] for v in filtro(r, "funcao")["values"]] == ["99"]
    assert [v["pattern"] for v in filtro(r, "subfuncao")["values"]] == ["997"]
    refs_l50 = rule("bo.quadro_principal.despesas.l50")["calculation"]["references"]
    assert "bo.quadro_principal.despesas.l51" not in {ref["rule"] for ref in refs_l50}
    assert r["provenance"].get("decision") == "B6"
    assert r["status"] != "review_required"


# ─── Cobertura completa e fronteira do escopo ────────────────────────────────

def test_cobertura_de_69_linhas_em_tres_quadros():
    """Scenario: contagem por quadro — 51 · 9 · 9, total 69."""
    base = _base()
    por_quadro = {q: len([rid for rid in base if rid.startswith(f"bo.{q}.")]) for q in QUADROS}
    assert por_quadro == {"quadro_principal": 51, "rp_nao_processados": 9, "rp_processados": 9}
    assert len(base) == 69


def test_nenhuma_regra_nasce_bloqueada():
    """Scenario: nenhum bloqueio documental permanece no IPC07."""
    bloqueadas = {rid: r for rid, r in _base().items() if r.get("review", {}).get("blocker")}
    assert bloqueadas == {}
    assert not [r for r in _base().values() if r["status"] == "review_required"]


def test_estrutura_de_publicacao_nao_gera_regra():
    """Scenario: estrutura de publicação não gera regra (pp. 14–17)."""
    das_paginas_de_layout = {
        rid for rid, r in _base().items() if r["source"]["page"] in (14, 15, 16, 17)
    }
    assert das_paginas_de_layout == set()
