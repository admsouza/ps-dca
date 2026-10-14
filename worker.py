"""Worker da DCA. Wrapper fino: delega ao serviço de apuração e registra o resultado.

Uma função de job para os oito anexos (P4), parametrizada por `anexo`. O contraexemplo é o
`worker.py` do RGF, com 1.760 linhas e seis funções quase iguais.

O que este arquivo faz, e nada além: recebe o job, monta as portas, chama
`services/pipeline/job.executar` e encerra. Nenhuma regra de cálculo, nenhuma consulta a fonte.
"""
from __future__ import annotations

import logging

from arq.connections import RedisSettings
from dotenv import load_dotenv

from app.core.config import config
from app.services.pipeline.cache import versao_do_pedido

load_dotenv()

cfg = config()
logging.basicConfig(
    level="INFO",
    format="%(asctime)s %(levelname)-7s [%(name)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("dca.worker")


async def apurar_anexo(ctx: dict, *, job_id: str, ente: str, exercicio: int, anexo: str,
                       **parametros) -> None:
    """Job único, parametrizado por anexo.

    `parametros` são as escolhas do pedido que mudam o valor — competência e, no BF, a origem da
    coluna do exercício anterior. Chegam do enfileiramento e são repassadas ao serviço do anexo
    que as aceitar; o que não for da assinatura dele é descartado antes da chamada.

    Roda em thread: a apuração é síncrona e CPU/IO-bound, e executá-la no event loop travaria o
    heartbeat do `arq` — o job apareceria como perdido.
    """
    import asyncio

    from app.core.database import sessao
    from app.infra.cache.repositorio import RepositorioCache
    from app.infra.cache.vigencias_repo import RepositorioVigencias
    from app.infra.msc.escopo import escopo
    from app.services.pipeline import apuracao
    from app.services.pipeline.job import executar

    db = sessao()
    try:
        repo = RepositorioCache(db)
        credencial = _credencial(ctx, job_id)
        if parametros.get("fonte") == "publicsoft" and not credencial:
            # Sem token a PublicSoft responde 401; TOKEN_ENCRYPTION_KEY ausente ou diferente da API.
            logger.warning("job PublicSoft sem credencial no cofre | job=%s ente=%s", job_id, ente)
        apurador = apuracao.apurador(
            anexo,
            fonte_nome=parametros.get("fonte"),      # escolhida pelo front; sem ela, DATA_SOURCE
            token=credencial,
            repo_vigencias=RepositorioVigencias(db), repo=repo,
            parametros=parametros,
        )
        versao = versao_do_pedido(
            apuracao.versao_regras(exercicio, anexo, RepositorioVigencias(db)),
            anexo,
            parametros,
        )

        # O escopo abre aqui e fecha com o job: é a única memória de dado da MSC que existe, e
        # ela morre com a execução — o ente retifica declaração publicada, e nada do que foi lido
        # pode ser servido a um job seguinte. Dentro do job, ela evita as leituras repetidas da
        # apuração (três origens × seis classes no BF) e o gate de auditoria da fonte.
        # `to_thread` copia o contexto, então a thread da apuração enxerga o mesmo escopo.
        with escopo():
            await asyncio.to_thread(
                executar,
                ente=ente, exercicio=exercicio, anexo=anexo,
                repo=repo, lock=ctx["lock"], jobs=ctx["jobs"],
                apurador=apurador, versao_api=apuracao.VERSAO_API, versao_regras=versao,
                job_id=job_id, notificador=ctx.get("notificador"),
            )
    finally:
        db.close()


async def apurar_completo(ctx: dict, *, job_id: str, ente: str, exercicio: int,
                          forcar: bool = False, solicitado_por: int | None = None,
                          solicitante_email: str | None = None, **parametros) -> None:
    """O percurso inteiro num job. Wrapper fino, como o job por anexo.

    A memória de execução da MSC abre **uma vez** para todos os anexos: o BO reaproveita as classes
    que o BF já leu (18 consultas à fonte contra 20 em jobs separados) e nada disso sobrevive ao
    job. O percurso é remontado aqui, e não herdado da rota: entre o `202` e a execução, um anexo
    pode ter sido apurado por outro pedido.
    """
    import asyncio
    from functools import cache

    from app.core.database import sessao
    from app.infra.cache.repositorio import RepositorioCache
    from app.infra.cache.vigencias_repo import RepositorioVigencias
    from app.infra.msc.escopo import escopo
    from app.services.pipeline import apuracao, completo

    db = sessao()
    try:
        repo = RepositorioCache(db)
        vigencias = RepositorioVigencias(db)
        credencial = _credencial(ctx, job_id)

        fonte = parametros.get("fonte") or cfg.fonte_padrao

        @cache                       # `versao_de` e `apurador_de` pedem o mesmo anexo
        def pedido_de(anexo: str) -> dict:
            # A mesma identidade que a rota confere: sem a fonte, o `GET` seguinte veria o anexo
            # como desatualizado (`pipeline-visualizar-sem-reprocessar`, D3).
            registro = repo.obter(ente, exercicio, anexo)
            return completo.pedido_do_percurso(registro, fonte, anexo, parametros.get("origem_bp"))

        def versao_de(anexo: str) -> str:
            return versao_do_pedido(
                apuracao.versao_regras(exercicio, anexo, vigencias), anexo, pedido_de(anexo)
            )

        def apurador_de(anexo: str):
            return apuracao.apurador(anexo, fonte_nome=fonte, token=credencial,
                                     repo_vigencias=vigencias, repo=repo,
                                     parametros=pedido_de(anexo))

        percurso = completo.montar_percurso(
            ente=ente, exercicio=exercicio, repo=repo, lock=ctx["lock"], jobs=ctx["jobs"],
            versao_api=apuracao.VERSAO_API, versao_de_regras=versao_de, forcar=forcar,
        )

        with escopo():
            await asyncio.to_thread(
                completo.executar_percurso,
                ente=ente, exercicio=exercicio, percurso=percurso,
                repo=repo, lock=ctx["lock"], jobs=ctx["jobs"], job_id=job_id,
                apurador_de=apurador_de, versao_api=apuracao.VERSAO_API,
                versao_de_regras=versao_de, notificador=ctx.get("notificador"),
                solicitado_por=solicitado_por, solicitante=solicitante_email, fonte=fonte,
            )
    finally:
        db.close()


def _credencial(ctx: dict, job_id: str) -> str | None:
    """Token da fonte, se a rota guardou um. Cifrado no Redis, e lido só aqui."""
    from app.infra.fila.credencial import ler

    if not ctx.get("cofre") or not cfg.token_encryption_key:
        return None
    try:
        return ler(ctx["cofre"], job_id=job_id)
    except Exception:
        logger.warning("credencial da fonte ilegível — seguindo sem ela", exc_info=True)
        return None


async def startup(ctx: dict) -> None:
    """Verifica dependências e libera locks órfãos **antes** de consumir a fila.

    Nesta ordem, e não na inversa: worker de pé consumindo fila que não sabe gravar tira o job da
    fila, falha, e ninguém vê.
    """
    from app.core.database import ping as ping_banco
    from app.infra.fila.redis_adapters import (
        CofreRedis,
        JobsRedis,
        LockRedis,
        cliente,
    )
    from app.infra.fila.redis_adapters import (
        ping as ping_redis,
    )
    from app.services.pipeline.startup import (
        preparar,
        soltar_jobs_interrompidos,
        verificar_dependencias,
    )

    verificar_dependencias(redis=ping_redis, banco=ping_banco)

    sincrono = cliente()
    ctx["redis_sincrono"] = sincrono
    ctx["jobs"] = JobsRedis(sincrono)
    ctx["lock"] = LockRedis(sincrono)
    ctx["cofre"] = CofreRedis(sincrono)
    ctx["notificador"] = _notificador()

    preparar(ctx["lock"])
    soltar_jobs_interrompidos(sincrono, cfg.fila)
    _semear()

    from app.services.pipeline.apuracao import VERSAO_API

    logger.info("worker iniciado | fila=%s | max_jobs=%s | timeout=%ss | fonte=%s | versao_api=%s",
                cfg.fila, cfg.max_concorrentes, cfg.job_timeout, cfg.fonte_padrao, VERSAO_API)


def _notificador():
    """Canal de operação. `None` sem webhook configurado — ambiente local apura sem notificar."""
    from app.infra.notificacao.discord import de_configuracao

    return de_configuracao(cfg)


def _semear() -> None:
    """Vigência inicial do mapeamento. Idempotente, e não fatal: sem tabela, o boot segue."""
    from app.core.database import sessao
    from app.infra.cache.vigencias_repo import RepositorioVigencias
    from app.infra.regras.vigencias import semear

    db = sessao()
    try:
        semear(RepositorioVigencias(db))
    except Exception:
        logger.warning("semente do mapeamento não aplicada no boot", exc_info=True)
    finally:
        db.close()


async def shutdown(ctx: dict) -> None:
    cliente_redis = ctx.get("redis_sincrono")
    if cliente_redis is not None:
        cliente_redis.close()
    logger.info("worker encerrado")


class WorkerSettings:
    """Configuração do `arq`. Fila própria: o worker da DCA não consome job de outro pipeline."""

    functions = [apurar_anexo, apurar_completo]
    queue_name = cfg.fila
    redis_settings = RedisSettings(
        host=cfg.redis_host,
        port=cfg.redis_port,
        password=cfg.redis_password,
        database=cfg.redis_db,
        conn_timeout=5,
        conn_retries=5,          # blip transitório de rede não derruba o worker
        conn_retry_delay=1,
    )
    max_jobs = cfg.max_concorrentes
    job_timeout = cfg.job_timeout
    keep_result = 0              # o resultado vive no cache do anexo, não na fila
    retry_jobs = False           # reapurar é decisão de quem pede, não retentativa automática
    on_startup = startup
    on_shutdown = shutdown
