"""BF por recorte: o estorno de GRE/GDE abatido é o das unidades do recorte.

Change `bf-por-unidade-gestora`.
"""
from __future__ import annotations

from decimal import Decimal

import pytest

from app.infra.msc.publicsoft import Estorno
from app.services.pipeline import apuracao
from tests.bf.conftest import ENTE, EXERCICIO, FontePorOrigem, fonte_com
from tests.bo.conftest import registro

D = Decimal
MOTIVO_SEM_PO = "estorno sem poder/órgão"
MOTIVO_G8 = "informado só no consolidado"


def _dep(natureza: str, valor: str, ug: str = "", po: str = ""):
    """Depósito extraorçamentário: L27 soma os créditos e L60 os débitos."""
    return registro("218800000", natureza, valor, fonte_recursos="1860",
                    poder_orgao=po)._replace(unidade_gestora=ug,
                                             nome_unidade_gestora=f"UG {ug}" if ug else "")


def _estorno(itens: dict[str, tuple[str, str | None]], com_po: bool = True) -> Estorno:
    """`{"ug:1": ("10.00", "10131")}` → `Estorno` como o `ps-erp` devolve."""
    return Estorno(sum((D(v) for v, _ in itens.values()), D("0")),
                   {u: D(v) for u, (v, _) in itens.items()},
                   {u: po for u, (_, po) in itens.items()} if com_po else None)


class _SemRelatorio(FontePorOrigem):
    """`period_change` só em janeiro. Sem `estorno_*`: SICONFI sem `token_ps`."""

    def registros(self, ente, ano, mes, classe, matriz=None, tipo_saldo=None):
        if getattr(tipo_saldo, "name", "") == "PERIODO" and mes != 1:
            return []
        return super().registros(ente, ano, mes, classe, matriz, tipo_saldo)


class _ComEstorno(_SemRelatorio):
    def __init__(self, por_origem, receita: dict[int, Estorno],
                 despesa: dict[int, Estorno] | None = None):
        super().__init__(por_origem)
        self._receita, self._despesa = receita, despesa or {}
        self.chamadas_estorno: list[tuple[str, int]] = []

    def estorno_receita_extra(self, ano):
        self.chamadas_estorno.append(("receita", ano))
        return self._receita[ano]

    def estorno_despesa_extra(self, ano):
        self.chamadas_estorno.append(("despesa", ano))
        return self._despesa.get(ano, Estorno(D("0"), {}, {}))


RECEITA_2025 = {"ug:1": ("10.00", "10131"), "ug:3": ("5.00", "10131"), "ug:4": ("1.00", "20231")}
RECEITA_2024 = {"ug:1": ("2.00", "10131")}


def _ug_origens():
    """2025: UG 1 e 3 (Executivo) e UG 4 (Câmara). 2024: só a UG 1."""
    return fonte_com(
        p2025={2: [_dep("C", "100.00", "1", "10131"), _dep("D", "80.00", "1", "10131"),
                   _dep("C", "60.00", "3", "10131"), _dep("C", "40.00", "4", "20231")]},
        p2024={2: [_dep("C", "50.00", "1", "10131"), _dep("D", "40.00", "1", "10131")]},
        a2024={2: [_dep("C", "1.00", "1", "10131")]},
    )._por_origem


def _fonte_ug(extra: dict | None = None, com_po: bool = True):
    return _ComEstorno(_ug_origens(), {
        2025: _estorno({**RECEITA_2025, **(extra or {})}, com_po),
        2024: _estorno(RECEITA_2024, com_po)})


def _po_origens():
    return fonte_com(
        p2025={2: [_dep("C", "100.00", po="10131"), _dep("D", "80.00", po="10131"),
                   _dep("C", "40.00", po="20231")]},
        p2024={2: [_dep("C", "50.00", po="10131")]},
    )._por_origem


def _fonte_po(com_po: bool = True):
    return _ComEstorno(_po_origens(), {
        2025: _estorno({"ug:1": ("10.00", "10131"), "ug:2": ("4.00", "20231"),
                        "ug:7": ("50.00", None), "ug:8": ("3.00", "20232")}, com_po),
        2024: _estorno({"ug:1": ("2.00", "10131")}, com_po)})


def _bf(fonte, **extras):
    from app.services.bf.quadro_principal import apurar
    return apuracao.com_recortes(apurar, ENTE, EXERCICIO, fonte, **extras)


def _linha(resultado, codigo: str):
    return next(i for i in resultado.mapa.linhas
                if i.quadro == "QUADRO_PRINCIPAL" and i.codigo == codigo)


def _celula(resultado, codigo: str, coluna: str = "exercicio_atual"):
    return resultado.matriz[_linha(resultado, codigo).id][coluna]


def _motivos(resultado, codigo: str, coluna: str) -> list[str]:
    rule_id = _linha(resultado, codigo).id
    return [n.motivo for n in resultado.diagnostico.nao_apuradas
            if n.rule_id == rule_id and n.coluna == coluna]


def test_ug_abate_so_o_estorno_da_unidade():
    """Scenario: UG"""
    r = _bf(_fonte_ug()).recortes
    assert _celula(r["ug:1"].resultado, "L27") == D("90.00")
    assert _celula(r["ug:1"].resultado, "L60") == D("70.00")
    assert _celula(r["ug:3"].resultado, "L27") == D("55.00")
    assert _celula(r["ug:4"].resultado, "L27") == D("39.00")
    assert r["ug:1"].resultado.procedencia.estorno_receita_extra == {"2025": "10.00"}


def test_grupo_de_poder_soma_as_unidades():
    """Requisito: estorno por unidade — `poder:*` é a soma das unidades do grupo"""
    r = _bf(_fonte_ug()).recortes
    assert _celula(r["poder:executivo"].resultado, "L27") == D("145.00")
    assert _celula(r["poder:legislativo"].resultado, "L27") == D("39.00")
    assert _celula(r["poder:executivo+legislativo"].resultado, "L27") == D("184.00")


def test_totalizadora_acompanha_o_abatimento_na_unidade():
    """Requisito: as totalizadoras que somam L27 acompanham o abatimento"""
    r = _bf(_fonte_ug()).recortes["ug:4"].resultado
    assert _celula(r, "L24") == D("39.00")


def test_consolidado_abate_o_total_geral():
    """Scenario: consolidado inalterado — exercício atual

    O consolidado não lê mais o exercício anterior diretamente
    (`pipeline-consolidado-anterior-soma-unidades`): o estorno de N−1 vive na procedência de cada
    unidade, não na do consolidado."""
    resultado = _bf(_fonte_ug())
    assert _celula(resultado, "L27") == D("184.00")
    assert resultado.procedencia.estorno_receita_extra == {"2025": "16.00"}


def test_consolidado_bit_a_bit():
    """Scenario: consolidado inalterado — coluna atual igual à apuração sem recortes

    A coluna anterior deixou de ser bit a bit igual (vira soma das unidades); só o atual e o G8
    são comparados aqui, como pede `pipeline-consolidado-anterior-soma-unidades`."""
    from app.services.bf.quadro_principal import apurar
    from app.services.pipeline.resultado import para_dados

    com = para_dados(_bf(_fonte_ug()))
    sem = para_dados(apurar(ENTE, EXERCICIO, _fonte_ug()))
    for linha in com["linhas"]:
        celulas_com = com["matriz"][linha["rule_id"]]
        celulas_sem = sem["matriz"][linha["rule_id"]]
        for coluna, valor in celulas_com.items():
            if coluna.endswith("_atual"):
                assert valor == celulas_sem[coluna], (linha["codigo"], coluna)


def test_particao_do_estorno_por_ug():
    """Scenario: partição do estorno — por UG"""
    resultado = _bf(_fonte_ug({"ug:9": ("100.00", "10131")}))
    abatido = sum(D(r.resultado.procedencia.estorno_receita_extra["2025"])
                  for c, r in resultado.recortes.items() if c.startswith("ug:"))
    sem = sum(D(s["valor"]) for s in resultado.diagnostico.estorno_sem_unidade
              if (s["exercicio"], s["tipo"]) == (2025, "receita"))
    assert abatido + sem == D(resultado.procedencia.estorno_receita_extra["2025"]) == D("116.00")


def test_contribuicao_sem_unidade_na_coluna_anterior_falha():
    """Scenario: contribuição sem UG ou PO
    Scenario: falha de atribuição não publica parcial
    (`pipeline-consolidado-anterior-soma-unidades`): sem unidade no exercício ATUAL é só
    diagnóstico (fora de escopo); no exercício ANTERIOR, o job falha."""
    from app.services.pipeline.anterior import ParcelaSemUnidade

    fonte = _ComEstorno(_ug_origens(), {
        2025: _estorno(RECEITA_2025),
        2024: _estorno({**RECEITA_2024, "ug:9": ("3.00", "10131")})})

    with pytest.raises(ParcelaSemUnidade):
        _bf(fonte)


def test_estorno_de_ug_sem_registro_vai_para_o_diagnostico():
    """Scenario: UG sem registro"""
    resultado = _bf(_fonte_ug({"ug:9": ("100.00", "10131")}))
    assert resultado.diagnostico.estorno_sem_unidade == [
        {"exercicio": 2025, "tipo": "receita", "unidade": "ug:9", "valor": "100.00"}]
    assert _celula(resultado, "L27") == D("84.00")
    assert not any("ug:9" in c for c in resultado.recortes)


def test_po_abate_pelo_poder_orgao_da_instituicao():
    """Scenario: PO"""
    r = _bf(_fonte_po()).recortes
    assert _celula(r["po:10131"].resultado, "L27") == D("90.00")
    assert _celula(r["po:10131"].resultado, "L60") == D("70.00")
    assert _celula(r["po:20231"].resultado, "L27") == D("36.00")
    assert _celula(r["poder:executivo"].resultado, "L27") == D("90.00")


def test_po_nulo_ou_nao_observado_vai_para_o_diagnostico():
    """Scenario: PO nulo / partição do estorno — por PO"""
    resultado = _bf(_fonte_po())
    assert resultado.diagnostico.estorno_sem_unidade == [
        {"exercicio": 2025, "tipo": "receita", "unidade": "ug:7", "valor": "50.00"},
        {"exercicio": 2025, "tipo": "receita", "unidade": "ug:8", "valor": "3.00"}]
    abatido = sum(D(r.resultado.procedencia.estorno_receita_extra["2025"])
                  for c, r in resultado.recortes.items() if c.startswith("po:"))
    assert abatido + D("53.00") == D("67.00")


def test_resposta_sem_poder_orgao_deixa_os_po_nao_apurados():
    """Scenario: resposta sem o campo poderOrgao"""
    resultado = _bf(_fonte_po(com_po=False))
    po = resultado.recortes["po:20231"].resultado
    for codigo in ("L27", "L60", "L24"):
        assert _celula(po, codigo) is None
    assert _motivos(po, "L27", "exercicio_atual") == [MOTIVO_SEM_PO]
    sem_n1 = resultado.recortes["po:10131"].resultado     # sem N−1: coluna em zero, sem não apurada
    assert _motivos(sem_n1, "L27", "exercicio_anterior") == []
    assert _celula(sem_n1, "L27", "exercicio_anterior") == D("0.00")
    assert _celula(resultado, "L27") == D("140.00") - D("67.00")


def test_uma_chamada_por_exercicio_e_tipo():
    """Scenario: uma chamada por exercício"""
    from app.infra.msc.escopo import escopo

    fonte = _fonte_ug()
    with escopo():
        resultado = _bf(apuracao._NoEscopo(fonte, "publicsoft"))
    assert len(resultado.recortes) == 3 + 3
    assert sorted(fonte.chamadas_estorno) == [("despesa", 2024), ("despesa", 2025),
                                              ("receita", 2024), ("receita", 2025)]


def test_fonte_sem_relatorio_nao_abate_em_nenhum_recorte():
    """Requisito: SICONFI sem token_ps — nenhum recorte abate"""
    resultado = _bf(_SemRelatorio(_ug_origens()))
    assert _celula(resultado.recortes["ug:1"].resultado, "L27") == D("100.00")
    assert resultado.recortes["ug:1"].resultado.procedencia.estorno_receita_extra is None
    assert resultado.diagnostico.estorno_sem_unidade is None


def test_g8_so_no_consolidado():
    """Scenario: G8 fora do consolidado"""
    resultado = _bf(_fonte_ug(), valores_sem_mapeamento={"L22": "7.00"})
    ug = resultado.recortes["ug:1"].resultado
    assert _celula(resultado, "L22") == D("7.00")
    assert _celula(ug, "L22") is None
    assert _motivos(ug, "L22", "exercicio_atual") == [MOTIVO_G8]
    assert ug.procedencia.valores_sem_mapeamento is None


def test_topo_nao_aceita_mais_manual_proprio():
    """Requisito: o consolidado não tem origem própria (`pipeline-consolidado-anterior-soma-
    unidades`): o legado `anterior=manual`/`valores_anteriores` do topo é ignorado, e sai da soma
    das unidades."""
    resultado = _bf(_fonte_ug(), anterior="manual", valores_anteriores={"L27": "999.00"})
    ug = resultado.recortes["ug:1"].resultado
    assert _celula(resultado, "L27", "exercicio_anterior") != D("999.00")
    assert resultado.procedencia.origem_exercicio_anterior == "soma_das_unidades"
    assert _celula(ug, "L27", "exercicio_anterior") == D("0.00")
    assert ug.procedencia.origem_exercicio_anterior == "sem_anterior"
    assert ug.procedencia.valores_anteriores is None


def test_sem_n1_toda_unidade_sai_em_zero_com_marca():
    """Scenario: primeira apuração sem exercício anterior conclui"""
    r = _bf(_fonte_ug()).recortes
    for chave in ("ug:1", "ug:3", "ug:4"):
        assert _celula(r[chave].resultado, "L27", "exercicio_anterior") == D("0.00")
        assert r[chave].resultado.diagnostico.sem_dados_exercicio_anterior is True


def test_bf_e_recortavel():
    """Scenario: BF com UG"""
    assert "BF" in apuracao.RECORTAVEIS
    assert {"ug:1", "ug:3", "ug:4", "poder:executivo"} <= set(_bf(_fonte_ug()).recortes)
