"""Reprodução do caso de referência — João Pessoa (2507507), exercício 2025.

Os 11 valores de `docs/validacao-bo-jp-2025.md`, conferidos em centavos contra
`DCA-Anexo I-C`, `I-D` e `RREO-Anexo 01`.

Os saldos entram como registros sintéticos, um por conta, com o valor consolidado que a
medição apurou. É o motor que está sob teste, não a rede: a conferência contra a API oficial é
a task 5.4 da change, executada uma vez com dados reais.
"""
from __future__ import annotations

from decimal import Decimal

import pytest

from tests.bo.conftest import ENTE, EXERCICIO, FonteFake, saldo

ND_PESSOAL = "3.1.00.00.00"
NR_IMPOSTOS = "1100.00.00"

# Saldos consolidados por conta, medidos na MSC de JP 12/2025 (`ending_balance`, MSCC).
# Sinal já na direção do PCASP: credora entra como C, devedora como D.
SALDOS_CLASSE_5 = [
    ("522110100", "C", "5314144648.00"),   # crédito inicial
    ("522120100", "C", "828005403.02"),    # suplementar
    ("522120201", "C", "161060637.16"),    # especiais abertos
    # Cancelamento de dotações. João Pessoa escriturou em `522130900`; a regra do IPC 07 compõe
    # a dotação atualizada por `5.2.2.1.9`, onde a conta equivalente é `522190400`. O valor é o
    # medido; a conferência com a escrituração real do ente é a task 5.4.
    ("522190400", "C", "260029556.28"),
    ("521110000", "C", "5313644648.00"),   # previsão inicial da receita
    ("521210100", "C", "246698151.26"),    # previsão atualizada — acréscimo
]
SALDOS_CLASSE_6 = [
    ("622130400", "D", "4529794533.11"),   # pagas
    ("622130500", "D", "281307109.52"),    # inscrição de RP não processados
    ("622130700", "D", "39255202.67"),     # inscrição de RP processados
    ("621200000", "C", "5495365004.80"),   # receita bruta realizada
    ("621310100", "D", "332643194.90"),    # deduções FUNDEB — conta DEVEDORA
    ("621390000", "D", "44846513.57"),     # outras deduções — conta DEVEDORA
]

ESPERADO_DESPESA = {
    "pagas": "4529794533.11",
    "liquidadas": "4569049735.78",
    "empenhadas": "4850356845.30",
    "dotacao_inicial": "5314144648.00",
    "dotacao_atualizada": "6043181131.90",
}


@pytest.fixture
def resultado_jp(apurar_quadro):
    fonte = FonteFake({
        5: [saldo(c, v, natureza_despesa=ND_PESSOAL, natureza_receita=NR_IMPOSTOS)
            for c, _n, v in SALDOS_CLASSE_5],
        6: [saldo(c, v, natureza_despesa=ND_PESSOAL, natureza_receita=NR_IMPOSTOS)
            for c, _n, v in SALDOS_CLASSE_6],
    })
    return apurar_quadro(ente=ENTE, exercicio=EXERCICIO, fonte=fonte)


@pytest.mark.parametrize("coluna,esperado", sorted(ESPERADO_DESPESA.items()))
def test_conferencia_do_caso_de_referencia(resultado_jp, coluna, esperado):
    """Scenario: conferência do caso de referência — colunas de despesa, em centavos."""
    celulas = resultado_jp.matriz["bo.quadro_principal.despesas.l32"]
    assert celulas[coluna] == Decimal(esperado), f"coluna {coluna} divergiu do gabarito do STN"


def test_conferencia_das_colunas_de_receita(resultado_jp):
    """Scenario: conferência do caso de referência — receita realizada líquida das deduções.

    `5.495.365.004,80 − 332.643.194,90 − 44.846.513,57`, com as duas deduções entrando
    positivas porque são contas devedoras no PCASP.
    """
    celulas = resultado_jp.matriz["bo.quadro_principal.receitas.l2"]
    assert celulas["receitas_realizadas"] == Decimal("5117875296.33")


def test_diagnostico_do_caso_de_referencia(resultado_jp):
    """Scenario: conferência do caso de referência — o relatório informa o que não apurou."""
    d = resultado_jp.diagnostico
    assert isinstance(d.nao_apuradas, list)
    assert all(a.conta and a.rule_id and a.coluna and a.motivo for a in d.nao_apuradas)


def test_rotulos_em_latin_1():
    """Scenario: rótulos em latin-1 — decodificar antes de comparar.

    Os nomes de conta do `tt/dca` e da MSC chegam em latin-1; comparar sem decodificar acusaria
    divergência que não existe.
    """
    from app.infra.msc.normalizacao import decodificar

    bruto = "Deduções da Receita".encode("latin-1")
    assert decodificar(bruto) == "Deduções da Receita"
    assert decodificar("Deduções da Receita") == "Deduções da Receita"


def test_exercicio_determina_a_edicao(resultado_jp):
    """Scenario: exercício determina a edição — a edição usada aparece na procedência."""
    assert resultado_jp.procedencia.exercicio == EXERCICIO
    assert resultado_jp.procedencia.edicao == "2020-01"
