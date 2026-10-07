"""Visualizar um anexo apurado nunca reprocessa (`pipeline-visualizar-sem-reprocessar`).

A leitura (`ler_ou_enfileirar` sem `forcar`) serve todo cache `ok`, marcado com os motivos de
desatualização. Processar é ação explícita: `reprocessar` (`forcar`) ou percurso.
"""
from __future__ import annotations

from fastapi import Request

from tests.pipeline.conftest import (
    ANEXO,
    ENTE,
    EXERCICIO,
    OUTRA_VERSAO_REGRAS,
    VERSAO_API,
    VERSAO_REGRAS,
    RegistroFake,
)


def _identidade(versao_regras: str, fonte: str) -> str:
    from app.services.pipeline.cache import versao_do_pedido

    return versao_do_pedido(versao_regras, ANEXO, {"fonte": fonte})


def test_visualizar_resultado_desatualizado_nao_processa(pedido, repo, fila):
    """Scenario: visualizar resultado desatualizado não processa"""
    gravado = RegistroFake(ENTE, EXERCICIO, ANEXO, status="ok", resultado={"bf": "10:13"},
                           versao_api="0.0.1",
                           versao_regras=_identidade(OUTRA_VERSAO_REGRAS, "siconfi"))
    repo.gravar(gravado)

    r = pedido(parametros={"fonte": "publicsoft"})

    assert (r.status, r.resultado) == (200, {"bf": "10:13"})
    assert r.motivos_desatualizado == ["versao_api", "versao_regras", "pedido"]
    assert fila.enfileirados == []
    assert repo.obter(ENTE, EXERCICIO, ANEXO).status == "ok", "ver não pode tocar o cache"


def test_so_a_fonte_diferente_e_motivo_pedido(pedido, repo, fila):
    """Requisito: fonte diferente da processada é motivo `pedido`, e só ele."""
    repo.gravar(RegistroFake(ENTE, EXERCICIO, ANEXO, status="ok", resultado={"m": 1},
                             versao_regras=_identidade(VERSAO_REGRAS, "siconfi")))

    assert pedido(parametros={"fonte": "publicsoft"}).motivos_desatualizado == ["pedido"]
    assert pedido(parametros={"fonte": "siconfi"}).motivos_desatualizado == []
    assert fila.enfileirados == []


def test_reprocessar_e_percurso_reapuram_o_desatualizado(pedido, repo, fila, lock, jobs):
    """Scenario: reprocessar e percurso reapuram o desatualizado"""
    from app.services.pipeline.completo import A_APURAR, montar_percurso

    repo.gravar(RegistroFake(ENTE, EXERCICIO, ANEXO, status="ok", resultado={"m": 1},
                             versao_regras=OUTRA_VERSAO_REGRAS))

    percurso = montar_percurso(ente=ENTE, exercicio=EXERCICIO, repo=repo, lock=lock, jobs=jobs,
                               versao_api=VERSAO_API, versao_de_regras=lambda _a: VERSAO_REGRAS)
    assert next(no for no in percurso if no.anexo == ANEXO).estado == A_APURAR

    r = pedido(forcar=True)
    assert r.status == 202 and len(fila.enfileirados) == 1


def test_visualizacao_depois_do_percurso_reconhece_o_cache(pedido, repo, fila):
    """Scenario: visualização depois do percurso reconhece o cache"""
    from app.services.pipeline.cache import versao_do_pedido
    from app.services.pipeline.completo import pedido_do_percurso

    gravada = versao_do_pedido(VERSAO_REGRAS, ANEXO, pedido_do_percurso(None, "siconfi"))
    repo.gravar(RegistroFake(ENTE, EXERCICIO, ANEXO, status="ok", resultado={"m": 1},
                             versao_regras=gravada))

    r = pedido(parametros={"fonte": "siconfi"})       # o que `GET ...&use_siconfi=true` manda
    assert (r.status, r.motivos_desatualizado) == (200, [])
    assert fila.enfileirados == []


def test_corpo_do_200_traz_a_marca(repo, lock, jobs):
    """Requisito: o corpo do `200` traz `desatualizado` e `motivos_desatualizado` no topo."""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.routes import anexos as rotas
    from app.routes.dependencias import repositorio, unidade_autorizada

    repo.gravar(RegistroFake(ENTE, EXERCICIO, ANEXO, status="ok",
                             resultado={"matriz": {"L1": {}}}, versao_api="0.0.1"))

    def autorizada(request: Request) -> str:
        request.state.claims = {"sub": "u@x"}
        return ENTE

    class Fila:
        pendente = None

        def enfileirar(self, *args, **kwargs):
            raise AssertionError("visualizar não pode enfileirar")

    app = FastAPI()
    app.include_router(rotas.router)
    app.dependency_overrides[repositorio] = lambda: repo
    app.dependency_overrides[unidade_autorizada] = autorizada
    app.state.portas = {"fila_async": Fila, "lock": lock, "jobs": jobs, "repo_vigencias": None,
                        "base_url": ""}

    resposta = TestClient(app).get(
        f"/dca/{ANEXO}?anReferencia={EXERCICIO}&id_ente={ENTE}&use_siconfi=true",
        headers={"Authorization": "Bearer t", "X-Unidade-Id": ENTE})

    assert resposta.status_code == 200, resposta.text
    corpo = resposta.json()
    assert corpo["matriz"] == {"L1": {}}
    assert corpo["desatualizado"] is True
    assert "versao_api" in corpo["motivos_desatualizado"]
