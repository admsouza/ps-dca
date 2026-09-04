"""C5 e C7 — as 4 linhas que cruzam receita e despesa, e a previsão inicial de `L29`.

Todos os valores vêm do `RREO-Anexo 01` de 2025, `nr_periodo=6`, medidos e registrados em
`docs/evidencia-c5-deficit-superavit.md` e `docs/evidencia-c6-c7.md`.

A metade do superávit é medida em João Pessoa, superavitária; a do déficit em São Paulo, porque
nenhum município da amostra de referência é deficitário. As duas **não são simétricas**: o
superávit sai em 3 colunas de execução da despesa, o déficit em 1 só.
"""
from __future__ import annotations

from decimal import Decimal

import pytest

from tests.bo.conftest import ENTE, EXERCICIO, FonteFake, saldo

ND = "3.1.00.00.00"
NR = "1100.00.00"

L24 = "bo.quadro_principal.receitas.l24"
L25 = "bo.quadro_principal.receitas.l25"
L26 = "bo.quadro_principal.receitas.l26"
L48 = "bo.quadro_principal.despesas.l48"
L49 = "bo.quadro_principal.despesas.l49"
L50 = "bo.quadro_principal.despesas.l50"

COLUNAS_L50 = {"dotacao_inicial", "dotacao_atualizada", "empenhadas", "liquidadas", "pagas"}

# Saldos de João Pessoa 12/2025 que produzem `L24` e `L48` do caso real.
JP = {
    5: [saldo("521110000", "5313644648.00", natureza_receita=NR),
        saldo("521210100", "246698151.26", natureza_receita=NR)],
    6: [saldo("621200000", "5495365004.80", natureza_receita=NR),
        saldo("621310100", "332643194.90", natureza_receita=NR),
        saldo("621390000", "44846513.57", natureza_receita=NR),
        saldo("622130400", "4529794533.11", natureza_despesa=ND),
        saldo("622130500", "281307109.52", natureza_despesa=ND),
        saldo("622130700", "39255202.67", natureza_despesa=ND)],
}


@pytest.fixture
def jp(apurar_quadro):
    return apurar_quadro(ente=ENTE, exercicio=EXERCICIO, fonte=FonteFake(JP))


# ─── C5, metade do superávit — João Pessoa ───────────────────────────────────

def test_superavit_sai_nas_tres_colunas_de_execucao(jp):
    """Scenario: superávit orçamentário.

    Medido: `Superavit` do `RREO-Anexo 01` de JP 2025 sai em 3 colunas, cada uma contra a receita
    realizada. As três fecham em centavos.
    """
    assert jp.matriz[L49] == {
        "empenhadas": Decimal("267518451.03"),
        "liquidadas": Decimal("548825560.55"),
        "pagas": Decimal("588080763.22"),
    }


def test_total_com_superavit_iguala_a_receita_realizada(jp):
    """Scenario: total que agrega linha condicional declara as colunas do publicado.

    `TotalDespesasComSuperavit` vale a receita realizada nas 3 colunas de execução, e o próprio
    `L48` nas de dotação — onde o superávit é zero.
    """
    receita = jp.matriz[L24]["receitas_realizadas"]
    l50 = jp.matriz[L50]
    assert set(l50) == COLUNAS_L50
    assert "saldo_dotacao" not in l50
    for coluna in ("empenhadas", "liquidadas", "pagas"):
        assert l50[coluna] == receita, coluna
    for coluna in ("dotacao_inicial", "dotacao_atualizada"):
        assert l50[coluna] == jp.matriz[L48][coluna], coluna


def test_deficit_fica_em_branco_em_ente_superavitario(jp):
    """Scenario: exercício superavitário.

    `L25` tem uma coluna só, e em ente superavitário ela fica sem valor — sem virar zero e sem
    gerar aviso, porque "não se aplica" não é defeito de apuração.
    """
    assert set(jp.matriz[L25]) == {"receitas_realizadas"}
    assert jp.matriz[L25]["receitas_realizadas"] is None
    avisos = [a for a in jp.diagnostico.nao_apuradas if L25 in str(a)]
    assert avisos == [], "célula suprimida pela condição não é célula não apurada"


def test_total_com_deficit_tem_valor_com_a_parcela_suprimida(jp):
    """Scenario: exercício superavitário.

    O STN publica `TotalReceitasComDeficit` mesmo em ente superavitário, igual a `TotalReceitas`:
    a parcela de `L25` vale **zero**, não indeterminada.
    """
    l26 = jp.matriz[L26]
    assert set(l26) == {"previsao_inicial", "previsao_atualizada", "receitas_realizadas"}
    assert "saldo" not in l26
    for coluna in l26:
        assert l26[coluna] == jp.matriz[L24][coluna], coluna


# ─── C5, metade do déficit — São Paulo ───────────────────────────────────────

# Saldos sintéticos com a proporção de SP 2025: empenhada acima da receita realizada.
SP = {
    5: [saldo("521110000", "1000.00", natureza_receita=NR)],
    6: [saldo("621200000", "1000.00", natureza_receita=NR),
        saldo("622130400", "1200.00", natureza_despesa=ND)],
}


@pytest.fixture
def sp(apurar_quadro):
    return apurar_quadro(ente=ENTE, exercicio=EXERCICIO, fonte=FonteFake(SP))


def test_deficit_sai_na_coluna_de_receita_realizada(sp):
    """Scenario: exercício deficitário.

    Medido em 11 dos 12 estados deficitários de 2025: `Deficit` sai em **uma** coluna,
    `Até o Bimestre (c)`, e vale `empenhada − receita realizada`.
    """
    assert set(sp.matriz[L25]) == {"receitas_realizadas"}
    esperado = sp.matriz[L48]["empenhadas"] - sp.matriz[L24]["receitas_realizadas"]
    assert esperado > 0, "o cenário precisa ser deficitário"
    assert sp.matriz[L25]["receitas_realizadas"] == esperado


def test_superavit_fica_em_branco_em_ente_deficitario(sp):
    """Scenario: exercício deficitário."""
    assert all(v is None for v in sp.matriz[L49].values())
    assert [a for a in sp.diagnostico.nao_apuradas if L49 in str(a)] == []


def test_total_com_superavit_iguala_l48_em_ente_deficitario(sp):
    """Scenario: exercício deficitário.

    Medido em SP e GO: `Superavit` ausente e `TotalDespesasComSuperavit` **publicado**, igual a
    `TotalDespesas` em cada coluna.
    """
    l50 = sp.matriz[L50]
    assert set(l50) == COLUNAS_L50
    for coluna, valor in l50.items():
        assert valor == sp.matriz[L48][coluna], coluna


def test_total_com_deficit_soma_o_deficit(sp):
    """Scenario: exercício deficitário."""
    l26 = sp.matriz[L26]
    assert l26["receitas_realizadas"] == sp.matriz[L48]["empenhadas"]
    for coluna in ("previsao_inicial", "previsao_atualizada"):
        assert l26[coluna] == sp.matriz[L24][coluna], coluna


# ─── C7 — previsão inicial de `L29` ──────────────────────────────────────────

def test_l29_nao_tem_previsao_inicial(jp):
    """Scenario: L27, L28 e L30 têm as quatro colunas de receita, e L29 tem três.

    Medido em 25 entes: nenhum publica `PREVISÃO INICIAL` para `SuperavitFinanceiro`. Um superávit
    financeiro é apurado sobre o exercício fechado e não existe no orçamento originário.
    """
    l29 = jp.matriz["bo.quadro_principal.receitas.l29"]
    assert "previsao_inicial" not in l29
    assert set(l29) == {"previsao_atualizada", "receitas_realizadas", "saldo"}


def test_l27_ignora_a_parcela_ausente_de_l29(apurar_quadro):
    """Scenario: L27, L28 e L30 têm as quatro colunas de receita, e L29 tem três.

    `L27 = L28 + L29 + L30`. Em `previsao_inicial` a parcela de `L29` **não existe** — o total é
    `L28 + L30`, e não sai `None`. É o que reproduz os 12.000.000,00 publicados por JP 2025.
    """
    registros = {
        5: [saldo("521110000", "12000000.00", natureza_receita="9.9.9.0.00.0.0"),
            saldo("522130100", "470338332.64", natureza_despesa=ND)],
        6: [],
    }
    r = apurar_quadro(ente=ENTE, exercicio=EXERCICIO, fonte=FonteFake(registros))
    l27 = r.matriz["bo.quadro_principal.receitas.l27"]
    assert l27["previsao_inicial"] == Decimal("12000000.00")
    assert [a for a in r.diagnostico.nao_apuradas if "l27" in str(a)] == []
