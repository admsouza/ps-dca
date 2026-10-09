"""O job apura cada recorte com o mesmo serviço, sobre a fonte filtrada.

Change `pipeline-dca-por-unidade-gestora`, D1/D2/D5.
"""
from __future__ import annotations

from decimal import Decimal

from app.services.pipeline import apuracao
from tests.bo.conftest import FonteFake, saldo
from tests.bp.conftest import FontePorAno, fp

ENTE, EXERCICIO = 2505204, 2025
L25, L49 = "bo.quadro_principal.receitas.l25", "bo.quadro_principal.despesas.l49"


def _ug(r, ug: str, po: str, nome: str = ""):
    return r._replace(unidade_gestora=ug, nome_unidade_gestora=nome or f"UG {ug}", poder_orgao=po)


def _bo_duas_ugs() -> dict[int, list]:
    """Prefeitura superavitária (1000 − 400) e Câmara deficitária (100 − 300)."""
    prefeitura = [(5, saldo("521110000", "1000.00", natureza_receita="1100.00.00")),
                  (6, saldo("621200000", "1000.00", natureza_receita="1100.00.00")),
                  (6, saldo("622130400", "400.00", natureza_despesa="3.1.00.00.00"))]
    camara = [(5, saldo("521110000", "100.00", natureza_receita="1100.00.00")),
              (6, saldo("621200000", "100.00", natureza_receita="1100.00.00")),
              (6, saldo("622130400", "300.00", natureza_despesa="3.1.00.00.00"))]
    por_classe: dict[int, list] = {5: [], 6: []}
    for classe, r in prefeitura:
        por_classe[classe].append(_ug(r, "1", "10131", "Prefeitura"))
    for classe, r in camara:
        por_classe[classe].append(_ug(r, "4", "20231", "Câmara"))
    return por_classe


def _bo(fonte):
    from app.services.bo.quadro_principal import apurar
    return apuracao.com_recortes(apurar, ENTE, EXERCICIO, fonte)


def test_chaves_e_rotulos_do_bo():
    """Scenario: ente com UG"""
    resultado = _bo(FonteFake(_bo_duas_ugs()))
    assert set(resultado.recortes) == {"poder:executivo", "poder:legislativo",
                                       "poder:executivo+legislativo", "ug:1", "ug:4"}
    assert resultado.recortes["ug:4"][:3] == ("ug", "Câmara", "20231")
    assert resultado.recortes["poder:executivo"][:2] == ("poder", "Poder Executivo")


def test_deficit_e_superavit_por_recorte():
    """Scenario: Déficit e Superávit por recorte"""
    resultado = _bo(FonteFake(_bo_duas_ugs()))
    prefeitura = resultado.recortes["ug:1"].resultado.matriz
    camara = resultado.recortes["ug:4"].resultado.matriz

    assert all(v is None for v in prefeitura[L25].values())
    assert any(isinstance(v, Decimal) and v > 0 for v in prefeitura[L49].values())
    assert any(isinstance(v, Decimal) and v > 0 for v in camara[L25].values())
    assert all(v is None for v in camara[L49].values())
    # O consolidado é superavitário: 1100 − 700.
    assert all(v is None for v in resultado.matriz[L25].values())


def test_consolidado_bit_a_bit():
    """Scenario: consolidado inalterado"""
    from app.services.bo.quadro_principal import apurar
    from app.services.pipeline.resultado import para_dados

    com = para_dados(_bo(FonteFake(_bo_duas_ugs())))
    sem = para_dados(apurar(ENTE, EXERCICIO, FonteFake(_bo_duas_ugs())))
    com.pop("recortes")
    for corpo in (com, sem):
        corpo["diagnostico"].pop("duracao_ms")
    assert com == sem


def test_particao_cobre_cada_registro_uma_vez():
    """Requisito: recortes apurados no mesmo job (D8) — cada registro cai em uma unidade só."""
    registros = [r for lista in _bo_duas_ugs().values() for r in lista]
    resultado = _bo(FonteFake(_bo_duas_ugs()))
    unidades = [c for c in resultado.recortes if c.startswith("ug:")]
    fonte = FonteFake(_bo_duas_ugs())
    vistos = [r for c in unidades for classe in (5, 6)
              for r in apuracao._Filtrada(fonte, {c}).registros(ENTE, EXERCICIO, 12, classe)]
    assert sorted(vistos) == sorted(registros)


def test_fonte_bruta_lida_uma_vez_por_classe():
    """Scenario: ente com UG — a fonte é consultada o mesmo número de vezes que hoje."""
    from app.infra.msc.escopo import escopo
    from app.services.bo.quadro_principal import apurar

    bruta, referencia = FonteFake(_bo_duas_ugs()), FonteFake(_bo_duas_ugs())
    with escopo():
        _bo(apuracao._NoEscopo(bruta, "fake"))
    with escopo():
        apurar(ENTE, EXERCICIO, apuracao._NoEscopo(referencia, "fake"))
    assert len(bruta.chamadas) == len(referencia.chamadas) == 2


def test_ente_sem_ug_recorta_por_po():
    """Scenario: ente sem UG"""
    fonte = FonteFake({5: [saldo("521110000", "10.00", natureza_receita="1100.00.00",
                                 poder_orgao="10131")],
                       6: [saldo("621200000", "10.00", natureza_receita="1100.00.00",
                                 poder_orgao="20231"),
                           saldo("621200000", "5.00", natureza_receita="1100.00.00")]})
    resultado = _bo(fonte)
    assert {c for c in resultado.recortes if c.startswith("po:")} == {
        "po:10131", "po:20231", "po:"}
    assert resultado.recortes["po:20231"][:2] == ("po", "Poder Legislativo - Câmara Municipal")
    assert resultado.recortes["po:"][1] == "Sem poder/órgão identificado"


class _DcaVazia:
    def itens(self, ente, ano):
        return []


def test_bp_fora_do_consolidado_usa_msce_do_ano_anterior():
    """Scenario: consolidado pelo publicado, UG pela MSC"""
    from app.services.bp.quadro_principal import apurar

    fonte = FontePorAno({
        EXERCICIO: {1: [_ug(fp("111110100", "100.00", "F"), "1", "10131")]},
        EXERCICIO - 1: {1: [_ug(fp("111110100", "70.00", "F"), "1", "10131")]},
    })
    resultado = apuracao.com_recortes(apurar, ENTE, EXERCICIO, fonte,
                                      anterior="publicado_siconfi", dca=_DcaVazia())

    assert resultado.procedencia.origem_exercicio_anterior == "publicado_siconfi"
    ug = resultado.recortes["ug:1"].resultado
    assert ug.procedencia.origem_exercicio_anterior == "msce_exercicio_anterior"
    assert ug.diagnostico.conferencia_publicado is None
    l1 = next(linha.id for linha in ug.mapa.linhas
              if linha.quadro == "QUADRO_PRINCIPAL" and linha.codigo == "L1")
    assert ug.matriz[l1] == {"exercicio_atual": Decimal("100.00"),
                             "exercicio_anterior": Decimal("70.00")}


def test_anexo_fora_do_recorte_nao_ganha_recortes():
    """Scenario: anexo sem recorte — o BF segue como hoje."""
    assert "BF" not in apuracao.RECORTAVEIS and set(apuracao.RECORTAVEIS) == {"BO", "BP"}


def test_serializacao_dos_recortes():
    """Requisito: leitura de um recorte — o cache guarda o resultado completo de cada recorte."""
    from app.services.pipeline.resultado import para_dados

    dados = para_dados(_bo(FonteFake(_bo_duas_ugs())))
    camara = dados["recortes"]["ug:4"]
    assert (camara["tipo"], camara["rotulo"], camara["poderOrgao"]) == ("ug", "Câmara", "20231")
    assert set(camara["resultado"]) >= {"linhas", "matriz", "procedencia", "diagnostico"}
    assert "recortes" not in camara["resultado"]


def test_grupo_sem_unidade_nao_e_apurado():
    """Scenario: grupo sem unidade"""
    fonte = FonteFake({5: [_ug(saldo("521110000", "10.00", natureza_receita="1100.00.00"),
                               "1", "10131")], 6: []})
    assert set(_bo(fonte).recortes) == {"poder:executivo", "poder:executivo+legislativo", "ug:1"}
