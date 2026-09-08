"""`GET /dca/{anexo}` · `POST /dca/{anexo}/reprocessar` · `GET /dca/resumo`.

A rota valida entrada e autorização, lê o cache, enfileira e responde. **Nada** de cálculo,
consulta a fonte ou composição de demonstrativo — o requisito é explícito, e o contraexemplo é a
rota de 114 KB do RREO (`app/routes/anexo_08/rota_anexo_08.py`).

Uma rota para os oito anexos, com `anexo` no path. O RGF tem seis conjuntos quase iguais.
"""
from __future__ import annotations

import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.routes.dependencias import repositorio, unidade_autorizada, usuario_id
from app.services.pipeline import apuracao
from app.services.pipeline import cache as cache_service
from app.services.pipeline import resumo as resumo_service
from app.services.pipeline.registry import ANEXOS, AnexoDesconhecido, validar_anexo

router = APIRouter(tags=["DCA — anexos"])
logger = logging.getLogger(__name__)


class JobAceito(BaseModel):
    """`202` — apuração enfileirada, ou já em andamento para a identidade.

    Mesmo corpo que RREO e RGF publicam, porque é o que o front já consome: `job_id` sempre
    preenchido, e `status` distinguindo o job criado agora do que já estava em voo.
    """

    status: str = Field(
        default="processing",
        description="`processing` = job criado por esta requisição. "
                    "`already_queued` = já havia apuração em andamento; acompanhe-a, mas o job "
                    "não é seu (nenhum segundo job foi enfileirado).",
    )
    job_id: str | None = Field(default=None, description="Job a acompanhar.")
    poll_url: str | None = None
    sse_url: str | None = None
    anexo: str | None = None
    mensagem: str | None = None


class EntradaResumo(BaseModel):
    anexo: str
    status: str
    calculado_em: Any = None
    duracao_ms: int | None = None
    versao_api: str | None = None
    versao_regras: str | None = None
    erro_detalhe: str | None = None
    implementado: bool = False


def _anexo_valido(anexo: Annotated[str, Path(description=f"Um de: {', '.join(ANEXOS)}")]) -> str:
    try:
        return validar_anexo(anexo)
    except AnexoDesconhecido as erro:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(erro)) from erro


def _exercicio(
    an_referencia: Annotated[int, Query(alias="anReferencia", ge=2000, le=2100,
                                        description="Exercício apurado.")],
) -> int:
    return an_referencia


async def _decidir(request: Request, ente: str, exercicio: int, anexo: str, repo,
                   forcar: bool, solicitante: int | None):
    """Caminho comum de leitura e reprocessamento. Difere só em `forcar`."""
    portas = request.app.state.portas
    fila = portas["fila_async"]()

    try:
        versao = apuracao.versao_regras(exercicio, anexo, portas.get("repo_vigencias"))
    except Exception as erro:
        # Sem regra vigente para o exercício não há o que apurar, e apurar por aproximação
        # publicaria número com regra de outra edição normativa.
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(erro)) from erro

    try:
        resposta = cache_service.ler_ou_enfileirar(
            ente=ente, exercicio=exercicio, anexo=anexo,
            repo=repo, fila=fila, lock=portas["lock"], jobs=portas["jobs"],
            versao_api=apuracao.VERSAO_API, versao_regras=versao,
            forcar=forcar, solicitado_por=solicitante,
            base_url=str(request.base_url).rstrip("/"),
        )
    except RuntimeError as erro:                 # fila indisponível — não vira `202` mentiroso
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(erro)) from erro

    if fila.pendente is not None:
        await fila.pendente                      # o service é síncrono; o enfileiramento é async

    if resposta.status == 200:
        return JSONResponse(status_code=200, content=resposta.resultado)

    return JSONResponse(
        status_code=202,
        content=JobAceito(
            status=resposta.estado_job,
            job_id=resposta.job_id,
            poll_url=resposta.poll_url,
            sse_url=resposta.sse_url,
            anexo=resposta.anexo,
            mensagem=resposta.mensagem,
        ).model_dump(),
    )


@router.get(
    "/dca/resumo",
    response_model=list[EntradaResumo],
    summary="Estado dos anexos de um ente e exercício",
    description="Responde `200` mesmo sem nenhuma apuração. Só metadados, e nunca inicia cálculo.",
)
def resumo(
    ente: Annotated[str, Depends(unidade_autorizada)],
    exercicio: Annotated[int, Depends(_exercicio)],
    repo: Annotated[Any, Depends(repositorio)],
) -> list[dict]:
    return resumo_service.resumir(ente=ente, exercicio=exercicio, repo=repo)


@router.get(
    "/dca/{anexo}",
    summary="Apurar (ou servir do cache) um anexo da DCA",
    description=(
        "**200** → resultado em cache. **202** com `status: processing` → apuração enfileirada "
        "por esta requisição. **202** com `status: already_queued` → já havia apuração em "
        "andamento para a identidade; o `job_id` devolvido é dela."
    ),
    responses={200: {"description": "Resultado apurado."},
               202: {"model": JobAceito, "description": "Enfileirado ou em andamento."}},
)
async def obter_anexo(
    request: Request,
    anexo: Annotated[str, Depends(_anexo_valido)],
    ente: Annotated[str, Depends(unidade_autorizada)],
    exercicio: Annotated[int, Depends(_exercicio)],
    repo: Annotated[Any, Depends(repositorio)],
):
    return await _decidir(request, ente, exercicio, anexo, repo,
                          forcar=False, solicitante=None)


@router.post(
    "/dca/{anexo}/reprocessar",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=JobAceito,
    summary="Reapurar um anexo, ignorando o cache válido",
    description=(
        "Mesma autorização da leitura. O resultado anterior permanece legível até o novo "
        "substituí-lo, e o solicitante fica registrado."
    ),
)
async def reprocessar_anexo(
    request: Request,
    anexo: Annotated[str, Depends(_anexo_valido)],
    ente: Annotated[str, Depends(unidade_autorizada)],
    exercicio: Annotated[int, Depends(_exercicio)],
    repo: Annotated[Any, Depends(repositorio)],
    solicitante: Annotated[int | None, Depends(usuario_id)] = None,
):
    return await _decidir(request, ente, exercicio, anexo, repo,
                          forcar=True, solicitante=solicitante)
