"""Dependências das rotas: autorização, sessão, portas de infra.

A rota não constrói nada disso — recebe pronto e passa ao service. É o que a mantém fina e o
service testável com fakes.

**O contrato de entrada é o dos irmãos**, de propósito: `id_ente` como query param, `Authorization:
Bearer <jwt>` e `X-Unidade-Id` conferido contra `id_ente`
(`regras-rgf-api/app/auth/rgf_dependencies.py`). Um frontend que já fala com RREO/RGF não muda nada
para falar com a DCA.

A autorização por unidade é confirmada **no hub**, não lida de um claim: quem pode ler qual ente é
dado de banco, e um usuário ganha ou perde unidade sem reemitir JWT. Sem hub configurado, cai para
o claim de unidade do próprio token — modo de desenvolvimento local, e o log diz isso.
"""
from __future__ import annotations

import logging
from typing import Annotated

from fastapi import Header, HTTPException, Query, Request, status

from app.auth.autorizacao import (
    CredencialDeFonteRecusada,
    NaoAutenticado,
    NaoAutorizado,
    autorizar,
    recusar_credencial_de_fonte,
)
from app.auth.hub import AutorizadorHub, HubIndisponivel, SemAcessoAUnidade
from app.core.config import config

logger = logging.getLogger(__name__)


async def unidade_autorizada(
    request: Request,
    id_ente: Annotated[int, Query(examples=[2507507], description="Código IBGE do ente.")],
    authorization: Annotated[str | None, Header()] = None,
    x_unidade_id: Annotated[str | None, Header(alias="X-Unidade-Id")] = None,
) -> str:
    """Devolve o `cod_ibge` autorizado. `401` sem JWT válido, `403` para unidade sem acesso."""
    try:
        recusar_credencial_de_fonte(dict(request.headers))
    except CredencialDeFonteRecusada as erro:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(erro)) from erro

    ente = str(id_ente).strip()
    if x_unidade_id and x_unidade_id.strip() != ente:
        raise HTTPException(status.HTTP_400_BAD_REQUEST,
                            detail="X-Unidade-Id não corresponde ao id_ente informado.")

    token = (authorization or "").removeprefix("Bearer ").strip() or None
    claims = _claims(token)
    sub = str(claims.get("sub") or claims.get("email") or "").strip()

    hub = AutorizadorHub()
    if hub.configurado and sub:
        try:
            await hub.autorizar(sub, ente)
        except SemAcessoAUnidade as erro:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail=str(erro)) from erro
        except HubIndisponivel as erro:
            # Fail closed: hub fora do ar não libera acesso.
            raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE,
                                detail="serviço de autorização indisponível") from erro
    else:
        _autorizar_pelo_token(claims, ente)

    request.state.claims = claims
    request.state.ente = ente
    return ente


def _claims(token: str | None) -> dict:
    from app.auth.autorizacao import verificar_jwt

    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="requisição sem JWT",
                            headers={"WWW-Authenticate": "Bearer"})
    claims = verificar_jwt(token)
    if not claims:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="JWT inválido ou expirado",
                            headers={"WWW-Authenticate": "Bearer"})
    return claims


def _autorizar_pelo_token(claims: dict, ente: str) -> None:
    """Modo local: a unidade vem do próprio token. Nunca é o caminho de produção."""
    if config().ambiente not in ("development", "test", "local"):
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AUTH_API_URL/S2S_API_SECRET não configurados — autorização indisponível",
        )
    logger.warning(
        "autorização pelo claim do token (ambiente %s, hub não configurado) | unidade=%s",
        config().ambiente, ente,
    )
    try:
        autorizar(token="local", unidade=ente, ente=ente, verificar=lambda _: claims)
    except NaoAutenticado as erro:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail=str(erro)) from erro
    except NaoAutorizado as erro:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail=str(erro)) from erro


def usuario_id(request: Request) -> int | None:
    """Id do usuário, para registrar quem solicitou um reprocessamento."""
    claims = getattr(request.state, "claims", {}) or {}
    bruto = claims.get("id") or claims.get("usuario_id") or claims.get("sub")
    try:
        return int(bruto) if bruto is not None else None
    except (TypeError, ValueError):
        return None                     # `sub` costuma ser e-mail; então não há id numérico


def token_da_fonte(request: Request) -> str | None:
    """Token da fonte para o job, quando vem por via server-to-server.

    Nunca de browser: `recusar_credencial_de_fonte` barra `x-authorization` e `token_ps` antes.
    """
    return getattr(request.state, "token_fonte", None)


def portas(request: Request) -> dict:
    """Repositório, fila, lock, jobs e cache — montados no lifespan, reusados por requisição."""
    return request.app.state.portas


def repositorio(request: Request):
    """Repositório de cache sobre uma sessão nova, fechada ao fim da requisição."""
    from app.core.database import sessao
    from app.infra.cache.repositorio import RepositorioCache

    db = sessao()
    try:
        yield RepositorioCache(db)
    finally:
        db.close()
