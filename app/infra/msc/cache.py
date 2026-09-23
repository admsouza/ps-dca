"""De onde a apuração lê a MSC, e por quanto tempo o dado lido continua valendo.

**Nada de dado da MSC é persistido.** O ente pode retificar declaração já publicada, de qualquer
exercício — inclusive de anos fechados —, e um recorte guardado entre execuções entregaria o
número anterior à retificação sem que nada acusasse a diferença. Cache de dado aqui é decisão
contábil, não de desempenho: reapurar é barato, publicar número revogado não é.

O que existe é a **memória da execução** (`app/infra/msc/escopo.py`): o recorte lido uma vez no
job é reaproveitado pelas demais leituras *daquele* job e descartado ao fim dele. É o que evita as
18 consultas idênticas de um BF (três origens × seis classes) sem nunca atravessar execuções.

A chave continua sendo a do RREO byte a byte (`app/infra/fila/chaves.py::msc`): identifica o
recorte dentro do escopo e mantém a compatibilidade documentada, caso um dia a retificação passe a
ser detectável e o espaço comum volte a ser usável.
"""
from __future__ import annotations

import logging
from collections.abc import Sequence
from typing import Any, Protocol

from app.infra.fila import chaves

logger = logging.getLogger(__name__)


class Fonte(Protocol):
    def registros(self, ente: int, ano: int, mes: int, classe: int,
                  matriz=None, tipo_saldo=None) -> Sequence[Any]: ...


def ler_ou_baixar(*, fonte: Fonte, ente: int, ano: int, mes: int, classe: int,
                  matriz=None, tipo_saldo=None, fonte_nome: str = "") -> Any:
    """Devolve o recorte pedido, consultando a fonte uma vez por execução.

    A chave inclui competência, classe e o **par (matriz, tipo de saldo)**: um demonstrativo que
    lê três origens — o BF lê a abertura do exercício, o encerramento e a abertura do exercício
    anterior — receberia três vezes a mesma se o par ficasse de fora, e `L25`, `L26` e `L29`–`L32`
    sairiam com números plausíveis e errados, sem exceção e sem célula não apurada.

    Fora de um escopo aberto (CLI, teste), consulta a fonte a cada chamada.
    """
    from app.infra.msc.escopo import obter_ou_buscar

    chave = _chave(ente, ano, mes, classe, matriz, tipo_saldo, fonte_nome)
    return obter_ou_buscar(
        chave,
        lambda: fonte.registros(ente, ano, mes, classe, matriz=matriz, tipo_saldo=tipo_saldo),
    )


def _chave(ente: int, ano: int, mes: int, classe: int, matriz, tipo_saldo,
           fonte_nome: str = "") -> str:
    """Identidade do recorte, no formato de chave do RREO.

    `id_tv` e `fonte_dados` entram preenchidos com o vocabulário que o RREO grava
    (`ending_balance`, `siconfi`/`publicsoft`) — é o texto deles que compõe o hash, e deixá-los
    vazios produzia uma identidade que não corresponde a recorte nenhum dos irmãos.
    """
    from app.infra.msc.fonte import Matriz, TipoSaldo
    from app.infra.msc.siconfi import ID_TV  # o vocabulário de API que o RREO grava na chave

    do_rreo = matriz in (None, Matriz.CONSOLIDADA) and tipo_saldo in (
        None, TipoSaldo.ENCERRAMENTO
    )
    if do_rreo:
        return chaves.msc(ente, ano, mes, classe,
                          id_tv=ID_TV[TipoSaldo.ENCERRAMENTO], fonte=fonte_nome)
    return chaves.msc(ente, ano, mes, classe, fonte=fonte_nome,
                      id_tv=ID_TV[tipo_saldo or TipoSaldo.ENCERRAMENTO],
                      extra=str(matriz or ""))
