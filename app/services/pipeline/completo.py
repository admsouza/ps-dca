"""O percurso completo: todos os anexos implementados, num job só.

Orquestração e nada mais. Cada anexo é apurado pela **mesma** função que o job individual chama
(`job.executar`), sob o **mesmo** lock por identidade e gravando no **mesmo** cache — é o que
impede o percurso de divergir do individual justamente quando algo falha, que é quando a divergência
custaria caro.

Duas coisas o percurso faz que a soma de jobs individuais não faz:

- **paga a leitura da MSC uma vez.** O worker abre uma memória de execução em volta de todo o
  percurso, e o BO reaproveita as classes que o BF já leu: 18 consultas à fonte contra 20 em jobs
  separados (João Pessoa, 2025). Nada disso sobrevive ao job — o ente retifica declaração
  publicada, e o dado bruto nunca é persistido;
- **notifica como o pipeline do RGF**: uma mensagem por anexo, na ordem do registry (inclusive o
  que veio do cache), e um resumo ao fim com o detalhamento (`pipeline-notificacao-discord-padrao`).

O desfecho terminal é `done` ou `error`, nunca um terceiro nome: o consumidor fecha o
acompanhamento em `done | error | cancelled | interrupted`
(`front-declaracoes/src/utils/rreoBatchJobStatus.ts`), e um status fora disso deixaria o cliente
esperando para sempre um job que já acabou. "Terminou com falhas" é `done` com `falhas > 0`.
"""
from __future__ import annotations

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, replace
from typing import Any

from app.infra.fila import job_manager
from app.infra.fila import lock as trava_lock
from app.services.pipeline import notificacao
from app.services.pipeline.cache import parametros_efetivos, servivel

logger = logging.getLogger(__name__)

A_APURAR = "a_apurar"
EM_CACHE = "em_cache"
ALREADY_QUEUED = "already_queued"
NAO_IMPLEMENTADO = "nao_implementado"


@dataclass(frozen=True)
class NoPercurso:
    """Um anexo e o que o percurso vai fazer com ele."""

    anexo: str
    estado: str
    job_id: str | None = None          # preenchido em `already_queued`: o job alheio a acompanhar
    calculado_em: Any = None           # preenchido em `em_cache`
    erro_detalhe: str | None = None
    duracao_ms: int | None = None


def montar_percurso(*, ente: str, exercicio: int, repo, lock, jobs,
                    versao_api: str, versao_de_regras: Callable[[str], str],
                    forcar: bool = False) -> list[NoPercurso]:
    """Classifica cada anexo do registry. Não apura, não enfileira, não toma lock.

    `versao_de_regras` é função do anexo porque a vigência é por anexo e por exercício — a mesma
    que a rota individual consulta antes de decidir invalidação.
    """
    from app.services.pipeline import registry

    percurso: list[NoPercurso] = []
    for anexo in registry.REGISTRY:
        codigo = anexo.codigo
        if anexo.servico is None:
            percurso.append(NoPercurso(codigo, NAO_IMPLEMENTADO))
            continue

        registro = repo.obter(ente, exercicio, codigo)
        if not forcar and servivel(registro, versao_api, versao_de_regras(codigo)):
            percurso.append(NoPercurso(codigo, EM_CACHE,
                                       calculado_em=getattr(registro, "calculado_em", None)))
            continue

        dono = lock.dono(ente, exercicio, codigo)
        if dono and job_manager.em_execucao(jobs, dono):
            percurso.append(NoPercurso(codigo, ALREADY_QUEUED, job_id=dono))
            continue

        percurso.append(NoPercurso(codigo, A_APURAR))
    return percurso


def pedido_do_percurso(registro, fonte: str) -> dict:
    """Identidade de pedido do percurso: a fonte padrão, mais o que o BF reaplica do registro.

    Rota e worker gravam e conferem a mesma. Sem a fonte, o `GET` seguinte — que sempre manda a
    sua — veria todo anexo do percurso como desatualizado.
    """
    return parametros_efetivos({"fonte": fonte}, registro)


def implementados(percurso: list[NoPercurso]) -> list[NoPercurso]:
    """Os que entram no percurso de fato — o total do progresso."""
    return [no for no in percurso if no.estado != NAO_IMPLEMENTADO]


def registrar(jobs, job_id: str, *, ente: str, exercicio: int,
              percurso: list[NoPercurso]) -> dict:
    """Publica o percurso como `processing` **antes** de a resposta sair.

    Sem isto, o polling responderia `not_found` entre o `202` e o primeiro passo do worker — e
    `not_found` é resposta legítima de job expirado, que o cliente não sabe distinguir de "ainda
    não começou".
    """
    return _publicar(jobs, job_id, ente, exercicio,
                     {no.anexo: no for no in implementados(percurso)}, status="processing")


def executar_percurso(*, ente: str, exercicio: int, percurso: list[NoPercurso], repo, lock, jobs,
                      job_id: str, apurador_de: Callable[[str], Callable[[int, int], Any]],
                      versao_api: str, versao_de_regras: Callable[[str], str],
                      notificador=None, solicitado_por: int | None = None,
                      solicitante: str | None = None, fonte: str | None = None) -> dict:
    """Apura os anexos pendentes, em série, e devolve o desfecho do percurso."""
    inicio = time.monotonic()
    estados = {no.anexo: no for no in implementados(percurso)}
    _publicar(jobs, job_id, ente, exercicio, estados, status="processing")

    for no in implementados(percurso):
        if no.estado == EM_CACHE:
            notificacao.notificar_fim(notificador, ente=ente, exercicio=exercicio,
                                      anexo=no.anexo, duracao_ms=0, desfecho="cache")
            continue
        if no.estado != A_APURAR:
            continue                      # em voo: é de outro job, que notifica por si
        apurado = _apurar_um(
            no, ente=ente, exercicio=exercicio, repo=repo, lock=lock, jobs=jobs,
            job_id=job_id, apurador_de=apurador_de, versao_api=versao_api,
            versao_de_regras=versao_de_regras, solicitado_por=solicitado_por,
        )
        estados[no.anexo] = apurado
        _publicar(jobs, job_id, ente, exercicio, estados, status="processing")
        if apurado.estado != ALREADY_QUEUED:
            notificacao.notificar_fim(
                notificador, ente=ente, exercicio=exercicio, anexo=no.anexo,
                duracao_ms=apurado.duracao_ms or 0,
                desfecho="sucesso" if apurado.estado == "ok" else "erro",
                erro=apurado.erro_detalhe,
            )

    duracao_ms = int((time.monotonic() - inicio) * 1000)
    desfecho = _publicar(jobs, job_id, ente, exercicio, estados,
                         status=_status_final(estados), duracao_ms=duracao_ms)

    notificacao.notificar_percurso(
        notificador, ente=ente, exercicio=exercicio, duracao_ms=duracao_ms,
        falhas=desfecho["falhas"], anexos=desfecho["anexos"],
        solicitante=solicitante, fonte=fonte,
    )
    logger.info("percurso concluído | ente=%s exercicio=%s job=%s status=%s falhas=%s",
                ente, exercicio, job_id, desfecho["status"], desfecho["falhas"])
    return desfecho


def _apurar_um(no: NoPercurso, *, ente, exercicio, repo, lock, jobs, job_id, apurador_de,
               versao_api, versao_de_regras, solicitado_por) -> NoPercurso:
    """Um anexo: lock, `job.executar`, desfecho lido do cache que ele mesmo gravou.

    `jobs` e `notificador` **não** vão para `executar`: o estado do job e a notificação são do
    percurso. Passá-los ali sobrescreveria o estado do job pai a cada anexo, e a mensagem do anexo
    em cache — que nem passa por aqui — sairia fora de ordem.
    """
    from app.services.pipeline.job import executar

    em_voo = trava_lock.adquirir_com_recuperacao(
        lock, jobs, ente=ente, exercicio=exercicio, anexo=no.anexo, job_id=job_id
    )
    if em_voo:
        logger.info("anexo em voo — pulado no percurso | anexo=%s ente=%s job=%s",
                    no.anexo, ente, em_voo)
        return replace(no, estado=ALREADY_QUEUED, job_id=em_voo)

    executar(ente=ente, exercicio=exercicio, anexo=no.anexo, repo=repo, lock=lock,
             apurador=apurador_de(no.anexo), versao_api=versao_api,
             versao_regras=versao_de_regras(no.anexo), solicitado_por=solicitado_por)

    registro = repo.obter(ente, exercicio, no.anexo)
    diagnostico = getattr(registro, "diagnostico", None) or {}
    return replace(
        no,
        estado=getattr(registro, "status", "erro"),
        erro_detalhe=getattr(registro, "erro_detalhe", None),
        duracao_ms=getattr(registro, "duracao_ms", None) or diagnostico.get("duracao_ms"),
        calculado_em=getattr(registro, "calculado_em", None),
    )


def _isoformat(valor: Any) -> Any:
    """`datetime` não é JSON — vira string antes de `jobs.gravar` (mesma regra de `resumo.py`)."""
    return valor.isoformat() if hasattr(valor, "isoformat") else valor


def _status_final(estados: dict[str, NoPercurso]) -> str:
    """`error` só quando nada concluiu. Com um anexo de pé, o percurso terminou — com falhas."""
    concluidos = [no for no in estados.values() if no.estado in ("ok", EM_CACHE, ALREADY_QUEUED)]
    return "done" if concluidos else "error"


def _publicar(jobs, job_id: str, ente: str, exercicio: int, estados: dict[str, NoPercurso],
              *, status: str, duracao_ms: int | None = None) -> dict:
    """Grava o estado do percurso onde o polling e a stream leem, e devolve o que gravou."""
    anexos = [
        {"anexo": no.anexo, "status": no.estado, "job_id": no.job_id,
         "duracao_ms": no.duracao_ms, "erro_detalhe": no.erro_detalhe,
         "calculado_em": _isoformat(no.calculado_em)}
        for no in estados.values()
    ]
    concluidos = sum(1 for no in estados.values() if no.estado != A_APURAR)
    estado = {
        "job_id": job_id,
        "status": status,
        "ente": ente,
        "exercicio": exercicio,
        "progresso": {"concluidos": concluidos, "total": len(estados)},
        "falhas": sum(1 for no in estados.values() if no.estado == "erro"),
        "anexos": anexos,
        "duracao_ms": duracao_ms,
        "resultado": None,     # o demonstrativo vive no cache do anexo, não no estado do job
        "erro": None,
    }
    jobs.gravar(job_id, estado)
    return estado
