"""API da DCA. Monta as portas no boot e serve rotas finas.

A API **não apura**: ela lê o cache, enfileira e responde. A apuração é do worker, e mesmo em cache
miss a resposta sai imediatamente — o requisito existe porque um gateway derruba a conexão em ~55s
e uma apuração de ente grande leva minutos.
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import config
from app.routes.anexos import router as anexos_router
from app.routes.jobs import router as jobs_router
from app.routes.mapeamentos import router as mapeamentos_router

load_dotenv()

cfg = config()
logging.basicConfig(
    level=cfg.__dict__.get("log_level", "INFO"),
    format="%(asctime)s %(levelname)-7s [%(name)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("dca.api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Portas montadas uma vez, reusadas por requisição.

    A fila do `arq` é assíncrona e o service de cache é síncrono: por isso `fila_async` é uma
    **fábrica** — cada requisição cria o adapter, que guarda a corrotina do enfileiramento para a
    rota aguardar. Manter o service síncrono é o que o requisito "chamável por rota, worker e CLI"
    exige.
    """
    import redis.asyncio as aioredis
    from arq import create_pool
    from arq.connections import RedisSettings

    from app.core.database import sessao
    from app.infra.cache.vigencias_repo import RepositorioVigencias
    from app.infra.fila.redis_adapters import (
        CacheMscRedis,
        CofreRedis,
        FilaArqAsync,
        JobsRedis,
        LockRedis,
        cliente,
    )

    ajustes = RedisSettings(host=cfg.redis_host, port=cfg.redis_port,
                            password=cfg.redis_password, database=cfg.redis_db)
    pool = await create_pool(ajustes, default_queue_name=cfg.fila)
    sincrono = cliente()
    assincrono = aioredis.from_url(
        f"redis://{cfg.redis_host}:{cfg.redis_port}",
        password=cfg.redis_password, decode_responses=False,
    )

    db_vigencias = sessao()
    app.state.portas = {
        "jobs": JobsRedis(sincrono),
        "lock": LockRedis(sincrono),
        "cofre": CofreRedis(sincrono),
        "cache_msc": CacheMscRedis(sincrono),
        "repo_vigencias": RepositorioVigencias(db_vigencias),
        "fila_async": lambda: FilaArqAsync(pool, cfg.fila),
    }
    logger.info("Redis %s:%s | fila=%s | banco=%s", cfg.redis_host, cfg.redis_port,
                cfg.fila, cfg.postgres_db)

    _semear(db_vigencias)

    yield

    await pool.aclose()
    await assincrono.aclose()
    sincrono.close()
    db_vigencias.close()
    logger.info("conexões encerradas")


def _semear(db) -> None:
    """Publica o mapeamento versionado como vigência inicial, se ainda não houver nenhuma.

    Idempotente e não fatal: banco sem migration ainda não tem a tabela, e a API precisa subir para
    que o operador rode `alembic upgrade head`.
    """
    from app.infra.cache.vigencias_repo import RepositorioVigencias
    from app.infra.regras.vigencias import semear

    try:
        publicadas = semear(RepositorioVigencias(db))
    except Exception:
        logger.warning("semente do mapeamento não aplicada no boot", exc_info=True)
        return
    logger.info("semente do mapeamento: %d vigência(s) publicada(s)", publicadas)


app = FastAPI(
    title="DCA — Declaração de Contas Anuais",
    description=(
        "Anexos da DCA apurados da Matriz de Saldos Contábeis pelas regras do IPC 07. "
        "O primeiro é o Balanço Orçamentário, publicado pelo STN como `RREO-Anexo 01`."
    ),
    version="0.1.0",
    docs_url="/docs" if cfg.swagger else None,
    redoc_url="/redoc" if cfg.swagger else None,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cfg.cors_origens,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Unidade-Id"],
)

app.include_router(anexos_router)
app.include_router(jobs_router)
app.include_router(mapeamentos_router)


@app.get("/health", tags=["infra"], summary="Liveness")
def health() -> dict:
    """Responde sem tocar banco nem Redis — é liveness, não readiness."""
    return {"status": "ok", "versao": app.version, "ambiente": cfg.ambiente}


@app.get("/ready", tags=["infra"], summary="Readiness — verifica Postgres e Redis")
def ready() -> dict:
    """Falha de dependência aparece aqui, e não como job que desaparece."""
    from fastapi import HTTPException, status

    from app.core.database import ping as ping_banco
    from app.infra.fila.redis_adapters import ping as ping_redis
    from app.services.pipeline.startup import DependenciaIndisponivel, verificar_dependencias

    try:
        return verificar_dependencias(redis=ping_redis, banco=ping_banco)
    except DependenciaIndisponivel as erro:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(erro)) from erro


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
