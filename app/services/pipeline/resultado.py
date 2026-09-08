"""Serialização do resultado apurado — **uma** função, usada por rota, worker e CLI.

Se o CLI tivesse a sua própria cópia, as duas saídas divergiriam em silêncio, e a divergência
apareceria como "o número do terminal não é o da tela".

`Decimal` vira **string**. Em `float`, `6.043.181.131,90` perde centavo, e o aceite do projeto é
1:1 em centavos contra o STN.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any


def _valor(v: Any) -> Any:
    return str(v) if isinstance(v, Decimal) else v


def para_dados(resultado) -> dict:
    """`Resultado` (matriz + procedência + diagnóstico) como dado puro, pronto para JSONB."""
    procedencia = resultado.procedencia
    diagnostico = resultado.diagnostico
    return {
        "matriz": {
            rule_id: {coluna: _valor(valor) for coluna, valor in celulas.items()}
            for rule_id, celulas in resultado.matriz.items()
        },
        "procedencia": {
            "documento": procedencia.documento,
            "edicao": procedencia.edicao,
            "exercicio": procedencia.exercicio,
            "versao_regras": procedencia.versao_regras,
            "regras_aplicadas": procedencia.regras_aplicadas,
            "tabelas_stn": dict(procedencia.tabelas_stn),
        },
        "diagnostico": {
            # Declarado sempre, vazio inclusive: consumidor que não encontra a chave não sabe se a
            # apuração fechou ou se a versão do produtor não a produzia.
            "nao_apuradas": [str(a) for a in diagnostico.nao_apuradas],
            "residuos": [str(r) for r in diagnostico.residuos],
            "duracao_ms": diagnostico.duracao_ms,
            "sem_dados": diagnostico.sem_dados,
        },
    }
