"""Base canônica do Balanço Patrimonial (IPC 04, ed. 2020-01), fechada por `bp-apuracao-f1`.

Decisões do PO de 2026-10-07: P2 (`L4` com `11382`), P3 (`L34` bloqueada; destravada em 2026-10-08)
e P4 (atributo F/P por termo de conta, como o IPC 04 escreve).
Evidência: `docs/evidencia-bp-fp-2025.md`.
"""
from __future__ import annotations

import functools

import yaml

from tests.conftest import KNOWLEDGE, mensagens, regra


@functools.lru_cache(maxsize=1)
def _base() -> dict[str, dict]:
    regras: dict[str, dict] = {}
    for arquivo in sorted((KNOWLEDGE / "rules" / "bp").glob("*.yaml")):
        for r in (yaml.safe_load(arquivo.read_text(encoding="utf-8")) or {}).get("rules", []):
            regras[r["rule_id"]] = r
    return regras


def termos(rule_id: str, coluna: str = "exercicio_atual") -> list[tuple[str, str | None]]:
    contas = _base()[rule_id]["columns"][coluna]["accounts"]
    return [(c["pattern"], c.get("financeiro_permanente")) for c in contas]


def test_validador_nao_acusa_regra_do_bp(validar):
    """Requisito: `validate_rules` sem erro `bp.*`; índice com as 58 regras do BP."""
    rel = validar(KNOWLEDGE)
    do_bp = [e for e in rel.erros
             if (e.rule_id or "").startswith("bp.") or "bp." in e.mensagem]
    assert not do_bp, "\n".join(f"{e.rule_id} {e.mensagem}" for e in do_bp)
    assert rel.contagens["por_quadro"]["BP"] == {
        "quadro_principal": 40, "ativos_passivos_financeiros": 7,
        "contas_compensacao": 10, "superavit_deficit": 1,
    }


def test_termos_qualificados_do_quadro_fp():
    """Requisito: IPC 04 p. 10 — o atributo é do termo de conta, não da linha."""
    prefixo = "bp.ativos_passivos_financeiros"
    assert termos(f"{prefixo}.l2") == [("1", "F")]
    assert termos(f"{prefixo}.l3") == [("1", "P")]
    assert termos(f"{prefixo}.l5") == [("21", "F"), ("22", "F"), ("6311", None),
                                       ("6315", None), ("63171", None)]
    assert termos(f"{prefixo}.l6") == [("21", "P"), ("22", "P")]
    for codigo in ("l2", "l3", "l5", "l6"):
        assert _base()[f"{prefixo}.{codigo}"]["status"] == "extracted", codigo
        assert termos(f"{prefixo}.{codigo}") == termos(f"{prefixo}.{codigo}", "exercicio_anterior")


def test_exclusao_intra_so_na_visao_consolidada():
    """Requisito: bp-visao-consolidado-isolado — toda exclusão intra do Quadro Principal é filtro
    `visao: consolidado`; filtro sem visão não existe (valeria nas duas). Literal do PDF
    (inclusive `1.1.3.8.2.000.00` da L4) fica na evidência."""
    l4 = _base()["bp.quadro_principal.ativo.l4"]
    com_filtro = [r for r in _base().values() if r["rule_id"].startswith("bp.quadro_principal")
                  and r.get("filters")]
    assert len(com_filtro) == 21
    for r in com_filtro:
        assert {f.get("visao") for f in r["filters"]} == {"consolidado"}, r["rule_id"]
        assert "só na visão consolidada" in r["review"]["reason"], r["rule_id"]
    assert "1.1.3.8.2.000.00" in l4["evidence"]["text"]
    assert l4["status"] == "extracted"
    assert "blocker" not in (l4.get("review") or {})


def test_l34_apurada_pela_232():
    """Requisito: PO 2026-10-08 — `2.3.2.0.2` do PDF vira `2.3.2.1.2`; L34 apura `2.3.2`."""
    l34 = _base()["bp.quadro_principal.passivo.l34"]
    assert l34["status"] == "extracted"
    assert "blocker" not in l34["review"]
    assert "2.3.2.1.2.00.00" in l34["review"]["reason"]
    assert [c["pattern"] for c in l34["columns"]["exercicio_atual"]["accounts"]] == ["232"]
    assert [v["pattern"] for v in l34["filters"][0]["values"]] == ["23212"]


def test_atributo_fp_e_recusado_fora_do_ipc04(base, validar):
    """Requisito: o qualificador F/P é vocabulário do IPC 04; numa regra do IPC 07 é erro."""
    r = regra(columns={"previsao_inicial": {"label": "x", "accounts": [
        {"literal": "5.2.1.1.0.00.00", "pattern": "5211", "sign": "+",
         "financeiro_permanente": "F"}]}})
    rel = validar(base(quadro_principal=[r]))
    linhas = [m for m in mensagens(rel).splitlines() if "financeiro_permanente" in m]
    assert any("IPC04" in m for m in linhas), mensagens(rel)


def test_visao_do_filtro_e_recusada_fora_do_ipc04(base, validar):
    """Requisito: `visao` no filtro é vocabulário do IPC 04; numa regra do IPC 07 é erro."""
    r = regra(filters=[{"field": "conta_contabil", "operator": "not_in", "visao": "consolidado",
                        "values": [{"literal": "1.1.1.1.2.00.00", "pattern": "11112"}]}])
    rel = validar(base(quadro_principal=[r]))
    assert any("visao" in m for m in mensagens(rel).splitlines()), mensagens(rel)
