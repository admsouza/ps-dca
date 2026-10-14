"""`GET /dca/{BO|BP}?recorte=` serve um recorte do cache, conforme o poder do usuário no hub.

Change `pipeline-dca-por-unidade-gestora`.
"""
from __future__ import annotations

import asyncio

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from tests.bo.conftest import FonteFake, saldo
from tests.pipeline.conftest import ENTE, EXERCICIO, RegistroFake


def _resultado_bo(com_recortes: bool = True) -> dict:
    from app.services.bo.quadro_principal import apurar
    from app.services.pipeline import apuracao
    from app.services.pipeline.resultado import para_dados

    def r(conta, valor, ug, po, **kw):
        return saldo(conta, valor, **kw)._replace(unidade_gestora=ug, poder_orgao=po,
                                                  nome_unidade_gestora=f"UG {ug}")

    fonte = FonteFake({5: [r("521110000", "10.00", "1", "10131", natureza_receita="1100.00.00"),
                           r("521110000", "7.00", "4", "20231", natureza_receita="1100.00.00")],
                       6: []})
    resultado = (apuracao.com_recortes(apurar, int(ENTE), EXERCICIO, fonte) if com_recortes
                 else apurar(int(ENTE), EXERCICIO, fonte))
    return para_dados(resultado)


def _resultado_bo_por_po() -> dict:
    """Ente sem UG (SICONFI): recortes `po:`."""
    from app.services.bo.quadro_principal import apurar
    from app.services.pipeline import apuracao
    from app.services.pipeline.resultado import para_dados

    fonte = FonteFake({5: [saldo("521110000", "10.00", natureza_receita="1100.00.00",
                                 poder_orgao="10131"),
                           saldo("521110000", "7.00", natureza_receita="1100.00.00",
                                 poder_orgao="20231")], 6: []})
    return para_dados(apuracao.com_recortes(apurar, int(ENTE), EXERCICIO, fonte))


def _resultado_bf() -> dict:
    from app.services.pipeline.resultado import para_dados
    from tests.recorte.test_bf_estorno_por_unidade import _bf, _fonte_ug

    return para_dados(_bf(_fonte_ug()))


def _resultado_bf_por_po() -> dict:
    from app.services.pipeline.resultado import para_dados
    from tests.recorte.test_bf_estorno_por_unidade import _bf, _fonte_po

    return para_dados(_bf(_fonte_po()))


def _cliente(repo, lock, jobs, poderes, anexo: str = "BO", resultado: dict | None = None,
             fonte=None):
    from app.routes import anexos as rotas
    from app.routes.dependencias import fonte_do_pedido, repositorio, unidade_autorizada

    corpo = _resultado_bo() if resultado is None else resultado
    repo.gravar(RegistroFake(ENTE, EXERCICIO, anexo, status="ok", resultado=corpo))

    def autorizada(request: Request) -> str:
        request.state.claims = {"sub": "u@x"}
        request.state.poderes = tuple(poderes)
        return ENTE

    class Fila:
        pendente = None

        def enfileirar(self, *args, **kwargs):
            raise AssertionError("ler um recorte não pode enfileirar")

    app = FastAPI()
    app.include_router(rotas.router)
    app.dependency_overrides[repositorio] = lambda: repo
    app.dependency_overrides[unidade_autorizada] = autorizada
    if fonte is not None:
        app.dependency_overrides[fonte_do_pedido] = lambda: fonte
    app.state.portas = {"fila_async": Fila, "lock": lock, "jobs": jobs, "repo_vigencias": None,
                        "base_url": ""}
    return TestClient(app)


def _get(cliente, anexo: str = "BO", query: str = ""):
    return cliente.get(f"/dca/{anexo}?anReferencia={EXERCICIO}&id_ente={ENTE}{query}",
                       headers={"Authorization": "Bearer t", "X-Unidade-Id": ENTE})



def _previsao(corpo: dict, rule_id: str = "bo.quadro_principal.receitas.l24") -> str:
    return corpo["matriz"][rule_id]["previsao_inicial"]


def test_uma_ug_sem_job(repo, lock, jobs):
    """Scenario: uma UG"""
    r = _get(_cliente(repo, lock, jobs, ["consolidado"]), query="&recorte=ug:4")
    assert r.status_code == 200
    corpo = r.json()
    assert corpo["recorte"] == "ug:4" and _previsao(corpo) == "7.00"
    assert "recortes" not in corpo


def test_grupo_de_poder(repo, lock, jobs):
    """Scenario: grupo de poder"""
    corpo = _get(_cliente(repo, lock, jobs, ["consolidado"]),
                 query="&recorte=poder:executivo").json()
    assert corpo["recorte"] == "poder:executivo" and _previsao(corpo) == "10.00"


def test_consolidado_sem_mudanca(repo, lock, jobs):
    """Scenario: consolidado sem mudança"""
    corpo = _get(_cliente(repo, lock, jobs, ["consolidado"])).json()
    esperado = _resultado_bo()
    esperado.pop("recortes")
    assert corpo["recorte"] == "consolidado" and _previsao(corpo) == "17.00"
    assert corpo["matriz"] == esperado["matriz"] and corpo["linhas"] == esperado["linhas"]
    assert [d["chave"] for d in corpo["recortesDisponiveis"]] == [
        "consolidado", "poder:executivo", "poder:legislativo", "poder:executivo+legislativo",
        "ug:1", "ug:4"]
    assert corpo["recortesDisponiveis"][-1] == {"chave": "ug:4", "tipo": "ug", "rotulo": "UG 4",
                                                "poderOrgao": "20231"}


def test_usuario_do_legislativo(repo, lock, jobs):
    """Scenario: usuário do Legislativo"""
    corpo = _get(_cliente(repo, lock, jobs, ["legislativo"])).json()
    assert corpo["recorte"] == "poder:legislativo" and _previsao(corpo) == "7.00"
    assert [d["chave"] for d in corpo["recortesDisponiveis"]] == ["poder:legislativo", "ug:4"]


@pytest.mark.parametrize("recorte", ["ug:4", "consolidado", "poder:legislativo"])
def test_executivo_pede_a_camara(repo, lock, jobs, recorte):
    """Scenario: Executivo pede a Câmara"""
    r = _get(_cliente(repo, lock, jobs, ["executivo"]), query=f"&recorte={recorte}")
    assert r.status_code == 403 and "matriz" not in r.text


@pytest.mark.parametrize("poderes", [["judiciario"], []])
def test_sem_poder_util(repo, lock, jobs, poderes):
    """Requisito: `judiciario`, ou nenhum poder → 403"""
    assert _get(_cliente(repo, lock, jobs, poderes)).status_code == 403


def test_recorte_inexistente(repo, lock, jobs):
    """Scenario: recorte inexistente"""
    assert _get(_cliente(repo, lock, jobs, ["executivo"]),
                query="&recorte=ug:99").status_code == 404


def test_recorte_malformado(repo, lock, jobs):
    """Scenario: recorte malformado"""
    assert _get(_cliente(repo, lock, jobs, ["consolidado"]),
                query="&recorte=99").status_code == 422


def test_anexo_sem_recorte(repo, lock, jobs):
    """Scenario: anexo sem recorte"""
    cliente = _cliente(repo, lock, jobs, ["executivo"], anexo="I-C", resultado={"matriz": {}})
    assert _get(cliente, "I-C", "&recorte=ug:1").status_code == 422
    assert _get(cliente, "I-C").status_code == 200


def test_bf_por_ug_sem_job(repo, lock, jobs):
    """Scenario: BF por UG"""
    cliente = _cliente(repo, lock, jobs, ["consolidado"], anexo="BF", resultado=_resultado_bf())
    r = _get(cliente, "BF", "&recorte=ug:3")
    assert r.status_code == 200
    corpo = r.json()
    assert corpo["recorte"] == "ug:3"
    assert corpo["procedencia"]["estorno_receita_extra"]["2025"] == "5.00"
    assert "ug:3" in [d["chave"] for d in corpo["recortesDisponiveis"]]


def test_usuario_do_legislativo_no_bf(repo, lock, jobs):
    """Scenario: usuário do Legislativo no BF"""
    cliente = _cliente(repo, lock, jobs, ["legislativo"], anexo="BF", resultado=_resultado_bf())
    corpo = _get(cliente, "BF").json()
    assert corpo["recorte"] == "poder:legislativo"
    assert [d["chave"] for d in corpo["recortesDisponiveis"]] == ["poder:legislativo", "ug:4"]


@pytest.mark.parametrize("recorte", ["ug:4", "consolidado"])
def test_executivo_pede_a_camara_no_bf(repo, lock, jobs, recorte):
    """Scenario: Executivo pede a Câmara (BF)"""
    cliente = _cliente(repo, lock, jobs, ["executivo"], anexo="BF", resultado=_resultado_bf())
    r = _get(cliente, "BF", f"&recorte={recorte}")
    assert r.status_code == 403 and "matriz" not in r.text


def test_bf_recorte_inexistente_e_malformado(repo, lock, jobs):
    """Scenario: recorte inexistente / malformado (BF)"""
    cliente = _cliente(repo, lock, jobs, ["consolidado"], anexo="BF", resultado=_resultado_bf())
    assert _get(cliente, "BF", "&recorte=ug:99").status_code == 404
    assert _get(cliente, "BF", "&recorte=99").status_code == 422


def test_bf_cache_anterior_a_change(repo, lock, jobs):
    """Scenario: cache anterior à change (BF)"""
    antigo = {k: v for k, v in _resultado_bf().items() if k != "recortes"}
    cliente = _cliente(repo, lock, jobs, ["consolidado"], anexo="BF", resultado=antigo)
    assert _get(cliente, "BF").status_code == 200
    assert _get(cliente, "BF", "&recorte=ug:1").status_code == 409


AVISO = ("Recorte por poder/órgão: o SICONFI não informa a unidade gestora. "
         "Para emitir por unidade gestora, processe com SIAFIC.")


@pytest.mark.parametrize("anexo", ["BO", "BF"])
def test_aviso_de_recorte_ente_com_siafic_pela_msc(repo, lock, jobs, anexo):
    """Scenario: ente com SIAFIC pela MSC"""
    from app.routes.dependencias import FontePedido

    resultado = _resultado_bo_por_po() if anexo == "BO" else _resultado_bf_por_po()
    cliente = _cliente(repo, lock, jobs, ["consolidado"], anexo=anexo, resultado=resultado,
                       fonte=FontePedido("siconfi", "token_ps"))
    corpo = _get(cliente, anexo).json()
    assert {"po:10131", "po:20231"} <= {d["chave"] for d in corpo["recortesDisponiveis"]}
    assert corpo["avisoRecorte"] == AVISO


@pytest.mark.parametrize("fonte,resultado", [
    ("sem_token", _resultado_bo_por_po),       # ente CSV: o hub não resolve o token
    ("publicsoft", _resultado_bo_por_po),      # leitura pela fonte SIAFIC
    ("siconfi_com_token", _resultado_bo),      # recortes `ug:`: nada a avisar
])
def test_sem_aviso_de_recorte(repo, lock, jobs, fonte, resultado):
    """Scenario: ente CSV pela MSC"""
    from app.routes.dependencias import FontePedido

    pedido = {"sem_token": FontePedido("siconfi"), "publicsoft": FontePedido("publicsoft", "t"),
              "siconfi_com_token": FontePedido("siconfi", "t")}[fonte]
    corpo = _get(_cliente(repo, lock, jobs, ["consolidado"], resultado=resultado(),
                          fonte=pedido)).json()
    assert "avisoRecorte" not in corpo


def test_cache_anterior_a_change(repo, lock, jobs):
    """Scenario: cache anterior à change"""
    antigo = _resultado_bo(com_recortes=False)
    assert _get(_cliente(repo, lock, jobs, ["consolidado"], resultado=antigo)).status_code == 200
    assert _get(_cliente(repo, lock, jobs, ["consolidado"], resultado=antigo),
                query="&recorte=ug:1").status_code == 409
    assert _get(_cliente(repo, lock, jobs, ["executivo"], resultado=antigo)).status_code == 409


def test_hub_devolve_poderes():
    """Requisito: recortes visíveis pelo poder (D7).

    `poderes` vem do corpo do `/internal/authorize`; valor fora do vocabulário é ignorado.
    """
    from app.auth.hub import AutorizadorHub

    def com(corpo):
        async def http(url, json, headers):
            return {"status": 200, "corpo": corpo}
        return asyncio.run(AutorizadorHub(base_url="http://hub", secret="s",
                                          http=http).autorizar("u@x", ENTE))

    assert com({"authorized": True, "poderes": ["legislativo", "xpto"]}) == ("legislativo",)
    assert com({"authorized": True}) == ()


def test_unidade_autorizada_guarda_os_poderes(monkeypatch):
    """Requisito: recortes visíveis pelo poder (D7) — `poderes` do hub em `request.state`."""
    from app.routes import dependencias

    class Hub:
        configurado = True

        async def autorizar(self, sub, ente):
            return ("executivo",)

    monkeypatch.setattr(dependencias, "AutorizadorHub", Hub)
    monkeypatch.setattr(dependencias, "_claims", lambda token: {"sub": "u@x"})
    app = FastAPI()

    @app.get("/p")
    async def p(request: Request,
                ente: str = dependencias.Depends(dependencias.unidade_autorizada)):
        return {"poderes": list(request.state.poderes)}

    r = TestClient(app).get(f"/p?id_ente={ENTE}", headers={"Authorization": "Bearer t"})
    assert r.json() == {"poderes": ["executivo"]}
