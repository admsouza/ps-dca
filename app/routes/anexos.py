"""`GET /dca/{anexo}` · `POST /dca/{anexo}/reprocessar` · `GET /dca/resumo` · `POST /batch-jobs`.

A rota valida entrada e autorização, lê o cache, enfileira e responde. **Nada** de cálculo,
consulta a fonte ou composição de demonstrativo — o requisito é explícito, e o contraexemplo é a
rota de 114 KB do RREO (`app/routes/anexo_08/rota_anexo_08.py`).

Uma rota para os oito anexos, com `anexo` no path. O RGF tem seis conjuntos quase iguais.
"""
from __future__ import annotations

import logging
from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends, HTTPException, Path, Query, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.infra.fila import job_manager
from app.routes.dependencias import repositorio, unidade_autorizada, usuario_id
from app.services.pipeline import apuracao, completo
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


class NoPercursoResposta(BaseModel):
    anexo: str
    estado: str = Field(description="`a_apurar`, `em_cache`, `already_queued` "
                                    "ou `nao_implementado`.")
    job_id: str | None = Field(default=None, description="Em `already_queued`: o job em voo.")
    calculado_em: Any = None


class PercursoAceito(BaseModel):
    """`202` — percurso enfileirado. Mesmo contrato de batch job que RREO e RGF publicam."""

    batch_job_id: str
    status: str = "processing"
    poll_url: str | None = None
    sse_url: str | None = None
    anexos: list[NoPercursoResposta] = Field(default_factory=list)


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


def _erro_422(detalhe: str) -> HTTPException:
    return HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detalhe)


class CorpoAnterior(BaseModel):
    """Mapa manual do exercício anterior. Vai no corpo, nunca na query."""

    origem_exercicio_anterior: str | None = None
    valores_anteriores: dict[str, str] | None = None


def _parametros_bf(
    anexo: Annotated[str, Depends(_anexo_valido)],
    origem: Annotated[str | None, Query(alias="origem_exercicio_anterior")] = None,
    valores_json: Annotated[str | None, Query(alias="valores_anteriores")] = None,
) -> dict:
    """Origem na query. O mapa em si não entra aqui: query com valores responde `400`."""
    if valores_json is not None or (anexo == "BF" and origem == "manual"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST,
                            detail="valores_anteriores não é aceito na query")
    if anexo != "BF":
        return {}
    if origem == "msce_exercicio_anterior":
        return {"origem_anterior": "msce_exercicio_anterior"}
    if origem:
        raise _erro_422("origem_exercicio_anterior inválida")
    return {}


def _parametros_do_corpo(corpo: CorpoAnterior, exercicio: int) -> dict:
    """Manual no corpo, ou MSC explícita. Valor não-numérico e código fora do IPC 06 são `422`.

    A recusa é do serviço, que já percorre o mapa informado para conferir os códigos: validar o
    valor aqui também significaria converter cada um duas vezes, e a segunda conversão é a que
    vale.
    """
    from app.services.bf.informados import validar_valores_anteriores

    origem = corpo.origem_exercicio_anterior
    if origem == "msce_exercicio_anterior":
        return {"origem_anterior": "msce_exercicio_anterior"}
    if origem != "manual":
        raise _erro_422("origem_exercicio_anterior inválida")
    valores = {
        str(codigo): str(valor) for codigo, valor in (corpo.valores_anteriores or {}).items()
    }
    try:
        validar_valores_anteriores(exercicio, valores)
    except ValueError as erro:                   # `LinhaDesconhecida` é `ValueError`
        raise _erro_422(str(erro)) from erro
    return {"origem_anterior": "manual", "anterior": "manual", "valores_anteriores": valores}


async def _decidir(request: Request, ente: str, exercicio: int, anexo: str, repo,
                   forcar: bool, solicitante: int | None, parametros: dict | None = None):
    """Caminho comum de leitura e reprocessamento. Difere só em `forcar`."""
    parametros = cache_service.parametros_efetivos(
        parametros, repo.obter(ente, exercicio, anexo),
    )
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
            parametros=parametros,
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


@router.post(
    "/batch-jobs",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=PercursoAceito,
    summary="Apurar todos os anexos implementados de um ente e exercício",
    description=(
        "Um job para o percurso inteiro. Anexo com cache válido não é reapurado, salvo "
        "`forcar=true`; anexo com job em voo é reportado como `already_queued` e pulado; anexo sem "
        "serviço aparece como `nao_implementado`. O demonstrativo continua sendo lido em "
        "`GET /dca/{anexo}` — aqui só se acompanha o percurso."
    ),
)
async def processar_percurso(
    request: Request,
    ente: Annotated[str, Depends(unidade_autorizada)],
    exercicio: Annotated[int, Depends(_exercicio)],
    repo: Annotated[Any, Depends(repositorio)],
    forcar: Annotated[bool, Query(description="Reapura todos, ignorando cache válido.")] = False,
    solicitante: Annotated[int | None, Depends(usuario_id)] = None,
):
    portas = request.app.state.portas
    fila = portas["fila_async"]()

    def versao_de(anexo: str) -> str:
        return apuracao.versao_regras(exercicio, anexo, portas.get("repo_vigencias"))

    try:
        percurso = completo.montar_percurso(
            ente=ente, exercicio=exercicio, repo=repo, lock=portas["lock"], jobs=portas["jobs"],
            versao_api=apuracao.VERSAO_API, versao_de_regras=versao_de, forcar=forcar,
        )
    except Exception as erro:                    # sem regra vigente não há o que apurar
        raise _erro_422(str(erro)) from erro

    if not completo.implementados(percurso):
        # `202` aqui prometeria um job que não faria nada, e o cliente ficaria acompanhando o vazio.
        raise _erro_422("nenhum anexo implementado no registry")

    job_id = job_manager.novo_id()
    completo.registrar(portas["jobs"], job_id, ente=ente, exercicio=exercicio, percurso=percurso)
    try:
        fila.enfileirar_percurso(ente, exercicio, job_id,
                                 forcar=forcar, solicitado_por=solicitante)
        if getattr(fila, "pendente", None) is not None:
            await fila.pendente
    except Exception as erro:
        # O estado já saiu como `processing`. Sem este desfecho, o cliente acompanha um job
        # que a fila recusou e que ninguém vai executar.
        detalhe = f"fila indisponível: {erro}"
        job_manager.falhar(portas["jobs"], job_id, detalhe)
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail=detalhe) from erro

    raiz = str(request.base_url).rstrip("/")
    logger.info("percurso enfileirado | ente=%s exercicio=%s job=%s forcar=%s anexos=%s",
                ente, exercicio, job_id, forcar, len(completo.implementados(percurso)))
    return PercursoAceito(
        batch_job_id=job_id,
        poll_url=f"{raiz}/batch-jobs/{job_id}",
        sse_url=f"{raiz}/sse/batch-jobs/{job_id}",
        anexos=[NoPercursoResposta(anexo=no.anexo, estado=no.estado, job_id=no.job_id,
                                   calculado_em=no.calculado_em) for no in percurso],
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
    parametros: Annotated[dict, Depends(_parametros_bf)],
):
    return await _decidir(request, ente, exercicio, anexo, repo,
                          forcar=False, solicitante=None, parametros=parametros)


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
    parametros: Annotated[dict, Depends(_parametros_bf)],
    corpo: Annotated[CorpoAnterior | None, Body()] = None,
    solicitante: Annotated[int | None, Depends(usuario_id)] = None,
):
    if corpo is not None and corpo.origem_exercicio_anterior:
        parametros = _parametros_do_corpo(corpo, exercicio)
    return await _decidir(request, ente, exercicio, anexo, repo,
                          forcar=True, solicitante=solicitante, parametros=parametros)
