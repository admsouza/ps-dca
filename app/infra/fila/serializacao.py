"""Estado e resultado de job em formato de dados. Nunca `pickle`.

`pickle.loads` executa código arbitrário: um Redis compartilhado por três pipelines, onde qualquer
processo pode escrever, não é lugar para desserializar objeto. O requisito é explícito, e a
verificação está em `tests/pipeline/test_execucao.py`.

`Decimal` atravessa como **string**. Virar `float` perderia centavo, e o aceite do projeto é 1:1
em centavos contra o STN.
"""
from __future__ import annotations

import json
import math
from decimal import Decimal
from typing import Any

# Assinatura dos protocolos do `pickle` (0 a 5). Payload que comece assim é recusado na leitura.
_MARCAS_PICKLE = (b"\x80", b"(dp", b"}q", b"ccopy_reg", b"cbuiltins")


class PayloadInvalido(ValueError):
    """O payload não é dado: está em formato que executaria código, ou não é JSON."""


def _para_dados(valor: Any) -> Any:
    if isinstance(valor, Decimal):
        return str(valor)
    if isinstance(valor, float) and math.isnan(valor):
        return None                                   # NaN não é JSON válido
    if isinstance(valor, dict):
        return {k: _para_dados(v) for k, v in valor.items()}
    if isinstance(valor, (list, tuple)):
        return [_para_dados(v) for v in valor]
    return valor


def serializar(objeto: Any) -> bytes:
    return json.dumps(_para_dados(objeto), ensure_ascii=False).encode("utf-8")


def desserializar(bruto: bytes | str | None) -> Any:
    """Lê JSON. Recusa qualquer coisa que pareça `pickle`, em vez de tentar interpretar."""
    if bruto is None:
        return None
    if isinstance(bruto, str):
        bruto = bruto.encode("utf-8")
    if not isinstance(bruto, (bytes, bytearray)):
        raise PayloadInvalido(f"payload não é bytes nem str: {type(bruto).__name__}")
    if any(bytes(bruto).startswith(marca) for marca in _MARCAS_PICKLE):
        raise PayloadInvalido("payload em formato pickle — desserializar executaria código")
    try:
        return json.loads(bytes(bruto).decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as erro:
        raise PayloadInvalido(f"payload não é JSON: {erro}") from erro
