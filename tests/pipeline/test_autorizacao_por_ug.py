"""Leitura do DCA restrita às UGs autorizadas — change `dca-autorizacao-por-unidade-gestora`.

O hub é um dublê no transporte (`AutorizadorHub._chamar`): o parse real de `poderes/modulos/ugs`
e a dependência `unidade_autorizada` rodam de verdade.
"""
from __future__ import annotations

import asyncio
import json
from copy import deepcopy
from pathlib import Path

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from app.domain import recorte
from tests.pipeline import test_rota_recorte as rota
from tests.pipeline.conftest import ENTE, EXERCICIO, JobsFake, LockFake, RegistroFake, RepoFake
from tests.pipeline.test_rota_anterior_por_recorte import (  # noqa: F401  (fixture `api`)
    CAMARA,
    MANUAL_BP,
    PREFEITURA,
    _cache_com_unidades,
    _n1_com,
    _reprocessar,
    api,
)

OUTRO_ENTE = "2505204"
# Cuitegi: 1 Prefeitura, 3 FMS, 4 FMAS, 5 FMP (RPPS) no Executivo; 7 Câmara no Legislativo.
UGS_CUITEGI = {"ug:1": "10131", "ug:3": "10131", "ug:4": "10131", "ug:5": "10132", "ug:7": "20231"}
GOLDEN = Path(__file__).parent / "golden" / "rota_recorte_sem_ug.json"


def _resultado_cuitegi() -> dict:
    grupos = {c: {"rotulo": c, "resultado": {}} for c in recorte.GRUPOS}
    unidades = {c: {"rotulo": f"UG {c[3:]}", "poderOrgao": po, "resultado": {"ug": c}}
                for c, po in UGS_CUITEGI.items()}
    return {"matriz": {}, "recortes": {**grupos, **unidades}}


class HubFake:
    """Estado do hub por ente: `{ente: corpo}`; `None` = hub fora do ar."""

    def __init__(self, corpos: dict):
        self.corpos = corpos

    async def chamar(self, sub, cod_ibge, caminho="/internal/authorize"):
        corpo = self.corpos[cod_ibge]
        if corpo is None:
            raise ConnectionError("hub fora")
        return {"status": 200, "corpo": corpo}


@pytest.fixture
def hub(monkeypatch):
    from app.auth.hub import AutorizadorHub
    from app.routes import dependencias

    fake = HubFake({})
    monkeypatch.setattr(AutorizadorHub, "configurado", property(lambda self: True))
    monkeypatch.setattr(AutorizadorHub, "_chamar",
                        lambda self, sub, cod_ibge, caminho="/internal/authorize":
                        fake.chamar(sub, cod_ibge, caminho))
    monkeypatch.setattr(dependencias, "_claims", lambda token: {"sub": "u@x"})
    return fake


def _cliente(repo=None, anexo: str = "BO", resultado: dict | None = None, entes=(ENTE,)):
    from app.routes import anexos as rotas
    from app.routes.dependencias import FontePedido, fonte_do_pedido, repositorio

    repo = repo if repo is not None else RepoFake()
    for ente in entes:
        repo.gravar(RegistroFake(ente, EXERCICIO, anexo, status="ok",
                                 resultado=resultado or _resultado_cuitegi()))

    class Fila:
        pendente = None

        def enfileirar(self, *args, **kwargs):
            raise AssertionError("ler um recorte não pode enfileirar")

    app = FastAPI()
    app.include_router(rotas.router)
    app.dependency_overrides[repositorio] = lambda: repo
    app.dependency_overrides[fonte_do_pedido] = lambda: FontePedido("publicsoft")
    app.state.portas = {"fila_async": Fila, "lock": LockFake(), "jobs": JobsFake(),
                        "repo_vigencias": None, "base_url": ""}
    return TestClient(app)


def _ler(cliente, query: str = "", ente: str = ENTE, anexo: str = "BO"):
    return cliente.get(f"/dca/{anexo}?anReferencia={EXERCICIO}&id_ente={ente}{query}",
                       headers={"Authorization": "Bearer t"})


def _chaves(resposta) -> list[str]:
    return [d["chave"] for d in resposta.json()["recortesDisponiveis"]]


def _corpo(poderes, ugs=None, modulos=("dca",)) -> dict:
    corpo = {"authorized": True, "poderes": list(poderes), "modulos": list(modulos)}
    if ugs is not None:
        corpo["ugs"] = list(ugs)
    return corpo


# ─── hub: contrato ───────────────────────────────────────────────────────────

def test_hub_devolve_poderes_modulos_e_ugs():
    """Requisito: `Autorizacao(poderes, modulos, ugs)`; `ugs` ausente vira `()`."""
    from app.auth.hub import Autorizacao, AutorizadorHub

    def com(corpo):
        async def http(url, json, headers):
            return {"status": 200, "corpo": corpo}
        return asyncio.run(AutorizadorHub(base_url="http://hub", secret="s",
                                          http=http).autorizar("u@x", ENTE))

    assert com(_corpo(["executivo", "xpto"], ["3", 5])) == Autorizacao(
        ("executivo",), ("dca",), ("3", "5"))
    assert com({"authorized": True, "poderes": ["executivo"]}) == Autorizacao(
        ("executivo",), (), ())


# ─── domínio: `visiveis` com UGs ─────────────────────────────────────────────

CHAVES = ["consolidado", *recorte.recortes(UGS_CUITEGI)]


def _vis(poderes, ugs=()):
    return recorte.visiveis(CHAVES, UGS_CUITEGI, poderes, ugs)


def test_visiveis_sem_ugs_e_o_filtro_por_poder():
    assert _vis(["executivo"]) == _vis(["executivo"], ()) == [
        "poder:executivo", "ug:1", "ug:3", "ug:4", "ug:5"]


def test_visiveis_duas_ugs_do_mesmo_poder_nao_se_concedem():
    assert _vis(["executivo"], ["4"]) == ["ug:4"]
    assert _vis(["executivo"], ["3", "5"]) == ["ug:3", "ug:5"]


def test_visiveis_grupo_so_com_cobertura_total():
    assert _vis(["executivo"], ["1", "3", "4", "5"]) == [
        "poder:executivo", "ug:1", "ug:3", "ug:4", "ug:5"]


def test_visiveis_todas_as_ugs_com_consolidado():
    assert _vis(["consolidado"], ["1", "3", "4", "5", "7"]) == [
        "consolidado", "poder:executivo", "poder:legislativo", "poder:executivo+legislativo",
        "ug:1", "ug:3", "ug:4", "ug:5", "ug:7"]


def test_visiveis_ug_fora_do_poder_nao_aparece():
    assert _vis(["legislativo"], ["7", "1"]) == ["poder:legislativo", "ug:7"]
    assert _vis(["executivo"], ["7"]) == []


# ─── rota: leitura ───────────────────────────────────────────────────────────

def test_duas_ugs_do_mesmo_poder_contadores_diferentes(hub):
    """Scenario: duas UGs do mesmo poder, contadores diferentes"""
    hub.corpos = {ENTE: _corpo(["executivo"], ["3"])}
    a = _ler(_cliente())
    assert a.status_code == 200 and _chaves(a) == ["ug:3"] and a.json()["recorte"] == "ug:3"
    assert _ler(_cliente(), "&recorte=ug:4").status_code == 403

    hub.corpos = {ENTE: _corpo(["executivo"], ["4"])}
    assert _chaves(_ler(_cliente())) == ["ug:4"]
    assert _ler(_cliente(), "&recorte=ug:3").status_code == 403


def test_403_nao_vaza_valor_do_recorte_negado(hub):
    hub.corpos = {ENTE: _corpo(["executivo"], ["3"])}
    r = _ler(_cliente(), "&recorte=ug:4")
    assert r.status_code == 403 and "matriz" not in r.json() and "recorte" not in r.json()


def test_usuario_com_varias_ugs(hub):
    """Scenario: usuário com várias UGs"""
    hub.corpos = {ENTE: _corpo(["executivo"], ["3", "5"])}
    assert _chaves(_ler(_cliente())) == ["ug:3", "ug:5"]
    assert _ler(_cliente(), "&recorte=consolidado").status_code == 403
    assert _ler(_cliente(), "&recorte=poder:executivo").status_code == 403


def test_usuario_com_todas_as_ugs(hub):
    """Scenario: usuário com todas as UGs"""
    hub.corpos = {ENTE: _corpo(["consolidado"], ["1", "3", "4", "5", "7"])}
    r = _ler(_cliente())
    assert r.json()["recorte"] == "consolidado"
    assert _chaves(r) == ["consolidado", "poder:executivo", "poder:legislativo",
                          "poder:executivo+legislativo", "ug:1", "ug:3", "ug:4", "ug:5", "ug:7"]


def test_ugs_de_poderes_diferentes(hub):
    """Scenario: UGs de poderes diferentes"""
    hub.corpos = {ENTE: _corpo(["legislativo"], ["7"])}
    assert _chaves(_ler(_cliente())) == ["poder:legislativo", "ug:7"]
    assert _ler(_cliente(), "&recorte=ug:1").status_code == 403

    hub.corpos = {ENTE: _corpo(["executivo"], ["1", "3", "4", "5"])}
    assert "ug:7" not in _chaves(_ler(_cliente()))
    assert _ler(_cliente(), "&recorte=ug:7").status_code == 403


def test_mesmo_usuario_entes_diferentes(hub):
    """Scenario: mesmo usuário, entes diferentes"""
    hub.corpos = {ENTE: _corpo(["executivo"], ["3"]), OUTRO_ENTE: _corpo(["executivo"], [])}
    cliente = _cliente(entes=(ENTE, OUTRO_ENTE))
    assert _chaves(_ler(cliente, ente=ENTE)) == ["ug:3"]
    assert _chaves(_ler(cliente, ente=OUTRO_ENTE)) == [
        "poder:executivo", "ug:1", "ug:3", "ug:4", "ug:5"]


@pytest.mark.parametrize("ugs", [[], None])
def test_usuario_sem_restricao_de_ug(hub, ugs):
    """Scenario: usuário sem restrição de UG (`ugs` vazio ou ausente no hub anterior à CH-49)"""
    hub.corpos = {ENTE: _corpo(["executivo"], ugs)}
    r = _ler(_cliente())
    assert r.json()["recorte"] == "poder:executivo"
    assert _chaves(r) == ["poder:executivo", "ug:1", "ug:3", "ug:4", "ug:5"]


def test_recorte_padrao_respeita_a_restricao(hub):
    """Scenario: recorte padrão respeita a restrição"""
    hub.corpos = {ENTE: _corpo(["executivo"], ["4", "5"])}
    assert _ler(_cliente()).json()["recorte"] in ("ug:4", "ug:5")

    hub.corpos = {ENTE: _corpo(["executivo"], ["7"])}      # UG de outro poder: nada visível
    assert _ler(_cliente()).status_code == 403


def test_hub_fora_responde_503(hub):
    """Scenario: fonte da autorização indisponível"""
    hub.corpos = {ENTE: None}
    assert _ler(_cliente()).status_code == 503


def test_cache_legado_sem_recortes_nao_serve_consolidado_a_quem_tem_ugs(hub):
    hub.corpos = {ENTE: _corpo(["consolidado"], ["3"])}
    assert _ler(_cliente(resultado={"matriz": {}})).status_code == 409


def test_resumo_so_lista_ugs_autorizadas(hub):
    hub.corpos = {ENTE: _corpo(["executivo"], ["3", "5"])}
    r = _cliente(anexo="BF").get(f"/dca/resumo?anReferencia={EXERCICIO}&id_ente={ENTE}",
                                 headers={"Authorization": "Bearer t"})
    bf = next(e for e in r.json() if e["anexo"] == "BF")
    assert [u["chave"] for u in bf["recortes"]] == ["ug:3", "ug:5"]


# ─── rota: anterior_por_recorte ──────────────────────────────────────────────

def _com_ugs(cliente, poderes, ugs):
    from app.routes.dependencias import unidade_autorizada

    def autorizada(request: Request) -> str:
        request.state.poderes = tuple(poderes)
        request.state.ugs = tuple(ugs)
        return "2505204"

    cliente.app.dependency_overrides[unidade_autorizada] = autorizada


def test_anterior_por_recorte_de_ug_nao_autorizada(api):  # noqa: F811
    """Scenario: escolha do exercício anterior em UG não autorizada"""
    repo = _cache_com_unidades()
    cliente, fila = api(repo, "BP", ("executivo",))
    outra = "ug:30"
    repo.gravar(RegistroFake("2505204", EXERCICIO, "BP", resultado={"recortes": {
        PREFEITURA: {"poderOrgao": "10131", "rotulo": "P", "resultado": {}},
        outra: {"poderOrgao": "10131", "rotulo": "F", "resultado": {}}}}))
    repo.gravar(_n1_com(PREFEITURA, outra))
    _com_ugs(cliente, ["executivo"], [PREFEITURA[3:]])

    ok = _reprocessar(cliente, "BP", {"anterior_por_recorte": {PREFEITURA: MANUAL_BP}})
    assert ok.status_code == 202
    antes = (len(fila.chamadas), len(repo.gravacoes))

    negado = _reprocessar(cliente, "BP", {"anterior_por_recorte": {
        PREFEITURA: MANUAL_BP, outra: MANUAL_BP}})
    assert negado.status_code == 403
    assert (len(fila.chamadas), len(repo.gravacoes)) == antes


def test_consolidado_com_ugs_restritas_nao_escolhe_qualquer_unidade(api):  # noqa: F811
    cliente, fila = api(_cache_com_unidades(), "BP", ("consolidado",))
    _com_ugs(cliente, ["consolidado"], [PREFEITURA[3:]])

    r = _reprocessar(cliente, "BP", {"anterior_por_recorte": {CAMARA: MANUAL_BP}})
    assert r.status_code == 403 and fila.chamadas == []


# ─── regressão: ugs vazio sai bit a bit igual ao golden gerado antes da change ────────────

PODERES = (["consolidado"], ["executivo"], ["legislativo"], ["executivo", "legislativo"])
RESULTADOS = {"BO": rota._resultado_bo, "BP": rota._resultado_bf, "BF": rota._resultado_bf}


_APURADO: dict = {}


def _resultado(anexo: str) -> dict:
    """A apuração do fixture custa segundos e não depende do usuário: uma vez por anexo, copiada.

    Sem isto o golden paga 12 apurações (3 anexos × 4 conjuntos de poderes) para comparar o mesmo
    payload. A cobertura é a mesma: entre os casos varia o poder, não o resultado apurado.
    """
    fabrica = RESULTADOS[anexo]                 # BP e BF partem da mesma: uma apuração serve às duas
    if fabrica not in _APURADO:
        _APURADO[fabrica] = fabrica()
    return deepcopy(_APURADO[fabrica])


def _corpos_com_poderes() -> dict:
    saida = {}
    for anexo in RESULTADOS:
        for poderes in PODERES:
            cliente = rota._cliente(RepoFake(), LockFake(), JobsFake(), poderes, anexo,
                                    _resultado(anexo))
            nome = f"{anexo}|{'+'.join(poderes)}"
            saida[f"{nome}|leitura"] = rota._get(cliente, anexo).json()
            saida[f"{nome}|resumo"] = rota._resumo(cliente).json()
    return saida


def _sem_relogio(no):
    """`duracao_ms` é cronômetro da apuração do fixture, não do payload servido."""
    if isinstance(no, dict):
        return {k: _sem_relogio(v) for k, v in no.items() if k != "duracao_ms"}
    if isinstance(no, list):
        return [_sem_relogio(v) for v in no]
    return no


def test_golden_sem_ugs_bit_a_bit():
    """Scenario: usuário sem restrição de UG — payload idêntico ao anterior à change"""
    esperado = json.loads(GOLDEN.read_text(encoding="utf-8"))
    esperado = _sem_relogio(esperado)
    atual = _sem_relogio(json.loads(json.dumps(_corpos_com_poderes())))
    assert atual.keys() == esperado.keys()
    for chave in esperado:
        assert atual[chave] == esperado[chave], chave
