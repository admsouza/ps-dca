"""Rota e percurso com a coluna anterior por unidade (`pipeline-anterior-por-recorte`).

Capability `pipeline/anterior-por-recorte`: validação do corpo (`422`), `409` do processado
explícito, consolidado processado e o que o percurso aceita e reaplica.
"""
from __future__ import annotations

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from app.services.pipeline import apuracao
from app.services.pipeline.cache import parametros_efetivos
from app.services.pipeline.completo import pedido_do_percurso
from app.services.pipeline.job import executar
from tests.bp.conftest import FontePorAno
from tests.pipeline.conftest import LockFake, RegistroFake, RepoFake
from tests.recorte.test_anterior_por_recorte import (
    MANUAL,
    MSCE,
    N1,
    PROCESSADO,
    N,
    _bf_n1,
    _fonte_bf,
    _n1,
)

EXERCICIO = 2025
ENTES = {"BF": "2611606", "BP": "2505204", "BO": "2505204"}
HDR = {"Authorization": "Bearer t", "X-Unidade-Id": "x"}


class FilaFake:
    pendente = None

    def __init__(self):
        self.chamadas: list[dict] = []
        self.percursos: list[dict] = []

    def enfileirar(self, ente, exercicio, anexo, job_id, **parametros):
        self.chamadas.append({"ente": ente, "exercicio": exercicio, "anexo": anexo, **parametros})

    def enfileirar_percurso(self, ente, exercicio, job_id, **parametros):
        self.percursos.append(parametros)


@pytest.fixture
def api(monkeypatch, jobs, notificador):
    from app.routes import anexos as rotas
    from app.routes.dependencias import repositorio, unidade_autorizada

    monkeypatch.setattr("app.auth.autorizacao.verificar_jwt",
                        lambda _t: {"sub": "u@x", "unidade": "x"})

    def _montar(repo: RepoFake, anexo: str, poderes: tuple[str, ...] = ("consolidado",)):
        fila = FilaFake()
        app = FastAPI()
        app.include_router(rotas.router)
        app.dependency_overrides[repositorio] = lambda: repo

        def autorizada(request: Request) -> str:
            request.state.poderes = poderes
            return ENTES[anexo]

        app.dependency_overrides[unidade_autorizada] = autorizada
        app.state.portas = {"fila_async": lambda: fila, "lock": LockFake(), "jobs": jobs,
                            "repo_vigencias": None, "base_url": "", "notificador": notificador}
        return TestClient(app, raise_server_exceptions=False), fila

    return _montar


def _n1_de(anexo: str) -> RepoFake:
    if anexo == "BF":
        return _bf_n1(_fonte_bf())
    return RepoFake([_n1(N1)])


def _reprocessar(cliente, anexo: str, corpo: dict, query: str = ""):
    return cliente.post(f"/dca/{anexo}/reprocessar?anReferencia={EXERCICIO}{query}",
                        headers=HDR, json=corpo)


VALIDOS = {"BF": {"L27": "1.00"}, "BP": {"P:L3": "1.00"}}


# ─── 422 ─────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("anexo", ["BF", "BP"])
@pytest.mark.parametrize("escolhas", [
    {"poder:executivo": {"origem": MSCE}},                        # grupo
    {"consolidado": {"origem": MSCE}},
    {"ug": {"origem": MSCE}},                                     # chave que não é unidade
    {"ug:3": {"origem": "publicado_siconfi"}},                    # origem desconhecida
    {"ug:3": {"origem": MANUAL}},                                 # manual sem valores
    {"ug:3": {"origem": MANUAL, "valores": {}}},
    {"ug:3": {"origem": MANUAL, "valores": {"L27": "abc"}}},
])
def test_corpo_invalido_responde_422_sem_job(api, anexo, escolhas):
    """Scenario: chave de grupo — e as demais recusas"""
    cliente, fila = api(RepoFake(), anexo)

    resposta = _reprocessar(cliente, anexo, {"anterior_por_recorte": escolhas})

    assert resposta.status_code == 422
    assert fila.chamadas == []


def test_manual_do_bp_recusa_totalizadora_prefixo_e_codigo(api):
    """Scenario: totalizadora no manual"""
    for valores in ({"P:L2": "1.00"}, {"X:L3": "1.00"}, {"P:L999": "1.00"}, {"S:15": "1.00"},
                    {"S:1999": "1.00"}, {"S:3621": "1.00"}):
        cliente, fila = api(RepoFake(), "BP")
        resposta = _reprocessar(cliente, "BP", {"anterior_por_recorte": {
            "ug:3": {"origem": MANUAL, "valores": valores}}})
        assert resposta.status_code == 422, valores
        assert fila.chamadas == []


def test_manual_do_bp_aceita_fonte_oficial(api):
    """Scenario: fonte oficial é aceita"""
    cliente, fila = api(RepoFake(), "BP")
    valores = {"S:1621": "20000.00"}

    resposta = _reprocessar(cliente, "BP", {"anterior_por_recorte": {
        "ug:3": {"origem": MANUAL, "valores": valores}}})

    assert resposta.status_code == 202, resposta.text
    assert fila.chamadas[0]["anterior_por_recorte"]["ug:3"]["valores"] == valores


def test_manual_do_bf_recusa_codigo_inexistente(api):
    cliente, fila = api(RepoFake(), "BF")

    resposta = _reprocessar(cliente, "BF", {"anterior_por_recorte": {
        "ug:3": {"origem": MANUAL, "valores": {"L999": "1.00"}}}})

    assert resposta.status_code == 422 and fila.chamadas == []


@pytest.mark.parametrize("anexo", ["BF", "BP"])
def test_manual_no_consolidado_e_recusado(api, anexo):
    """Scenario: mapa manual consolidado é recusado — `pipeline-consolidado-anterior-soma-unidades`
    Scenario: mapa manual no topo é recusado"""
    cliente, fila = api(RepoFake(), anexo)

    resposta = _reprocessar(cliente, anexo, {"origem_exercicio_anterior": MANUAL,
                                             "valores_anteriores": VALIDOS[anexo]})

    assert resposta.status_code == 422 and fila.chamadas == []


@pytest.mark.parametrize("anexo", ["BF", "BP"])
def test_origem_propria_no_corpo_e_recusada(api, anexo):
    """Scenario: origem própria no corpo é recusada"""
    cliente, fila = api(RepoFake(), anexo)

    resposta = _reprocessar(cliente, anexo, {"origem_exercicio_anterior": MSCE})

    assert resposta.status_code == 422 and fila.chamadas == []


# ─── 409 ─────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("anexo", ["BF", "BP"])
def test_processado_explicito_sem_n1_responde_409_sem_job(api, anexo):
    """Scenario: processado explícito sem N−1"""
    cliente, fila = api(RepoFake(), anexo)

    resposta = _reprocessar(cliente, anexo, {"anterior_por_recorte": {
        "ug:3": {"origem": PROCESSADO}}})

    assert resposta.status_code == 409
    assert resposta.json()["detail"].startswith("processe 2024 antes")
    assert fila.chamadas == []


def test_processado_explicito_de_unidade_que_n1_nao_tem_responde_409(api):
    cliente, fila = api(_n1_de("BP"), "BP")

    resposta = _reprocessar(cliente, "BP", {"anterior_por_recorte": {
        "ug:99": {"origem": PROCESSADO}}})

    assert resposta.status_code == 409 and fila.chamadas == []


@pytest.mark.parametrize("anexo", ["BF", "BP"])
def test_consolidado_processado_no_corpo_e_recusado(api, anexo):
    """Requisito: origem própria do consolidado não é mais aceita, nem para exigir N−1"""
    cliente, fila = api(RepoFake(), anexo)

    resposta = _reprocessar(cliente, anexo, {"origem_exercicio_anterior": PROCESSADO})

    assert resposta.status_code == 422
    assert fila.chamadas == []


# ─── 202 ─────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("anexo", ["BF", "BP"])
def test_escolhas_validas_chegam_ao_job(api, anexo):
    """Scenario: origens diferentes no mesmo job"""
    cliente, fila = api(_n1_de(anexo), anexo)
    escolhas = {"ug:1": {"origem": PROCESSADO}, "ug:3": {"origem": MSCE},
                "ug:4": {"origem": MANUAL, "valores": VALIDOS[anexo]},
                "ug:99": {"origem": "padrao"}}

    resposta = _reprocessar(cliente, anexo, {"anterior_por_recorte": escolhas})

    assert resposta.status_code == 202
    enviado = fila.chamadas[0]
    assert enviado["anterior_por_recorte"] == {
        "ug:1": {"origem": PROCESSADO}, "ug:3": {"origem": MSCE},
        "ug:4": {"origem": MANUAL, "valores": VALIDOS[anexo]}}
    assert enviado["anterior_agora"] == ["ug:1", "ug:3", "ug:4", "ug:99"]


def test_unidade_inexistente_nao_barra_a_rota(api):
    """Scenario: unidade inexistente — o aviso é do job"""
    cliente, fila = api(RepoFake(), "BP")

    resposta = _reprocessar(cliente, "BP", {"anterior_por_recorte": {"ug:99": {"origem": MSCE}}})

    assert resposta.status_code == 202


@pytest.mark.parametrize("anexo", ["BF", "BP"])
def test_consolidado_na_query_da_leitura_responde_400(api, anexo):
    """Requisito: legado na query responde `400`, como os demais mapas do consolidado"""
    cliente, fila = api(RepoFake(), anexo)

    resposta = cliente.get(
        f"/dca/{anexo}?anReferencia={EXERCICIO}&origem_exercicio_anterior={PROCESSADO}",
        headers=HDR)

    assert resposta.status_code == 400
    assert fila.chamadas == []


def test_leitura_recusa_origem_na_query(api):
    cliente, fila = api(RepoFake(), "BP")

    resposta = cliente.get(f"/dca/BP?anReferencia={EXERCICIO}&origem_exercicio_anterior=x",
                           headers=HDR)

    assert resposta.status_code == 400
    assert fila.chamadas == []


def test_corpo_sem_escolhas_reaplica_as_gravadas(api):
    """Scenario: escolha gravada é reaplicada"""
    gravado = RegistroFake(ENTES["BP"], EXERCICIO, "BP", resultado={"recortes": {
        "ug:3": {"resultado": {"procedencia": {"escolha_anterior": {"origem": MSCE}}}}}})
    cliente, fila = api(RepoFake([gravado]), "BP")

    resposta = _reprocessar(cliente, "BP", {})

    assert resposta.status_code == 202
    assert fila.chamadas[0]["anterior_por_recorte"] == {"ug:3": {"origem": MSCE}}
    assert "anterior_agora" not in fila.chamadas[0]


# ─── percurso ────────────────────────────────────────────────────────────────

def test_percurso_recusa_origem_consolidada_do_bp(api):
    """Requisito: percurso recusa origem consolidada"""
    cliente, fila = api(RepoFake(), "BP")

    resposta = cliente.post(
        f"/batch-jobs?anReferencia={EXERCICIO}&origem_exercicio_anterior={PROCESSADO}",
        headers=HDR)

    assert resposta.status_code == 422
    assert fila.percursos == []


def test_percurso_nao_aceita_anterior_por_recorte(api):
    """Requisito: `/batch-jobs` NÃO aceita `anterior_por_recorte`"""
    cliente, fila = api(RepoFake(), "BP")

    resposta = cliente.post(f"/batch-jobs?anReferencia={EXERCICIO}", headers=HDR,
                            json={"anterior_por_recorte": {"ug:1": {"origem": MSCE}}})

    assert resposta.status_code == 202
    assert set(fila.percursos[0]) == {"fonte", "forcar", "solicitado_por", "solicitante_email"}


def test_percurso_reaplica_as_escolhas_gravadas():
    """Scenario: escolha gravada é reaplicada — pelo percurso
    Scenario: percurso soma as escolhas gravadas"""
    gravado = RegistroFake(ENTES["BP"], EXERCICIO, "BP", resultado={"recortes": {
        "ug:3": {"resultado": {"procedencia": {
            "escolha_anterior": {"origem": MANUAL, "valores": {"P:L3": "1.00"}}}}}}})

    pedido = pedido_do_percurso(gravado, "publicsoft", "BP")

    assert pedido["anterior_por_recorte"] == {"ug:3": {"origem": MANUAL,
                                                       "valores": {"P:L3": "1.00"}}}
    assert "anterior_agora" not in pedido


# ─── job ─────────────────────────────────────────────────────────────────────

def test_n1_some_entre_a_rota_e_o_job_termina_em_erro(monkeypatch):
    """Scenario: N−1 some entre a rota e o job"""
    monkeypatch.setattr(apuracao, "fonte", lambda nome=None, token=None: FontePorAno(
        {EXERCICIO: N, EXERCICIO - 1: N1}))
    repo = RepoFake()
    parametros = parametros_efetivos(
        {"origem_anterior": MSCE, "anterior_por_recorte": {"ug:1": {"origem": PROCESSADO}}},
        None, "BP")

    executar(ente=ENTES["BP"], exercicio=EXERCICIO, anexo="BP", repo=repo, lock=LockFake(),
             apurador=apuracao.apurador("BP", fonte_nome="fake", repo=repo, parametros=parametros),
             versao_api=apuracao.VERSAO_API, versao_regras="r")

    gravado = repo.obter(ENTES["BP"], EXERCICIO, "BP")
    assert gravado.status == "erro" and gravado.resultado is None
    assert "processe 2024 antes" in gravado.erro_detalhe


@pytest.mark.parametrize("anexo", ["BF", "BP"])
def test_processado_na_query_do_reprocessar_responde_400(api, anexo):
    cliente, fila = api(RepoFake(), anexo)

    resposta = cliente.post(
        f"/dca/{anexo}/reprocessar?anReferencia={EXERCICIO}&origem_exercicio_anterior={PROCESSADO}",
        headers=HDR)

    assert resposta.status_code == 400
    assert fila.chamadas == []


def test_anterior_por_recorte_em_anexo_sem_recortes_por_unidade_responde_422(api):
    cliente, fila = api(RepoFake(), "BO")

    resposta = _reprocessar(cliente, "BO", {"anterior_por_recorte": {"ug:3": {"origem": MSCE}}})

    assert resposta.status_code == 422
    assert fila.chamadas == []


@pytest.mark.parametrize("anexo", ["BF", "BP"])
@pytest.mark.parametrize("valor", ["1E+999999999", "NaN", "Infinity", "-1E+20"])
def test_manual_recusa_valor_nao_finito_ou_fora_de_escala(api, anexo, valor):
    chave = next(iter(VALIDOS[anexo]))
    cliente, fila = api(RepoFake(), anexo)

    resposta = _reprocessar(cliente, anexo, {"anterior_por_recorte": {
        "ug:3": {"origem": MANUAL, "valores": {chave: valor}}}})

    assert resposta.status_code == 422
    assert fila.chamadas == []


# ─── autorização por poder (`pipeline-anterior-autorizacao-por-poder`) ───────

PREFEITURA, CAMARA = "ug:10", "ug:20"
MANUAL_BP = {"origem": MANUAL, "valores": {"P:L3": "1.00"}}


def _cache_com_unidades(ano: int = EXERCICIO) -> RepoFake:
    return RepoFake([RegistroFake(ENTES["BP"], ano, "BP", resultado={"recortes": {
        PREFEITURA: {"poderOrgao": "10131", "rotulo": "Prefeitura", "resultado": {}},
        CAMARA: {"poderOrgao": "20231", "rotulo": "Câmara", "resultado": {}}}})])


def _sem_efeito(repo: RepoFake, fila: FilaFake) -> None:
    assert fila.chamadas == [] and repo.gravacoes == []


def test_unidade_do_proprio_poder(api):
    """Scenario: Unidade do próprio poder"""
    repo = _cache_com_unidades()
    cliente, fila = api(repo, "BP", ("executivo",))

    resposta = _reprocessar(cliente, "BP", {"anterior_por_recorte": {PREFEITURA: {"origem": MSCE}}})

    assert resposta.status_code == 202
    assert fila.chamadas[0]["anterior_por_recorte"] == {PREFEITURA: {"origem": MSCE}}


def test_unidade_de_outro_poder(api):
    """Scenario: Unidade de outro poder"""
    repo = _cache_com_unidades()
    cliente, fila = api(repo, "BP", ("executivo",))

    resposta = _reprocessar(cliente, "BP", {"anterior_por_recorte": {CAMARA: MANUAL_BP}})

    assert resposta.status_code == 403
    assert resposta.json()["detail"] == f"sem acesso à unidade {CAMARA}"
    _sem_efeito(repo, fila)


def test_pedido_misto_e_tudo_ou_nada(api):
    """Scenario: Pedido misto é tudo ou nada"""
    repo = _cache_com_unidades()
    cliente, fila = api(repo, "BP", ("executivo",))

    resposta = _reprocessar(cliente, "BP", {"anterior_por_recorte": {
        PREFEITURA: {"origem": MSCE}, CAMARA: {"origem": MSCE}}})

    assert resposta.status_code == 403
    _sem_efeito(repo, fila)


def test_poder_orgao_pelo_codigo(api):
    """Scenario: Poder/Órgão pelo código"""
    repo = _cache_com_unidades()
    cliente, fila = api(repo, "BP", ("executivo",))

    resposta = _reprocessar(cliente, "BP", {"anterior_por_recorte": {"po:20231": {"origem": MSCE}}})

    assert resposta.status_code == 403
    _sem_efeito(repo, fila)


def test_po_do_proprio_poder_passa(api):
    """Requisito: `po:` resolve pelo próprio código"""
    cliente, fila = api(_cache_com_unidades(), "BP", ("executivo",))

    resposta = _reprocessar(cliente, "BP", {"anterior_por_recorte": {"po:10131": {"origem": MSCE}}})

    assert resposta.status_code == 202


def test_consolidado_escolhe_qualquer_unidade(api):
    """Scenario: Consolidado escolhe qualquer unidade"""
    cliente, fila = api(_cache_com_unidades(), "BP", ("consolidado",))

    resposta = _reprocessar(cliente, "BP", {"anterior_por_recorte": {
        CAMARA: MANUAL_BP, "ug:999": {"origem": MSCE}}})

    assert resposta.status_code == 202
    assert set(fila.chamadas[0]["anterior_por_recorte"]) == {CAMARA, "ug:999"}


def test_ug_desconhecida(api):
    """Scenario: UG desconhecida"""
    repo = _cache_com_unidades()
    cliente, fila = api(repo, "BP", ("executivo",))

    resposta = _reprocessar(cliente, "BP", {"anterior_por_recorte": {"ug:999": {"origem": MSCE}}})

    assert resposta.status_code == 403
    _sem_efeito(repo, fila)


def test_unidade_resolvida_pelo_cache_de_n1(api):
    """Requisito: `ug:` sem poder no cache de N usa o de N−1"""
    cliente, fila = api(_cache_com_unidades(EXERCICIO - 1), "BP", ("executivo",))

    ok = _reprocessar(cliente, "BP", {"anterior_por_recorte": {PREFEITURA: {"origem": MSCE}}})
    negado = _reprocessar(cliente, "BP", {"anterior_por_recorte": {CAMARA: {"origem": MSCE}}})

    assert (ok.status_code, negado.status_code) == (202, 403)


@pytest.mark.parametrize("anexo", ["BF", "BP"])
@pytest.mark.parametrize("poderes", [(), ("judiciario",)])
def test_sem_poder_util_recusa_qualquer_escolha(api, anexo, poderes):
    """Requisito: sem `poderes` no estado, todo `anterior_por_recorte` recebe `403`"""
    repo = RepoFake()
    cliente, fila = api(repo, anexo, poderes)

    resposta = _reprocessar(cliente, anexo, {"anterior_por_recorte": {"ug:3": {"origem": MSCE}}})

    assert resposta.status_code == 403
    _sem_efeito(repo, fila)


def test_formato_invalido_vem_antes_do_poder(api):
    """Requisito: a validação de formato (`422`) vem antes da de poder"""
    cliente, fila = api(_cache_com_unidades(), "BP", ("executivo",))

    resposta = _reprocessar(cliente, "BP", {"anterior_por_recorte": {
        CAMARA: {"origem": MANUAL}}})

    assert resposta.status_code == 422 and fila.chamadas == []


@pytest.mark.parametrize("status", ["erro", "processando"])
def test_cache_nao_ok_nao_resolve_poder(api, status):
    """Requisito: só resultado `ok` resolve o poder da `ug:`; senão só `consolidado` passa."""
    unidades = {PREFEITURA: {"poderOrgao": "10131", "rotulo": "Prefeitura", "resultado": {}}}
    repo = RepoFake([RegistroFake(ENTES["BP"], EXERCICIO, "BP", status=status,
                                  resultado={"recortes": unidades})])
    cliente, fila = api(repo, "BP", ("executivo",))

    resposta = _reprocessar(cliente, "BP", {"anterior_por_recorte": {PREFEITURA: {"origem": MSCE}}})

    assert resposta.status_code == 403
    _sem_efeito(repo, fila)
