"""Nomes de chave no Redis compartilhado. Dois espaços, e a fronteira entre eles importa.

| Categoria | Prefixo | Por quê |
|---|---|---|
| job, lock, resultado, credencial | `dca:` — **próprio** | execução de um pipeline não é do outro |
| cache de dados da MSC | `msc_cache:` — **comum** | mesmo recorte = mesmo dado para os três |

A chave de MSC reproduz **byte a byte** a do RREO (`app/utils/redis_cache.py::build_cache_key`):
MD5 dos parâmetros ordenados, mesmos nomes, mesma normalização. Não é estilo — é o que faz a
MSC de João Pessoa baixada pelo RREO servir à DCA sem nova consulta à fonte. Nome de parâmetro
divergente produziria outro hash, e o reuso viraria silenciosamente um segundo download.
"""
from __future__ import annotations

import hashlib
import os

PREFIXO = "dca:"
FILA = os.getenv("DCA_ARQ_QUEUE_NAME", "arq:queue:dca")

# O RREO guarda o prefixo sem `:` e junta com `:` — `REDIS_PREFIX` no `.env` traz o `:` final.
PREFIXO_MSC = (os.getenv("REDIS_PREFIX", "msc_cache:").rstrip(":")) + ":"


def job(job_id: str) -> str:
    return f"{PREFIXO}job:{job_id}"


def resultado(job_id: str) -> str:
    return f"{PREFIXO}job:{job_id}:resultado"


def credencial(job_id: str) -> str:
    return f"{PREFIXO}job:{job_id}:credencial"


def lock(ente: str, exercicio: int, anexo: str) -> str:
    return f"{PREFIXO}lock:{anexo}:{ente}:{exercicio}"


def PREFIXO_LOCK() -> str:  # noqa: N802 - constante derivada, usada na varredura de órfãos
    return f"{PREFIXO}lock:"


def _normalizar(valor) -> str:
    """Mesma normalização do RREO: `None` vira string vazia, o resto vira `str`."""
    return "" if valor is None else str(valor)


def msc(ente: int | str, ano: int, mes: int, classe: int,
        requested_mes: int | None = None, id_tv: str = "",
        fonte: str = "", extra: str | None = None) -> str:
    """Chave do cache de MSC, compatível com a do RREO.

    Os nomes dos parâmetros dentro do hash são os do RREO (`id_ente`, `an_referencia`, `mes`,
    `requested_mes`, `classe`, `id_tv`, `fonte_dados`, `key_extra`) porque é o texto deles que
    entra no MD5. Parâmetro `None` é omitido, como lá.
    """
    parametros = {
        "id_ente": ente,
        "an_referencia": ano,
        "mes": mes,
        "requested_mes": requested_mes,
        "classe": classe,
        "id_tv": id_tv,
        "fonte_dados": fonte,
        "key_extra": extra,
    }
    itens = sorted((k, _normalizar(v)) for k, v in parametros.items() if v is not None)
    base = "|".join(f"{k}:{v}" for k, v in itens)
    return f"{PREFIXO_MSC}{hashlib.md5(base.encode('utf-8')).hexdigest()}"  # noqa: S324
