"""Percurso completo: todos os anexos implementados num job só.

Fakes do `conftest` do pipeline — nada de Redis, Postgres ou rede. O que estes testes protegem é a
equivalência entre o percurso e as rotas por anexo: o mesmo `job.executar`, o mesmo lock, o mesmo
cache. Um percurso que divergisse do individual seria descoberto em produção, num anexo só, e
justamente quando algo falhasse.
"""
from __future__ import annotations

import pytest

from tests.pipeline.conftest import ENTE, EXERCICIO, VERSAO_API, VERSAO_REGRAS, RegistroFake

BO, BF = "BO", "BF"
HDR = {"Authorization": "Bearer t", "X-Unidade-Id": ENTE}


@pytest.fixture
def cliente(repo, lock, jobs, monkeypatch):
    """A rota do percurso com as portas fakes ligadas — mesmo molde de `test_rota_bf`."""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.routes import anexos as rotas
    from app.routes.dependencias import repositorio, unidade_autorizada

    monkeypatch.setattr("app.auth.autorizacao.verificar_jwt",
                        lambda _t: {"sub": "u@x", "unidade": ENTE})

    class FilaFake:
        """Mesma forma do adapter async: `enfileirar_percurso` só agenda; a rota aguarda."""

        pendente = None

        def enfileirar_percurso(self, ente, exercicio, job_id, **_):
            self.enfileirados = [(ente, exercicio, job_id)]

    def _montar(fila_cls=FilaFake):
        app = FastAPI()
        app.include_router(rotas.router)
        app.dependency_overrides[repositorio] = lambda: repo
        app.dependency_overrides[unidade_autorizada] = lambda: ENTE
        app.state.portas = {"fila_async": fila_cls, "lock": lock, "jobs": jobs,
                            "repo_vigencias": None, "base_url": ""}
        return TestClient(app, raise_server_exceptions=False)

    return _montar


@pytest.fixture
def versao_de():
    """Versão vigente por anexo — a mesma para todos, no caso feliz."""
    return lambda anexo: VERSAO_REGRAS


@pytest.fixture
def montar():
    from app.services.pipeline.completo import montar_percurso
    return montar_percurso


@pytest.fixture
def executar():
    from app.services.pipeline.completo import executar_percurso
    return executar_percurso


def _apurador_de(resultados: dict[str, object]):
    """Apurador por anexo: devolve o resultado combinado, ou levanta o que o teste pediu."""
    def _de(anexo: str):
        def _apurar(ente: int, exercicio: int):
            alvo = resultados[anexo]
            if isinstance(alvo, Exception):
                raise alvo
            return alvo
        return _apurar
    return _de


class ResultadoFake:
    """O que o serviço de um anexo devolve — só o que o serializador do pipeline consome."""

    def __init__(self, anexo: str):
        self.anexo = anexo
        self.matriz = {"L1": {"C1": 1}}
        self.procedencia = {"versao_regras": VERSAO_REGRAS, "documento": "IPC", "edicao": "2024"}
        self.diagnostico = {"nao_apuradas": [], "residuos": [], "duracao_ms": 1, "sem_dados": False}


@pytest.fixture(autouse=True)
def _serializador_simples(monkeypatch):
    """`para_dados` do pipeline sobre o `ResultadoFake`, sem arrastar o modelo do BO/BF."""
    def _para_dados(resultado):
        return {"matriz": resultado.matriz, "procedencia": resultado.procedencia,
                "diagnostico": resultado.diagnostico}

    monkeypatch.setattr("app.services.pipeline.job.para_dados", _para_dados)


# ─── Requirement: Uma chamada apura todos os anexos implementados ────────────

def test_um_job_para_todos_os_anexos(repo, lock, jobs, montar, versao_de):
    """Scenario: um job para todos os anexos."""
    percurso = montar(ente=ENTE, exercicio=EXERCICIO, repo=repo, lock=lock, jobs=jobs,
                      versao_api=VERSAO_API, versao_de_regras=versao_de)

    por_anexo = {no.anexo: no.estado for no in percurso}
    assert por_anexo[BO] == "a_apurar"
    assert por_anexo[BF] == "a_apurar"
    assert por_anexo["I-C"] == "nao_implementado"


def test_rota_do_percurso_aceita_e_devolve_o_identificador(cliente):
    """Requisito: a rota do percurso enfileira um job e devolve o identificador a acompanhar."""
    resposta = cliente().post(f"/batch-jobs?anReferencia={EXERCICIO}", headers=HDR)

    assert resposta.status_code == 202
    corpo = resposta.json()
    assert corpo["batch_job_id"]
    assert corpo["poll_url"].endswith(corpo["batch_job_id"])
    assert {a["anexo"] for a in corpo["anexos"] if a["estado"] == "a_apurar"} == {BO, BF}


def test_nenhum_anexo_implementado(cliente, monkeypatch):
    """Scenario: nenhum anexo implementado."""
    from app.services.pipeline import registry

    sem_servico = tuple(type(a)(a.codigo, None, a.job, a.base_canonica) for a in registry.REGISTRY)
    monkeypatch.setattr(registry, "REGISTRY", sem_servico)

    resposta = cliente().post(f"/batch-jobs?anReferencia={EXERCICIO}", headers=HDR)

    assert resposta.status_code == 422
    assert resposta.json()["detail"]


def test_exercicio_ausente_ou_invalido(cliente):
    """Scenario: exercício ausente ou inválido."""
    assert cliente().post("/batch-jobs", headers=HDR).status_code == 422
    assert cliente().post("/batch-jobs?anReferencia=1500", headers=HDR).status_code == 422


def test_fila_indisponivel_nao_deixa_o_job_em_processing(cliente, jobs):
    """Caso de erro: fila indisponível no enfileiramento.

    O estado do percurso é gravado antes do enfileiramento. Se a fila recusar, o job tem de
    terminar em `error` — `processing` faria o cliente acompanhar um job que ninguém executa.
    """

    class FilaQueRecusa:
        def enfileirar_percurso(self, ente, exercicio, job_id, **_):
            async def recusada():
                raise ConnectionError("redis recusou")

            self.pendente = recusada()

    resposta = cliente(FilaQueRecusa).post(f"/batch-jobs?anReferencia={EXERCICIO}", headers=HDR)

    assert resposta.status_code == 503
    assert jobs.registros, "o percurso foi registrado antes da fila recusar"
    estado = next(iter(jobs.registros.values()))
    assert estado["status"] == "error"
    assert "fila" in (estado.get("erro") or "").lower()


# ─── Requirement: Cache válido é respeitado; reprocessar ignora ──────────────

def test_anexo_ja_apurado_nao_e_reapurado(repo, lock, jobs, montar, versao_de):
    """Scenario: anexo já apurado não é reapurado."""
    repo.gravar(RegistroFake(ENTE, EXERCICIO, BO, status="ok", resultado={"matriz": {}},
                             calculado_em="2026-09-20T10:00:00Z"))

    percurso = montar(ente=ENTE, exercicio=EXERCICIO, repo=repo, lock=lock, jobs=jobs,
                      versao_api=VERSAO_API, versao_de_regras=versao_de)
    por_anexo = {no.anexo: no for no in percurso}

    assert por_anexo[BO].estado == "em_cache"
    assert por_anexo[BO].calculado_em == "2026-09-20T10:00:00Z"
    assert por_anexo[BF].estado == "a_apurar"


def test_reprocessamento_completo_reapura_tudo(repo, lock, jobs, montar, executar, versao_de):
    """Scenario: reprocessamento completo reapura tudo."""
    anterior = {"matriz": {"L1": {"C1": 0}}}
    for anexo in (BO, BF):
        repo.gravar(RegistroFake(ENTE, EXERCICIO, anexo, status="ok", resultado=anterior))

    percurso = montar(ente=ENTE, exercicio=EXERCICIO, repo=repo, lock=lock, jobs=jobs,
                      versao_api=VERSAO_API, versao_de_regras=versao_de, forcar=True)
    assert [no.estado for no in percurso if no.anexo in (BO, BF)] == ["a_apurar", "a_apurar"]

    # Durante a reapuração o resultado anterior continua legível — o requisito proíbe a janela
    # em que o ente vê o anexo vazio.
    assert repo.obter(ENTE, EXERCICIO, BO).resultado == anterior

    executar(ente=ENTE, exercicio=EXERCICIO, percurso=percurso, repo=repo, lock=lock, jobs=jobs,
             job_id="batch-1", apurador_de=_apurador_de({BO: ResultadoFake(BO),
                                                         BF: ResultadoFake(BF)}),
             versao_api=VERSAO_API, versao_de_regras=versao_de, solicitado_por=77)

    for anexo in (BO, BF):
        registro = repo.obter(ENTE, EXERCICIO, anexo)
        assert registro.status == "ok"
        assert registro.resultado != anterior, f"{anexo} não foi reapurado"
        assert registro.solicitado_por == 77


# ─── Requirement: Falha de um anexo não interrompe o percurso ────────────────

def test_um_anexo_falha_e_os_demais_concluem(repo, lock, jobs, montar, executar, versao_de):
    """Scenario: um anexo falha e os demais concluem."""
    percurso = montar(ente=ENTE, exercicio=EXERCICIO, repo=repo, lock=lock, jobs=jobs,
                      versao_api=VERSAO_API, versao_de_regras=versao_de)

    desfecho = executar(
        ente=ENTE, exercicio=EXERCICIO, percurso=percurso, repo=repo, lock=lock, jobs=jobs,
        job_id="batch-1", versao_api=VERSAO_API, versao_de_regras=versao_de,
        apurador_de=_apurador_de({BO: ResultadoFake(BO), BF: RuntimeError("fonte fora do ar")}),
    )

    assert repo.obter(ENTE, EXERCICIO, BO).status == "ok"
    assert repo.obter(ENTE, EXERCICIO, BF).status == "erro"
    assert "fonte fora do ar" in repo.obter(ENTE, EXERCICIO, BF).erro_detalhe

    assert desfecho["status"] == "done", "status terminal fora do conjunto que o front encerra"
    assert desfecho["falhas"] == 1
    assert [a["anexo"] for a in desfecho["anexos"] if a["status"] == "erro"] == [BF]
    assert lock.tomados == {}, "lock retido depois do percurso"


def test_todos_os_anexos_falham(repo, lock, jobs, montar, executar, versao_de):
    """Scenario: todos os anexos falham."""
    percurso = montar(ente=ENTE, exercicio=EXERCICIO, repo=repo, lock=lock, jobs=jobs,
                      versao_api=VERSAO_API, versao_de_regras=versao_de)

    desfecho = executar(
        ente=ENTE, exercicio=EXERCICIO, percurso=percurso, repo=repo, lock=lock, jobs=jobs,
        job_id="batch-1", versao_api=VERSAO_API, versao_de_regras=versao_de,
        apurador_de=_apurador_de({BO: RuntimeError("falhou BO"), BF: RuntimeError("falhou BF")}),
    )

    assert desfecho["status"] == "error"
    assert desfecho["falhas"] == 2
    assert all(r.status == "erro" for r in repo.listar(ENTE, EXERCICIO))


# ─── Requirement: Anexo com job em voo não é apurado duas vezes ──────────────

def test_anexo_ja_em_andamento_e_pulado(repo, lock, jobs, montar, executar, versao_de):
    """Scenario: anexo já em andamento é pulado."""
    from app.infra.fila import job_manager

    job_manager.criar(jobs, "job-bf-vivo", ente=ENTE, exercicio=EXERCICIO, anexo=BF)
    lock.adquirir(ENTE, EXERCICIO, BF, "job-bf-vivo")

    percurso = montar(ente=ENTE, exercicio=EXERCICIO, repo=repo, lock=lock, jobs=jobs,
                      versao_api=VERSAO_API, versao_de_regras=versao_de)
    em_voo = next(no for no in percurso if no.anexo == BF)
    assert em_voo.estado == "already_queued"
    assert em_voo.job_id == "job-bf-vivo"

    apurados = []

    def apurador_de(anexo):
        def _apurar(ente, exercicio):
            apurados.append(anexo)
            return ResultadoFake(anexo)
        return _apurar

    desfecho = executar(ente=ENTE, exercicio=EXERCICIO, percurso=percurso, repo=repo, lock=lock,
                        jobs=jobs, job_id="batch-1", apurador_de=apurador_de,
                        versao_api=VERSAO_API, versao_de_regras=versao_de)

    assert apurados == [BO], "o anexo em voo foi apurado de novo"
    assert repo.obter(ENTE, EXERCICIO, BF) is None
    assert [a["status"] for a in desfecho["anexos"] if a["anexo"] == BF] == ["already_queued"]
    assert lock.dono(ENTE, EXERCICIO, BF) == "job-bf-vivo", "lock alheio foi liberado"


# ─── Requirement: Leitura da MSC é paga uma vez por percurso ─────────────────

def test_anexos_que_leem_a_mesma_classe_consultam_a_fonte_uma_vez():
    """Scenario: anexos que leem a mesma classe consultam a fonte uma vez.

    O BO lê as classes 5 e 6 da mesma matriz que o BF já lê. Em jobs separados são 20 consultas
    (2 + 18); no percurso, com uma memória de execução só, são 18 — e nenhuma delas sobrevive ao
    job.
    """
    from app.infra.msc.escopo import escopo
    from app.services.pipeline.apuracao import _NoEscopo

    class FonteContada:
        def __init__(self):
            self.consultas = []

        def registros(self, ente, ano, mes, classe, matriz=None, tipo_saldo=None):
            self.consultas.append((ente, ano, mes, classe, matriz, tipo_saldo))
            return []

    def ler_como_o_bo(fonte):
        from app.infra.msc.fonte import fonte_de

        origem = fonte_de("BO")
        for classe in origem.classes:
            fonte.registros(1, EXERCICIO, 12, classe, matriz=origem.matriz,
                            tipo_saldo=origem.tipo_saldo)

    def ler_como_o_bf(fonte):
        from app.infra.msc.fonte import TipoSaldo, fonte_de

        origem = fonte_de("BF")
        for tipo_saldo, ano in ((origem.tipo_saldo, EXERCICIO),
                                (TipoSaldo.ENCERRAMENTO, EXERCICIO),
                                (origem.tipo_saldo, EXERCICIO - 1)):
            for classe in origem.classes:
                fonte.registros(1, ano, 12, classe, matriz=origem.matriz, tipo_saldo=tipo_saldo)

    separados = FonteContada()
    with escopo():
        ler_como_o_bo(_NoEscopo(separados, "siconfi"))
    with escopo():
        ler_como_o_bf(_NoEscopo(separados, "siconfi"))
    assert len(separados.consultas) == 20

    percurso = FonteContada()
    envelope = _NoEscopo(percurso, "siconfi")
    with escopo():
        ler_como_o_bo(envelope)
        ler_como_o_bf(envelope)
    assert len(percurso.consultas) == 18


# ─── Requirement: Progresso do percurso é acompanhável ──────────────────────

def test_progresso_e_legivel_durante_a_execucao(repo, lock, jobs, montar, executar, versao_de):
    """Scenario: progresso é legível durante a execução."""
    from app.infra.fila import job_manager

    percurso = montar(ente=ENTE, exercicio=EXERCICIO, repo=repo, lock=lock, jobs=jobs,
                      versao_api=VERSAO_API, versao_de_regras=versao_de)

    vistos = []

    def apurador_de(anexo):
        def _apurar(ente, exercicio):
            vistos.append(dict(job_manager.estado(jobs, "batch-1")))
            return ResultadoFake(anexo)
        return _apurar

    executar(ente=ENTE, exercicio=EXERCICIO, percurso=percurso, repo=repo, lock=lock, jobs=jobs,
             job_id="batch-1", apurador_de=apurador_de, versao_api=VERSAO_API,
             versao_de_regras=versao_de)

    # Estado visto pelo segundo anexo: o primeiro já concluiu, e o desfecho dele já aparece.
    durante_o_segundo = vistos[1]
    assert durante_o_segundo["progresso"] == {"concluidos": 1, "total": 2}
    assert durante_o_segundo["status"] == "processing"
    assert [a["anexo"] for a in durante_o_segundo["anexos"] if a["status"] == "ok"] == [BO]


def test_conclusao_do_percurso_e_notificada_uma_vez(repo, lock, jobs, montar, executar,
                                                    versao_de, notificador):
    """Scenario: conclusão do percurso é notificada uma vez."""
    percurso = montar(ente=ENTE, exercicio=EXERCICIO, repo=repo, lock=lock, jobs=jobs,
                      versao_api=VERSAO_API, versao_de_regras=versao_de)

    executar(ente=ENTE, exercicio=EXERCICIO, percurso=percurso, repo=repo, lock=lock, jobs=jobs,
             job_id="batch-1", versao_api=VERSAO_API, versao_de_regras=versao_de,
             apurador_de=_apurador_de({BO: ResultadoFake(BO), BF: RuntimeError("falhou")}),
             notificador=notificador)

    assert len(notificador.enviadas) == 1, "uma notificação por anexo faria oito num percurso"
    mensagem = notificador.enviadas[0]
    assert mensagem["ente"] == ENTE
    assert mensagem["falhas"] == 1
    assert {a["anexo"] for a in mensagem["anexos"]} == {BO, BF}
    assert mensagem["duracao_ms"] >= 0
