"""Adapters Redis das portas de fila, lock, jobs e cofre. Síncronos, como o worker e a rota usam.

Cada classe aqui implementa exatamente a porta que os fakes dos testes implementam — é o que
permitiu escrever a decisão de servir/enfileirar sem Redis, e é o único lugar onde `redis` aparece.
"""
from __future__ import annotations

import logging

from app.core.config import config
from app.infra.fila import chaves
from app.infra.fila.serializacao import desserializar, serializar

logger = logging.getLogger(__name__)


def cliente():
    """Conexão do processo. `decode_responses=False`: o payload é bytes, e o formato é nosso."""
    import redis

    cfg = config()
    return redis.Redis(
        host=cfg.redis_host,
        port=cfg.redis_port,
        db=cfg.redis_db,
        password=cfg.redis_password,
        socket_timeout=cfg.redis_socket_timeout,
        socket_connect_timeout=cfg.redis_connect_timeout,
        max_connections=cfg.redis_max_connections,
        decode_responses=False,
    )


def ping(redis_cliente=None) -> bool:
    """Verificação de dependência para o startup do worker."""
    return bool((redis_cliente or cliente()).ping())


class JobsRedis:
    """Estado do job: um documento JSON por `job_id`, sob `dca:job:<id>`."""

    def __init__(self, redis, ttl: int | None = None) -> None:
        self._redis = redis
        self._ttl = ttl if ttl is not None else config().job_ttl

    def gravar(self, job_id: str, estado: dict) -> None:
        self._redis.setex(chaves.job(job_id), self._ttl, serializar(estado))

    def obter(self, job_id: str) -> dict | None:
        bruto = self._redis.get(chaves.job(job_id))
        return desserializar(bruto) if bruto else None


class LockRedis:
    """Lock por identidade. `SET NX` é atômico — só uma requisição simultânea vence a corrida.

    O valor da chave é o `job_id`, e é isso que permite a requisição concorrente acompanhar o job
    existente em vez de criar um duplicado.
    """

    def __init__(self, redis, ttl: int | None = None) -> None:
        self._redis = redis
        self._ttl = ttl if ttl is not None else config().job_ttl

    def adquirir(self, ente: str, exercicio: int, anexo: str, job_id: str) -> bool:
        return bool(self._redis.set(chaves.lock(ente, exercicio, anexo), job_id.encode(),
                                    nx=True, ex=self._ttl))

    def liberar(self, ente: str, exercicio: int, anexo: str) -> None:
        self._redis.delete(chaves.lock(ente, exercicio, anexo))

    def dono(self, ente: str, exercicio: int, anexo: str) -> str | None:
        bruto = self._redis.get(chaves.lock(ente, exercicio, anexo))
        return bruto.decode("utf-8") if bruto else None

    def limpar_orfaos(self, jobs=None) -> int:
        """Varre `dca:lock:*` e libera o que aponta job que não está mais `processing`.

        `scan_iter`, não `KEYS`: o Redis é compartilhado com RREO e RGF, e `KEYS` num banco com o
        cache de MSC dos três bloqueia o servidor.
        """
        from app.infra.fila import job_manager

        jobs = jobs or JobsRedis(self._redis)
        liberados = 0
        for chave in self._redis.scan_iter(match=f"{chaves.PREFIXO_LOCK()}*", count=200):
            nome = chave.decode("utf-8") if isinstance(chave, bytes) else str(chave)
            bruto = self._redis.get(nome)
            if not bruto:
                continue
            job_id = bruto.decode("utf-8")
            if job_manager.em_execucao(jobs, job_id):
                continue
            self._redis.delete(nome)
            liberados += 1
            logger.warning("lock órfão liberado no startup | chave=%s job=%s", nome, job_id)
        return liberados


class CofreRedis:
    """Armazenamento com TTL para a credencial cifrada da fonte."""

    def __init__(self, redis) -> None:
        self._redis = redis

    def gravar(self, chave: str, valor: str, ttl: int) -> None:
        self._redis.setex(chave, ttl, valor.encode("utf-8"))

    def obter(self, chave: str) -> str | None:
        bruto = self._redis.get(chave)
        return bruto.decode("utf-8") if bruto else None


class FilaArq:
    """Enfileira no `arq`, na fila própria da DCA. Um job só, parametrizado por anexo (P4)."""

    def __init__(self, pool, fila: str | None = None) -> None:
        self._pool = pool
        self._fila = fila or chaves.FILA

    def enfileirar(self, ente: str, exercicio: int, anexo: str, job_id: str,
                   **parametros) -> None:
        import asyncio

        from app.services.pipeline.registry import anexo as descrever

        corrotina = self._pool.enqueue_job(
            descrever(anexo).job,
            _job_id=job_id,
            _queue_name=self._fila,
            job_id=job_id,
            ente=ente,
            exercicio=exercicio,
            anexo=anexo,
            **parametros,
        )
        # A rota é async e o service é síncrono: quem chama de dentro do loop usa
        # `FilaArqAsync.enfileirar`. Aqui cobrimos o caso do CLI e de scripts.
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            asyncio.run(corrotina)
        else:
            raise RuntimeError(
                "FilaArq.enfileirar chamada de dentro de um event loop — use FilaArqAsync"
            )


    def enfileirar_percurso(self, ente: str, exercicio: int, job_id: str, **parametros) -> None:
        """Job do percurso completo: um para todos os anexos, sem `anexo` no payload."""
        import asyncio

        from app.services.pipeline.registry import JOB_COMPLETO

        corrotina = self._pool.enqueue_job(
            JOB_COMPLETO, _job_id=job_id, _queue_name=self._fila,
            job_id=job_id, ente=ente, exercicio=exercicio, **parametros,
        )
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            asyncio.run(corrotina)
        else:
            raise RuntimeError(
                "FilaArq.enfileirar_percurso chamada de dentro de um event loop — use FilaArqAsync"
            )


class FilaArqAsync:
    """Mesma fila, para quem já está no event loop da API.

    `enfileirar` devolve a corrotina pendente em `pendente`, e a rota a aguarda. Manter o service
    síncrono é o que o requisito "serviço chamável por rota, worker e CLI" exige.
    """

    def __init__(self, pool, fila: str | None = None) -> None:
        self._pool = pool
        self._fila = fila or chaves.FILA
        self.pendente = None

    def enfileirar(self, ente: str, exercicio: int, anexo: str, job_id: str,
                   **parametros) -> None:
        from app.services.pipeline.registry import anexo as descrever

        self.pendente = self._pool.enqueue_job(
            descrever(anexo).job,
            _job_id=job_id,
            _queue_name=self._fila,
            job_id=job_id,
            ente=ente,
            exercicio=exercicio,
            anexo=anexo,
            **parametros,
        )

    def enfileirar_percurso(self, ente: str, exercicio: int, job_id: str, **parametros) -> None:
        from app.services.pipeline.registry import JOB_COMPLETO

        self.pendente = self._pool.enqueue_job(
            JOB_COMPLETO, _job_id=job_id, _queue_name=self._fila,
            job_id=job_id, ente=ente, exercicio=exercicio, **parametros,
        )
