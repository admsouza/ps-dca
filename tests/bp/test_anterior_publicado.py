"""BP — coluna anterior pelo `DCA-Anexo I-AB` publicado (`bp-anterior-publicado-siconfi`).

`tt/dca` entra por dublê (`DCAFake`); o que está sob teste é a conversão e o motor, não a rede.
Números de Cuitegi e João Pessoa 2024 vêm da medição de `docs/evidencia-bp-publicado-2024.md`.
"""
from __future__ import annotations

from decimal import Decimal

import pytest

from app.services.bp.quadro_principal import apurar
from tests.bp.conftest import ENTE, EXERCICIO, FontePorAno, celula, fp

PRINCIPAL = "QUADRO_PRINCIPAL"
FP = "ATIVOS_PASSIVOS_FINANCEIROS"
ANT = "exercicio_anterior"


def item(cod: str, valor: str) -> dict:
    return {"cod_conta": cod, "valor": float(valor), "exercicio": 2024}


class DCAFake:
    """`SiconfiDCA.itens(ente, ano)`; registra o que foi pedido."""

    def __init__(self, itens: list[dict] | None = None):
        self._itens = itens or []
        self.chamadas: list[tuple[int, int]] = []

    def itens(self, ente: int, ano: int) -> list[dict]:
        self.chamadas.append((ente, ano))
        return list(self._itens)


FONTE_ATUAL = {EXERCICIO: {1: [fp("111110100", "26286597.15", "F")]}}


# ─── Origem escolhida pelo usuário ───────────────────────────────────────────

def test_publicado_e_o_padrao():
    """Scenario: publicado é o padrão"""
    fonte = FontePorAno(FONTE_ATUAL)
    dca = DCAFake([item("P1.1.1.1.1.00.00", "19812433.77")])
    resultado = apurar(ENTE, EXERCICIO, fonte, dca=dca)

    assert celula(resultado, PRINCIPAL, "L3", ANT) == Decimal("19812433.77")
    assert resultado.procedencia.origem_exercicio_anterior == "publicado_siconfi"
    assert dca.chamadas == [(ENTE, 2024)]
    assert {c["ano"] for c in fonte.chamadas if c["classe"] != 8} == {EXERCICIO}
    assert {(c["ano"], c["classe"]) for c in fonte.chamadas if c["ano"] == 2024} == {(2024, 8)}
    assert celula(resultado, PRINCIPAL, "L3") == Decimal("26286597.15")


def test_msc_continua_disponivel_e_igual():
    """Scenario: MSC continua disponível e igual"""
    fonte = FontePorAno({**FONTE_ATUAL, 2024: {1: [fp("111110100", "7.00", "F")]}})
    dca = DCAFake([item("P1.1.1.1.1.00.00", "999.00")])
    resultado = apurar(ENTE, EXERCICIO, fonte, anterior="msce_exercicio_anterior", dca=dca)

    assert celula(resultado, PRINCIPAL, "L3", ANT) == Decimal("7.00")
    assert celula(resultado, FP, "L2", ANT) == Decimal("7.00"), "F/P pelo atributo do fato"
    assert resultado.procedencia.origem_exercicio_anterior == "msce_exercicio_anterior"
    assert dca.chamadas == [], "origem MSC nunca consulta o tt/dca"
    assert resultado.diagnostico.sem_publicacao_exercicio_anterior is False
    assert resultado.diagnostico.conferencia_publicado is None


# ─── Conversão do publicado ──────────────────────────────────────────────────

def test_folha_publicada_sem_dupla_contagem():
    """Scenario: folha publicada, sem dupla contagem"""
    dca = DCAFake([item("P1.1.1.0.0.00.00", "100.00"), item("P1.1.1.1.0.00.00", "100.00"),
                   item("P1.1.1.1.1.00.00", "100.00")])
    resultado = apurar(ENTE, EXERCICIO, FontePorAno(FONTE_ATUAL), dca=dca)
    assert celula(resultado, PRINCIPAL, "L3", ANT) == Decimal("100.00")


def test_intra_entra_no_publicado():
    """Scenario: intra entra no publicado — sem exclusão intra, espelho do I-AB."""
    dca = DCAFake([item("P1.2.1.1.1.00.00", "10.00"), item("P1.2.1.1.2.00.00", "90.00")])
    resultado = apurar(ENTE, EXERCICIO, FontePorAno(FONTE_ATUAL), dca=dca)
    assert celula(resultado, PRINCIPAL, "L10", ANT) == Decimal("100.00")


def test_redutora_reduz_qualquer_que_seja_o_sinal_publicado():
    """Requisito: conta de natureza oposta à do grupo reduz, com qualquer sinal publicado."""
    base = [item("P1.2.3.1.1.01.01", "1000.00")]
    for sinal in ("200.00", "-200.00"):
        dca = DCAFake(base + [item("P1.2.3.8.1.01.00", sinal)])
        resultado = apurar(ENTE, EXERCICIO, FontePorAno(FONTE_ATUAL), dca=dca)
        assert celula(resultado, PRINCIPAL, "L12", ANT) == Decimal("800.00"), sinal


def test_pl_deficitario_publicado_negativo_sai_negativo():
    """Requisito: o sinal do `I-AB` é o da posição — PL deficitário vem negativo."""
    dca = DCAFake([item("P2.3.7.1.1.01.00", "-50.00"), item("P2.3.6.1.1.00.00", "20.00")])
    resultado = apurar(ENTE, EXERCICIO, FontePorAno(FONTE_ATUAL), dca=dca)
    assert celula(resultado, PRINCIPAL, "L32", ANT) == Decimal("-30.00")


def test_conta_publicada_fora_do_pcasp_nao_entra():
    """Requisito: item que não é conta (`P` + dígito) não vira registro."""
    from app.services.bp.publicado import registros_publicados

    itens = [item("AtivoFinanceiro", "5.00"), item("PassivoFinanceiro", "6.00"),
             item("SaldoPatrimonial", "-1.00"), item("P1.1.1.1.1.00.00", "3.00")]
    registros = registros_publicados(itens, _direcao())
    assert [r.conta for r in registros] == ["111110000"]


def _direcao():
    from app.infra.pcasp.natureza import do_pcasp
    from app.services.bp.publicado import DirecaoDoPublicado
    from app.services.bp.quadro_principal import _DirecaoDoBP

    return DirecaoDoPublicado(_DirecaoDoBP(do_pcasp()))


# ─── Quadro F/P ──────────────────────────────────────────────────────────────

def test_quadro_fp_pelo_publicado():
    """Scenario: quadro F/P pelo publicado"""
    dca = DCAFake([
        item("P1.1.1.1.1.00.00", "100.00"),
        item("AtivoFinanceiro", "100.00"), item("AtivoPermanente", "400.00"),
        item("PassivoFinanceiro", "30.00"), item("PassivoPermanente", "70.00"),
        item("SaldoPatrimonial", "400.00"),
    ])
    resultado = apurar(ENTE, EXERCICIO, FontePorAno(FONTE_ATUAL), dca=dca)

    assert [celula(resultado, FP, c, ANT) for c in ("L2", "L3", "L5", "L6")] == [
        Decimal("100.00"), Decimal("400.00"), Decimal("30.00"), Decimal("70.00")]
    assert celula(resultado, FP, "L1", ANT) == Decimal("500.00")
    assert celula(resultado, FP, "L4", ANT) == Decimal("100.00")
    assert celula(resultado, FP, "L7", ANT) == Decimal("400.00")
    assert resultado.diagnostico.conferencia_publicado == {
        "l7_apurado": Decimal("400.00"), "saldo_patrimonial_publicado": Decimal("400.00"),
        "diferenca": Decimal("0.00")}
    assert resultado.diagnostico.sem_atributo_fp is False
    assert not resultado.diagnostico.residuos
    assert celula(resultado, FP, "L2") == Decimal("26286597.15"), "o atual segue pela MSC"


def test_conferencia_expoe_a_diferenca_do_saldo_patrimonial():
    """Requisito: `L7` apurado × `SaldoPatrimonial` — a diferença é achado, nunca ajuste."""
    dca = DCAFake([item("P1.1.1.1.1.00.00", "1.00"),
                   item("AtivoFinanceiro", "10.00"), item("AtivoPermanente", "5.00"),
                   item("PassivoFinanceiro", "3.00"), item("PassivoPermanente", "2.00"),
                   item("SaldoPatrimonial", "9.50")])
    resultado = apurar(ENTE, EXERCICIO, FontePorAno(FONTE_ATUAL), dca=dca)
    assert celula(resultado, FP, "L7", ANT) == Decimal("10.00")
    assert resultado.diagnostico.conferencia_publicado["diferenca"] == Decimal("0.50")


def test_total_fp_nao_publicado_fica_nao_apurado():
    """Requisito: total F/P ausente do `I-AB` — `None`, e o total que o soma também."""
    dca = DCAFake([item("P1.1.1.1.1.00.00", "1.00"), item("AtivoFinanceiro", "10.00")])
    resultado = apurar(ENTE, EXERCICIO, FontePorAno(FONTE_ATUAL), dca=dca)
    assert celula(resultado, FP, "L2", ANT) == Decimal("10.00")
    assert celula(resultado, FP, "L3", ANT) is None
    assert celula(resultado, FP, "L1", ANT) is None
    assert celula(resultado, FP, "L7", ANT) is None
    assert resultado.diagnostico.conferencia_publicado is None


# ─── Casos de erro ───────────────────────────────────────────────────────────

def test_ente_sem_publicacao_no_ano_anterior():
    """Scenario: ente sem publicação no ano anterior"""
    fonte = FontePorAno({**FONTE_ATUAL, 2024: {1: [fp("111110100", "7.00", "F")]}})
    resultado = apurar(ENTE, EXERCICIO, fonte, dca=DCAFake([]))

    demais = {regra: valores for regra, valores in resultado.matriz.items()
              if not regra.startswith("bp.superavit_deficit")}
    assert all(valores[ANT] is None for valores in demais.values())
    assert resultado.diagnostico.sem_publicacao_exercicio_anterior is True
    assert celula(resultado, PRINCIPAL, "L3") == Decimal("26286597.15")
    assert {c["classe"] for c in fonte.chamadas if c["ano"] == 2024} == {8}


def test_tt_dca_fora_do_ar_e_erro_explicito():
    """Requisito: `tt/dca` indisponível — exceção após o retry, nunca a MSC no lugar."""
    from app.infra.siconfi.dca import SiconfiDCA

    esperas: list[float] = []

    def http(url, params, timeout):
        raise ConnectionError("reset")

    dca = SiconfiDCA(http=http, espera=esperas.append)
    fonte = FontePorAno({**FONTE_ATUAL, 2024: {1: [fp("111110100", "7.00", "F")]}})
    with pytest.raises(ConnectionError, match="DCA publicada indisponível"):
        apurar(ENTE, EXERCICIO, fonte, dca=dca)
    assert len(esperas) == 5
    assert 2024 not in {c["ano"] for c in fonte.chamadas}


def test_adapter_pagina_e_pede_o_iab_do_ente():
    """Requisito: o adapter segue `hasMore`, com timeout, e pede o `DCA-Anexo I-AB` do ente."""
    from app.infra.siconfi.dca import SiconfiDCA

    pedidos: list[dict] = []
    paginas = iter([{"items": [{"cod_conta": "a"}], "hasMore": True},
                    {"items": [{"cod_conta": "b"}], "hasMore": False}])

    def http(url, params, timeout):
        pedidos.append({"url": url, "timeout": timeout, **params})
        return next(paginas)

    itens = SiconfiDCA(http=http, url="https://x/ords/siconfi/", timeout=7).itens(2505204, 2024)

    assert [i["cod_conta"] for i in itens] == ["a", "b"]
    assert pedidos[0]["url"] == "https://x/ords/siconfi/tt/dca" and pedidos[0]["timeout"] == 7
    assert (pedidos[0]["an_exercicio"], pedidos[0]["no_anexo"], pedidos[0]["id_ente"]) == (
        2024, "DCA-Anexo I-AB", 2505204)
    assert [p["offset"] for p in pedidos] == [0, 5000]


def test_procedencia_e_diagnostico_serializados():
    """Requisito: a origem e o diagnóstico novo saem no dado gravado no cache."""
    from app.services.pipeline.resultado import para_dados

    dca = DCAFake([item("P1.1.1.1.1.00.00", "1.00"), item("AtivoFinanceiro", "1.00"),
                   item("AtivoPermanente", "0.00"), item("PassivoFinanceiro", "0.00"),
                   item("PassivoPermanente", "0.00"), item("SaldoPatrimonial", "1.00")])
    dados = para_dados(apurar(ENTE, EXERCICIO, FontePorAno(FONTE_ATUAL), dca=dca))
    assert dados["procedencia"]["origem_exercicio_anterior"] == "publicado_siconfi"
    assert dados["diagnostico"]["sem_publicacao_exercicio_anterior"] is False
    assert dados["diagnostico"]["conferencia_publicado"] == {
        "l7_apurado": "1.00", "saldo_patrimonial_publicado": "1.00", "diferenca": "0.00"}
