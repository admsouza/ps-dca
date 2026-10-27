"""A DFC servida pelo mesmo pipeline de BO, BF, BP e DVP.

Os defeitos que estes testes pegam são silenciosos: sem `base_canonica="dfc"` o carregador
devolve as regras do BO, e sem o anexo no registry a rota responde 404 sem dizer por quê.
"""
from __future__ import annotations

from tests.pipeline.conftest import ENTE, EXERCICIO

DFC = "DFC"


def test_anexo_dfc_declarado_no_registry():
    """Scenario: anexo implementado entra no registry"""
    from app.services.pipeline.registry import anexo

    declarado = anexo(DFC)
    assert declarado.servico == "app.services.dfc.quadro_principal:apurar"
    assert declarado.base_canonica == "dfc"


def test_grafia_nao_canonica_resolve_para_dfc():
    """Requisito: a grafia que chega do cliente aponta sempre o mesmo anexo."""
    from app.services.pipeline.registry import validar_anexo

    assert {validar_anexo(g) for g in ("dfc", "DFC", " dfc ", "D-F-C")} == {DFC}


def test_servico_da_dfc_e_o_apurador_da_dfc():
    """Scenario: o apurador vem do serviço declarado no registry"""
    from app.services.pipeline.apuracao import _servico_de

    assert _servico_de(DFC).__module__ == "app.services.dfc.quadro_principal"


def test_mapa_da_dfc_vem_do_ipc08():
    """Scenario: o mapa do anexo vem da sua própria base canônica"""
    from app.services.pipeline.apuracao import mapa_vigente

    mapa = mapa_vigente(2025, DFC)
    assert mapa.vigencia.documento == "IPC08"
    assert len(mapa.linhas) == 84


def test_resumo_reporta_a_dfc_como_implementada(repo):
    """Scenario: resumo deixa de reportar anexo sem serviço"""
    from app.services.pipeline.resumo import resumir

    entrada = next(e for e in resumir(ente=ENTE, exercicio=EXERCICIO, repo=repo)
                   if e["anexo"] == DFC)
    assert entrada["implementado"] is True


def test_ordem_dos_quatro_quadros_da_dfc():
    """Scenario: os quadros da DFC saem na ordem do IPC 08"""
    from app.infra.regras.carregador import carregar
    from app.services.pipeline.resultado import template

    linhas = template(carregar(2025, demonstrativo="dfc"))
    assert len(linhas) == 84
    quadros = [linha["quadro"] for linha in linhas]
    # cada quadro sai inteiro, em bloco — sem intercalar com os auxiliares
    assert [q for i, q in enumerate(quadros) if i == 0 or quadros[i - 1] != q] == [
        "QUADRO_PRINCIPAL", "TRANSFERENCIAS_RECEBIDAS_CONCEDIDAS",
        "DESEMBOLSOS_PESSOAL_POR_FUNCAO", "JUROS_ENCARGOS_DIVIDA"]
    assert linhas[0]["codigo"] == "L1" and linhas[0]["grupo"] == "OPERACIONAIS"
    assert linhas[35]["codigo"] == "L36" and linhas[35]["grupo"] == "CAIXA"


def test_percurso_completo_inclui_a_dfc(repo, lock, jobs):
    """Scenario: o percurso completo inclui a DFC"""
    from app.services.pipeline.completo import montar_percurso
    from tests.pipeline.conftest import VERSAO_API

    percurso = montar_percurso(ente=ENTE, exercicio=EXERCICIO, repo=repo, lock=lock, jobs=jobs,
                               versao_api=VERSAO_API, versao_de_regras=lambda _a: "r")
    assert [no.anexo for no in percurso if no.estado == "a_apurar"] == [
        "BO", "BF", "BP", "DFC", "I-HI"]
