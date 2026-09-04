"""Fixtures da apuração do Balanço Orçamentário (F1 do BO).

Contrato exercitado — ainda não implementado:

    app.domain.bo.saldo        saldo_da_conta(registros, credora) -> Decimal
    app.domain.bo.matriz       apurar(mapa, registros, direcao) -> Matriz
    app.infra.regras.carregador  carregar(exercicio) -> MapaBO
    app.services.bo.quadro_principal  apurar(ente, exercicio, fonte, direcao=None) -> Resultado

`Resultado` expõe `matriz` (`{rule_id: {coluna: Decimal | None}}`), `procedencia` e
`diagnostico` (`nao_apuradas`, `residuos`, `duracao_ms`).

As duas portas do domínio entram aqui como fakes — é o que permite exercitar a apuração sem
rede, sem banco e sem container, que é a razão de o núcleo ser puro (D3 da plataforma).
"""
from __future__ import annotations

from decimal import Decimal

import pytest

ENTE = 2507507          # João Pessoa — o caso de referência medido
EXERCICIO = 2025


# ─── funções sob teste, importadas tarde ─────────────────────────────────────

@pytest.fixture
def apurar_quadro():
    from app.services.bo.quadro_principal import apurar
    return apurar


@pytest.fixture
def apurar_matriz():
    from app.domain.bo.matriz import apurar
    return apurar


@pytest.fixture
def saldo_da_conta():
    from app.domain.bo.saldo import saldo_da_conta
    return saldo_da_conta


@pytest.fixture
def carregar_mapa():
    from app.infra.regras.carregador import carregar
    return carregar


@pytest.fixture
def direcao_do_pcasp():
    from app.infra.pcasp.natureza import do_pcasp
    return do_pcasp


# ─── dublês das portas ───────────────────────────────────────────────────────

class FonteFake:
    """Implementa `FonteSaldos`. Registra o que foi pedido, para asserção sobre a leitura."""

    def __init__(self, por_classe: dict[int, list], rotulo: str = "fake"):
        self._por_classe = por_classe
        self.rotulo = rotulo
        self.chamadas: list[dict] = []

    def registros(self, ente: int, ano: int, mes: int, classe: int):
        self.chamadas.append({"ente": ente, "ano": ano, "mes": mes, "classe": classe})
        return list(self._por_classe.get(classe, []))


class FonteVazia(FonteFake):
    """Fonte que não devolve nada — o caso do gate de auditoria reprovado."""

    def __init__(self):
        super().__init__({}, rotulo="vazia")


class DirecaoFake:
    """Implementa `DirecaoSaldo`. `None` = direção desconhecida, que não pode virar zero."""

    def __init__(self, credoras: set[str] = frozenset(), devedoras: set[str] = frozenset()):
        self._credoras = set(credoras)
        self._devedoras = set(devedoras)

    def credora(self, conta: str) -> bool | None:
        if conta in self._credoras:
            return True
        if conta in self._devedoras:
            return False
        return None

    def credora_prefixo(self, prefixo: str) -> bool | None:
        """Direção do grupo, como a implementação real — por predominância sob o prefixo."""
        sob = [c for c in self._credoras | self._devedoras if c.startswith(prefixo)]
        if not sob:
            return None
        credoras = sum(1 for c in sob if c in self._credoras)
        return credoras * 2 > len(sob)


def registro(conta: str, natureza: str, valor: str, **classificadores):
    """Constrói um registro da MSC já normalizado pelo adapter."""
    from app.domain.bo.modelo import Registro

    return Registro(
        conta=conta,
        natureza=natureza,
        valor=Decimal(valor),
        natureza_receita=classificadores.get("natureza_receita", ""),
        natureza_despesa=classificadores.get("natureza_despesa", ""),
        funcao=classificadores.get("funcao", ""),
        subfuncao=classificadores.get("subfuncao", ""),
        poder_orgao=classificadores.get("poder_orgao", ""),
        fonte_recursos=classificadores.get("fonte_recursos", ""),
    )


def saldo(conta: str, valor: str, **classificadores):
    """Registro cujo saldo, na direção que o PCASP dá à conta, é `valor` positivo.

    Conta credora recebe lançamento a crédito; devedora, a débito. Escrever a natureza à mão
    em teste de integração é fonte de erro — o sinal do gabarito do STN é sempre o do saldo na
    direção da conta, não o de um lançamento isolado.
    """
    from app.infra.pcasp.natureza import do_pcasp

    credora = do_pcasp().credora(conta)
    assert credora is not None, f"conta fora do PCASP: {conta}"
    return registro(conta, "C" if credora else "D", valor, **classificadores)


# ─── exemplo documental do IPC 07 p. 8 (task 2.2) ────────────────────────────
#
# `L2` — Impostos, Taxas e Contribuições de Melhoria. O item 23 da norma usa exatamente esta
# linha como exemplo. Contas reais do PCASP, para que a direção venha da tabela; os valores são
# arbitrários. Cobre numa passagem: conta do grupo, conta redutora e coluna derivada.

NR_IMPOSTOS = "1100.00.00"


@pytest.fixture
def exemplo_l2():
    """Registros de `L2`: previsão, previsão adicional, arrecadação e uma dedução.

    Direções no PCASP: `521110000` e `521210100` devedoras (previsão), `621200000` credora
    (receita realizada), `621310100` devedora — é a redutora dentro do grupo credor.

        previsao_inicial     = 1.000,00
        previsao_atualizada  = 1.000,00 + 200,00 = 1.200,00
        receitas_realizadas  = 900,00 − 100,00   =   800,00
        saldo (d) = (c − b)  = 800,00 − 1.200,00 = −400,00
    """
    return [
        registro("521110000", "D", "1000.00", natureza_receita=NR_IMPOSTOS),
        registro("521210100", "D", "200.00", natureza_receita=NR_IMPOSTOS),
        registro("621200000", "C", "950.00", natureza_receita=NR_IMPOSTOS),
        registro("621200000", "D", "50.00", natureza_receita=NR_IMPOSTOS),
        registro("621310100", "D", "100.00", natureza_receita=NR_IMPOSTOS),
    ]


@pytest.fixture
def direcao_l2():
    """A direção real do PCASP — o exemplo não inventa natureza de conta."""
    from app.infra.pcasp.natureza import do_pcasp

    return do_pcasp()
