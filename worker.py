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

load_dotenv()

cfg = config()
logging.basicConfig(
    level="INFO",
    format="%(asctime)s %(levelname)-7s [%(name)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("dca.worker")


async def apurar_anexo(ctx: dict, *, job_id: str, ente: str, exercicio: int, anexo: str) -> None:
    """Job único, parametrizado por anexo.

    Roda em thread: a apuração é síncrona e CPU/IO-bound, e executá-la no event loop travaria o
    heartbeat do `arq` — o job apareceria como perdido.
    """
    import asyncio

    from app.core.database import sessao
    from app.infra.cache.repositorio import RepositorioCache
    from app.infra.cache.vigencias_repo import RepositorioVigencias
    from app.services.pipeline import apuracao
    from app.services.pipeline.job import executar

    db = sessao()
    try:
        repo = RepositorioCache(db)
        credencial = _credencial(ctx, job_id)
        apurador = apuracao.apurador(
            anexo,
            token=credencial,
            cache=ctx.get("cache_msc"),
            repo_vigencias=RepositorioVigencias(db),
        )
        versao = apuracao.versao_regras(exercicio, anexo, RepositorioVigencias(db))

        await asyncio.to_thread(
            executar,
            ente=ente, exercicio=exercicio, anexo=anexo,
            repo=repo, lock=ctx["lock"], jobs=ctx["jobs"],
            apurador=apurador, versao_api=apuracao.VERSAO_API, versao_regras=versao,
            job_id=job_id, notificador=ctx.get("notificador"),
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
        CacheMscRedis,
        CofreRedis,
        JobsRedis,
        LockRedis,
        cliente,
    )
    from app.infra.fila.redis_adapters import (
        ping as ping_redis,
    )
    from app.services.pipeline.startup import preparar, verificar_dependencias

    verificar_dependencias(redis=ping_redis, banco=ping_banco)

    sincrono = cliente()
    ctx["redis_sincrono"] = sincrono
    ctx["jobs"] = JobsRedis(sincrono)
    ctx["lock"] = LockRedis(sincrono)
    ctx["cofre"] = CofreRedis(sincrono)
    ctx["cache_msc"] = CacheMscRedis(sincrono)
    ctx["notificador"] = _notificador()

    preparar(ctx["lock"])
    _semear()

    logger.info("worker iniciado | fila=%s | max_jobs=%s | timeout=%ss",
                cfg.fila, cfg.max_concorrentes, cfg.job_timeout)


def _notificador():
    """Canal de operação. `None` sem webhook configurado — ambiente local apura sem notificar."""
    if not cfg.discord_webhook:
        return None

    from app.infra.notificacao.discord import DiscordNotificador

    return DiscordNotificador(cfg.discord_webhook)


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

    functions = [apurar_anexo]
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
