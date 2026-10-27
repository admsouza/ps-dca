"""Base canônica da Demonstração dos Fluxos de Caixa (IPC 08, ed. 2020-01).

Transcrição apenas. A apuração em Python não entra nesta change.
"""
from __future__ import annotations

import functools

import yaml

from tests.conftest import KNOWLEDGE, mensagens


@functools.lru_cache(maxsize=1)
def _base() -> dict[str, dict]:
    regras: dict[str, dict] = {}
    for arquivo in sorted((KNOWLEDGE / "rules" / "dfc").glob("*.yaml")):
        for r in (yaml.safe_load(arquivo.read_text(encoding="utf-8")) or {}).get("rules", []):
            regras[r["rule_id"]] = r
    return regras


def test_contagem_por_quadro():
    """Scenario: contagem por quadro"""
    base = _base()
    assert len([r for r in base if r.startswith("dfc.quadro_principal.")]) == 36
    assert len([r for r in base if r.startswith("dfc.transferencias_recebidas_concedidas.")]) == 15
    assert len([r for r in base if r.startswith("dfc.desembolsos_pessoal_por_funcao.")]) == 29
    assert len([r for r in base if r.startswith("dfc.juros_encargos_divida.")]) == 4
    assert len(base) == 84


def test_identificadores_de_grupos_do_quadro_principal():
    """Scenario: identificadores de grupos do quadro principal"""
    assert _base()["dfc.quadro_principal.operacionais.l1"]["grupo"]["codigo"] == "OPERACIONAIS"
    assert _base()["dfc.quadro_principal.investimento.l17"]["grupo"]["codigo"] == "INVESTIMENTO"
    assert _base()["dfc.quadro_principal.financiamento.l26"]["grupo"]["codigo"] == "FINANCIAMENTO"
    assert _base()["dfc.quadro_principal.caixa.l34"]["grupo"]["codigo"] == "CAIXA"


def test_l3_nas_duas_colunas():
    """Scenario: L3 nas duas colunas"""
    l3 = _base()["dfc.quadro_principal.operacionais.l3"]
    for coluna in ("exercicio_atual", "exercicio_anterior"):
        contas = [(c["literal"], c["sign"]) for c in l3["columns"][coluna]["accounts"]]
        assert contas == [("6.2.1.2.0.00.00", "+"), ("6.2.1.3.0.00.00", "-")]


def test_l1_subtrai_desembolsos():
    """Scenario: L1 subtrai desembolsos"""
    refs = [(r["rule"], r["sign"]) for r in
            _base()["dfc.quadro_principal.operacionais.l1"]["calculation"]["references"]]
    assert refs == [
        ("dfc.quadro_principal.operacionais.l2", "+"),
        ("dfc.quadro_principal.operacionais.l12", "-"),
    ]


def test_l35_e_saldo_inicial():
    """Scenario: L35 é saldo inicial"""
    l35 = _base()["dfc.quadro_principal.caixa.l35"]
    for coluna in ("exercicio_atual", "exercicio_anterior"):
        contas = l35["columns"][coluna]["accounts"]
        assert [c["pattern"] for c in contas] == ["111"]
        assert all(c["saldo"] == "inicial" for c in contas)


def test_l36_so_referencia_linhas():
    """Scenario: L36 só referencia linhas"""
    l36 = _base()["dfc.quadro_principal.caixa.l36"]
    assert "columns" not in l36
    refs = [(r["rule"], r["sign"]) for r in l36["calculation"]["references"]]
    assert refs == [
        ("dfc.quadro_principal.caixa.l34", "+"),
        ("dfc.quadro_principal.caixa.l35", "+"),
    ]


def test_l5_exclui_remuneracao_das_disponibilidades():
    """Scenario: L5 exclui remuneração das disponibilidades"""
    filtros = _base()["dfc.quadro_principal.operacionais.l5"]["filters"]
    por_op = {(f["field"], f["operator"]): [v["literal"] for v in f["values"]] for f in filtros}
    assert "1.3.xx.xx.xx" in por_op[("natureza_receita", "in")]
    assert "7.3.xx.xx.xx" in por_op[("natureza_receita", "in")]
    assert "1.3.21.00.1.x" in por_op[("natureza_receita", "not_in")]
    assert "7.3.21.00.31.x" in por_op[("natureza_receita", "not_in")]


def test_l16_sem_contas():
    """Scenario: L16 sem contas"""
    l16 = _base()["dfc.quadro_principal.operacionais.l16"]
    assert l16["status"] == "review_required"
    assert "columns" not in l16
    assert "ipc08.outros_campos_nao_previstos" in l16["policies"]


def test_458066_permanece():
    """Scenario: 45.80.66 permanece"""
    l15 = _base()["dfc.quadro_principal.operacionais.l15"]
    l14 = _base()["dfc.transferencias_recebidas_concedidas.concedidas.l14"]
    for regra in (l15, l14):
        exclusoes = [v["literal"] for f in regra["filters"] if f["operator"] == "not_in"
                     for v in f["values"]]
        assert "45.80.66" in exclusoes


def test_ponto_duplo_em_l9_das_transferencias_concedidas():
    """Scenario: ponto duplo em L9 das transferências concedidas"""
    l9 = _base()["dfc.transferencias_recebidas_concedidas.concedidas.l9"]
    literais = [v["literal"] for f in l9["filters"] for v in f["values"]]
    assert "4.4..22.xx.xx" in literais


def test_l10_saude_filtra_funcao_10():
    """Scenario: L10 Saúde filtra função 10"""
    l10 = _base()["dfc.desembolsos_pessoal_por_funcao.l10"]
    assert l10["linha"]["descricao"] == "Saúde"
    por_campo = {f["field"]: [v["literal"] for v in f["values"]] for f in l10["filters"]}
    assert por_campo["funcao"] == ["10"]
    assert "3.1.71.xx.xx" in por_campo["natureza_despesa"]


def test_dfc_continua_msce_abertura():
    """Scenario: DFC continua MSCE abertura"""
    l35 = _base()["dfc.quadro_principal.caixa.l35"]
    assert all(c.get("saldo") == "inicial" for col in l35["columns"].values()
               for c in col["accounts"])
    for regra in _base().values():
        if regra["rule_id"] == "dfc.quadro_principal.caixa.l35":
            continue
        for coluna in (regra.get("columns") or {}).values():
            assert all(c.get("saldo") != "final" for c in coluna.get("accounts") or [])


def test_agregadora_soma_a_propria_linha_outros():
    """Scenario: agregadora soma a própria linha Outros"""
    esperado = {
        "dfc.quadro_principal.operacionais.l2": "l11",
        "dfc.quadro_principal.operacionais.l12": "l16",
        "dfc.quadro_principal.investimento.l18": "l21",
        "dfc.quadro_principal.investimento.l22": "l25",
        "dfc.quadro_principal.financiamento.l27": "l30",
        "dfc.quadro_principal.financiamento.l31": "l33",
    }
    for agregadora, outros in esperado.items():
        refs = _base()[agregadora]["calculation"]["references"]
        assert (f"dfc.quadro_principal.{agregadora.split('.')[2]}.{outros}", "+") in \
            [(r["rule"], r["sign"]) for r in refs], f"{agregadora} não soma {outros}"
    # a divergência do literal fica registrada, e o literal intacto
    l27 = _base()["dfc.quadro_principal.financiamento.l27"]
    assert l27["evidence"]["text"] == "L27 Ingressos (L28 + L29)"
    assert "D9" in l27["review"]["reason"]


def test_validador_nao_acusa_regra_da_dfc(validar):
    """Requisito: validate_rules sem erro dfc.*; índice com as 84 regras."""
    rel = validar(KNOWLEDGE)
    da_dfc = [e for e in rel.erros if (e.rule_id or "").startswith("dfc.") or "dfc." in e.mensagem]
    assert not da_dfc, "\n".join(f"{e.rule_id} {e.mensagem}" for e in da_dfc)
    assert rel.contagens["por_quadro"]["DFC"] == {
        "quadro_principal": 36,
        "transferencias_recebidas_concedidas": 15,
        "desembolsos_pessoal_por_funcao": 29,
        "juros_encargos_divida": 4,
    }
    assert rel.exit_code == 0, mensagens(rel)


def test_desdobramento_da_natureza_de_receita():
    """Scenario: a remuneração das disponibilidades apura"""
    l9 = _base()["dfc.quadro_principal.operacionais.l9"]
    por_literal = {v["literal"]: v["pattern"]
                   for f in l9["filters"] if f["field"] == "natureza_receita"
                   for v in f["values"]}
    for n in "1234":
        # o 00 do IPC ocupa a posição do desdobramento DD2; o dígito seguinte é o DD2 real
        assert por_literal[f"1.3.21.00.{n}.x"] == f"13210{n}"
        assert por_literal[f"7.3.21.00.{n}.x"] == f"73210{n}"


def test_exclusao_que_nao_casa_fica_declarada():
    """Scenario: a exclusão que não casa fica declarada"""
    l5 = _base()["dfc.quadro_principal.operacionais.l5"]
    assert l5["status"] == "review_required"
    assert "7.3.21.00.31.x" in l5["review"]["blocker"]
    literais = [v["literal"] for f in l5["filters"] for v in f["values"]]
    assert "7.3.21.00.31.x" in literais, "o literal do PDF permanece"
