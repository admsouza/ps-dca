"""`Cidade - UF` do ente, para o canal de operação — o `label_ente` do RGF.

Lê `public.unidade_gestora` (`cod_ibge`, `cidade`, `uf`), tabela do RGF no banco compartilhado,
schema confirmado pelo PO em 2026-10-07. Só leitura.

Nunca falha: ente ausente ou banco fora devolvem o código IBGE. Só o acerto fica guardado — cidade
e UF não mudam durante a vida do processo, e banco que volta passa a responder.
"""
from __future__ import annotations

import logging
from collections.abc import Callable

logger = logging.getLogger(__name__)

# ponytail: memória por processo sem teto de tempo; renomear município exige reiniciar o worker.
_ROTULOS: dict[str, str] = {}


def _consultar(cod_ibge: str) -> tuple[str, str] | None:
    from sqlalchemy import text

    from app.core.database import sessao

    db = sessao()
    try:
        linha = db.execute(
            text("SELECT cidade, uf FROM public.unidade_gestora WHERE cod_ibge = :cod LIMIT 1"),
            {"cod": cod_ibge},
        ).first()
    finally:
        db.close()
    return (linha[0], linha[1]) if linha else None


def rotulo_ente(cod_ibge: str,
                consultar: Callable[[str], tuple[str, str] | None] = _consultar) -> str:
    codigo = str(cod_ibge)
    if codigo in _ROTULOS:
        return _ROTULOS[codigo]
    try:
        achado = consultar(codigo)
    except Exception:
        logger.debug("rótulo do ente indisponível — usando o código IBGE | ente=%s", codigo,
                     exc_info=True)
        return codigo
    if not achado or not all(achado):
        return codigo
    _ROTULOS[codigo] = f"{achado[0]} - {achado[1]}"
    return _ROTULOS[codigo]
