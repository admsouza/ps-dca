"""`GET /dca/{anexo}` · `POST /dca/{anexo}/reprocessar` · `GET /dca/resumo` · `POST /batch-jobs`.

A rota valida entrada e autorização, lê o cache, enfileira e responde. **Nada** de cálculo,
consulta a fonte ou composição de demonstrativo — o requisito é explícito, e o contraexemplo é a
rota de 114 KB do RREO (`app/routes/anexo_08/rota_anexo_08.py`).

Uma rota para os oito anexos, com `anexo` no path. O RGF tem seis conjuntos quase iguais.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends, Header, HTTPException, Path, Query, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.core.config import config
from app.domain import recorte as recortes
from app.infra.fila import credencial, job_manager
from app.routes.dependencias import (
    FontePedido,
    email_do_solicitante,
    fonte_do_pedido,
    repositorio,
    unidade_autorizada,
    usuario_id,
)
from app.services.pipeline import anterior, apuracao, completo, notificacao
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
    # Só BF e BP. `anterior` (`{origem, manual}`) vem só na unidade com escolha gravada.
    recortes: list[dict[str, Any]] | None = None

class FonteRecursoResposta(BaseModel):
    codigo: str
    nome: str


class CatalogoFontesResposta(BaseModel):
    fontes: list[FonteRecursoResposta]


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


class AnteriorDaUnidade(BaseModel):
    """Origem da coluna anterior de uma unidade (`ug:`/`po:`); `valores` só no `manual`."""

    origem: str
    valores: dict[str, str] | None = None


class CorpoAnterior(BaseModel):
    """Escolha por unidade e override G8 do atual. Vai no corpo, nunca na query.

    `origem_exercicio_anterior`/`valores_anteriores` no topo são campos legados do consolidado
    (`pipeline-consolidado-anterior-soma-unidades`): o consolidado não tem origem própria, e o
    pedido com eles responde `422` antes do job.
    """

    origem_exercicio_anterior: str | None = None
    valores_anteriores: dict[str, str] | None = None
    valores_sem_mapeamento: dict[str, str] | None = None
    anterior_por_recorte: dict[str, AnteriorDaUnidade] | None = None
    valores_atuais_por_recorte: dict[str, dict[str, str]] | None = None


VISOES_BP = ("isolado", "consolidado")


def _visao(
    anexo: Annotated[str, Depends(_anexo_valido)],
    visao: Annotated[str | None, Query(description="BP: `isolado` (padrão), `consolidado`")] = None,
) -> str | None:
    """Escolha de leitura: fora da identidade do pedido. `None` fora do BP."""
    if anexo != "BP":
        if visao is not None:
            raise _erro_422("visao só é aceita no BP")
        return None
    if visao is not None and visao not in VISOES_BP:
        raise _erro_422("visao inválida")
    return visao or VISOES_BP[0]


def _na_visao(resultado: dict, visao: str) -> dict:
    """O corpo do BP na visão pedida: troca `matriz` e `equilibrio` e ecoa `visao`."""
    corpo = {chave: valor for chave, valor in resultado.items() if chave != "visoes"}
    if visao == "consolidado":
        consolidado = (resultado.get("visoes") or {}).get("consolidado")
        if consolidado is None:
            raise HTTPException(status.HTTP_409_CONFLICT,
                                detail="reprocesse o BP para obter a visão consolidada")
        corpo["matriz"] = consolidado["matriz"]
        corpo["diagnostico"] = {**resultado["diagnostico"],
                                "equilibrio": consolidado["equilibrio"]}
    return {**corpo, "visao": visao}


def _recorte(
    anexo: Annotated[str, Depends(_anexo_valido)],
    recorte: Annotated[str | None, Query(
        description="BO/BP/BF: `consolidado`, `poder:executivo`, `poder:legislativo`, "
                    "`poder:executivo+legislativo`, `ug:<id>` ou `po:<código>`. Omitido, vale o "
                    "padrão do poder do usuário.")] = None,
) -> str | None:
    """Escolha de leitura, como a `visao`: fora da identidade do pedido."""
    if recorte is None:
        return None
    if anexo not in apuracao.RECORTAVEIS:
        raise _erro_422("recorte só é aceito no BO, no BP e no BF")
    if not recortes.valida(recorte):
        raise _erro_422("recorte inválido")
    return recorte


AVISO_RECORTE_PO = ("O SICONFI agrupa os dados por Poder/Órgão. "
                    "Use o SIAFIC para emitir por unidade gestora.")


def _aviso_recorte(resultado: dict, fonte: FontePedido | None) -> dict:
    """Calculado na leitura, sem estado no cache: fonte SICONFI, `token_ps` resolvido (ente com
    SIAFIC) e recortes `po:`. Ente sem token (CSV, hub fora) e fonte SIAFIC não têm aviso."""
    por_po = any(chave.startswith("po:") for chave in resultado.get("recortes") or {})
    if fonte is not None and fonte.nome == "siconfi" and fonte.token and por_po:
        return {"avisoRecorte": AVISO_RECORTE_PO}
    return {}


def _no_recorte(resultado: dict, pedido: str | None, poderes: tuple[str, ...],
                ugs: tuple[str, ...] = ()) -> dict:
    """O corpo do recorte pedido — ou do padrão do poder —, com os recortes visíveis.

    Busca por chave no que o worker gravou: nada é somado nem calculado aqui. Sem `consolidado`,
    nenhum valor de recorte não visível sai na resposta, nem o consolidado do ente. Com `ugs`, o
    padrão é o primeiro recorte visível quando o do poder soma UG não autorizada.
    """
    chave = pedido or recortes.padrao(poderes)
    if chave is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="sem poder para ler este anexo")
    gravados = resultado.get("recortes")
    if gravados is None:                         # cache anterior à change
        if chave == recortes.CONSOLIDADO and recortes.CONSOLIDADO in poderes and not ugs:
            return resultado
        raise HTTPException(status.HTTP_409_CONFLICT,
                            detail="reprocesse o anexo para emitir por recorte")
    poder_orgao = {c: r["poderOrgao"] for c, r in gravados.items() if c not in recortes.GRUPOS}
    disponiveis = recortes.visiveis([recortes.CONSOLIDADO, *gravados], poder_orgao, poderes, ugs)
    if pedido is None and ugs and disponiveis and chave not in disponiveis:
        chave = disponiveis[0]
    if chave != recortes.CONSOLIDADO and chave not in gravados:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=f"recorte {chave} não apurado")
    if chave not in disponiveis:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="sem acesso a este recorte")

    if chave == recortes.CONSOLIDADO:
        corpo = {k: v for k, v in resultado.items() if k != "recortes"}
    else:
        corpo = gravados[chave]["resultado"]
    return {**corpo, "recorte": chave, "recortesDisponiveis": [
        {"chave": c, "tipo": recortes.tipo(c),
         "rotulo": gravados[c]["rotulo"] if c in gravados else recortes.ROTULOS[c],
         **({"poderOrgao": po} if (po := poder_orgao.get(c)) else {})}
        for c in disponiveis
    ]}


def _parametros_bf(
    anexo: Annotated[str, Depends(_anexo_valido)],
    origem: Annotated[str | None, Query(alias="origem_exercicio_anterior")] = None,
    valores_json: Annotated[str | None, Query(alias="valores_anteriores")] = None,
    g8_json: Annotated[str | None, Query(alias="valores_sem_mapeamento")] = None,
) -> dict:
    """G8 na query, exercício atual (`400` se vier com valores). O consolidado não tem origem
    própria (`pipeline-consolidado-anterior-soma-unidades`): `origem_exercicio_anterior` em BF/BP
    responde `400`, legado ou não."""
    if valores_json is not None or g8_json is not None or (anexo in ("BF", "BP")
                                                           and origem is not None):
        raise HTTPException(status.HTTP_400_BAD_REQUEST,
                            detail="origem_exercicio_anterior/valores_anteriores/"
                                   "valores_sem_mapeamento não é aceito na query")
    return {}


def _parametros_g8_do_corpo(corpo: CorpoAnterior) -> dict:
    """G8 do exercício atual — independente do Manual do anterior (D2)."""
    from app.services.bf.informados import validar_valores_sem_mapeamento

    valores = {
        str(codigo): str(valor)
        for codigo, valor in (corpo.valores_sem_mapeamento or {}).items()
    }
    try:
        validar_valores_sem_mapeamento(valores)
    except ValueError as erro:
        raise _erro_422(str(erro)) from erro
    return {"valores_sem_mapeamento": valores}


def _parametros_por_unidade(corpo: CorpoAnterior, anexo: str, exercicio: int) -> dict:
    """`anterior_por_recorte` validado: chave de grupo, origem e manual inválidos são `422`."""
    try:
        escolhas = anterior.validar_escolhas(anexo, exercicio, corpo.anterior_por_recorte)
    except ValueError as erro:
        raise _erro_422(str(erro)) from erro
    return {"anterior_por_recorte": escolhas}


def _parametros_atuais_por_unidade(corpo: CorpoAnterior, anexo: str, exercicio: int) -> dict:
    """Compensação atual validada integralmente antes de qualquer autorização ou job."""
    if anexo != "BP":
        raise _erro_422("valores_atuais_por_recorte só é aceito no BP")
    from app.services.bp.informados import validar_valores_atuais

    saida = {}
    for chave, valores in (corpo.valores_atuais_por_recorte or {}).items():
        if (not recortes.valida(chave) or not chave.startswith(("ug:", "po:"))
                or not chave.partition(":")[2]):
            raise _erro_422(f"valores_atuais_por_recorte aceita só ug:<id> e po:<código>: {chave}")
        normalizados = {str(codigo): str(valor) for codigo, valor in valores.items()}
        try:
            validar_valores_atuais(exercicio, normalizados)
        except ValueError as erro:
            raise _erro_422(str(erro)) from erro
        saida[chave] = normalizados
    return {"valores_atuais_por_recorte": saida}


def _exigir_poder_nas_unidades(request: Request, repo, ente: str, exercicio: int, anexo: str,
                               chaves: list[str]) -> None:
    """Cada chave de `anterior_por_recorte` precisa ser visível ao usuário (A01), como na leitura.

    `po:` vale pelo próprio código; `ug:` pelo `poderOrgao` gravado em N, ou em N−1. Sem poder
    resolvido (`""`), só `consolidado` passa. Tudo ou nada: roda antes de qualquer job.
    """
    poderes = getattr(request.state, "poderes", ())
    ugs = getattr(request.state, "ugs", ())
    if recortes.CONSOLIDADO in poderes and not ugs:
        return
    gravados: dict = {}
    for ano in (exercicio - 1, exercicio):       # N por último: vence N−1
        registro = repo.obter(ente, ano, anexo)
        # Só resultado `ok`, como no resumo: cache em erro/processando não resolve poder.
        if registro is not None and registro.status == "ok":
            gravados |= (registro.resultado or {}).get("recortes") or {}
    unidades = {c: c[3:] if c.startswith("po:") else gravados.get(c, {}).get("poderOrgao", "")
                for c in chaves}
    visiveis = recortes.visiveis(chaves, unidades, poderes, ugs)
    for chave in chaves:
        if chave not in visiveis:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail=f"sem acesso à unidade {chave}")


def _exigir_n1(repo, ente: str, exercicio: int, anexo: str, parametros: dict) -> None:
    """Unidade que o job apuraria em `processado` sem N−1 `ok` com o recorte: `409`, sem job.

    Vale para toda unidade conhecida, não só para as do pedido: o padrão é Processado, e quem
    ficou de fora do pedido derrubava o job inteiro depois do `202` (`ProcessadoSemAnterior` no
    worker). As unidades vêm do último resultado `ok` de N, que é o que o frontend tem em tela.

    ponytail: unidade que exista na MSC e ainda não esteja no cache de N escapa daqui e só falha
    no worker. Ler a MSC na rota para fechar o caso custaria o job inteiro antes de enfileirar.
    """
    escolhas = cache_service.parametros_efetivos(
        parametros, repo.obter(ente, exercicio, anexo), anexo,
    ).get("anterior_por_recorte") or {}
    chaves = set(escolhas) | _unidades_gravadas(repo, ente, exercicio, anexo)
    if not chaves:
        return
    faltam = anterior.faltam_processado(
        anterior.ler_n1(repo, ente, exercicio, anexo), chaves, escolhas,
    )
    if faltam:
        raise HTTPException(status.HTTP_409_CONFLICT,
                            detail=anterior.mensagem_sem_processado(exercicio - 1, faltam))


def _unidades_gravadas(repo, ente: str, exercicio: int, anexo: str) -> set[str]:
    """Os recortes `ug:`/`po:` do último resultado `ok` de N — grupos e consolidado não têm
    origem própria (`pipeline-consolidado-anterior-soma-unidades`)."""
    registro = repo.obter(ente, exercicio, anexo)
    if registro is None or registro.status != "ok":
        return set()
    gravados = (registro.resultado or {}).get("recortes") or {}
    return {c for c in gravados
            if c.startswith(("ug:", "po:")) and c not in recortes.GRUPOS}


async def _decidir(request: Request, ente: str, exercicio: int, anexo: str, repo,
                   forcar: bool, solicitante: int | None, parametros: dict | None = None,
                   fonte: FontePedido | None = None, visao: str | None = None,
                   recorte: str | None = None):
    """Caminho comum de leitura e reprocessamento. Difere só em `forcar`."""
    if fonte is not None:
        parametros = {**(parametros or {}), "fonte": fonte.nome}
    parametros = cache_service.parametros_efetivos(
        parametros, repo.obter(ente, exercicio, anexo), anexo,
    )
    portas = request.app.state.portas
    guardar = None
    if fonte is not None and fonte.token:
        def guardar(job_id: str) -> None:
            credencial.guardar(portas["cofre"], job_id=job_id, token=fonte.token)
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
            guardar_credencial=guardar,
        )
    except RuntimeError as erro:                 # fila indisponível — não vira `202` mentiroso
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(erro)) from erro

    if fila.pendente is not None:
        await fila.pendente                      # o service é síncrono; o enfileiramento é async

    if resposta.status == 200:
        motivos = resposta.motivos_desatualizado or []
        resultado = resposta.resultado
        aviso = {}
        if anexo in apuracao.RECORTAVEIS:
            aviso = _aviso_recorte(resultado, fonte)
            # Sem `poderes` no estado a autorização não rodou: nenhum recorte (fail closed).
            resultado = _no_recorte(resultado, recorte, getattr(request.state, "poderes", ()),
                                    getattr(request.state, "ugs", ()))
        if visao:
            resultado = _na_visao(resultado, visao)
        return JSONResponse(status_code=200, content={
            **resultado, **aviso, "desatualizado": bool(motivos),
            "motivos_desatualizado": motivos,
        })

    if resposta.estado_job == cache_service.PROCESSING:
        await _notificar_recebida(request, ente, exercicio, [anexo], percurso=False,
                                  forcar=forcar,
                                  fonte=(parametros or {}).get("fonte") or config().fonte_padrao)

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


async def _notificar_recebida(request: Request, ente: str, exercicio: int, anexos: list[str], *,
                              percurso: bool, forcar: bool, fonte: str | None) -> None:
    """Requisição recebida, no padrão do RGF. Em thread: o webhook é síncrono, e o pedido não
    espera nem falha por ele (`notificacao` engole a falha do canal)."""
    await asyncio.to_thread(
        notificacao.notificar_recebida,
        request.app.state.portas.get("notificador"),
        ente=ente, exercicio=exercicio, anexos=anexos, percurso=percurso, forcar=forcar,
        solicitante=email_do_solicitante(request), fonte=fonte,
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
    origem_exercicio_anterior: Annotated[str | None, Query(
        description="Legado, não aceito: o consolidado não tem origem própria "
                    "(`pipeline-consolidado-anterior-soma-unidades`).",
    )] = None,
    fonte: Annotated[FontePedido | None, Depends(fonte_do_pedido)] = None,
    solicitante: Annotated[int | None, Depends(usuario_id)] = None,
):
    if origem_exercicio_anterior is not None:
        raise _erro_422("origem_exercicio_anterior não é mais aceito — o consolidado não tem "
                        "origem própria")
    portas = request.app.state.portas
    fila = portas["fila_async"]()
    # A fonte do front (SIAFIC/MSC), como no anexo: sem ela o percurso apurava sempre pela padrão.
    nome_fonte = fonte.nome if fonte is not None else config().fonte_padrao

    def versao_de(anexo: str) -> str:
        return cache_service.versao_do_pedido(
            apuracao.versao_regras(exercicio, anexo, portas.get("repo_vigencias")), anexo,
            completo.pedido_do_percurso(repo.obter(ente, exercicio, anexo), nome_fonte, anexo),
        )

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
    if fonte is not None and fonte.token:        # cifrado no Redis; nunca no payload da fila
        credencial.guardar(portas["cofre"], job_id=job_id, token=fonte.token)
    try:
        fila.enfileirar_percurso(ente, exercicio, job_id, fonte=nome_fonte,
                                 forcar=forcar, solicitado_por=solicitante,
                                 solicitante_email=email_do_solicitante(request))
        if getattr(fila, "pendente", None) is not None:
            await fila.pendente
    except Exception as erro:
        # O estado já saiu como `processing`. Sem este desfecho, o cliente acompanha um job
        # que a fila recusou e que ninguém vai executar.
        detalhe = f"fila indisponível: {erro}"
        job_manager.falhar(portas["jobs"], job_id, detalhe)
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail=detalhe) from erro

    await _notificar_recebida(
        request, ente, exercicio,
        [no.anexo for no in completo.implementados(percurso) if no.estado == completo.A_APURAR],
        percurso=True, forcar=forcar, fonte=nome_fonte,
    )
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


def _usuario_autenticado(
    authorization: Annotated[str | None, Header()] = None,
) -> None:
    from app.routes.dependencias import _claims

    token = (authorization or "").removeprefix("Bearer ").strip()
    _claims(token or None)


@router.get(
    "/dca/fontes-recursos",
    response_model=CatalogoFontesResposta,
    summary="Catálogo oficial de fontes de recursos",
    description="Classificação pública da STN; não lê MSC, cache ou fila.",
)
def catalogo_fontes_recursos(
    _: Annotated[None, Depends(_usuario_autenticado)] = None,
) -> dict:
    from app.services.bp.fontes import fontes_oficiais

    return {"fontes": [
        {"codigo": fonte.codigo, "nome": fonte.nome} for fonte in fontes_oficiais()
    ]}

@router.get(
    "/dca/resumo",
    response_model=list[EntradaResumo],
    response_model_exclude_unset=True,           # `recortes` só no BF e no BP
    summary="Estado dos anexos de um ente e exercício",
    description="Responde `200` mesmo sem nenhuma apuração. Só metadados, e nunca inicia cálculo.",
)
def resumo(
    ente: Annotated[str, Depends(unidade_autorizada)],
    exercicio: Annotated[int, Depends(_exercicio)],
    repo: Annotated[Any, Depends(repositorio)],
    request: Request,
) -> list[dict]:
    # Sem `poderes` no estado a autorização não rodou: nenhuma unidade (fail closed).
    return resumo_service.resumir(ente=ente, exercicio=exercicio, repo=repo,
                                  poderes=getattr(request.state, "poderes", ()),
                                  ugs=getattr(request.state, "ugs", ()))


async def _auditor_regra(
    authorization: Annotated[str | None, Header()] = None,
) -> None:
    """`auditor_mapeamentos` ou `adm_sistema` no hub. O corpo de erro não cita contas."""
    from app.auth.perfil import HubIndisponivel, SessaoRecusada, pode_ver_regra
    from app.routes.dependencias import _claims

    token = (authorization or "").removeprefix("Bearer ").strip()
    _claims(token or None)
    try:
        if not await pode_ver_regra(token):
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Acesso negado.")
    except SessaoRecusada:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, detail="requisição sem JWT",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None
    except HubIndisponivel:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="serviço de autorização indisponível",
        ) from None


@router.get(
    "/dca/{anexo}/regra",
    summary="Regra de cálculo de uma célula",
    description="Não recalcula o valor e não lê a MSC. Exige a flag de auditor do hub.",
)
async def regra_da_celula(
    anexo: Annotated[str, Depends(_anexo_valido)],
    exercicio: Annotated[int, Depends(_exercicio)],
    linha: Annotated[str, Query(min_length=1, max_length=16)],
    coluna: Annotated[str, Query(min_length=1, max_length=64)],
    quadro: Annotated[str | None, Query(max_length=40)] = None,
    _: Annotated[None, Depends(_auditor_regra)] = None,
) -> dict:
    from app.services.regra_celula import RegraIndisponivel, consultar

    try:
        return consultar(anexo, exercicio, linha, coluna, quadro)
    except RegraIndisponivel:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Consulta indisponível.") from None


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
    fonte: Annotated[FontePedido, Depends(fonte_do_pedido)],
    visao: Annotated[str | None, Depends(_visao)],
    recorte: Annotated[str | None, Depends(_recorte)],
):
    return await _decidir(request, ente, exercicio, anexo, repo,
                          forcar=False, solicitante=None, parametros=parametros, fonte=fonte,
                          visao=visao, recorte=recorte)


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
    fonte: Annotated[FontePedido, Depends(fonte_do_pedido)],
    corpo: Annotated[CorpoAnterior | None, Body()] = None,
    solicitante: Annotated[int | None, Depends(usuario_id)] = None,
):
    if corpo is not None:
        if corpo.origem_exercicio_anterior or corpo.valores_anteriores:
            raise _erro_422("origem_exercicio_anterior/valores_anteriores do consolidado não são "
                            "mais aceitos — escolha a origem por unidade em anterior_por_recorte")
        if "valores_sem_mapeamento" in corpo.model_fields_set:
            parametros = {**parametros, **_parametros_g8_do_corpo(corpo)}
        if corpo.anterior_por_recorte:
            parametros = {**parametros, **_parametros_por_unidade(corpo, anexo, exercicio)}
            _exigir_poder_nas_unidades(request, repo, ente, exercicio, anexo,
                                       list(corpo.anterior_por_recorte))
        if "valores_atuais_por_recorte" in corpo.model_fields_set:
            parametros = {**parametros, **_parametros_atuais_por_unidade(corpo, anexo, exercicio)}
            _exigir_poder_nas_unidades(request, repo, ente, exercicio, anexo,
                                       list(corpo.valores_atuais_por_recorte or {}))
    _exigir_n1(repo, ente, exercicio, anexo, parametros)
    return await _decidir(request, ente, exercicio, anexo, repo,
                          forcar=True, solicitante=solicitante, parametros=parametros,
                          fonte=fonte)
