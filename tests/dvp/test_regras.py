"""Base canônica da DVP (IPC 05, ed. 2020-01).

A coluna Exclusões fica na evidência e não vira filtro (PO 2026-10-23).
"""
from __future__ import annotations

import functools

import yaml

from tests.conftest import KNOWLEDGE


@functools.lru_cache(maxsize=1)
def base() -> dict[str, dict]:
    regras: dict[str, dict] = {}
    for arquivo in sorted((KNOWLEDGE / "rules" / "dvp").glob("*.yaml")):
        for regra in (yaml.safe_load(arquivo.read_text(encoding="utf-8")) or {}).get("rules", []):
            regras[regra["rule_id"]] = regra
    return regras


def test_dezenove_regras_sem_exclusao():
    """Scenario: dezenove regras sem exclusão."""
    regras = base()
    assert len(regras) == 19
    assert len(regras) == len(set(regras))
    assert all(rule_id.startswith("dvp.quadro_principal.") for rule_id in regras)
    for regra in regras.values():
        assert "filters" not in regra, regra["rule_id"]
        assert "exclusion_groups" not in regra, regra["rule_id"]


def test_formulas_do_quadro():
    """Requisito: dezenove linhas — L1, L9 e L19 só referenciam outras linhas."""
    regras = base()

    def sinais(rule_id: str) -> list[tuple[str, str]]:
        return [(ref["rule"], ref["sign"]) for ref in regras[rule_id]["calculation"]["references"]]

    assert sinais("dvp.quadro_principal.vpa.l1") == [
        (f"dvp.quadro_principal.vpa.l{n}", "+") for n in range(2, 9)
    ]
    assert sinais("dvp.quadro_principal.vpd.l9") == [
        (f"dvp.quadro_principal.vpd.l{n}", "+") for n in range(10, 19)
    ]
    assert sinais("dvp.quadro_principal.resultado.l19") == [
        ("dvp.quadro_principal.vpa.l1", "+"),
        ("dvp.quadro_principal.vpd.l9", "-"),
    ]
    for rule_id in (
        "dvp.quadro_principal.vpa.l1",
        "dvp.quadro_principal.vpd.l9",
        "dvp.quadro_principal.resultado.l19",
    ):
        assert "columns" not in regras[rule_id]


def test_prefixo_do_segundo_nivel_nas_duas_colunas():
    """Requisito: duas colunas — mesmo prefixo nas duas, sem saldo patrimonial."""
    esperado = {
        "dvp.quadro_principal.vpa.l2": "41",
        "dvp.quadro_principal.vpa.l3": "42",
        "dvp.quadro_principal.vpa.l4": "43",
        "dvp.quadro_principal.vpa.l5": "44",
        "dvp.quadro_principal.vpa.l6": "45",
        "dvp.quadro_principal.vpa.l7": "46",
        "dvp.quadro_principal.vpa.l8": "49",
        "dvp.quadro_principal.vpd.l10": "31",
        "dvp.quadro_principal.vpd.l11": "32",
        "dvp.quadro_principal.vpd.l12": "33",
        "dvp.quadro_principal.vpd.l13": "34",
        "dvp.quadro_principal.vpd.l14": "35",
        "dvp.quadro_principal.vpd.l15": "36",
        "dvp.quadro_principal.vpd.l16": "37",
        "dvp.quadro_principal.vpd.l17": "38",
        "dvp.quadro_principal.vpd.l18": "39",
    }
    for rule_id, prefixo in esperado.items():
        regra = base()[rule_id]
        for coluna in ("exercicio_atual", "exercicio_anterior"):
            contas = regra["columns"][coluna]["accounts"]
            assert [conta["pattern"] for conta in contas] == [prefixo], rule_id
            assert all("saldo" not in conta for conta in contas), rule_id


def test_validador_nao_acusa_regra_da_dvp(validar):
    """Requisito: dezenove linhas — índice e validador enxergam as 19 regras da DVP."""
    rel = validar(KNOWLEDGE)
    da_dvp = [erro for erro in rel.erros if (erro.rule_id or "").startswith("dvp.")]
    assert not da_dvp, "\n".join(f"{erro.rule_id} {erro.mensagem}" for erro in da_dvp)
    assert rel.contagens["por_quadro"]["DVP"] == {"quadro_principal": 19}
