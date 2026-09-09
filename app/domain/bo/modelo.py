"""Modelo do Balanço Orçamentário — núcleo puro.

Sem I/O, sem framework, sem `pandas`: a apuração inteira roda sobre estas estruturas e uma
lista de registros em memória. É o que permite verificar os 11 valores do caso de referência
sem subir container (D2/D3).

`Decimal` em toda parte. O aceite da DCA é 1:1 em centavos contra o STN, e `float` erra centavo
em soma de milhões.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import NamedTuple


class Registro(NamedTuple):
    """Uma linha da MSC, já normalizada pelo adapter da fonte."""

    conta: str                    # conta folha de 9 dígitos
    natureza: str                 # "C" | "D" — natureza do lançamento, não da conta
    valor: Decimal
    natureza_receita: str = ""
    natureza_despesa: str = ""
    funcao: str = ""
    subfuncao: str = ""
    poder_orgao: str = ""
    fonte_recursos: str = ""


class ContaCC(NamedTuple):
    """Uma conta dentro de uma coluna, com o sinal que ela tem na fórmula."""

    cc: str                       # dígitos, sem separadores
    operacao: str = "+"


class Filtro(NamedTuple):
    campo: str                    # conta_contabil | natureza_receita | natureza_despesa | ...
    operador: str                 # in | not_in
    valores: tuple[str, ...]      # padrões normalizados


class RefColuna(NamedTuple):
    coluna: str
    sinal: str


class RefLinha(NamedTuple):
    regra: str
    sinal: str
    coluna: str | None = None   # lê esta coluna da linha referenciada, em vez da calculada


class Coluna(NamedTuple):
    id: str
    rotulo: str
    contas: tuple[ContaCC, ...] = ()
    derivada: tuple[RefColuna, ...] = ()   # coluna calculada de outras colunas da mesma linha


class Linha(NamedTuple):
    id: str
    codigo: str
    rotulo: str
    quadro: str
    grupo: str = ""
    filtros: tuple[Filtro, ...] = ()
    exclusoes: tuple[tuple[Filtro, ...], ...] = ()   # grupos independentes (D2)
    colunas: tuple[Coluna, ...] = ()
    referencias: tuple[RefLinha, ...] = ()
    condicao: str | None = None                      # result_positive | result_negative
    condicao_coluna: str | None = None               # coluna que decide, para a linha inteira
    # Apresentação, declarada pela norma e transcrita na base canônica. Não entra no cálculo, e
    # **não** se deriva da árvore de composição: as duas coisas divergem, e a norma é a que vale.
    nivel: int = 0                                   # 1 a 3 no IPC 07
    ordem: int = 0                                   # 1-based, relativa ao GRUPO

    @property
    def composta(self) -> bool:
        return bool(self.referencias)


class Vigencia(NamedTuple):
    documento: str
    edicao: str
    exercicio: int


@dataclass(frozen=True)
class MapaBO:
    """As regras vigentes para um exercício, prontas para apurar."""

    linhas: tuple[Linha, ...]
    vigencia: Vigencia
    versao_regras: str = ""
    tabelas_stn: dict[str, str] = field(default_factory=dict)

    def por_id(self) -> dict[str, Linha]:
        return {linha.id: linha for linha in self.linhas}

    def com_ciclo_para_teste(self, origem: str, destino: str) -> MapaBO:
        """Devolve uma cópia com uma referência a mais, criando um ciclo.

        Existe para o teste do detector de ciclo: sem isso não há como provocá-lo, já que a
        base canônica é validada e nunca tem ciclo.
        """
        linhas = []
        for linha in self.linhas:
            if linha.id == destino:
                linha = linha._replace(referencias=(*linha.referencias, RefLinha(origem, "+")))
            linhas.append(linha)
        return MapaBO(tuple(linhas), self.vigencia, self.versao_regras, self.tabelas_stn)


class NaoApurada(NamedTuple):
    """Por que uma célula não pôde ser apurada — nunca vira zero silencioso."""

    rule_id: str
    coluna: str
    conta: str
    motivo: str

    def __str__(self) -> str:
        return f"{self.rule_id}.{self.coluna}: conta {self.conta} — {self.motivo}"


class Residuo(NamedTuple):
    """Classificação que nenhuma linha do total captura. Medida e reportada, nunca somada."""

    campo: str
    codigo: str
    valor: Decimal

    def __str__(self) -> str:
        return f"{self.campo}={self.codigo}: {self.valor}"


@dataclass
class Matriz:
    """Resultado da apuração: valores por linha e coluna, mais o que não fechou."""

    valores: dict[str, dict[str, Decimal | None]] = field(default_factory=dict)
    nao_apuradas: list[NaoApurada] = field(default_factory=list)
    residuos: list[Residuo] = field(default_factory=list)
    vigencia: Vigencia | None = None

    # `(rule_id, coluna)` das células que a condição suprimiu. Em `valores` elas são `None`, como
    # as não apuradas; é este conjunto que separa "não se aplica" de "não sei". Célula suprimida
    # contribui **zero** no total que a agrega — medido: o STN publica o total mesmo quando a
    # linha de ajuste fica em branco.
    suprimidas: set[tuple[str, str]] = field(default_factory=set)
