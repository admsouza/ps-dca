"""A decisão de servir do cache ou enfileirar job. Um service, para os oito anexos.

Quatro caminhos, e o que cada um responde:

| Estado da identidade | Resposta |
|---|---|
| `ok` e versões conferem | **200** com o resultado |
| `processando`, com job vivo | **202 + `job_id` do job em voo**, `estado_job="already_queued"` |
| ausente, `erro`, versão divergente, ou `forcar` | **202 + `job_id`**, `estado_job="processing"` |
| `processando` com lock órfão | libera, loga, e cria job novo |

**O job em voo é devolvido com `job_id`, e quem diz que ele não é seu é `estado_job`.** Medido no
consumidor, não escolhido: `front-declaracoes/src/utils/rgfAnexoJob.ts` **lança erro** em `202` sem
`job_id` ("job iniciado sem ID de rastreamento"), e a UI já renderiza `status: "already_queued"`
como "Já existe um cálculo em andamento. Acompanhe o progresso."
(`components/rgf/RGFDialog.tsx`). Omitir o `job_id` custaria a stream SSE e, no caminho
compartilhado do front, viraria erro na tela em vez de "aguarde".

Não há HTTP aqui: a rota transporta o `status`. É o que permite trocar de framework sem reescrever
a decisão, e é o mesmo motivo pelo qual a apuração é alcançável sem rota e sem worker.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Protocol

from app.infra.fila import job_manager
from app.infra.fila import lock as trava_lock
from app.services.pipeline.registry import validar_anexo

logger = logging.getLogger(__name__)


# Estado do job na resposta, no vocabulário que RREO e RGF já publicam e o front já consome.
PROCESSING = "processing"
ALREADY_QUEUED = "already_queued"

MSG_EM_VOO = "Já existe um cálculo em andamento. Acompanhe o progresso."


@dataclass
class Resposta:
    """O que a rota devolve.

    `status` é o código HTTP; `estado_job` é o que a rota publica como `status` no corpo — são
    coisas distintas, e juntá-las num campo só foi o que confundiu a primeira versão disto.
    """

    status: int
    estado_job: str = PROCESSING
    resultado: dict | None = None
    job_id: str | None = None
    poll_url: str | None = None
    sse_url: str | None = None
    anexo: str | None = None
    mensagem: str | None = None


class Repo(Protocol):
    def obter(self, ente: str, exercicio: int, anexo: str) -> Any: ...
    def gravar(self, registro: Any) -> None: ...


class Fila(Protocol):
    def enfileirar(self, ente: str, exercicio: int, anexo: str, job_id: str) -> None: ...


def _url_de_job(job_id: str, base: str = "") -> tuple[str, str]:
    raiz = base.rstrip("/")
    return f"{raiz}/jobs/{job_id}", f"{raiz}/sse/jobs/{job_id}"


def _servivel(registro, versao_api: str, versao_regras: str) -> bool:
    """`ok` com as duas versões conferindo.

    `versao_regras` é o que a DCA tem e os irmãos não: uma correção de conta em
    `knowledge/rules/**.yaml` sem bump de código **tem** de invalidar o cache, ou o ente recebe
    número velho depois de a regra ser corrigida.
    """
    return (registro is not None
            and registro.status == "ok"
            and bool(registro.resultado)
            and registro.versao_api == versao_api
            and registro.versao_regras == versao_regras)


def ler_ou_enfileirar(*, ente: str, exercicio: int, anexo: str, repo: Repo, fila: Fila,
                      lock, versao_api: str, versao_regras: str, jobs=None,
                      forcar: bool = False, solicitado_por: int | None = None,
                      base_url: str = "") -> Resposta:
    """Decide entre servir o cache e criar job. Nunca apura — a apuração é do worker."""
    anexo = validar_anexo(anexo)
    registro = repo.obter(ente, exercicio, anexo)

    if not forcar and _servivel(registro, versao_api, versao_regras):
        return Resposta(status=200, resultado=registro.resultado, anexo=anexo)

    job_id = job_manager.novo_id()
    em_voo = trava_lock.adquirir_com_recuperacao(
        lock, jobs, ente=ente, exercicio=exercicio, anexo=anexo, job_id=job_id
    )
    if em_voo:
        # O job é de outro requisitante, e o `job_id` vai preenchido para ele poder acompanhar:
        # `estado_job` é o que diz que o job não é dele. Nenhum segundo job é enfileirado.
        logger.info("job em voo para a identidade | anexo=%s ente=%s job=%s",
                    anexo, ente, em_voo)
        poll, sse = _url_de_job(em_voo, base_url)
        return Resposta(status=202, estado_job=ALREADY_QUEUED, job_id=em_voo,
                        poll_url=poll, sse_url=sse, anexo=anexo, mensagem=MSG_EM_VOO)

    if registro is not None and registro.status == "processando":
        # Lock livre com cache em `processando`: o worker anterior morreu sem gravar desfecho.
        logger.warning(
            "cache em processando sem job vivo — lock órfão recuperado | anexo=%s ente=%s "
            "exercicio=%s", anexo, ente, exercicio,
        )

    # `processando` é gravado ANTES do enfileiramento — visibilidade imediata mesmo com fila
    # lenta, e um segundo cliente no mesmo instante não cria segundo job.
    _marcar_processando(repo, registro, ente, exercicio, anexo,
                        versao_api, versao_regras, solicitado_por)
    try:
        fila.enfileirar(ente, exercicio, anexo, job_id)
    except Exception as falha:
        # Fila fora do ar não pode virar `202` mentiroso, nem deixar a identidade presa em
        # `processando`: o cliente esperaria um job que ninguém vai executar.
        detalhe = f"fila indisponível: {type(falha).__name__}: {falha}"
        logger.error("falha ao enfileirar | anexo=%s ente=%s -> %s", anexo, ente, detalhe)
        _marcar_erro(repo, repo.obter(ente, exercicio, anexo), ente, exercicio, anexo, detalhe)
        lock.liberar(ente, exercicio, anexo)
        raise RuntimeError(detalhe) from falha

    if jobs is not None:
        job_manager.criar(jobs, job_id, ente=ente, exercicio=exercicio, anexo=anexo)

    logger.info("job enfileirado | anexo=%s ente=%s exercicio=%s job=%s forcar=%s",
                anexo, ente, exercicio, job_id, forcar)
    poll, sse = _url_de_job(job_id, base_url)
    return Resposta(status=202, estado_job=PROCESSING, job_id=job_id,
                    poll_url=poll, sse_url=sse, anexo=anexo)


def _marcar_processando(repo: Repo, registro, ente: str, exercicio: int, anexo: str,
                        versao_api: str, versao_regras: str,
                        solicitado_por: int | None) -> None:
    """Grava `processando` **antes** de a resposta sair, preservando o resultado anterior.

    Duas coisas de uma vez:

    - um segundo cliente no mesmo instante encontra `processando` e não cria segundo job;
    - o resultado anterior **continua legível** durante a reapuração. Apagá-lo abriria uma janela
      de minutos em que o ente vê o anexo vazio, e o requisito proíbe.
    """
    if registro is None:
        registro = _novo_registro(repo, ente, exercicio, anexo)

    registro.status = "processando"
    registro.erro_detalhe = None
    registro.versao_api = versao_api
    registro.versao_regras = versao_regras
    if solicitado_por is not None:
        registro.solicitado_por = solicitado_por
    repo.gravar(registro)


def _marcar_erro(repo: Repo, registro, ente: str, exercicio: int, anexo: str,
                 detalhe: str) -> None:
    """Desfaz o `processando` quando o job não chegou a existir."""
    if registro is None:
        registro = _novo_registro(repo, ente, exercicio, anexo)
    registro.status = "erro"
    registro.erro_detalhe = detalhe
    repo.gravar(registro)


def _novo_registro(repo: Repo, ente: str, exercicio: int, anexo: str):
    """Constrói o registro na classe que o próprio repositório usa — fake ou SQLAlchemy."""
    try:
        from app.infra.cache.repositorio import Registro
    except ImportError:                                  # pragma: no cover - infra ausente
        Registro = None

    modelo = getattr(repo, "Registro", None) or Registro
    return modelo(id_ente=ente, an_referencia=exercicio, anexo=anexo,
                  status="processando", resultado=None)
