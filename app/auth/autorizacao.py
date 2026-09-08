"""JWT verificado localmente e autorização por unidade. Herdado de RREO/RGF sem exceção.

`SECRET_KEY` é a **do hub**: o token é emitido lá e verificado aqui em `HS256`. Chave própria não
validaria token do hub, e toda rota daria `401`.

A verificação do token entra por parâmetro (`verificar`). Duas consequências: o teste roda sem
`jose` e sem `SECRET_KEY`, e a unidade é confrontada **com o token** — aceitar `X-Unidade-Id` sem
confronto deixaria qualquer autenticado ler qualquer ente (OWASP A01).
"""
from __future__ import annotations

import logging
from collections.abc import Callable

from app.core.config import config

logger = logging.getLogger(__name__)

# Credencial de fonte de dados não vem de browser. Herdado de RREO/RGF.
CABECALHOS_DE_FONTE = ("x-authorization", "token_ps")


class NaoAutenticado(PermissionError):
    """Sem JWT válido — `401`. Nenhum job é criado."""


class NaoAutorizado(PermissionError):
    """Autenticado, mas para outra unidade — `403`. Nenhum dado do ente é devolvido."""


class CredencialDeFonteRecusada(PermissionError):
    """Cabeçalho de credencial de fonte na requisição — recusado, e não usado."""


def verificar_jwt(token: str) -> dict | None:
    """Verificação real, com a chave do hub. `None` = inválido ou expirado."""
    from jose import JWTError, jwt

    cfg = config()
    cfg.exigir("secret_key")
    try:
        return jwt.decode(token, cfg.secret_key, algorithms=[cfg.algoritmo])
    except JWTError as erro:
        logger.info("JWT inválido: %s", erro)
        return None


def autorizar(*, token: str | None, unidade: str | None, ente: str,
              verificar: Callable[[str], dict | None] | None = None) -> dict:
    """Devolve os claims quando o requisitante pode ler o ente. Levanta nos dois outros casos."""
    if not token:
        raise NaoAutenticado("requisição sem JWT")

    claims = (verificar or verificar_jwt)(token)
    if not claims:
        raise NaoAutenticado("JWT inválido ou expirado")

    do_token = str(claims.get("unidade") or claims.get("cod_ibge") or "").strip()
    if not do_token:
        raise NaoAutorizado("token sem unidade — não é possível autorizar o ente")

    # A unidade do cabeçalho é conferida contra a do token; a do token é a que decide.
    if unidade and str(unidade).strip() != do_token:
        raise NaoAutorizado(
            f"unidade do cabeçalho ({unidade}) não corresponde à do token ({do_token})"
        )
    if str(ente).strip() != do_token:
        raise NaoAutorizado(f"unidade {do_token} não autorizada para o ente {ente}")

    return {**claims, "unidade": do_token}


def recusar_credencial_de_fonte(cabecalhos: dict) -> None:
    """Recusa credencial de fonte vinda do cliente. Comparação sem caso."""
    presentes = {str(nome).strip().lower() for nome in (cabecalhos or {})}
    achados = sorted(presentes & set(CABECALHOS_DE_FONTE))
    if achados:
        raise CredencialDeFonteRecusada(
            f"credencial de fonte não é aceita na requisição: {', '.join(achados)}"
        )
