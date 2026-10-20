"""Módulo `dca` exigido em toda rota de anexo — change `dca-autorizacao-por-unidade-gestora`."""
from __future__ import annotations

from tests.pipeline.conftest import ENTE
from tests.pipeline.test_autorizacao_por_ug import (  # noqa: F401  (fixture `hub`)
    OUTRO_ENTE,
    _chaves,
    _cliente,
    _corpo,
    _ler,
    hub,
)


def test_usuario_sem_o_modulo(hub):  # noqa: F811
    """Scenario: usuário sem o módulo — sem job e sem dado do ente"""
    hub.corpos = {ENTE: _corpo(["consolidado"], [], modulos=("rgf", "importacao"))}
    cliente = _cliente()
    r = _ler(cliente)
    assert r.status_code == 403 and "recortes" not in r.text
    resumo = cliente.get(f"/dca/resumo?anReferencia=2025&id_ente={ENTE}",
                         headers={"Authorization": "Bearer t"})
    assert resumo.status_code == 403


def test_modulos_ausentes_no_hub_negam(hub):  # noqa: F811
    hub.corpos = {ENTE: {"authorized": True, "poderes": ["consolidado"]}}
    assert _ler(_cliente()).status_code == 403


def test_modulo_so_em_outro_ente(hub):  # noqa: F811
    """Scenario: módulo concedido só em outro ente"""
    hub.corpos = {ENTE: _corpo(["consolidado"]),
                  OUTRO_ENTE: _corpo(["consolidado"], modulos=("rgf",))}
    cliente = _cliente(entes=(ENTE, OUTRO_ENTE))
    assert _ler(cliente, ente=ENTE).status_code == 200
    assert _ler(cliente, ente=OUTRO_ENTE).status_code == 403


def test_revogacao_vale_na_requisicao_seguinte(hub):  # noqa: F811
    """Scenario: revogação vale na requisição seguinte, com o mesmo JWT"""
    hub.corpos = {ENTE: _corpo(["consolidado"])}
    cliente = _cliente()
    assert _ler(cliente).status_code == 200
    hub.corpos = {ENTE: _corpo(["consolidado"], modulos=())}
    assert _ler(cliente).status_code == 403


def test_modo_local_sem_hub_continua_liberado(monkeypatch):
    """Requisito: modo local (sem hub, só development/test/local) segue consolidado, sem guard."""
    from app.auth.hub import AutorizadorHub
    from app.routes import dependencias

    monkeypatch.setattr(AutorizadorHub, "configurado", property(lambda self: False))
    monkeypatch.setattr(dependencias, "_claims", lambda token: {"sub": "u@x", "unidade": ENTE})
    monkeypatch.setattr(dependencias, "_autorizar_pelo_token", lambda claims, ente: None)
    r = _ler(_cliente())
    assert r.status_code == 200 and "consolidado" in _chaves(r)
