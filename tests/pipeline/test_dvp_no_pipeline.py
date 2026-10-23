"""A DVP (`I-HI`) servida pelo mesmo pipeline de BO, BF e BP.

Os defeitos que estes testes pegam são silenciosos: sem `base_canonica="dvp"` o carregador devolve
as regras do BO, e sem a ordem do IPC 05 declarada os grupos da DVP caem todos no fim.
"""
from __future__ import annotations

import json
from dataclasses import replace

from tests.pipeline.conftest import ENTE, EXERCICIO, VERSAO_API


def _mapa():
    from app.infra.regras.carregador import carregar
    return carregar(2025, demonstrativo="dvp")


def test_vpa_antes_de_vpd_resultado_por_ultimo():
    """Scenario: VPA antes de VPD, resultado por último"""
    from app.services.pipeline.resultado import ORDEM_POR_DOCUMENTO, template

    assert ORDEM_POR_DOCUMENTO["IPC05"] == (("QUADRO_PRINCIPAL",), ("VPA", "VPD", "RESULTADO"))
    linhas = template(_mapa())
    assert len(linhas) == 19
    assert linhas[0]["codigo"] == "L1" and linhas[0]["grupo"] == "VPA"
    grupos = [linha["grupo"] for linha in linhas]
    assert max(i for i, g in enumerate(grupos) if g == "VPA") < grupos.index("VPD")
    assert linhas[-1]["codigo"] == "L19" and linhas[-1]["grupo"] == "RESULTADO"


def test_linha_nova_com_ordem_relativa_ao_grupo():
    """Scenario: linha nova com ordem relativa ao grupo

    Falha se a ordem vier da numeração global 1..19: `ordem` 1 e grupo `VPD` jogariam a linha para
    o grupo desconhecido (fim) ou para o topo."""
    from app.services.pipeline.resultado import template

    mapa = _mapa()
    modelo = next(linha for linha in mapa.linhas if linha.grupo == "VPD")
    nova = modelo._replace(id="dvp.quadro_principal.lx", codigo="LX", ordem=1)
    linhas = template(replace(mapa, linhas=(*mapa.linhas, nova)))

    grupos = [linha["grupo"] for linha in linhas]
    codigos = [linha["codigo"] for linha in linhas]
    primeira_vpd = grupos.index("VPD")
    assert codigos[0] == "L1"
    assert codigos[primeira_vpd] == "LX", "ordem 1 do grupo: primeira de VPD, não do documento"
    assert max(i for i, g in enumerate(grupos) if g == "VPA") < primeira_vpd
    assert codigos[-1] == "L19"


def test_resumo_deixa_de_reportar_anexo_sem_servico(repo):
    """Scenario: resumo deixa de reportar anexo sem serviço"""
    from app.services.pipeline.registry import anexo
    from app.services.pipeline.resumo import resumir

    entrada = next(e for e in resumir(ente=ENTE, exercicio=EXERCICIO, repo=repo)
                   if e["anexo"] == "I-HI")
    assert entrada["implementado"] is True
    assert anexo("I-HI").servico == "app.services.dvp.quadro_principal:apurar"
    assert anexo("I-HI").base_canonica == "dvp"


def test_percurso_completo_inclui_a_dvp(repo, lock, jobs):
    """Scenario: percurso completo inclui a DVP"""
    from app.services.pipeline.completo import montar_percurso

    percurso = montar_percurso(ente=ENTE, exercicio=EXERCICIO, repo=repo, lock=lock, jobs=jobs,
                               versao_api=VERSAO_API, versao_de_regras=lambda _a: "r")
    assert [no.anexo for no in percurso if no.estado == "a_apurar"] == [
        "BO", "BF", "BP", "I-HI"]


def test_grafia_nao_canonica():
    """Scenario: grafia não canônica"""
    from app.services.pipeline.registry import validar_anexo

    assert {validar_anexo(g) for g in ("i-hi", "I_HI", "I-HI", "ihi")} == {"I-HI"}


def test_rota_e_cli_nao_divergem():
    """Scenario: rota e CLI não divergem"""
    from app.cli.dvp import _json
    from app.services.dvp.quadro_principal import apurar
    from app.services.pipeline.resultado import para_dados
    from tests.bp.conftest import FontePorAno

    resultado = apurar(2507507, 2025, FontePorAno({}))
    assert json.loads(_json(resultado)) == para_dados(resultado)


def test_apurador_usa_o_servico_declarado_no_registry():
    """Requisito: o apurador do anexo chama o serviço que o registry declara, não o do BO."""
    from app.services.pipeline.apuracao import _servico_de

    assert _servico_de("I-HI").__module__ == "app.services.dvp.quadro_principal"
    assert _servico_de("BO").__module__ == "app.services.bo.quadro_principal"


def test_mapa_vigente_carrega_a_base_da_dvp():
    """Requisito: o mapa do `I-HI` vem de `rules/dvp` (IPC 05), não de `rules/bo`."""
    from app.services.pipeline.apuracao import mapa_vigente

    assert mapa_vigente(2025, "I-HI").vigencia.documento == "IPC05"
    assert mapa_vigente(2025, "BO").vigencia.documento == "IPC07"
