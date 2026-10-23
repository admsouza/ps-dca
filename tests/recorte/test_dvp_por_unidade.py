"""DVP (`I-HI`) por unidade gestora, com a coluna do exercício anterior por recorte.

Change `dvp-por-unidade-gestora`, capabilities `dca/demonstracao-variacoes-patrimoniais` e
`pipeline/unidade-gestora`.
"""
from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.services.dvp.quadro_principal import apurar as apurar_dvp
from app.services.pipeline import apuracao
from app.services.pipeline.anterior import validar_escolhas
from app.services.pipeline.cache import parametros_efetivos
from app.services.pipeline.resultado import para_dados
from tests.bo.conftest import saldo
from tests.bp.conftest import FontePorAno
from tests.dvp.conftest import EXERCICIO, JP
from tests.pipeline.conftest import RegistroFake, RepoFake

D = Decimal
ATUAL, ANTERIOR = "exercicio_atual", "exercicio_anterior"
PROCESSADO, MSCE, MANUAL = ("processado_exercicio_anterior", "msce_exercicio_anterior", "manual")
SEM_ANTERIOR = "sem_anterior"
CALCULADO = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)
L2, L6 = "411210200", "451120100"          # VPA: impostos (L2) e transferências intra (L6)
BASE = ("L2", "L3", "L4", "L5", "L6", "L7", "L8", "L10", "L11", "L12", "L13", "L14", "L15",
        "L16", "L17", "L18")


def _r(conta: str, valor: str, ug: str, po: str):
    return saldo(conta, valor)._replace(
        unidade_gestora=ug, nome_unidade_gestora=f"UG {ug}", poder_orgao=po)


def _ano(l2: dict[str, str], l6: dict[str, str] | None = None) -> dict[int, list]:
    """`{ug: valor}` de L2 (e L6) na classe 4; UG 1 é do Executivo, UG 4 do Legislativo."""
    po = {"1": "10131", "4": "20231"}
    return {4: [_r(L2, v, ug, po[ug]) for ug, v in l2.items()]
            + [_r(L6, v, ug, po[ug]) for ug, v in (l6 or {}).items()]}


def _fonte(n: dict, n1: dict | None = None) -> FontePorAno:
    return FontePorAno({EXERCICIO: n, EXERCICIO - 1: n1 or {}})


def _dvp(fonte, repo=None, escolhas=None, agora=(), **extras):
    return apuracao.com_recortes(apurar_dvp, JP, EXERCICIO, fonte, repo=repo, anexo="I-HI",
                                 escolhas=escolhas, agora=agora,
                                 anterior=extras.pop("anterior", MSCE), **extras)


def _n1(registros: dict, status: str = "ok") -> RegistroFake:
    ano = EXERCICIO - 1
    dados = para_dados(apuracao.com_recortes(
        apurar_dvp, JP, ano, FontePorAno({ano: registros}), anterior=MSCE))
    return RegistroFake(str(JP), ano, "I-HI", status=status, resultado=dados,
                        versao_regras="r|c12:-:f=publicsoft", calculado_em=CALCULADO)


def _cel(resultado, codigo: str, coluna: str = ANTERIOR):
    rule_id = next(i.id for i in resultado.mapa.linhas if i.codigo == codigo)
    return resultado.matriz[rule_id][coluna]


N = _ano({"1": "100.00", "4": "40.00"}, {"1": "7.00", "4": "3.00"})
N1 = _ano({"1": "70.00", "4": "30.00"})


# ─── origens por unidade ─────────────────────────────────────────────────────

def test_processado_traz_a_procedencia_do_n1():
    """Scenario: processado traz a procedência do N−1"""
    r = _dvp(_fonte(N), RepoFake([_n1(N1)]))

    ug1 = r.recortes["ug:1"].resultado
    assert _cel(ug1, "L2") == D("70.00") and _cel(ug1, "L2", ATUAL) == D("100.00")
    assert _cel(r.recortes["ug:4"].resultado, "L2") == D("30.00")
    assert ug1.procedencia.origem_exercicio_anterior == PROCESSADO
    assert ug1.procedencia.anterior_processado["exercicio"] == EXERCICIO - 1
    assert ug1.procedencia.anterior_processado["versao_regras"]


def test_unidade_sem_msc_no_exercicio_anterior():
    """Scenario: unidade sem MSC no exercício anterior"""
    r = _dvp(_fonte(N), RepoFake())

    ug1 = r.recortes["ug:1"].resultado
    assert _cel(ug1, "L2") == D("0.00") and _cel(ug1, "L17") == D("0.00")
    assert not [n for n in ug1.diagnostico.nao_apuradas if n.coluna == ANTERIOR]
    assert ug1.diagnostico.sem_dados_exercicio_anterior is True
    assert ug1.procedencia.origem_exercicio_anterior == SEM_ANTERIOR


def test_msce_nao_e_escolha_do_pedido():
    """Scenario: msce não é escolha do pedido"""
    with pytest.raises(ValueError, match="Processado ou Manual"):
        validar_escolhas("I-HI", EXERCICIO, {"ug:3": SimpleNamespace(origem=MSCE, valores=None)})


def test_consolidado_soma_as_unidades():
    """Scenario: consolidado soma as unidades"""
    escolhas = {"ug:4": {"origem": MANUAL, "valores": {"L2": "5.00", "L6": "1.00"}}}
    r = _dvp(_fonte(N), RepoFake([_n1(N1)]), escolhas=escolhas)

    ug1, ug4 = (r.recortes[c].resultado for c in ("ug:1", "ug:4"))
    assert _cel(ug1, "L2") == D("70.00") and _cel(ug4, "L2") == D("5.00")
    assert _cel(r, "L2") == D("75.00") and _cel(r, "L6") == D("1.00")
    assert _cel(r, "L1") == D("76.00")
    assert r.procedencia.origem_exercicio_anterior == "soma_das_unidades"
    assert _cel(r, "L2", ATUAL) == D("140.00")


# ─── manual ──────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("codigo", ["L1", "L9", "L19"])
def test_manual_recusa_linha_totalizadora(codigo):
    """Scenario: manual recusa linha totalizadora"""
    from app.services.dvp.informados import validar_valores_anteriores

    with pytest.raises(ValueError, match="totalizadora"):
        validar_valores_anteriores(EXERCICIO, {codigo: "1.00"})


def test_manual_aceita_as_16_linhas_base_e_recusa_codigo_e_valor_invalidos():
    """Requisito: Manual da DVP por unidade — só L2–L8 e L10–L18, chave sem prefixo"""
    from app.services.dvp.informados import validar_valores_anteriores

    validar_valores_anteriores(EXERCICIO, {c: "1.00" for c in BASE})
    for ruim in ({"L99": "1.00"}, {"P:L2": "1.00"}, {"L2": "abc"}):
        with pytest.raises(ValueError):
            validar_valores_anteriores(EXERCICIO, ruim)


def test_totalizadora_sai_da_calculation():
    """Scenario: totalizadora sai da calculation"""
    valores = {c: "10.00" for c in ("L2", "L3", "L4", "L5", "L6", "L7", "L8")}
    r = _dvp(_fonte(N), escolhas={"ug:1": {"origem": MANUAL, "valores": valores}})

    ug1 = r.recortes["ug:1"].resultado
    assert _cel(ug1, "L1") == D("70.00")
    assert ug1.procedencia.origem_exercicio_anterior == MANUAL
    assert ug1.procedencia.valores_anteriores == valores


def test_manual_sem_valores():
    """Scenario: manual sem valores"""
    for valores in (None, {}):
        with pytest.raises(ValueError, match="manual exige valores"):
            validar_escolhas("I-HI", EXERCICIO,
                             {"ug:3": SimpleNamespace(origem=MANUAL, valores=valores)})


# ─── recortes no mesmo job ───────────────────────────────────────────────────

def test_unidades_somam_o_consolidado():
    """Scenario: unidades somam o consolidado"""
    r = _dvp(_fonte(N), RepoFake([_n1(N1)]))

    assert {"ug:1", "ug:4"} <= set(r.recortes)
    unidades = [r.recortes[c].resultado for c in ("ug:1", "ug:4")]
    for codigo in BASE:
        for coluna in (ATUAL, ANTERIOR):
            assert sum(_cel(u, codigo, coluna) for u in unidades) == _cel(r, codigo, coluna), codigo


def test_consolidado_atual_igual_ao_de_antes():
    """Requisito: o consolidado da DVP não muda de valor com os recortes"""
    com = para_dados(_dvp(_fonte(N, N1)))
    sem = para_dados(apurar_dvp(JP, EXERCICIO, _fonte(N, N1), anterior=MSCE))
    atual = {k: v[ATUAL] for k, v in com["matriz"].items()}
    assert atual == {k: v[ATUAL] for k, v in sem["matriz"].items()}


def test_uma_leitura_da_fonte_para_todos_os_recortes():
    """Scenario: uma leitura da fonte para todos os recortes"""
    from app.infra.msc.escopo import escopo

    bruta = _fonte(N, N1)
    with escopo():
        _dvp(apuracao._NoEscopo(bruta, "publicsoft"), RepoFake([_n1(N1)]))

    lidas = [(c["ano"], c["classe"]) for c in bruta.chamadas]
    assert lidas and len(lidas) == len(set(lidas)), lidas


# ─── percurso ────────────────────────────────────────────────────────────────

def test_percurso_completo_apura_a_dvp_por_unidade(monkeypatch):
    """Scenario: percurso completo apura a DVP por unidade"""
    from app.services.pipeline.completo import pedido_do_percurso

    assert "I-HI" in apuracao.RECORTAVEIS
    gravado = RegistroFake(str(JP), EXERCICIO, "I-HI", resultado={"recortes": {
        "ug:1": {"resultado": {"procedencia": {
            "escolha_anterior": {"origem": MANUAL, "valores": {"L2": "9.00"}}}}}}})
    pedido = pedido_do_percurso(gravado, "publicsoft", "I-HI")
    assert pedido["anterior_por_recorte"] == {"ug:1": {"origem": MANUAL,
                                                       "valores": {"L2": "9.00"}}}
    assert "anterior_agora" not in pedido
    assert parametros_efetivos({"fonte": "publicsoft"}, gravado, "I-HI") == pedido

    monkeypatch.setattr(apuracao, "fonte", lambda *_: _fonte(N))
    r = apuracao.apurador("I-HI", parametros=pedido, repo=RepoFake())(JP, EXERCICIO)

    assert set(r.recortes) >= {"ug:1", "ug:4"}
    ug1 = r.recortes["ug:1"].resultado
    assert _cel(ug1, "L2") == D("9.00") and ug1.procedencia.origem_exercicio_anterior == MANUAL
    assert r.recortes["ug:4"].resultado.procedencia.origem_exercicio_anterior == SEM_ANTERIOR
