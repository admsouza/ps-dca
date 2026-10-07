"""BP — origem da coluna anterior na identidade do pedido (`bp-anterior-publicado-siconfi`, D2).

Rota, worker individual e percurso têm de gravar e conferir a mesma `versao_do_pedido`; do contrário
a leitura seguinte marca `pedido` sem motivo, ou serve MSC como se fosse o publicado.
"""
from __future__ import annotations

import pytest

VERSAO = "r" * 64


def _parametros(origem: str | None, fonte: str = "siconfi") -> dict:
    from app.services.pipeline.cache import parametros_efetivos

    pedido = {"fonte": fonte, **({"origem_anterior": origem} if origem else {})}
    return parametros_efetivos(pedido, None, "BP")


def test_origens_nao_se_misturam_no_cache(pedido, repo, fila):
    """Scenario: origens não se misturam no cache"""
    from app.services.pipeline.cache import versao_do_pedido
    from tests.pipeline.conftest import ENTE as E
    from tests.pipeline.conftest import EXERCICIO as X
    from tests.pipeline.conftest import VERSAO_REGRAS, RegistroFake

    repo.gravar(RegistroFake(E, X, "BP", status="ok", resultado={"publicado": 1},
                             versao_regras=versao_do_pedido(
                                 VERSAO_REGRAS, "BP", _parametros("publicado_siconfi"))))

    msc = pedido(anexo="BP", parametros=_parametros("msce_exercicio_anterior"))
    assert (msc.status, msc.motivos_desatualizado) == (200, ["pedido"])

    omitida = pedido(anexo="BP", parametros=_parametros(None))
    assert (omitida.status, omitida.motivos_desatualizado) == (200, [])
    assert fila.enfileirados == []


def test_origem_omitida_e_explicitada_em_rota_worker_e_percurso():
    """Requisito: D2 — rota, worker individual e percurso gravam e conferem a MESMA versão."""
    from app.routes.anexos import _parametros_bf
    from app.services.pipeline.cache import parametros_efetivos, versao_do_pedido
    from app.services.pipeline.completo import pedido_do_percurso

    da_rota = parametros_efetivos({**_parametros_bf("BP", None, None, None), "fonte": "siconfi"},
                                  None, "BP")
    assert da_rota["origem_anterior"] == "publicado_siconfi"
    assert da_rota["anterior"] == "publicado_siconfi"      # o que o worker repassa ao serviço

    no_worker = versao_do_pedido(VERSAO, "BP", da_rota)    # job individual: params da rota
    no_percurso = versao_do_pedido(VERSAO, "BP", {
        **parametros_efetivos({}, None, "BP"), **pedido_do_percurso(None, "siconfi", "BP")})
    assert no_worker == no_percurso
    assert versao_do_pedido(VERSAO, "BP", _parametros("msce_exercicio_anterior")) != no_percurso


def test_bf_nao_muda_de_comportamento():
    """Requisito: regressão — a identidade do BF segue a de antes (msce = sem origem na chave)."""
    from app.services.pipeline.cache import parametros_efetivos
    from app.services.pipeline.completo import pedido_do_percurso

    assert parametros_efetivos({"origem_anterior": "msce_exercicio_anterior", "fonte": "x"},
                               None, "BF") == {"fonte": "x"}
    assert pedido_do_percurso(None, "siconfi", "BF") == {"fonte": "siconfi"}
    assert pedido_do_percurso(None, "siconfi") == {"fonte": "siconfi"}


def test_rota_aceita_as_duas_origens_e_recusa_o_resto():
    """Requisito: origem inválida no BP — `422`; `manual` é do BF."""
    from fastapi import HTTPException

    from app.routes.anexos import CorpoAnterior, _parametros_bf, _parametros_do_corpo

    assert _parametros_bf("BP", "publicado_siconfi", None, None) == {
        "origem_anterior": "publicado_siconfi"}
    assert _parametros_bf("BP", "msce_exercicio_anterior", None, None) == {
        "origem_anterior": "msce_exercicio_anterior"}
    for invalida in ("manual", "qualquer"):
        with pytest.raises(HTTPException) as erro:
            _parametros_bf("BP", invalida, None, None)
        assert erro.value.status_code == 422
    corpo = CorpoAnterior(origem_exercicio_anterior="publicado_siconfi")
    assert _parametros_do_corpo(corpo, 2025, "BP") == {"origem_anterior": "publicado_siconfi"}
    with pytest.raises(HTTPException) as erro:
        _parametros_do_corpo(CorpoAnterior(origem_exercicio_anterior="manual"), 2025, "BP")
    assert erro.value.status_code == 422


def test_apurador_do_bp_repassa_a_origem_ao_servico():
    """Requisito: o job do BP chega ao serviço com `anterior` — só o declarado na assinatura."""
    from app.services.bp.quadro_principal import Anterior, apurar
    from app.services.pipeline.apuracao import _aceitos_por

    efetivos = _parametros("msce_exercicio_anterior")
    assert _aceitos_por(apurar, {k: v for k, v in efetivos.items() if k != "fonte"}) == {
        "anterior": "msce_exercicio_anterior"}
    assert Anterior("publicado_siconfi") is Anterior.PUBLICADO
