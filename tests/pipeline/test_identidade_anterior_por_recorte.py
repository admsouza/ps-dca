"""Identidade do pedido com as escolhas por unidade (`pipeline-anterior-por-recorte`).

Capability `pipeline/anterior-por-recorte`: `ar-<hash>` só com escolha explícita; ler ou
reprocessar sem mudar escolhas não marca `pedido` em `motivos_desatualizado`.
"""
from __future__ import annotations

import pytest

from app.services.pipeline import apuracao
from app.services.pipeline.cache import (
    identidade_do_pedido,
    motivos_desatualizado,
    parametros_efetivos,
    versao_do_pedido,
)
from app.services.pipeline.job import executar
from tests.bp.conftest import FontePorAno
from tests.pipeline.conftest import ENTE, EXERCICIO, LockFake, RegistroFake, RepoFake
from tests.recorte.test_anterior_por_recorte import MANUAL, MSCE, N1, PROCESSADO, N, _n1

MSC = {"origem_anterior": MSCE, "fonte": "publicsoft"}


def _escolha(origem: str, **valores) -> dict:
    return {"origem": origem, **({"valores": valores} if valores else {})}


# ─── identidade ──────────────────────────────────────────────────────────────

def test_sem_escolha_a_identidade_nao_muda():
    base = identidade_do_pedido(anexo="BP", fonte="publicsoft")

    assert identidade_do_pedido(anexo="BP", fonte="publicsoft", anterior_por_recorte={}) == base
    assert "ar-" not in base


def test_escolha_explicita_entra_no_fim_da_identidade():
    com = identidade_do_pedido(anexo="BP", fonte="publicsoft",
                               anterior_por_recorte={"ug:1": _escolha(MSCE)})

    assert com.rsplit(":", 1)[1].startswith("ar-")


@pytest.mark.parametrize("a, b", [
    ({"ug:1": _escolha(MSCE)}, {"ug:1": _escolha(PROCESSADO)}),
    ({"ug:1": _escolha(MSCE)}, {"ug:2": _escolha(MSCE)}),
    ({"ug:1": _escolha(MANUAL, **{"P:L3": "1.00"})},
     {"ug:1": _escolha(MANUAL, **{"P:L3": "2.00"})}),
])
def test_escolhas_diferentes_dao_identidades_diferentes(a, b):
    def identidade(escolhas):
        return identidade_do_pedido(anexo="BP", anterior_por_recorte=escolhas)

    assert identidade(a) != identidade(b)


def test_ordem_das_unidades_nao_muda_a_identidade():
    a = {"ug:1": _escolha(MSCE), "ug:2": _escolha(PROCESSADO)}
    b = dict(reversed(a.items()))

    assert (identidade_do_pedido(anexo="BP", anterior_por_recorte=a)
            == identidade_do_pedido(anexo="BP", anterior_por_recorte=b))


# ─── parametros_efetivos ─────────────────────────────────────────────────────

def _gravado(escolhas: dict[str, dict | None], anexo: str = "BP") -> RegistroFake:
    recortes = {chave: {"resultado": {"procedencia": {"escolha_anterior": escolha}}}
                for chave, escolha in escolhas.items()}
    return RegistroFake("1", 2025, anexo, resultado={"recortes": recortes, "procedencia": {}})


def test_reaplica_as_escolhas_gravadas_nas_procedencias_dos_recortes():
    """Scenario: escolha gravada é reaplicada"""
    registro = _gravado({"ug:3": _escolha(MANUAL, **{"P:L3": "1.00"}), "ug:5": _escolha(MSCE),
                         "ug:7": None, "poder:executivo": None})

    efetivo = parametros_efetivos({"fonte": "publicsoft"}, registro, "BP")

    assert efetivo["anterior_por_recorte"] == {"ug:3": _escolha(MANUAL, **{"P:L3": "1.00"}),
                                               "ug:5": _escolha(MSCE)}
    assert "anterior_agora" not in efetivo


def test_pedido_vale_sobre_o_gravado_e_so_o_pedido_e_agora():
    registro = _gravado({"ug:3": _escolha(MSCE), "ug:5": _escolha(MSCE)})
    pedido = {"fonte": "publicsoft",
              "anterior_por_recorte": {"ug:1": _escolha(MANUAL, **{"P:L3": "1.00"}),
                                       "ug:3": _escolha(PROCESSADO)}}

    efetivo = parametros_efetivos(pedido, registro, "BP")

    assert efetivo["anterior_por_recorte"] == {
        "ug:1": _escolha(MANUAL, **{"P:L3": "1.00"}), "ug:3": _escolha(PROCESSADO),
        "ug:5": _escolha(MSCE)}
    assert efetivo["anterior_agora"] == ["ug:1", "ug:3"]


def test_padrao_limpa_a_escolha_gravada():
    """Scenario: limpar a escolha"""
    registro = _gravado({"ug:3": _escolha(MANUAL, **{"P:L3": "1.00"})})

    efetivo = parametros_efetivos({"anterior_por_recorte": {"ug:3": {"origem": "padrao"}}},
                                  registro, "BP")

    assert "anterior_por_recorte" not in efetivo


def test_o_bf_reaplica_as_escolhas_dos_recortes_ignorando_o_mapa_legado_do_consolidado():
    """Requisito: o consolidado não tem origem própria: procedência legada no registro não é
    reaplicada (`pipeline-consolidado-anterior-soma-unidades`)."""
    registro = _gravado({"ug:3": _escolha(MSCE)}, "BF")
    registro.procedencia = {"origem_exercicio_anterior": "manual",
                            "valores_anteriores": {"L2": "1.00"}}

    efetivo = parametros_efetivos({}, registro, "BF")

    assert "valores_anteriores" not in efetivo
    assert efetivo["anterior_por_recorte"] == {"ug:3": _escolha(MSCE)}


# ─── ler depois de reprocessar ───────────────────────────────────────────────

@pytest.fixture
def n1_no_cache(monkeypatch):
    monkeypatch.setattr(apuracao, "fonte", lambda nome=None, token=None: FontePorAno(
        {EXERCICIO: N, EXERCICIO - 1: N1}))
    return RepoFake([RegistroFake(ENTE, EXERCICIO - 1, "BP", resultado=_n1(N1).resultado,
                                  versao_regras="r|c12:-:f=publicsoft")])


def _reprocessar(repo: RepoFake, pedido: dict) -> RegistroFake:
    """A rota (identidade) e o worker (apuração e gravação), como em produção."""
    parametros = parametros_efetivos({**MSC, **pedido}, repo.obter(ENTE, EXERCICIO, "BP"), "BP")
    regras = apuracao.versao_regras(EXERCICIO, "BP")
    executar(ente=ENTE, exercicio=EXERCICIO, anexo="BP", repo=repo, lock=LockFake(),
             apurador=apuracao.apurador("BP", fonte_nome="fake", repo=repo, parametros=parametros),
             versao_api=apuracao.VERSAO_API,
             versao_regras=versao_do_pedido(regras, "BP", parametros))
    return repo.obter(ENTE, EXERCICIO, "BP")


def _motivos_da_leitura(repo: RepoFake) -> list[str]:
    """O `GET`: o pedido não traz escolhas, e o que vale é o gravado."""
    registro = repo.obter(ENTE, EXERCICIO, "BP")
    parametros = parametros_efetivos(MSC, registro, "BP")
    versao = versao_do_pedido(apuracao.versao_regras(EXERCICIO, "BP"), "BP", parametros)
    return motivos_desatualizado(registro, apuracao.VERSAO_API, versao)


def test_leitura_depois_de_escolha_manual_nao_marca_pedido(n1_no_cache):
    """Scenario: leitura depois de escolha manual"""
    escolhas = {"ug:1": _escolha(MANUAL, **{"P:L3": "11.00"}), "ug:4": _escolha(MSCE)}
    gravado = _reprocessar(n1_no_cache, {"anterior_por_recorte": escolhas})

    assert gravado.status == "ok"
    assert _motivos_da_leitura(n1_no_cache) == []


def test_reprocessar_sem_mudar_escolhas_nao_marca_pedido(n1_no_cache):
    _reprocessar(n1_no_cache, {"anterior_por_recorte": {"ug:1": _escolha(MSCE)}})
    antes = n1_no_cache.obter(ENTE, EXERCICIO, "BP").versao_regras

    _reprocessar(n1_no_cache, {})

    assert n1_no_cache.obter(ENTE, EXERCICIO, "BP").versao_regras == antes
    assert _motivos_da_leitura(n1_no_cache) == []


def test_unidade_inexistente_pedida_nao_entra_na_identidade_gravada(n1_no_cache):
    """Scenario: escolha de unidade inexistente descartada"""
    escolhas = {"ug:1": _escolha(MSCE), "ug:99": _escolha(MSCE)}
    gravado = _reprocessar(n1_no_cache, {"anterior_por_recorte": escolhas})

    assert "ug:99" not in gravado.resultado["recortes"]
    assert any("ug:99" in aviso for aviso in gravado.resultado["diagnostico"]["avisos_anterior"])
    assert _motivos_da_leitura(n1_no_cache) == []
    # A escolha de unidade inexistente nem volta a ser gravada: o próximo pedido não a carrega.
    assert "ug:99" not in parametros_efetivos({}, gravado, "BP").get("anterior_por_recorte", {})


def test_a_escolha_gravada_e_reaplicada_no_job_seguinte(n1_no_cache):
    """Scenario: escolha gravada é reaplicada"""
    _reprocessar(n1_no_cache,
                 {"anterior_por_recorte": {"ug:1": _escolha(MANUAL, **{"P:L3": "11.00"}),
                                           "ug:4": _escolha(MSCE)}})
    limpar = {"anterior_por_recorte": {"ug:4": {"origem": "padrao"}}}

    gravado = _reprocessar(n1_no_cache, limpar)

    recortes = gravado.resultado["recortes"]
    assert recortes["ug:1"]["resultado"]["procedencia"]["valores_anteriores"] == {"P:L3": "11.00"}
    ug4 = recortes["ug:4"]["resultado"]["procedencia"]
    assert ug4["escolha_anterior"] is None
    assert ug4["origem_exercicio_anterior"] == PROCESSADO
    assert _motivos_da_leitura(n1_no_cache) == []


def test_escolha_sobrevive_a_job_em_erro(n1_no_cache):
    """Scenario: escolha sobrevive a job em erro"""
    manual = {"ug:1": _escolha(MANUAL, **{"P:L3": "11.00"})}
    gravado = _reprocessar(n1_no_cache, {"anterior_por_recorte": manual})
    versao = gravado.versao_regras

    def falha(ente, exercicio):
        raise RuntimeError("fonte fora")

    executar(ente=ENTE, exercicio=EXERCICIO, anexo="BP", repo=n1_no_cache, lock=LockFake(),
             apurador=falha, versao_api=apuracao.VERSAO_API, versao_regras="x")
    assert n1_no_cache.obter(ENTE, EXERCICIO, "BP").status == "erro"

    gravado = _reprocessar(n1_no_cache, {})

    assert gravado.status == "ok"
    ug1 = gravado.resultado["recortes"]["ug:1"]["resultado"]["procedencia"]
    assert ug1["valores_anteriores"] == {"P:L3": "11.00"}
    assert gravado.versao_regras == versao
