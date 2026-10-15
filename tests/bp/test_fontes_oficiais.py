from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routes.anexos import router
from app.services.bp.fontes import fonte_oficial, fontes_oficiais, rotulo_fonte


def test_catalogo_deriva_duas_opcoes_por_codigo_principal():
    """Scenario: catálogo deriva duas opções por código principal."""
    fontes = fontes_oficiais()
    codigos = [fonte.codigo for fonte in fontes]

    assert codigos == sorted(codigos)
    assert len(codigos) == len(set(codigos))
    assert fonte_oficial("1621")
    assert fonte_oficial("2621")
    assert rotulo_fonte("1621") == (
        "Transferências Fundo a Fundo de Recursos do SUS provenientes do Governo Estadual"
    )
    assert rotulo_fonte("2621").endswith(" - Exercícios Anteriores")


def test_catalogo_nao_possui_codigos_arbitrarios():
    """Scenario: catálogo não possui códigos arbitrários."""
    codigos = {fonte.codigo for fonte in fontes_oficiais()}

    assert "1999" not in codigos
    assert "2999" not in codigos
    assert not fonte_oficial("3621")


def test_rota_do_catalogo_exige_autenticacao(monkeypatch):
    """Scenario: catálogo exige autenticação."""
    app = FastAPI()
    app.include_router(router)
    cliente = TestClient(app, raise_server_exceptions=False)

    sem_token = cliente.get("/dca/fontes-recursos")

    assert sem_token.status_code == 401

    monkeypatch.setattr(
        "app.auth.autorizacao.verificar_jwt",
        lambda _token: {"sub": "usuario@exemplo.com"},
    )
    resposta = cliente.get(
        "/dca/fontes-recursos",
        headers={"Authorization": "Bearer token-valido"},
    )

    assert resposta.status_code == 200
    assert resposta.json()["fontes"] == [
        {"codigo": fonte.codigo, "nome": fonte.nome} for fonte in fontes_oficiais()
    ]