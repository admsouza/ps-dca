"""`verificar_jwt` contra token real — a única rota que exercita a biblioteca de JWT.

O resto da suíte injeta `verificar` e nunca toca em `pyjwt`, então uma troca de biblioteca
passaria despercebida. Aqui o token é assinado de verdade: chave certa entra, chave errada e
token expirado saem como `None` (fail closed).
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import jwt
import pytest

from app.auth.autorizacao import verificar_jwt
from app.core.config import config

CHAVE = "chave-de-teste-do-hub"


@pytest.fixture
def _chave(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", CHAVE)
    monkeypatch.setenv("ALGORITHM", "HS256")
    config.cache_clear()
    yield
    config.cache_clear()


def _token(chave: str = CHAVE, *, expira_em: timedelta = timedelta(minutes=5)) -> str:
    agora = datetime.now(tz=UTC)
    return jwt.encode(
        {"unidade": "2505204", "sub": "fulano@ente.gov.br", "exp": agora + expira_em},
        chave,
        algorithm="HS256",
    )


def test_token_valido_devolve_claims(_chave):
    claims = verificar_jwt(_token())
    assert claims is not None
    assert claims["unidade"] == "2505204"


def test_assinatura_de_outra_chave_e_recusada(_chave):
    assert verificar_jwt(_token("chave-de-outro-emissor")) is None


def test_token_expirado_e_recusado(_chave):
    assert verificar_jwt(_token(expira_em=timedelta(minutes=-1))) is None


def test_token_corrompido_e_recusado(_chave):
    assert verificar_jwt("nem-parece-um-jwt") is None
