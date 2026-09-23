"""Acompanhamento de job: `GET /jobs/{job_id}` (polling) e `GET /sse/jobs/{job_id}` (stream).

O percurso completo usa o mesmo estado e as mesmas funções, sob `/batch-jobs/{id}` e
`/sse/batch-jobs/{id}` — o caminho que o cliente de batch job do front monta a partir da base
(`front-declaracoes/src/utils/rreoBatchJobStatus.ts`), e por isso sem prefixo de anexo, como o
`/jobs/{id}` individual. O corpo traz, além do status, o progresso e o desfecho por anexo.

O estado é `processing`, `done` ou `error`. O resultado aparece na conclusão; o motivo, no erro.
`not_found` é resposta legítima: o TTL do job vence, e o resultado segue no cache do anexo.
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Path, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.infra.fila import job_manager
from app.routes.dependencias import unidade_autorizada

router = APIRouter(tags=["DCA — jobs"])
logger = logging.getLogger(__name__)

INTERVALO_SSE = 2.0
LIMITE_SSE = 900          # 30 min a 2s — o job tem timeout de 1h, mas a stream não fica pendurada


class EstadoJob(BaseModel):
    job_id: str
    status: str
    resultado: Any = None
    erro: str | None = None
    ente: str | None = None
    exercicio: int | None = None
    anexo: str | None = None
    # Só no percurso completo: um anexo por linha, e o progresso do conjunto.
    progresso: dict | None = None
    falhas: int | None = None
    anexos: list[dict] | None = None
    duracao_ms: int | None = None


def _estado(request: Request, job_id: str) -> dict:
    return job_manager.estado(request.app.state.portas["jobs"], job_id)


@router.get("/batch-jobs/{job_id}", response_model=EstadoJob,
            summary="Estado de um percurso completo (polling)")
@router.get("/jobs/{job_id}", response_model=EstadoJob, summary="Estado de um job (polling)")
def consultar_job(
    request: Request,
    job_id: Annotated[str, Path()],
    _ente: Annotated[str, Depends(unidade_autorizada)],
) -> dict:
    return _estado(request, job_id)


def _stream(request: Request, job_id: str, *, evento_parcial: str) -> StreamingResponse:
    """Mesma informação do polling, empurrada. Encerra no estado final ou quando o cliente sai.

    `evento_parcial` é o nome do evento enquanto o job corre, e os dois consumidores do front
    divergem nele: o do job individual usa o **nome do evento como status**
    (`front-declaracoes/src/utils/rreoJobSsePoll.ts`), enquanto o de batch job só reconhece
    `update` como atualização e ignora qualquer outro nome (`rreoBatchJobSse.ts`). Os terminais
    são os mesmos nos dois, e é por isso que o percurso publica só `done` e `error`.
    """

    async def eventos():
        anterior = None
        for _ in range(LIMITE_SSE):
            if await request.is_disconnected():
                return
            estado = _estado(request, job_id)
            terminal = estado["status"] in ("done", "error", job_manager.DESCONHECIDO)
            # Um evento por mudança: no percurso, o polling de 2s repetiria o mesmo progresso
            # dezenas de vezes enquanto um anexo é apurado. A marca muda quando um anexo conclui.
            marca = (estado["status"], (estado.get("progresso") or {}).get("concluidos"))
            if marca != anterior:
                anterior = marca
                yield (
                    f"event: {estado['status'] if terminal else evento_parcial}\n"
                    f"data: {json.dumps(estado, ensure_ascii=False, default=str)}\n\n"
                )
            if terminal:
                return
            await asyncio.sleep(INTERVALO_SSE)

    return StreamingResponse(
        eventos(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get(
    "/sse/jobs/{job_id}",
    summary="Estado de um job (stream de eventos)",
    description="Exige `Authorization: Bearer` e `id_ente`. `EventSource` nativo não envia "
                "header — consumir com `fetch` + `ReadableStream`, como RREO e RGF.",
)
async def acompanhar_job(
    request: Request,
    job_id: Annotated[str, Path()],
    _ente: Annotated[str, Depends(unidade_autorizada)],
) -> StreamingResponse:
    return _stream(request, job_id, evento_parcial="processing")


@router.get(
    "/sse/batch-jobs/{job_id}",
    summary="Estado de um percurso completo (stream de eventos)",
    description="Um evento `update` a cada anexo concluído, e um terminal `done` ou `error`.",
)
async def acompanhar_percurso(
    request: Request,
    job_id: Annotated[str, Path()],
    _ente: Annotated[str, Depends(unidade_autorizada)],
) -> StreamingResponse:
    return _stream(request, job_id, evento_parcial="update")
