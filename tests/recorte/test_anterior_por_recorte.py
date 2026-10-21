"""Coluna do exercício anterior por unidade: processado, MSC ou manual (BF e BP).

Change `pipeline-anterior-por-recorte`, capability `pipeline/anterior-por-recorte`.
"""
from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from functools import wraps

import pytest

from app.services.bp.quadro_principal import apurar as apurar_bp
from app.services.pipeline import apuracao
from app.services.pipeline.anterior import ProcessadoSemAnterior
from app.services.pipeline.resultado import para_dados
from tests.bo.conftest import registro
from tests.bp.conftest import ENTE, EXERCICIO, FontePorAno, fp
from tests.pipeline.conftest import RegistroFake, RepoFake

D = Decimal
PRINCIPAL, SUPERAVIT = "QUADRO_PRINCIPAL", "SUPERAVIT_DEFICIT"
ATUAL, ANTERIOR = "exercicio_atual", "exercicio_anterior"
PROCESSADO, MSCE, MANUAL = ("processado_exercicio_anterior", "msce_exercicio_anterior", "manual")
CALCULADO = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)
CAIXA, SALDO_FONTE = "111110100", "821110100"


def _r(conta: str, valor: str, ug: str, po: str, atributo: str = "F"):
    return fp(conta, valor, atributo)._replace(
        unidade_gestora=ug, nome_unidade_gestora=f"UG {ug}", poder_orgao=po)


def _fonte_ano(caixa: dict[str, str], fontes: dict[tuple[str, str], str] | None = None,
               po: dict[str, str] | None = None) -> dict[int, list]:
    """`caixa`: `{ug: valor}`; `fontes`: `{(ug, fonte): saldo credor}` na classe 8."""
    po = po or {"1": "10131", "4": "20231"}
    return {1: [_r(CAIXA, v, ug, po[ug]) for ug, v in caixa.items()],
            8: [registro(SALDO_FONTE, "C", v, fonte_recursos=f, poder_orgao=po[ug])._replace(
                unidade_gestora=ug, nome_unidade_gestora=f"UG {ug}")
                for (ug, f), v in (fontes or {}).items()]}


def _fonte(n: dict[int, list], n1: dict[int, list] | None = None) -> FontePorAno:
    return FontePorAno({EXERCICIO: n, EXERCICIO - 1: n1 or {}})


def _bp(fonte, repo=None, escolhas=None, agora=(), spy=None, **extras):
    apurar = apurar_bp if spy is None else spy
    return apuracao.com_recortes(apurar, ENTE, EXERCICIO, fonte, repo=repo, anexo="BP",
                                 escolhas=escolhas, agora=agora,
                                 anterior=extras.pop("anterior", MSCE), **extras)


def _n1(registros: dict[int, list], status: str = "ok", versao: str = "r|c12:-:f=publicsoft",
        ano: int = EXERCICIO - 1, dados: dict | None = None) -> RegistroFake:
    """O BP de N−1 já em cache, apurado sobre `registros` (por classe)."""
    if dados is None:
        dados = para_dados(apuracao.com_recortes(
            apurar_bp, ENTE, ano, FontePorAno({ano: registros}), anterior=MSCE))
    return RegistroFake(str(ENTE), ano, "BP", status=status, resultado=dados, versao_regras=versao,
                        calculado_em=CALCULADO)


def _cache(*registros: RegistroFake) -> RepoFake:
    return RepoFake(list(registros))


def _linha(resultado, codigo: str, quadro: str = PRINCIPAL) -> str:
    return next(i.id for i in resultado.mapa.linhas if i.quadro == quadro and i.codigo == codigo)


def _cel(resultado, codigo: str, coluna: str = ANTERIOR, quadro: str = PRINCIPAL):
    return resultado.matriz[_linha(resultado, codigo, quadro)][coluna]


def _motivos(resultado, codigo: str, quadro: str = PRINCIPAL) -> list[str]:
    rule_id = _linha(resultado, codigo, quadro)
    return [n.motivo for n in resultado.diagnostico.nao_apuradas
            if n.rule_id == rule_id and n.coluna == ANTERIOR]


def _espiao(chamadas: list[tuple[str, frozenset]]):
    """`apurar` do BP que anota `(origem da coluna anterior, unidades do recorte)`."""
    @wraps(apurar_bp)
    def espiao(ente, exercicio, fonte, **kwargs):
        chamadas.append((str(kwargs.get("anterior")), frozenset(getattr(fonte, "_unidades", ()))))
        return apurar_bp(ente, exercicio, fonte, **kwargs)
    return espiao


N = _fonte_ano({"1": "100.00", "4": "40.00"})
N1 = _fonte_ano({"1": "70.00", "4": "30.00"})


def _repo_com_n1() -> RepoFake:
    return _cache(_n1(N1))


# ─── padrão ──────────────────────────────────────────────────────────────────

def test_padrao_com_n1_processado_nao_apura_n1_para_a_unidade():
    """Scenario: padrão com N−1 processado"""
    chamadas: list = []
    r = _bp(_fonte(N, N1), _repo_com_n1(), spy=_espiao(chamadas))

    ug1 = r.recortes["ug:1"].resultado
    assert _cel(ug1, "L3") == D("70.00") and _cel(ug1, "L3", ATUAL) == D("100.00")
    assert _cel(r.recortes["ug:4"].resultado, "L3") == D("30.00")
    assert ug1.procedencia.origem_exercicio_anterior == PROCESSADO
    assert ug1.procedencia.escolha_anterior is None
    assert ug1.procedencia.anterior_processado["exercicio"] == EXERCICIO - 1
    assert (MSCE, frozenset({"ug:1"})) not in chamadas
    assert (PROCESSADO, frozenset({"ug:1"})) in chamadas


def test_anterior_processado_declara_o_retrato_de_n1():
    """Requisito: a procedência declara `anterior_processado`"""
    n1 = _n1(N1, versao="regras|c12:-:f=publicsoft")
    ug1 = _bp(_fonte(N), _cache(n1)).recortes["ug:1"].resultado

    assert ug1.procedencia.anterior_processado == {
        "exercicio": EXERCICIO - 1, "calculado_em": CALCULADO.isoformat(),
        "versao_regras": n1.resultado["recortes"]["ug:1"]["resultado"]["procedencia"][
            "versao_regras"],
        "fonte": "publicsoft"}


def test_fonte_nula_quando_a_identidade_de_n1_nao_tem_f():
    ug1 = _bp(_fonte(N), _cache(_n1(N1, versao="regras"))).recortes["ug:1"].resultado

    assert ug1.procedencia.anterior_processado["fonte"] is None


def test_servico_direto_sem_repositorio_preserva_msce_bit_a_bit():
    """Scenario: padrão sem N−1 processado"""
    fonte = _fonte(N, N1)
    r = _bp(fonte)

    for chave in ("ug:1", "ug:4"):
        esperado = apurar_bp(ENTE, EXERCICIO, apuracao._Filtrada(fonte, {chave}), anterior=MSCE)
        ug = r.recortes[chave].resultado
        assert ug.matriz == esperado.matriz
        assert ug.procedencia.origem_exercicio_anterior == MSCE


def test_novo_padrao_sem_n1_processado_exige_processado_ou_manual():
    """Scenario: padrão sem Processado orienta a correção."""
    with pytest.raises(ProcessadoSemAnterior, match="Processe 2024 ou use Manual"):
        _bp(_fonte(N, N1), RepoFake())


def test_cache_de_n1_gravado_antes_dos_recortes_exige_novo_processamento():
    dados = para_dados(apurar_bp(ENTE, EXERCICIO - 1, FontePorAno({EXERCICIO - 1: N1}),
                                 anterior=MSCE))
    with pytest.raises(ProcessadoSemAnterior, match="Processe 2024 ou use Manual"):
        _bp(_fonte(N, N1), _cache(_n1(N1, dados=dados)))


@pytest.mark.parametrize("status", ["processando", "erro"])
def test_n1_fora_do_ok_exige_processado_ou_manual(status):
    """Scenario: N−1 em processamento"""
    with pytest.raises(ProcessadoSemAnterior, match="Processe 2024 ou use Manual"):
        _bp(_fonte(N, N1), _cache(_n1(N1, status=status)))


def test_unidade_ausente_em_n1_exige_manual():
    n1 = _n1(_fonte_ano({"1": "70.00"}))
    with pytest.raises(ProcessadoSemAnterior, match="Processe 2024 ou use Manual"):
        _bp(_fonte(N, N1), _cache(n1))


# ─── origens mistas, escolhas ────────────────────────────────────────────────

def test_origens_diferentes_no_mesmo_job():
    """Scenario: origens diferentes no mesmo job"""
    escolhas = {"ug:1": {"origem": MANUAL, "valores": {"P:L3": "11.00"}},
                "ug:4": {"origem": PROCESSADO}}
    r = _bp(_fonte(N, N1), _repo_com_n1(), escolhas=escolhas, agora=("ug:1", "ug:4"))

    ug1, ug4 = r.recortes["ug:1"].resultado, r.recortes["ug:4"].resultado
    assert _cel(ug1, "L3") == D("11.00")
    assert ug1.procedencia.valores_anteriores == {"P:L3": "11.00"}
    assert ug1.procedencia.escolha_anterior == escolhas["ug:1"]
    assert _cel(ug4, "L3") == D("30.00")
    assert ug4.procedencia.origem_exercicio_anterior == PROCESSADO
    assert ug4.procedencia.escolha_anterior == {"origem": PROCESSADO}


def test_escolha_explicita_de_processado_e_gravada():
    r = _bp(_fonte(N), _repo_com_n1(), escolhas={"ug:1": {"origem": PROCESSADO}},
            agora=("ug:1",))

    assert r.recortes["ug:1"].resultado.procedencia.escolha_anterior == {"origem": PROCESSADO}
    assert r.recortes["ug:4"].resultado.procedencia.escolha_anterior is None


def test_processado_explicito_sem_n1_falha_com_o_motivo():
    """Scenario: N−1 some entre a rota e o job"""
    with pytest.raises(ProcessadoSemAnterior, match="Processe 2024 ou use Manual"):
        _bp(_fonte(N, N1), RepoFake(), escolhas={"ug:1": {"origem": PROCESSADO}},
            agora=("ug:1",))


def test_processado_explicito_com_n1_processando_falha():
    with pytest.raises(ProcessadoSemAnterior, match="Processe 2024 ou use Manual"):
        _bp(_fonte(N, N1), _cache(_n1(N1, status="processando")),
            escolhas={"ug:1": {"origem": PROCESSADO}}, agora=("ug:1",))


def test_processado_gravado_sem_n1_exige_processado_ou_manual():
    """Scenario: processado gravado sem N−1"""
    with pytest.raises(ProcessadoSemAnterior, match="Processe 2024 ou use Manual"):
        _bp(_fonte(N, N1), RepoFake(), escolhas={"ug:1": {"origem": PROCESSADO}})


def test_escolha_gravada_de_unidade_inexistente_e_descartada_sem_aviso():
    """Scenario: escolha de unidade inexistente descartada"""
    r = _bp(_fonte(N, N1), _repo_com_n1(), escolhas={"ug:99": {"origem": PROCESSADO}})

    assert "ug:99" not in r.recortes
    assert not getattr(r.diagnostico, "avisos_anterior", None)


def test_unidade_pedida_agora_e_inexistente_gera_aviso():
    """Scenario: unidade inexistente"""
    r = _bp(_fonte(N, N1), _repo_com_n1(), escolhas={"ug:99": {"origem": PROCESSADO}},
            agora=("ug:99",))

    assert "ug:99" not in r.recortes
    assert any("ug:99" in aviso for aviso in r.diagnostico.avisos_anterior)


# ─── linha sem par, UG sem MSC ───────────────────────────────────────────────

def test_linha_sem_par_em_n1_fica_nao_apurada():
    """Scenario: linha sem par em N−1"""
    dados = _n1(N1).resultado
    for recorte in dados["recortes"].values():
        recorte["resultado"]["linhas"] = [linha for linha in recorte["resultado"]["linhas"]
                                          if not (linha["quadro"] == PRINCIPAL
                                                  and linha["codigo"] == "L3")]
    ug1 = _bp(_fonte(N), _cache(_n1(N1, dados=dados))).recortes["ug:1"].resultado

    assert _cel(ug1, "L3") is None
    assert _motivos(ug1, "L3") == ["sem linha no exercício anterior"]


def test_ug_sem_msc_em_n1_sai_em_zero_com_aviso_quando_o_job_leu_n1():
    """Scenario: UG sem MSC no ano anterior"""
    r = _bp(_fonte(N, _fonte_ano({"1": "70.00"})))

    ug4 = r.recortes["ug:4"].resultado
    assert _cel(ug4, "L3") == D("0.00")
    assert ug4.diagnostico.sem_dados_exercicio_anterior is True
    assert _cel(r.recortes["ug:1"].resultado, "L3") == D("70.00")


def test_consolidado_sem_nenhuma_leitura_de_n1_continua_nao_apurado():
    r = _bp(_fonte(N))

    assert _cel(r, "L3") is None and r.diagnostico.sem_dados_exercicio_anterior is True
    assert _cel(r.recortes["ug:1"].resultado, "L3") is None
    assert r.recortes["ug:1"].resultado.diagnostico.sem_dados_exercicio_anterior is True


# ─── Superávit, visões, fonte vazia ──────────────────────────────────────────

def test_superavit_une_as_fontes_de_n_e_n1_no_processado():
    """Scenario: Superávit por fonte no processado"""
    n = _fonte_ano({"1": "100.00"}, {("1", "1700"): "9.00"})
    n1 = _fonte_ano({"1": "70.00"}, {("1", "1500"): "7.00"})
    ug1 = _bp(_fonte(n), _cache(_n1(n1))).recortes["ug:1"].resultado

    assert _cel(ug1, "1500", ATUAL, SUPERAVIT) == D("0.00")
    assert _cel(ug1, "1500", ANTERIOR, SUPERAVIT) == D("7.00")
    assert _cel(ug1, "1700", ATUAL, SUPERAVIT) == D("9.00")
    assert _cel(ug1, "1700", ANTERIOR, SUPERAVIT) == D("0.00")
    assert _cel(ug1, "Total", ANTERIOR, SUPERAVIT) == D("7.00")


def test_visoes_e_fonte_vazia_sao_transpostos():
    n1 = _fonte_ano({"1": "70.00"}, {("1", "0"): "3.00"})
    escolhas = {"ug:4": {"origem": MANUAL, "valores": {}}}
    ug1 = _bp(_fonte(N), _cache(_n1(n1)), escolhas=escolhas).recortes["ug:1"].resultado

    assert ug1.diagnostico.fonte_vazia == {ANTERIOR: D("3.00")}
    visao = ug1.visoes["consolidado"].matriz[_linha(ug1, "L3")]
    assert visao[ANTERIOR] == D("70.00")
    assert ug1.visoes["consolidado"].equilibrio.get(ANTERIOR) is not None


# ─── grupo de poder = soma das unidades ──────────────────────────────────────

def test_grupo_com_origens_mistas_soma_as_unidades():
    """Scenario: grupo com origens mistas"""
    n = _fonte_ano({"1": "100.00", "4": "40.00", "5": "8.00"},
                   po={"1": "10131", "4": "10131", "5": "20231"})
    n1 = _fonte_ano({"1": "70.00", "4": "30.00"}, po={"1": "10131", "4": "10131"})
    escolhas = {
        "ug:4": {"origem": MANUAL, "valores": {"P:L3": "11.00"}},
        "ug:5": {"origem": MANUAL, "valores": {}},
    }
    r = _bp(_fonte(n, n1), _cache(_n1(n1)), escolhas=escolhas, agora=("ug:4",))

    assert _cel(r.recortes["ug:1"].resultado, "L3") == D("70.00")           # processado
    assert _cel(r.recortes["ug:4"].resultado, "L3") == D("11.00")           # manual
    assert _cel(r.recortes["ug:5"].resultado, "L3") is None                 # manual pendente
    executivo = r.recortes["poder:executivo"].resultado
    assert _cel(executivo, "L3") == D("81.00")
    assert executivo.procedencia.origem_exercicio_anterior == "soma_das_unidades"
    assert executivo.procedencia.escolha_anterior is None
    # Folha não informada no manual da unidade: a do grupo fica não apurada.
    assert _cel(executivo, "L4") is None
    assert _cel(r.recortes["poder:legislativo"].resultado, "L3") is None


@pytest.mark.parametrize("com_n1", [False, True])
def test_grupo_somado_e_igual_ao_grupo_filtrado_em_msce_no_bp(com_n1):
    """Scenario: aditividade"""
    fonte = _fonte(N, N1)
    repo = _repo_com_n1() if com_n1 else None
    r = _bp(fonte, repo)
    esperado = apurar_bp(ENTE, EXERCICIO, apuracao._Filtrada(fonte, {"ug:1", "ug:4"}),
                         anterior=MSCE)

    grupo = r.recortes["poder:executivo+legislativo"].resultado
    assert grupo.matriz == esperado.matriz


def test_visoes_do_grupo_somam_as_das_unidades():
    r = _bp(_fonte(N, N1), _repo_com_n1())

    grupo = r.recortes["poder:executivo+legislativo"].resultado
    assert grupo.visoes["consolidado"].matriz[_linha(grupo, "L3")][ANTERIOR] == D("100.00")


def test_superavit_do_grupo_une_as_fontes_das_unidades():
    n = _fonte_ano({"1": "100.00", "4": "40.00"}, {("1", "1700"): "9.00"})
    n1 = _fonte_ano({"1": "70.00", "4": "30.00"}, {("1", "1500"): "7.00", ("4", "1700"): "2.00"})
    r = _bp(_fonte(n, n1), _cache(_n1(n1)))

    grupo = r.recortes["poder:executivo+legislativo"].resultado
    assert _cel(grupo, "1500", ANTERIOR, SUPERAVIT) == D("7.00")
    assert _cel(grupo, "1700", ANTERIOR, SUPERAVIT) == D("2.00")
    assert _cel(grupo, "1700", ATUAL, SUPERAVIT) == D("9.00")
    assert _cel(grupo, "Total", ANTERIOR, SUPERAVIT) == D("9.00")


# ─── consolidado = soma das unidades (`pipeline-consolidado-anterior-soma-unidades`) ──────────

def test_consolidado_nao_tem_origem_propria_mesmo_pedindo_processado():
    """Scenario: Cuitegi consolidado pela soma dos POs (processado é ignorado no topo)
    Scenario: consolidado do BP usa somente as unidades"""
    n1 = _n1(N1)
    r = _bp(_fonte(N), _cache(n1), anterior=PROCESSADO)

    assert _cel(r, "L3") == D("100.00")          # soma das unidades, não o consolidado de N−1
    assert r.procedencia.origem_exercicio_anterior == "soma_das_unidades"
    assert r.procedencia.anterior_processado is None
    assert r.procedencia.escolha_anterior is None


def test_consolidado_e_a_soma_das_unidades_com_origens_mistas():
    """Scenario: origens diferentes entram na mesma soma
    Scenario: manual por unidade substitui manual consolidado"""
    escolhas = {"ug:1": {"origem": MANUAL, "valores": {"P:L3": "11.00"}}, "ug:4": {"origem": MSCE}}
    r = _bp(_fonte(N, N1), _repo_com_n1(), escolhas=escolhas, agora=("ug:1", "ug:4"))

    soma = D(_cel(r.recortes["ug:1"].resultado, "L3")) + D(_cel(r.recortes["ug:4"].resultado, "L3"))
    assert _cel(r, "L3") == soma == D("41.00")
    assert r.procedencia.origem_exercicio_anterior == "soma_das_unidades"


def test_consolidado_atual_nao_muda_com_a_soma_das_unidades():
    """Scenario: exercício atual permanece igual"""
    fonte = _fonte(N, N1)
    com = _bp(fonte, _repo_com_n1())
    sem = apurar_bp(ENTE, EXERCICIO, fonte, anterior=MSCE)

    assert _cel(com, "L3", ATUAL) == _cel(sem, "L3", ATUAL)


def test_consolidado_sem_nenhuma_unidade_falha():
    """Scenario: nenhuma unidade emitida"""
    from app.services.pipeline.anterior import ParcelaSemUnidade

    with pytest.raises(ParcelaSemUnidade):
        _bp(_fonte({}), RepoFake())


# ─── BP: po: pela MSC, nunca pelo publicado; N−1 de outra fonte ──────────────

class _DcaEspia:
    def __init__(self):
        self.chamadas = 0

    def itens(self, ente, ano):
        self.chamadas += 1
        return []


def test_po_em_msce_le_a_msc_e_nunca_o_publicado():
    """Scenario: PO pela MSC do SICONFI; o consolidado não lê mais o publicado"""
    def po(valor: str, codigo: str):
        return fp(CAIXA, valor, "F")._replace(poder_orgao=codigo)

    dca = _DcaEspia()
    fonte = _fonte({1: [po("100.00", "10131"), po("40.00", "20231")]},
                   {1: [po("70.00", "10131"), po("30.00", "20231")]})
    r = _bp(fonte, dca=dca)

    assert set(r.recortes) >= {"po:10131", "po:20231"}
    assert _cel(r.recortes["po:20231"].resultado, "L3") == D("30.00")
    assert r.recortes["po:20231"].resultado.procedencia.origem_exercicio_anterior == MSCE
    assert dca.chamadas == 0                    # consolidado não tem origem própria


def test_n1_processado_por_unidade_que_casa_soma_no_consolidado():
    """Scenario: N−1 processado, por unidade — o consolidado soma o resultado"""
    def po(valor: str, codigo: str):
        return fp(CAIXA, valor, "F")._replace(poder_orgao=codigo)

    fonte = _fonte({1: [po("100.00", "10131")]}, {1: [po("70.00", "10131")]})
    n1 = _n1({1: [po("70.00", "10131")]})
    r = _bp(fonte, _cache(n1), escolhas={"po:10131": {"origem": PROCESSADO}},
            agora=("po:10131",))

    assert r.recortes["po:10131"].resultado.procedencia.anterior_processado["fonte"] == "publicsoft"
    assert _cel(r.recortes["po:10131"].resultado, "L3") == D("70.00")
    assert r.procedencia.origem_exercicio_anterior == "soma_das_unidades"
    assert _cel(r, "L3") == D("70.00")


# ─── BF ──────────────────────────────────────────────────────────────────────

def _fonte_bf():
    from tests.recorte.test_bf_estorno_por_unidade import (
        RECEITA_2024,
        RECEITA_2025,
        _ComEstorno,
        _estorno,
        _ug_origens,
    )
    return _ComEstorno(_ug_origens(), {2025: _estorno(RECEITA_2025), 2024: _estorno(RECEITA_2024),
                                       2023: _estorno({})})


def _bf(fonte, repo=None, ano: int = EXERCICIO, escolhas=None, agora=(), **extras):
    from app.services.bf.quadro_principal import apurar
    return apuracao.com_recortes(apurar, 2611606, ano, fonte, repo=repo, anexo="BF",
                                 escolhas=escolhas, agora=agora, **extras)


def _bf_n1(fonte) -> RepoFake:
    return RepoFake([RegistroFake("2611606", EXERCICIO - 1, "BF", resultado=para_dados(
        _bf(fonte, ano=EXERCICIO - 1)), versao_regras="r|c12:-:f=publicsoft",
        calculado_em=CALCULADO)])


def _por_codigo(dados: dict) -> dict:
    return {(linha["quadro"], linha["codigo"]): dados["matriz"][linha["rule_id"]]
            for linha in dados["linhas"]}


def test_bf_unidade_em_processado_traz_a_coluna_atual_de_n1_em_centavos():
    """Scenario: padrão com N−1 processado — BF, principal e anexo"""
    fonte = _fonte_bf()
    repo = _bf_n1(fonte)
    escolhas = {chave: {"origem": MANUAL, "valores": {}} for chave in ("ug:3", "ug:4")}
    r = para_dados(_bf(fonte, repo, escolhas=escolhas))
    n1 = repo.obter("2611606", EXERCICIO - 1, "BF").resultado

    atual_n = _por_codigo(r["recortes"]["ug:1"]["resultado"])
    atual_n1 = _por_codigo(n1["recortes"]["ug:1"]["resultado"])
    comparadas = 0
    for chave, celulas in atual_n.items():
        for coluna, valor in celulas.items():
            if coluna.endswith("_anterior"):
                assert valor == atual_n1[chave].get(coluna[: -len("_anterior")] + "_atual"), chave
                comparadas += 1
    assert comparadas > 80
    procedencia = r["recortes"]["ug:1"]["resultado"]["procedencia"]
    assert procedencia["origem_exercicio_anterior"] == PROCESSADO
    assert procedencia["escolha_anterior"] is None


def test_bf_anterior_processado_traz_os_estornos_de_n1():
    """Requisito: `anterior_processado` com os estornos do recorte em N−1"""
    fonte = _fonte_bf()
    escolhas = {chave: {"origem": MANUAL, "valores": {}} for chave in ("ug:3", "ug:4")}
    ug1 = _bf(fonte, _bf_n1(fonte), escolhas=escolhas).recortes["ug:1"].resultado

    assert ug1.procedencia.anterior_processado["estorno_receita_extra"] == {"2024": "2.00"}
    assert ug1.procedencia.estorno_receita_extra == {"2025": "10.00"}     # o de N, só


def test_bf_unidade_ausente_em_n1_exige_manual():
    """Scenario: UG sem MSC no ano anterior — BF"""
    fonte = _fonte_bf()
    with pytest.raises(ProcessadoSemAnterior, match="Processe 2024 ou use Manual"):
        _bf(fonte, _bf_n1(fonte))


def test_bf_consolidado_e_a_soma_das_unidades():
    """Scenario: consolidado pela soma dos POs/UGs — BF, sem origem própria"""
    fonte = _fonte_bf()
    repo = _bf_n1(fonte)
    escolhas = {chave: {"origem": MANUAL, "valores": {}} for chave in ("ug:3", "ug:4")}
    r = _bf(fonte, repo, escolhas=escolhas,
            anterior=PROCESSADO)      # pedido ignorado: o topo nunca tem origem

    linha = next(i.id for i in r.mapa.linhas if i.quadro == PRINCIPAL and i.codigo == "L27")
    assert r.matriz[linha][ANTERIOR] is None
    assert r.procedencia.origem_exercicio_anterior == "soma_das_unidades"


def test_bf_grupo_somado_e_igual_ao_grupo_filtrado_em_msce():
    """Scenario: aditividade — BF"""
    from app.services.bf.quadro_principal import apurar

    fonte = _fonte_bf()
    r = _bf(fonte)
    esperado = apurar(2611606, EXERCICIO, apuracao._Filtrada(fonte, {"ug:1", "ug:3"}),
                      g8_so_no_consolidado=True)

    assert r.recortes["poder:executivo"].resultado.matriz == esperado.matriz


def test_bf_origem_manual_por_unidade():
    """Scenario: manual de uma UG participa do consolidado"""
    escolhas = {"ug:3": {"origem": MANUAL, "valores": {"L27": "5.00"}}}
    r = _bf(_fonte_bf(), escolhas=escolhas, agora=("ug:3",))
    ug3 = r.recortes["ug:3"].resultado

    assert _cel(ug3, "L27") == D("5.00")
    assert ug3.procedencia.valores_anteriores == {"L27": "5.00"}
    assert ug3.procedencia.escolha_anterior == escolhas["ug:3"]
    linha = next(i.id for i in r.mapa.linhas if i.quadro == PRINCIPAL and i.codigo == "L27")
    soma = sum((u.resultado.matriz[linha][ANTERIOR] for u in r.recortes.values()
               if u.tipo in ("ug", "po")), D("0.00"))
    assert r.matriz[linha][ANTERIOR] == soma
    assert r.procedencia.escolha_anterior is None


def test_celula_nao_apurada_na_unidade_deixa_a_fonte_e_o_total_do_grupo_nao_apurados():
    """Scenario: não apurada na unidade, não apurada no grupo (Superávit)"""
    po = {"1": "10131", "4": "10131"}
    n = _fonte_ano({"1": "100.00", "4": "40.00"}, {("4", "1700"): "5.00"}, po=po)
    n1 = _fonte_ano({"1": "70.00", "4": "30.00"}, po=po)
    escolhas = {"ug:4": {"origem": MANUAL, "valores": {"P:L3": "11.00"}}}
    r = _bp(_fonte(n, n1), _cache(_n1(n1)), escolhas=escolhas, agora=("ug:4",))

    ug4 = r.recortes["ug:4"].resultado
    assert _cel(ug4, "1700", ANTERIOR, SUPERAVIT) is None
    assert _cel(ug4, "Total", ANTERIOR, SUPERAVIT) is None
    executivo = r.recortes["poder:executivo"].resultado
    assert _cel(executivo, "1700", ANTERIOR, SUPERAVIT) is None
    assert _cel(executivo, "Total", ANTERIOR, SUPERAVIT) is None


def test_fonte_ausente_na_unidade_continua_contando_zero_no_grupo():
    po = {"1": "10131", "4": "10131"}
    n = _fonte_ano({"1": "100.00", "4": "40.00"}, {("4", "1700"): "5.00"}, po=po)
    n1 = _fonte_ano({"1": "70.00", "4": "30.00"}, {("1", "1500"): "7.00"}, po=po)
    r = _bp(_fonte(n, n1), _cache(_n1(n1)))

    executivo = r.recortes["poder:executivo"].resultado
    assert _cel(executivo, "1700", ANTERIOR, SUPERAVIT) == D("0.00")
    assert _cel(executivo, "Total", ANTERIOR, SUPERAVIT) == D("7.00")
