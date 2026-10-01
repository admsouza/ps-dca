"""De onde cada linha do BF leu o saldo. Sem MSC: a rota da regra importa este módulo."""
from __future__ import annotations

from app.domain.bo.regra_celula import OrigemCelula

# Origem do saldo por linha. Não é preferência: é onde o saldo existe.
DO_ENCERRAMENTO = frozenset({"L25", "L26"})
DO_EXERCICIO_ANTERIOR = frozenset({"L29", "L30", "L31", "L32"})

# codigo -> classe lida em period_change, meses 1 a 12.
# L28 só no exercício atual. L27, L60 e L61 nos dois exercícios.
PERIODO_MENSAL = {"L28": 1, "L61": 1, "L27": 2, "L60": 2}
PERIODO_MENSAL_ANTERIOR = frozenset({"L27", "L60", "L61"})

_SUFIXO_ANTERIOR = "_anterior"


def origem_da_celula(codigo: str, coluna: str) -> OrigemCelula:
    """De onde a célula leu o saldo. A consulta da regra usa a mesma função."""
    periodicos = PERIODO_MENSAL_ANTERIOR if coluna.endswith(_SUFIXO_ANTERIOR) else PERIODO_MENSAL
    if codigo in periodicos:
        return OrigemCelula("period_change", tuple(range(1, 13)))
    if codigo in DO_ENCERRAMENTO:
        return OrigemCelula("encerramento")
    if codigo in DO_EXERCICIO_ANTERIOR:
        return OrigemCelula("exercicio_anterior")
    return OrigemCelula("abertura")
