"""Token da fonte de dados guardado para o job — cifrado, e só pelo TTL do job.

Acesso ao Redis não pode virar acesso ao token da fonte (OWASP A02). O RGF deriva a chave Fernet
do `SECRET_KEY` (`app/utils/job_manager.py::_fernet`); aqui a chave é **dedicada**
(`TOKEN_ENCRYPTION_KEY`), porque um único segredo que cifra dados e assina JWT faz a rotação de um
quebrar o outro.
"""
from __future__ import annotations

import base64
import hashlib
import logging
from typing import Protocol

from app.core.config import config
from app.infra.fila import chaves

logger = logging.getLogger(__name__)


class Cofre(Protocol):
    """Porta do armazenamento com expiração. `ttl` em segundos."""

    def gravar(self, chave: str, valor: str, ttl: int) -> None: ...
    def obter(self, chave: str) -> str | None: ...


def _fernet():
    from cryptography.fernet import Fernet

    bruta = config().token_encryption_key
    if not bruta:
        raise RuntimeError(
            "TOKEN_ENCRYPTION_KEY ausente — obrigatória para cifrar o token da fonte no Redis."
        )
    try:                                    # chave já no formato Fernet (32 bytes urlsafe b64)
        return Fernet(bruta.encode())
    except (ValueError, TypeError):         # texto qualquer: deriva por SHA-256, como o RGF
        derivada = base64.urlsafe_b64encode(hashlib.sha256(bruta.encode()).digest())
        return Fernet(derivada)


def guardar(cofre: Cofre, *, job_id: str, token: str, ttl: int | None = None) -> str:
    """Cifra e grava. Devolve a chave usada — quem chama loga a chave, nunca o valor."""
    chave = chaves.credencial(job_id)
    cifrado = _fernet().encrypt(token.encode("utf-8")).decode("utf-8")
    cofre.gravar(chave, cifrado, ttl if ttl is not None else config().job_ttl)
    return chave


def ler(cofre: Cofre, *, job_id: str) -> str | None:
    """Decifra. `None` quando não há credencial guardada — job com fonte pública, por exemplo."""
    cifrado = cofre.obter(chaves.credencial(job_id))
    if not cifrado:
        return None
    dados = cifrado.encode("utf-8") if isinstance(cifrado, str) else cifrado
    try:
        return _fernet().decrypt(dados).decode("utf-8")
    except Exception:
        # Chave rotacionada ou payload corrompido. Não é erro do job: a fonte é reconsultada.
        logger.exception("falha ao decifrar credencial do job %s", job_id)
        return None
