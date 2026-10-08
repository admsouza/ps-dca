"""Apuração do Balanço Patrimonial — cenários de `dca/balanco-patrimonial`.

Saldos sintéticos; os números de Cuitegi vêm da medição de 2026-10-07
(`docs/evidencia-bp-fp-2025.md`). O que está sob teste é o motor, não a rede.
"""
from __future__ import annotations

from decimal import Decimal

import pytest

from tests.bp.conftest import ENTE, EXERCICIO, FontePorAno, celula, fp

PRINCIPAL = "QUADRO_PRINCIPAL"
FP = "ATIVOS_PASSIVOS_FINANCEIROS"
COMPENSACAO = "CONTAS_COMPENSACAO"


# ─── Quadro Principal apurado pela posição de encerramento ───────────────────

def test_caixa_de_cuitegi_2025(apurar_bp):
    """Scenario: caixa de Cuitegi 2025"""
    fonte = FontePorAno({
        2025: {1: [fp("111110100", "26286597.15", "F")]},
        2024: {1: [fp("111110100", "19812433.77", "F")]},
    })
    resultado = apurar_bp(ENTE, EXERCICIO, fonte)
    assert celula(resultado, PRINCIPAL, "L3") == Decimal("26286597.15")
    assert celula(resultado, PRINCIPAL, "L3", "exercicio_anterior") == Decimal("19812433.77")


def test_linha_nao_exclui_conta_intra(apurar_bp):
    """Requisito: (bp-espelho-iab) a conta intra entra na linha; cenário de exclusão revogado

    Revogado por bp-espelho-iab (P8-a): a linha não exclui mais intra-OFSS (5º nível = 2) e a conta
    entra. O cenário sai do spec na mescla (seção 4); até lá o teste o cita com o novo resultado.
    """
    fonte = FontePorAno({2025: {1: [fp("111110100", "100.00", "F"),
                                    fp("111120000", "999.00", "F")]}})
    resultado = apurar_bp(ENTE, EXERCICIO, fonte)
    assert celula(resultado, PRINCIPAL, "L3") == Decimal("1099.00")


def test_coluna_anterior_le_o_encerramento_do_exercicio_anterior(apurar_bp):
    """Scenario: coluna anterior lê o encerramento do exercício anterior

    Cobre também o Scenario: leitura só pelo par do BP — toda chamada usa `MSCE`, encerramento e
    as classes 1, 2 e 6, e `apurar` não aceita parâmetro que mude o par.
    """
    from app.infra.msc.fonte import Matriz, TipoSaldo

    fonte = FontePorAno({2024: {1: [fp("111110100", "7.00", "F")]}})
    resultado = apurar_bp(ENTE, EXERCICIO, fonte)

    assert celula(resultado, PRINCIPAL, "L3", "exercicio_anterior") == Decimal("7.00")
    assert {c["ano"] for c in fonte.chamadas} == {2025, 2024}
    assert {c["classe"] for c in fonte.chamadas} == {1, 2, 6}
    assert {c["matriz"] for c in fonte.chamadas} == {Matriz.ENCERRAMENTO}
    assert {c["tipo_saldo"] for c in fonte.chamadas} == {TipoSaldo.ENCERRAMENTO}


def test_redutora_dentro_do_grupo_reduz(apurar_bp):
    """Requisito: (D2c) depreciação acumulada `1.2.3.8` reduz o Imobilizado, não soma."""
    fonte = FontePorAno({2025: {1: [fp("123110101", "1000.00", "P"),
                                    fp("123810101", "200.00", "P")]}})
    resultado = apurar_bp(ENTE, EXERCICIO, fonte)
    assert celula(resultado, PRINCIPAL, "L12") == Decimal("800.00")


# ─── Equilíbrio do balanço declarado ─────────────────────────────────────────

def _balanco(ativo: str, passivo: str, pl: str) -> FontePorAno:
    return FontePorAno({2025: {
        1: [fp("111110100", ativo, "F")],
        2: [fp("211110101", passivo, "F"), fp("231110000", pl)],
    }})


def test_balanco_fecha(apurar_bp):
    """Scenario: balanço fecha"""
    resultado = apurar_bp(ENTE, EXERCICIO, _balanco("100.00", "60.00", "40.00"))
    assert celula(resultado, PRINCIPAL, "L1") == Decimal("100.00")
    assert celula(resultado, PRINCIPAL, "L15") == Decimal("100.00")
    assert resultado.diagnostico.equilibrio["exercicio_atual"] == Decimal("0.00")


def test_balanco_nao_fecha(apurar_bp):
    """Scenario: balanço não fecha"""
    resultado = apurar_bp(ENTE, EXERCICIO, _balanco("110.00", "60.00", "40.00"))
    assert celula(resultado, PRINCIPAL, "L1") == Decimal("110.00")
    assert resultado.diagnostico.equilibrio["exercicio_atual"] == Decimal("10.00")


# ─── Atributo Financeiro/Permanente ──────────────────────────────────────────

def test_ativo_financeiro_pelo_atributo_do_fato(apurar_bp):
    """Scenario: ativo financeiro pelo atributo do fato"""
    fonte = FontePorAno({2025: {1: [fp("111110100", "100.00", "F"),
                                    fp("111110100", "30.00", "P")]}})
    resultado = apurar_bp(ENTE, EXERCICIO, fonte)
    assert celula(resultado, FP, "L2") == Decimal("100.00")
    assert celula(resultado, FP, "L3") == Decimal("30.00")
    assert celula(resultado, FP, "L1") == celula(resultado, PRINCIPAL, "L1")


def test_termo_sem_qualificador_soma_todos_os_registros(apurar_bp):
    """Scenario: termo sem qualificador soma todos os registros"""
    fonte = FontePorAno({2025: {
        2: [fp("211110101", "100.00", "F")],
        6: [fp("631100000", "70972.63")],
    }})
    resultado = apurar_bp(ENTE, EXERCICIO, fonte)
    assert celula(resultado, FP, "L5") == Decimal("71072.63")


def test_atributo_ausente_vira_residuo(apurar_bp):
    """Scenario: atributo ausente vira resíduo"""
    fonte = FontePorAno({2025: {1: [fp("111110100", "100.00", "F"),
                                    fp("111110100", "25.00")]}})
    resultado = apurar_bp(ENTE, EXERCICIO, fonte)
    assert celula(resultado, FP, "L2") == Decimal("100.00")
    assert celula(resultado, FP, "L3") == Decimal("0.00")
    residuos = [r for r in resultado.diagnostico.residuos
                if r.campo == "financeiro_permanente"]
    assert residuos and residuos[0].valor == Decimal("25.00")


def test_saldo_patrimonial_e_ativo_menos_passivo(apurar_bp):
    """Scenario: saldo patrimonial de Cuitegi 2025 — `L7 = L1 − L4` em centavos."""
    fonte = FontePorAno({2025: {
        1: [fp("111110100", "26431637.72", "F"), fp("123110101", "49882694.20", "P")],
        2: [fp("211110101", "2647434.03", "F"), fp("221110100", "119311755.53", "P")],
        6: [fp("631100000", "70972.63"), fp("631710000", "387532.93")],
    }})
    resultado = apurar_bp(ENTE, EXERCICIO, fonte)
    assert celula(resultado, FP, "L5") == Decimal("3105939.59")
    assert celula(resultado, FP, "L7") == Decimal("-46103363.20")  # igual ao I-AB declarado


def test_fonte_sem_o_atributo(apurar_bp):
    """Scenario: fonte sem o atributo"""
    fonte = FontePorAno({2025: {1: [fp("111110100", "100.00")],
                                2: [fp("211110101", "60.00")]}})
    resultado = apurar_bp(ENTE, EXERCICIO, fonte)
    for codigo in ("L2", "L3", "L5", "L6"):
        assert celula(resultado, FP, codigo) is None, codigo
    assert resultado.diagnostico.sem_atributo_fp is True
    assert celula(resultado, PRINCIPAL, "L3") == Decimal("100.00")


def test_as_duas_fontes_normalizam_para_o_mesmo_valor():
    """Scenario: as duas fontes normalizam para o mesmo valor"""
    from app.infra.msc.normalizacao import normalizar

    base = {"conta_contabil": "111110100", "natureza_conta": "D", "valor": "1"}
    siconfi = normalizar({**base, "financeiro_permanente": "1"})
    publicsoft = normalizar({"codConta": "111110100", "naturezaConta": "D", "valor": 1,
                             "financeiroPermanente": 1})
    assert siconfi.financeiro_permanente == publicsoft.financeiro_permanente == "F"
    assert normalizar({**base, "financeiro_permanente": "2"}).financeiro_permanente == "P"
    for invalido in ("3", "", None):
        assert normalizar({**base, "financeiro_permanente": invalido}).financeiro_permanente == ""


# ─── Linhas e quadros não apuráveis declarados ───────────────────────────────

def test_compensacao_fora_de_escopo(apurar_bp):
    """Scenario: compensação fora de escopo"""
    fonte = FontePorAno({EXERCICIO: {1: [fp("111110100", "1.00", "F")]},
                         EXERCICIO - 1: {1: [fp("111110100", "1.00", "F")]}})
    resultado = apurar_bp(ENTE, EXERCICIO, fonte)
    linhas = [linha for linha in resultado.mapa.linhas if linha.quadro == COMPENSACAO]
    assert len(linhas) == 10
    nao_apuradas = {n.rule_id for n in resultado.diagnostico.nao_apuradas}
    for linha in linhas:
        assert set(resultado.matriz[linha.id].values()) == {None}, linha.codigo
    for linha in linhas:
        if not linha.referencias:
            assert linha.id in nao_apuradas, linha.codigo
    assert any("12" in n.motivo for n in resultado.diagnostico.nao_apuradas
               if n.rule_id.startswith("bp.contas_compensacao"))


def test_linha_bloqueada_nao_zera_o_total(apurar_bp):
    """Scenario: linha bloqueada não zera o total"""
    from dataclasses import replace

    from app.infra.regras.carregador import carregar
    mapa = carregar(EXERCICIO, demonstrativo="bp")
    mapa = replace(mapa, linhas=tuple(
        linha._replace(bloqueio="x") if linha.quadro == PRINCIPAL and linha.codigo == "L34"
        else linha for linha in mapa.linhas))
    fonte = FontePorAno({2025: {2: [fp("231110000", "50.00"), fp("232110000", "7.00")]}})
    resultado = apurar_bp(ENTE, EXERCICIO, fonte, mapa=mapa)
    assert celula(resultado, PRINCIPAL, "L34") is None
    assert celula(resultado, PRINCIPAL, "L32") == Decimal("50.00")
    l34 = next(linha.id for linha in resultado.mapa.linhas
               if linha.quadro == PRINCIPAL and linha.codigo == "L34")
    assert l34 in {n.rule_id for n in resultado.diagnostico.nao_apuradas}


def test_l34_apurada_pela_232(apurar_bp):
    """Scenario: L34 apurada pela 2.3.2"""
    fonte = FontePorAno({2025: {2: [fp("231110000", "50.00"), fp("232110000", "7.00"),
                                    fp("232120000", "3.00")]}})   # intra entra (espelho do I-AB)
    resultado = apurar_bp(ENTE, EXERCICIO, fonte)
    assert celula(resultado, PRINCIPAL, "L34") == Decimal("10.00")
    assert celula(resultado, PRINCIPAL, "L32") == Decimal("60.00")

# ─── Casos de erro ───────────────────────────────────────────────────────────

def test_exercicio_anterior_sem_dados(apurar_bp):
    """Requisito: exercício anterior sem dados — coluna `None`, atual íntegra."""
    fonte = FontePorAno({2025: {1: [fp("111110100", "5.00", "F")]}})
    resultado = apurar_bp(ENTE, EXERCICIO, fonte)
    assert resultado.diagnostico.sem_dados_exercicio_anterior is True
    assert celula(resultado, PRINCIPAL, "L3", "exercicio_anterior") is None
    assert celula(resultado, PRINCIPAL, "L3") == Decimal("5.00")


def test_exercicio_sem_vigencia(apurar_bp):
    """Requisito: exercício anterior à edição 2020-01 do IPC 04."""
    from app.infra.regras.carregador import SemVigencia

    with pytest.raises(SemVigencia):
        apurar_bp(ENTE, 2019, FontePorAno({}))


def test_procedencia_declara_o_par_e_a_vigencia(apurar_bp):
    """Requisito: BP no pipeline — procedência declara matriz, saldo, competência e IPC 04."""
    resultado = apurar_bp(ENTE, EXERCICIO, FontePorAno({}))
    p = resultado.procedencia
    assert (p.documento, p.edicao) == ("IPC04", "2020-01")
    assert (p.matriz, p.tipo_saldo, p.competencia) == ("encerramento", "encerramento", 12)
    assert p.versao_regras
