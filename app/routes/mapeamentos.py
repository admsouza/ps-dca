"""Rota administrativa do mapeamento vigente — `/dca/{anexo}/mapeamentos`.

Padrão do RGF (`/rgf/anexo-02/mapeamentos`), com a correção de P-D1: **uma** tabela para todos os
anexos, discriminada por `anexo`.

**INSERT-only.** Publicar uma correção acrescenta vigência; a anterior permanece legível. Não há
`PUT` nem `DELETE` — a ausência é o contrato, e a tentativa é recusada com `409`.
"""
from __future__ import annotations

import logging
from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from app.infra.regras.carregador import SemVigencia
from app.infra.regras.vigencias import PublicacaoDestrutiva, publicar, resolver
from app.routes.anexos import _anexo_valido
from app.routes.dependencias import unidade_autorizada, usuario_id

router = APIRouter(tags=["DCA — mapeamentos (admin)"])
logger = logging.getLogger(__name__)


class Publicacao(BaseModel):
    ano_vigencia: int = Field(ge=2000, le=2100)
    mes_vigencia: int = Field(default=1, ge=1, le=12)
    linhas: list[dict] = Field(min_length=1, description="Contrato de cálculo achatado.")


class VigenciaPublicada(BaseModel):
    anexo: str
    ano_vigencia: int
    mes_vigencia: int
    versao: str
    origem: str
    criado_em: Any = None
    criado_por_usuario_id: int | None = None
    linhas: int = Field(description="Quantidade de linhas — o array inteiro não volta aqui.")


def _repo(request: Request):
    repo = request.app.state.portas.get("repo_vigencias")
    if repo is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE,
                            detail="repositório de vigências indisponível")
    return repo


def _resumir(vigencia: dict) -> dict:
    return {**{k: v for k, v in vigencia.items() if k != "linhas"},
            "linhas": len(vigencia.get("linhas") or [])}


@router.get(
    "/dca/{anexo}/mapeamentos",
    response_model=list[VigenciaPublicada],
    summary="Vigências publicadas de um anexo",
)
def listar(
    request: Request,
    anexo: Annotated[str, Depends(_anexo_valido)],
    _ente: Annotated[str, Depends(unidade_autorizada)],
) -> list[dict]:
    return [_resumir(v) for v in _repo(request).listar(anexo)]


@router.get(
    "/dca/{anexo}/mapeamentos/vigente",
    response_model=VigenciaPublicada,
    summary="Vigência aplicável a um exercício",
    description="Maior vigência `<=` à competência pedida. `422` quando nenhuma cobre.",
)
def vigente(
    request: Request,
    anexo: Annotated[str, Depends(_anexo_valido)],
    _ente: Annotated[str, Depends(unidade_autorizada)],
    an_referencia: int,
) -> dict:
    try:
        return _resumir(resolver(_repo(request), anexo, an_referencia))
    except SemVigencia as erro:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(erro)) from erro


@router.post(
    "/dca/{anexo}/mapeamentos",
    status_code=status.HTTP_201_CREATED,
    response_model=VigenciaPublicada,
    summary="Publicar nova vigência do mapeamento",
    description=(
        "Acrescenta uma vigência. Publicar sobre `(anexo, ano, mês)` existente é recusado com "
        "`409` — corrigir é publicar outra, e a anterior tem de continuar legível."
    ),
)
def publicar_vigencia(
    request: Request,
    anexo: Annotated[str, Depends(_anexo_valido)],
    _ente: Annotated[str, Depends(unidade_autorizada)],
    corpo: Annotated[Publicacao, Body()],
    solicitante: Annotated[int | None, Depends(usuario_id)] = None,
) -> dict:
    if solicitante is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN,
                            detail="publicação administrativa exige usuário identificado")
    try:
        publicada = publicar(
            _repo(request),
            anexo=anexo,
            ano=corpo.ano_vigencia,
            mes=corpo.mes_vigencia,
            linhas=corpo.linhas,
            origem="api-admin",
            usuario_id=solicitante,
        )
    except PublicacaoDestrutiva as erro:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=str(erro)) from erro
    except ValueError as erro:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(erro)) from erro

    logger.info("mapeamento publicado | anexo=%s %s-%02d por usuario=%s",
                anexo, corpo.ano_vigencia, corpo.mes_vigencia, solicitante)
    return _resumir(publicada)
