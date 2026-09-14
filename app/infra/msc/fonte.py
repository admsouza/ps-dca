"""De onde cada demonstrativo lê os saldos da MSC.

O par (matriz, tipo de saldo) é **norma contábil**, não configuração: a matriz de encerramento
lida pelo saldo de encerramento zera as classes 3 e 4 e erra 47 das 337 células do BO, com a
diferença absorvida pela linha de Superávit — um total que continua fechando com linhas erradas.
Por isso o par é propriedade do demonstrativo, e a combinação errada não é exprimível daqui.

Decisão do PO de 2026-09-14, medida em `docs/evidencia-matriz-mscc-vs-msce.md`:

* competência **12** — matriz de encerramento; saldo de **abertura**, exceto o BP, que lê o de
  encerramento porque é ali que o resultado do exercício entra no patrimônio líquido;
* competências **1 a 11** — matriz consolidada, saldo de encerramento (posição acumulada até o
  mês).

**Pendente (`docs/pendencias-periodicidade-mensal.md`).** A regra dos meses 1 a 11 foi medida em
João Pessoa e Cuitegi, que prestam contas **anualmente** — e por isso não encerram nada fora de
dezembro. Falta confirmar, com um ente de prestação **mensal**, se ele publica matriz de
encerramento em competência intermediária e por qual critério ela se identifica. Se publicar, a
regra abaixo lê a matriz errada para esse ente, e lê em silêncio, porque a consolidada responde
normalmente.
"""
from __future__ import annotations

from enum import StrEnum
from typing import NamedTuple

COMPETENCIA_DE_ENCERRAMENTO = 12


class Matriz(StrEnum):
    CONSOLIDADA = "consolidada"
    ENCERRAMENTO = "encerramento"


class TipoSaldo(StrEnum):
    ABERTURA = "abertura"
    ENCERRAMENTO = "encerramento"
    PERIODO = "periodo"


class Fonte(NamedTuple):
    matriz: Matriz
    tipo_saldo: TipoSaldo
    classes: tuple[int, ...]


# Competência 12. As classes são as que cada demonstrativo precisa ler.
ENCERRAMENTO_DO_EXERCICIO: dict[str, Fonte] = {
    "BO": Fonte(Matriz.ENCERRAMENTO, TipoSaldo.ABERTURA, (5, 6)),
    "BF": Fonte(Matriz.ENCERRAMENTO, TipoSaldo.ABERTURA, (1, 2, 3, 4, 5, 6)),
    "BP": Fonte(Matriz.ENCERRAMENTO, TipoSaldo.ENCERRAMENTO, (1, 2)),
    "DVP": Fonte(Matriz.ENCERRAMENTO, TipoSaldo.ABERTURA, (3, 4)),
    "DFC": Fonte(Matriz.ENCERRAMENTO, TipoSaldo.ABERTURA, (1, 2, 3, 4, 5, 6)),
}


def fonte_de(demonstrativo: str, competencia: int = COMPETENCIA_DE_ENCERRAMENTO) -> Fonte:
    """Par e classes para apurar `demonstrativo` na `competencia`."""
    if not 1 <= competencia <= 12:
        raise ValueError(f"competência fora de 1–12: {competencia}")

    codigo = demonstrativo.upper()
    fonte = ENCERRAMENTO_DO_EXERCICIO.get(codigo)
    if fonte is None:
        conhecidos = ", ".join(sorted(ENCERRAMENTO_DO_EXERCICIO))
        raise LookupError(
            f"demonstrativo desconhecido: {demonstrativo}. Conhecidos: {conhecidos}"
        )
    if competencia == COMPETENCIA_DE_ENCERRAMENTO:
        return fonte
    # Meses 1–11: nos entes medidos só existe a consolidada, e nela o acumulado está no saldo de
    # encerramento. Teto conhecido: nenhum ente de prestação mensal foi medido ainda — quando
    # houver um, o critério de identificação da MSCE mensal entra aqui (pendência aberta).
    return fonte._replace(matriz=Matriz.CONSOLIDADA, tipo_saldo=TipoSaldo.ENCERRAMENTO)


def leitura_de_abertura_do_exercicio(exercicio: int) -> tuple[int, int]:
    """Onde está o saldo de abertura do exercício: competência 12 do exercício anterior.

    A abertura do próprio exercício na competência 12 é outra coisa — na consolidada é a abertura
    de dezembro, na de encerramento é a posição pré-encerramento. Medido em João Pessoa 2025: a
    leitura correta dá 1.865.100.624,27 e a incorreta 2.613.640.800,87.
    """
    return exercicio - 1, COMPETENCIA_DE_ENCERRAMENTO
