"""O boot da API: as portas que o `lifespan` monta e o encerramento que ele promete.

Este é o único caminho que nem a rota nem o worker exercitam, e onde um import tardio quebrado
passa por lint e suíte para falhar só no container — foi o que aconteceu ao remover um adapter que
o `main.py` ainda montava. Aqui não há Redis nem Postgres: o que entra no lugar são dublês das
mesmas portas, e o que se afirma é o contrato entre o boot e as rotas.
"""
from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest


class PoolFake:
    def __init__(self):
        self.fechado = False

    async def aclose(self):
        self.fechado = True


class ClienteFake:
    def __init__(self):
        self.fechado = False

    def close(self):
        self.fechado = True


class SessaoFake:
    def __init__(self):
        self.fechada = False

    def close(self):
        self.fechada = True


@pytest.fixture
def boot(monkeypatch):
    """Monta o `lifespan` sobre dublês e devolve o que foi criado, para o teste conferir.

    O ambiente é restaurado no fim: importar `main` executa `load_dotenv()`, e o `.env` do
    desenvolvedor passaria a valer para os testes seguintes — com `AUTH_API_URL` preenchido, a
    autorização por unidade sai do modo local e vai consultar o hub, derrubando testes que nada
    têm a ver com o boot.
    """
    import os

    import arq
    import redis.asyncio as aioredis

    from app.core import database
    from app.core.config import config

    ambiente = dict(os.environ)
    import main

    criados = SimpleNamespace(pool=PoolFake(), sincrono=ClienteFake(), assincrono=PoolFake(),
                              sessao=SessaoFake(), semeado=0)

    async def _create_pool(*_a, **_kw):
        return criados.pool

    monkeypatch.setattr(arq, "create_pool", _create_pool)
    monkeypatch.setattr(aioredis, "from_url", lambda *_a, **_kw: criados.assincrono)
    monkeypatch.setattr("app.infra.fila.redis_adapters.cliente", lambda: criados.sincrono)
    monkeypatch.setattr(database, "sessao", lambda: criados.sessao)
    monkeypatch.setattr(main, "_semear", lambda _db: setattr(criados, "semeado",
                                                             criados.semeado + 1))
    yield main, criados

    os.environ.clear()
    os.environ.update(ambiente)
    config.cache_clear()


async def _ciclo_completo(main, app) -> None:
    """Sobe e desce o `lifespan` — é o ciclo que o container faz a cada reinício."""
    async with main.lifespan(app):
        pass


# ─── Requisito: a API monta no boot as portas que as rotas consomem ──────────

def test_lifespan_monta_as_portas_que_as_rotas_consomem(boot):
    """Requisito: o boot da API monta todas as portas que as rotas leem de `app.state.portas`.

    A rota falha em runtime, não na importação, quando uma porta some — e some sem barulho, porque
    o dicionário aceita qualquer chave. Este teste é o contrato entre o `lifespan` e as rotas.
    """
    main, criados = boot
    app = main.FastAPI()

    async def _subir():
        async with main.lifespan(app):
            portas = app.state.portas
            assert set(portas) == {"jobs", "lock", "cofre", "repo_vigencias", "fila_async"}
            # `fila_async` é fábrica, não instância: cada requisição cria o seu adapter, que
            # guarda a corrotina do enfileiramento para a rota aguardar.
            assert callable(portas["fila_async"])
            assert portas["fila_async"]() is not portas["fila_async"]()
            assert criados.semeado == 1, "semente do mapeamento não foi aplicada no boot"

    asyncio.run(_subir())


def test_lifespan_encerra_o_que_abriu(boot):
    """Requisito: conexões abertas no boot são encerradas no shutdown.

    Pool, Redis e sessão do banco vazariam por reinício de container, e o Postgres é compartilhado
    com RREO e RGF — conexão órfã aqui consome o limite dos três.
    """
    main, criados = boot
    app = main.FastAPI()

    asyncio.run(_ciclo_completo(main, app))

    assert criados.pool.fechado, "pool do arq não foi encerrado"
    assert criados.assincrono.fechado, "cliente Redis assíncrono não foi encerrado"
    assert criados.sincrono.fechado, "cliente Redis síncrono não foi encerrado"
    assert criados.sessao.fechada, "sessão do banco não foi encerrada"


def test_semente_do_mapeamento_nao_derruba_o_boot(monkeypatch, caplog):
    """Requisito: banco sem a tabela de vigências não impede a API de subir.

    A API precisa responder para que o operador rode `alembic upgrade head` — recusar o boot aqui
    deixaria o ente sem a rota que diz o que está faltando.
    """
    import main

    def _explode(_repo):
        raise RuntimeError('relation "dca_regra_mapeamento" does not exist')

    monkeypatch.setattr("app.infra.regras.vigencias.semear", _explode)

    main._semear(SessaoFake())

    assert any("semente" in m.lower() for m in caplog.messages), \
        "falha da semente ficou silenciosa"
