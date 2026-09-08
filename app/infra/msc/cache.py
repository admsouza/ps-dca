"""Cache de dados da MSC — o único espaço do Redis compartilhado com RREO e RGF.

Mesmo ente, exercício, competência e classe produzem o mesmo dado para qualquer pipeline: a MSC de
João Pessoa baixada pelo RREO serve à DCA sem nova consulta à fonte. Por isso a chave é a **do
RREO**, byte a byte (`app/infra/fila/chaves.py::msc`).

**O que o RREO grava lá, e por que a DCA não lê tudo.** Ele serializa com um byte de formato à
frente (`app/utils/redis_cache.py`): `\\x02` = parquet+lz4 (DataFrame, o caso real da MSC) e
`\\x01` = **pickle**+lz4 (outros tipos). Desserializar pickle escrito por outro processo executa
código arbitrário — o mesmo risco que a spec proíbe para payload de job. Então:

| Formato no Redis | DCA |
|---|---|
| `\\x02` parquet | lê e reaproveita |
| `\\x01` pickle | trata como **miss** e reconsulta a fonte |
| desconhecido | miss — é o que o próprio RREO faz |

Perde-se reuso no caso raro; não se ganha um `pickle.loads` sobre dado de terceiro.
"""
from __future__ import annotations

import logging
from collections.abc import Sequence
from typing import Any, Protocol

from app.infra.fila import chaves

logger = logging.getLogger(__name__)

FORMATO_PARQUET = b"\x02"
FORMATO_PICKLE = b"\x01"


class CacheDados(Protocol):
    """Porta do cache de dados. O adapter Redis traduz formato; o service só vê registros."""

    def obter(self, chave: str) -> Any: ...
    def gravar(self, chave: str, valor: Any) -> None: ...


class Fonte(Protocol):
    def registros(self, ente: int, ano: int, mes: int, classe: int) -> Sequence[Any]: ...


def para_dados(registros: Sequence[Any]) -> list[dict]:
    """`Registro` -> dicts, para o cache guardar dado e não objeto (nada de pickle)."""
    return [
        {**r._asdict(), "valor": str(r.valor)} if hasattr(r, "_asdict") else dict(r)
        for r in registros
    ]


def de_dados(brutos: Sequence[Any]) -> list[Any] | None:
    """dicts -> `Registro`, pelo **mesmo** normalizador dos adapters de fonte.

    Serve aos dois formatos de uma vez: o nosso (chaves de `Registro`) e o do RREO (colunas da API
    do SICONFI). `normalizacao.CAMPOS` já cobre as duas grafias, então reidratar aqui não duplica
    conhecimento de payload.

    `None` quando o payload **não** é reconhecível — formato antigo, de outro produtor, ou
    corrompido. Num Redis compartilhado por três pipelines, isso acontece: o correto é tratar como
    miss e reconsultar a fonte, nunca deixar a apuração morrer por um dado alheio.
    """
    from app.infra.msc.normalizacao import normalizar

    reidratados = []
    for bruto in brutos:
        if hasattr(bruto, "conta"):
            reidratados.append(bruto)
            continue
        if not isinstance(bruto, dict):
            logger.info("cache MSC em formato não reconhecido (%s) — tratado como miss",
                        type(bruto).__name__)
            return None
        reidratados.append(normalizar(bruto))
    return reidratados


def ler_ou_baixar(*, fonte: Fonte, cache: CacheDados | None, ente: int, ano: int,
                  mes: int, classe: int) -> Any:
    """Devolve o recorte pedido, do cache comum quando houver.

    A chave inclui competência e classe: uma chave por ente/exercício devolveria despesa onde se
    pediu receita.
    """
    if cache is None:
        return fonte.registros(ente, ano, mes, classe)

    chave = chaves.msc(ente, ano, mes, classe)
    guardado = cache.obter(chave)
    if guardado:
        registros = de_dados(guardado)
        if registros is not None:
            logger.debug("cache MSC hit | ente=%s ano=%s mes=%s classe=%s",
                         ente, ano, mes, classe)
            return registros

    registros = fonte.registros(ente, ano, mes, classe)
    if registros:            # vazio pode ser falha de fonte; não se cacheia, como no RREO
        cache.gravar(chave, para_dados(registros))
    return registros


def decodificar(bruto: bytes | None) -> Any:
    """Lê o que o RREO gravou. `None` = miss, e quem chama reconsulta a fonte."""
    if not bruto:
        return None

    formato, corpo = bruto[:1], bruto[1:]
    if formato == FORMATO_PICKLE:
        logger.info("cache MSC em pickle — ignorado por segurança (A08); refazendo a consulta")
        return None
    if formato != FORMATO_PARQUET:
        return None

    try:
        import io

        import pyarrow.parquet as pq
    except ImportError:
        logger.debug("pyarrow ausente — cache MSC do RREO não é lido neste processo")
        return None

    try:
        tabela = pq.read_table(io.BytesIO(corpo))
    except Exception:
        logger.warning("cache MSC ilegível — tratado como miss", exc_info=True)
        return None
    return tabela.to_pylist()
