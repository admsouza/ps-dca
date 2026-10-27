"""Cenários sintéticos da apuração da DFC. O serviço ainda não existe: falham na importação.

A conferência contra ente real vive em `test_conferencia_viva.py` (marker `vivo`), como no BP e
na DVP: a suíte padrão não vai à rede.
"""
from __future__ import annotations

from decimal import Decimal

from tests.bo.conftest import saldo
from tests.bp.conftest import FontePorAno
from tests.dfc.conftest import ANTERIOR, EXERCICIO, FUNCAO, JUROS, POA, TRANSFERENCIAS, celula

# Receita tributária paga/arrecadada e despesa de pessoal, com os classificadores que a DFC filtra.
RECEITA = saldo("621200000", "1000.00")._replace(natureza_receita="11125001")
PESSOAL = saldo("622130400", "400.00")._replace(natureza_despesa="31900400", funcao="04")
CAIXA_N = saldo("111110100", "900.00")
CAIXA_N1 = saldo("111110100", "300.00")


def _fonte(**por_ano):
    """`FontePorAno` com cada registro na classe da sua própria conta.

    A DFC lê as classes 1 a 6 numa tacada; repetir o mesmo registro em todas multiplicaria o
    saldo por seis.
    """
    return FontePorAno({
        int(ano): {classe: [r for r in registros if r.conta.startswith(str(classe))]
                   for classe in (1, 2, 3, 4, 5, 6)}
        for ano, registros in por_ano.items()})


def test_as_84_linhas_apuram(apurar_dfc):
    """Scenario: as 84 linhas apuram"""
    resultado = apurar_dfc(POA, EXERCICIO, _fonte(**{str(EXERCICIO): [RECEITA, PESSOAL],
                                                     str(EXERCICIO - 1): [CAIXA_N1]}))
    assert len(resultado.matriz) == 84
    sem_coluna = [n for n in resultado.diagnostico.nao_apuradas
                  if "coluna em comum" in n.motivo]
    assert not sem_coluna, sem_coluna
    for codigo in ("L1", "L2", "L12", "L17", "L26", "L34", "L36"):
        assert celula(resultado, codigo) is not None, f"{codigo} não apurou"


def test_fonte_sem_registros_nao_vira_zero(apurar_dfc):
    """Scenario: fonte sem registros não vira zero"""
    resultado = apurar_dfc(POA, EXERCICIO, _fonte())
    assert celula(resultado, "L2") is None
    assert resultado.diagnostico.sem_dados


def test_l16_nao_informada_nao_derruba_l12(apurar_dfc):
    """Scenario: L16 não informada não derruba L12"""
    resultado = apurar_dfc(POA, EXERCICIO, _fonte(**{str(EXERCICIO): [RECEITA, PESSOAL]}))
    assert celula(resultado, "L16") == Decimal("0.00")
    # L12 = L13 + L14 + L15 + L16, e L13 recebeu os 400,00 de pessoal
    assert celula(resultado, "L12") == Decimal("400.00")
    assert "L16" in resultado.diagnostico.informaveis


def test_l16_informada_entra_no_total(apurar_dfc):
    """Scenario: L16 informada entra no total"""
    resultado = apurar_dfc(POA, EXERCICIO, _fonte(**{str(EXERCICIO): [RECEITA, PESSOAL]}),
                           valores_informados={"L16": "100.00"})
    assert celula(resultado, "L16") == Decimal("100.00")
    assert celula(resultado, "L12") == Decimal("500.00")


def test_l35_e_l36_sao_as_duas_pontas_do_caixa(apurar_dfc):
    """Scenario: L35 e L36 são as duas pontas do caixa"""
    resultado = apurar_dfc(POA, EXERCICIO, _fonte(**{str(EXERCICIO): [RECEITA, CAIXA_N],
                                                     str(EXERCICIO - 1): [CAIXA_N1]}))
    assert celula(resultado, "L35") == Decimal("300.00")      # caixa de N−1
    assert celula(resultado, "L36") == celula(resultado, "L34") + Decimal("300.00")


def test_sem_msc_do_exercicio_anterior(apurar_dfc):
    """Scenario: sem MSC do exercício anterior"""
    resultado = apurar_dfc(POA, EXERCICIO, _fonte(**{str(EXERCICIO): [RECEITA]}))
    assert celula(resultado, "L35") is None
    assert resultado.diagnostico.sem_dados_exercicio_anterior


def test_identidades_do_demonstrativo_fecham(apurar_dfc):
    """Scenario: identidades do demonstrativo fecham sobre o apurado"""
    resultado = apurar_dfc(POA, EXERCICIO, _fonte(**{str(EXERCICIO): [RECEITA, PESSOAL],
                                                     str(EXERCICIO - 1): [CAIXA_N1]}))
    v = {c: celula(resultado, c) for c in
         ("L1", "L2", "L12", "L17", "L18", "L22", "L26", "L27", "L31", "L34", "L35", "L36")}
    assert v["L2"] == sum(celula(resultado, f"L{n}") for n in range(3, 12))
    assert v["L12"] == sum(celula(resultado, f"L{n}") for n in range(13, 17))
    assert v["L1"] == v["L2"] - v["L12"]
    assert v["L17"] == v["L18"] - v["L22"]
    assert v["L26"] == v["L27"] - v["L31"]
    assert v["L34"] == v["L1"] + v["L17"] + v["L26"]
    assert v["L36"] == v["L34"] + v["L35"]


def test_quadros_auxiliares_amarram_no_principal(apurar_dfc):
    """Scenario: os quadros auxiliares amarram no principal"""
    resultado = apurar_dfc(POA, EXERCICIO, _fonte(**{str(EXERCICIO): [RECEITA, PESSOAL],
                                                     str(EXERCICIO - 1): [CAIXA_N1]}))
    assert celula(resultado, "L13") == celula(resultado, "L29", quadro=FUNCAO)
    assert celula(resultado, "L14") == celula(resultado, "L4", quadro=JUROS)
    assert celula(resultado, "L10") == celula(resultado, "L7", quadro=TRANSFERENCIAS)
    assert celula(resultado, "L15") == celula(resultado, "L15", quadro=TRANSFERENCIAS)


def test_desembolso_por_funcao_separa_pela_funcao(apurar_dfc):
    """Requisito: L1–L28 do quadro de função replicam L13 filtrando a função da linha."""
    resultado = apurar_dfc(POA, EXERCICIO, _fonte(**{str(EXERCICIO): [PESSOAL]}))
    assert celula(resultado, "L4", quadro=FUNCAO) == Decimal("400.00")   # função 04
    assert celula(resultado, "L10", quadro=FUNCAO) == Decimal("0.00")    # função 10, sem fato


def test_procedencia_declara_a_fonte_da_dfc(apurar_dfc):
    """Requisito: a procedência registra o par (matriz, tipo de saldo) e as classes lidas."""
    from app.infra.msc.fonte import Matriz, TipoSaldo

    resultado = apurar_dfc(POA, EXERCICIO, _fonte(**{str(EXERCICIO): [RECEITA]}))
    p = resultado.procedencia
    assert (p.matriz, p.tipo_saldo) == (str(Matriz.ENCERRAMENTO), str(TipoSaldo.ABERTURA))
    assert p.classes == (1, 2, 3, 4, 5, 6)
    assert p.documento == "IPC08"
    assert p.regras_aplicadas == 84


def test_coluna_anterior_vem_da_msc_de_n_menos_1(apurar_dfc):
    """Requisito: a coluna do exercício anterior é apurada da MSC de N−1."""
    resultado = apurar_dfc(POA, EXERCICIO, _fonte(**{str(EXERCICIO): [RECEITA],
                                                     str(EXERCICIO - 1): [RECEITA, PESSOAL]}))
    assert celula(resultado, "L13", ANTERIOR) == Decimal("400.00")
    assert celula(resultado, "L13") == Decimal("0.00")


def test_cli_imprime_os_quatro_quadros(capsys, monkeypatch):
    """Scenario: CLI imprime os quatro quadros"""
    from app.cli import dfc as cli
    from tests.bp.conftest import FontePorAno

    monkeypatch.setattr(cli, "_fonte", lambda *_a, **_k: FontePorAno(
        {EXERCICIO: dict.fromkeys((1, 2, 3, 4, 5, 6), [RECEITA])}))
    assert cli.main([str(POA), str(EXERCICIO)]) == 0

    saida = capsys.readouterr().out
    for quadro in ("QUADRO_PRINCIPAL", "TRANSFERENCIAS_RECEBIDAS_CONCEDIDAS",
                   "DESEMBOLSOS_PESSOAL_POR_FUNCAO", "JUROS_ENCARGOS_DIVIDA"):
        assert f"== {quadro}" in saida
    assert "IPC08" in saida and "84 regras" in saida
    assert "Informáveis   L16, L21, L30" in saida


def test_cli_aceita_linha_informada(capsys, monkeypatch):
    """Requisito: `--informado L16=...` chega à apuração."""
    from app.cli import dfc as cli
    from tests.bp.conftest import FontePorAno

    monkeypatch.setattr(cli, "_fonte", lambda *_a, **_k: FontePorAno(
        {EXERCICIO: dict.fromkeys((1, 2, 3, 4, 5, 6), [RECEITA])}))
    assert cli.main([str(POA), str(EXERCICIO), "--informado", "L16=250.00"]) == 0
    assert "250,00" in capsys.readouterr().out


# Despesa de capital paga: elemento 52 (equipamentos) em modalidade 90 (aplicação direta).
# Atende aos filtros de L23 (elemento) e também aos de L25 (4.4.xx.xx.xx sem exclusão de
# modalidade 90) — é a sobreposição que o IPC 08 deixa aberta.
ATIVO = saldo("622130400", "1791501.94")._replace(natureza_despesa="44905200")
# Modalidade 32 com elemento 51: o `not_in` de L23 a recusa (`443251`), e ela é "outros".
ATIVO_EXCLUIDO_DE_L23 = saldo("622130400", "500.00")._replace(natureza_despesa="44325100")


def test_aquisicao_de_ativo_nao_entra_duas_vezes(apurar_dfc):
    """Scenario: aquisição de ativo não entra duas vezes"""
    resultado = apurar_dfc(POA, EXERCICIO, _fonte(**{str(EXERCICIO): [ATIVO]}))
    assert celula(resultado, "L23") == Decimal("1791501.94")
    assert celula(resultado, "L25") == Decimal("0.00")
    assert celula(resultado, "L22") == celula(resultado, "L23")


def test_o_que_l23_exclui_continua_em_l25(apurar_dfc):
    """Scenario: o que L23 exclui continua em L25"""
    resultado = apurar_dfc(POA, EXERCICIO,
                           _fonte(**{str(EXERCICIO): [ATIVO, ATIVO_EXCLUIDO_DE_L23]}))
    assert celula(resultado, "L23") == Decimal("1791501.94"), "o not_in de L23 recusa a 4.4.32.51"
    assert celula(resultado, "L25") == Decimal("500.00"), "e ela é 'outros', não some"
    assert celula(resultado, "L22") == Decimal("1792001.94")
