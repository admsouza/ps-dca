"""Cenários de leitura da MSC, ordem de apuração, vigência, procedência e diagnóstico."""
from __future__ import annotations

from decimal import Decimal

import pytest

from tests.bo.conftest import (
    ENTE,
    EXERCICIO,
    DirecaoFake,
    FonteFake,
    FonteVazia,
    saldo,
)

# ─── Leitura da MSC fixa em ending_balance, MSCC, classes 5 e 6 ──────────────

def test_duas_consultas_por_apuracao(apurar_quadro):
    """Scenario: duas consultas por apuração — classes 5 e 6, mesmo mês e mesmo id_tv."""
    fonte = FonteFake({5: [], 6: []})
    apurar_quadro(ente=ENTE, exercicio=EXERCICIO, fonte=fonte)
    assert len(fonte.chamadas) == 2
    assert {c["classe"] for c in fonte.chamadas} == {5, 6}
    assert {c["mes"] for c in fonte.chamadas} == {12}
    assert {c["ano"] for c in fonte.chamadas} == {EXERCICIO}


def test_paginacao_completa_da_fonte_siconfi():
    """Scenario: paginação completa da fonte SICONFI — segue hasMore/offset até o fim."""
    from app.infra.msc.siconfi import SiconfiMSC

    paginas = [
        {"items": [{"conta_contabil": "621200000", "natureza_conta": "C", "valor": 1}] * 5000,
         "hasMore": True},
        {"items": [{"conta_contabil": "621200000", "natureza_conta": "C", "valor": 1}] * 137,
         "hasMore": False},
    ]
    chamadas: list[dict] = []

    def http_fake(url, params, timeout):
        chamadas.append(dict(params))
        return paginas[len(chamadas) - 1]

    fonte = SiconfiMSC(http=http_fake)
    registros = fonte.registros(ente=ENTE, ano=EXERCICIO, mes=12, classe=6)
    assert len(registros) == 5137
    assert [c["offset"] for c in chamadas] == [0, 5000]


def test_volume_do_caso_real(apurar_quadro):
    """Scenario: volume do caso real — 4.600 registros de classe 5 e 4.320 de classe 6."""
    fonte = FonteFake({
        5: [saldo("521110000", "1.00")] * 4600,
        6: [saldo("621200000", "1.00")] * 4320,
    })
    apurar_quadro(ente=ENTE, exercicio=EXERCICIO, fonte=fonte)
    lidos = {c["classe"]: c for c in fonte.chamadas}
    assert set(lidos) == {5, 6}


def test_period_change_nao_e_consultado():
    """Requisito: a DCA lê sempre `ending_balance`; `period_change` não é consultado."""
    from app.infra.msc.siconfi import SiconfiMSC

    enviados: list[dict] = []

    def http_fake(url, params, timeout):
        enviados.append(dict(params))
        return {"items": [], "hasMore": False}

    SiconfiMSC(http=http_fake).registros(ente=ENTE, ano=EXERCICIO, mes=12, classe=6)
    assert [p["id_tv"] for p in enviados] == ["ending_balance"]
    assert all(p["co_tipo_matriz"] == "MSCC" for p in enviados)


# ─── Fontes MSC intercambiáveis atrás do mesmo contrato ──────────────────────

def test_mesma_matriz_por_fontes_diferentes(apurar_quadro):
    """Scenario: mesma matriz por fontes diferentes."""
    registros = {
        5: [saldo("521110000", "100.00", natureza_receita="1100.00.00")],
        6: [saldo("621200000", "80.00", natureza_receita="1100.00.00")],
    }
    a = apurar_quadro(ente=ENTE, exercicio=EXERCICIO, fonte=FonteFake(registros, "siconfi"))
    b = apurar_quadro(ente=ENTE, exercicio=EXERCICIO, fonte=FonteFake(registros, "publicsoft"))
    assert a.matriz == b.matriz


def test_gate_de_auditoria_reprovado(apurar_quadro):
    """Scenario: gate de auditoria da PublicSoft reprovado — sem dados, não erro nem zeros."""
    from app.infra.msc.publicsoft import PublicSoftMSC

    def http_fake(url, **kwargs):
        if "auditorias" in url:
            return {"status": "reprovado", "podeGerar": False}
        raise AssertionError("não deve buscar saldos com auditoria reprovada")

    fonte = PublicSoftMSC(
        http=http_fake, token="x",
        url_saldos="http://ente/base-demonstrativos",
        url_auditoria="http://ente/auditorias",
    )
    assert fonte.registros(ente=ENTE, ano=EXERCICIO, mes=12, classe=6) == []

    resultado = apurar_quadro(ente=ENTE, exercicio=EXERCICIO, fonte=FonteVazia())
    assert resultado.diagnostico.sem_dados is True


def test_normalizacao_de_camelcase():
    """Scenario: normalização de camelCase."""
    from app.infra.msc.normalizacao import normalizar

    bruto = {"codConta": "621200000", "naturezaConta": "C", "valor": "10.00",
             "naturezaReceita": "1100.00.00", "poderOrgao": "10"}
    r = normalizar(bruto)
    assert r.conta == "621200000"
    assert r.natureza == "C"
    assert r.natureza_receita == "1100.00.00"
    assert r.poder_orgao == "10"
    assert r.valor == Decimal("10.00")


# ─── Ordem de apuração: células, agregações, derivadas ───────────────────────

def test_derivada_verdadeira_tambem_nos_totais(apurar_quadro):
    """Scenario: derivada verdadeira também nos totais."""
    registros = {
        5: [saldo("521110000", "100.00", natureza_receita="1100.00.00"),
            saldo("521210100", "20.00", natureza_receita="1100.00.00")],
        6: [saldo("621200000", "80.00", natureza_receita="1100.00.00")],
    }
    resultado = apurar_quadro(ente=ENTE, exercicio=EXERCICIO, fonte=FonteFake(registros))
    total = resultado.matriz["bo.quadro_principal.receitas.l1"]
    assert total["saldo"] == total["receitas_realizadas"] - total["previsao_atualizada"]


def test_agregacao_propaga_nao_apurado(apurar_matriz, carregar_mapa):
    """Scenario: agregação propaga não apurado — `None` nunca vira `0` na soma."""
    direcao = DirecaoFake(credoras={"521110000"})  # 6.2.1.2 sem direção
    registros = [
        saldo("521110000", "100.00", natureza_receita="1100.00.00"),
        saldo("621200000", "80.00", natureza_receita="1100.00.00"),
    ]
    matriz = apurar_matriz(carregar_mapa(exercicio=EXERCICIO), registros, direcao)
    assert matriz.valores["bo.quadro_principal.receitas.l2"]["receitas_realizadas"] is None
    assert matriz.valores["bo.quadro_principal.receitas.l1"]["receitas_realizadas"] is None


def test_ciclo_entre_referencias_e_rejeitado(apurar_matriz, carregar_mapa, direcao_do_pcasp):
    """Scenario: ciclo entre referências é rejeitado — sem matriz parcial."""
    from app.domain.bo.matriz import CicloDeDependencia

    mapa = carregar_mapa(exercicio=EXERCICIO)
    mapa_ciclico = mapa.com_ciclo_para_teste(
        "bo.quadro_principal.receitas.l16", "bo.quadro_principal.receitas.l1")
    with pytest.raises(CicloDeDependencia) as erro:
        apurar_matriz(mapa_ciclico, [], direcao_do_pcasp())
    assert "bo.quadro_principal.receitas.l1" in str(erro.value)


# ─── Override, linha sem coluna, condicional ─────────────────────────────────

def test_superavit_financeiro_pela_conta_da_linha(apurar_quadro):
    """Scenario: superávit financeiro pela conta da linha (L29, B5)."""
    registros = {5: [saldo("522130100", "470338332.64")], 6: []}
    resultado = apurar_quadro(ente=ENTE, exercicio=EXERCICIO, fonte=FonteFake(registros))
    assert resultado.matriz["bo.quadro_principal.receitas.l29"][
        "previsao_atualizada"] == Decimal("470338332.64")


def test_composicao_da_linha_27(apurar_quadro):
    """Scenario: composição da linha 27 — L27 = L28 + L29 + L30."""
    registros = {
        5: [saldo("521110000", "12000000.00", natureza_receita="9990.00.00"),
            saldo("522130100", "470338332.64")],
        6: [],
    }
    resultado = apurar_quadro(ente=ENTE, exercicio=EXERCICIO, fonte=FonteFake(registros))
    assert resultado.matriz["bo.quadro_principal.receitas.l27"][
        "previsao_atualizada"] == Decimal("482338332.64")


def test_reserva_do_rpps_nao_produz_celula(apurar_quadro):
    """Scenario: reserva do RPPS — L51 existe na matriz sem coluna de valor."""
    resultado = apurar_quadro(ente=ENTE, exercicio=EXERCICIO, fonte=FonteFake({5: [], 6: []}))
    assert resultado.matriz["bo.quadro_principal.despesas.l51"] == {}
    aviso = " ".join(str(a) for a in resultado.diagnostico.nao_apuradas)
    assert "l51" not in aviso


def test_exercicio_superavitario(apurar_quadro):
    """Scenario: exercício superavitário — L25 sem valor, L49 com valor positivo."""
    registros = {
        5: [saldo("521110000", "1000.00", natureza_receita="1100.00.00")],
        6: [saldo("621200000", "1000.00", natureza_receita="1100.00.00"),
            saldo("622130400", "400.00", natureza_despesa="3.1.00.00.00")],
    }
    resultado = apurar_quadro(ente=ENTE, exercicio=EXERCICIO, fonte=FonteFake(registros))
    deficit = resultado.matriz["bo.quadro_principal.receitas.l25"]
    superavit = resultado.matriz["bo.quadro_principal.despesas.l49"]
    assert all(v is None for v in deficit.values())
    assert any(isinstance(v, Decimal) and v > 0 for v in superavit.values())


# ─── Resíduo de classificação ────────────────────────────────────────────────

def test_recursos_arrecadados_em_exercicios_anteriores(apurar_quadro):
    """Scenario: recursos arrecadados em exercícios anteriores — os R$ 12 mi de JP."""
    registros = {
        5: [
            saldo("521110000", "5301644648.00", natureza_receita="1100.00.00"),
            saldo("521110000", "12000000.00", natureza_receita="9.9.9.0.00.0.0"),
        ],
        6: [],
    }
    resultado = apurar_quadro(ente=ENTE, exercicio=EXERCICIO, fonte=FonteFake(registros))
    assert resultado.matriz["bo.quadro_principal.receitas.l26"][
        "previsao_inicial"] == Decimal("5301644648.00")

    residuos = resultado.diagnostico.residuos
    assert any("9.9.9.0.00.0.0" in str(r) and Decimal("12000000.00") == r.valor
               for r in residuos)


# ─── Vigência, procedência, diagnóstico ──────────────────────────────────────

def test_exercicio_e_parametro_da_carga_de_regras(carregar_mapa):
    """Scenario: exercício é parâmetro da carga de regras."""
    mapa = carregar_mapa(exercicio=2025)
    assert mapa.vigencia.edicao == "2020-01"
    assert mapa.vigencia.exercicio == 2025


def test_exercicio_descoberto(carregar_mapa):
    """Scenario: exercício descoberto — falha nomeando as vigências disponíveis."""
    from app.infra.regras.carregador import SemVigencia

    with pytest.raises(SemVigencia) as erro:
        carregar_mapa(exercicio=2010)
    assert "2010" in str(erro.value) and "2020-01" in str(erro.value)


def test_divergencia_explicavel_pelo_resultado(apurar_quadro):
    """Scenario: divergência explicável pelo resultado."""
    resultado = apurar_quadro(ente=ENTE, exercicio=EXERCICIO, fonte=FonteFake({5: [], 6: []}))
    p = resultado.procedencia
    assert p.edicao == "2020-01"
    assert p.documento == "IPC07"
    assert p.versao_regras and len(p.versao_regras) >= 8
    assert p.tabelas_stn.get("PCASP.md")
    assert p.regras_aplicadas >= 51


def test_apuracao_sem_pendencia_declara_diagnostico_vazio(apurar_quadro):
    """Scenario: apuração sem pendência — diagnóstico vazio, não omitido."""
    resultado = apurar_quadro(ente=ENTE, exercicio=EXERCICIO, fonte=FonteFake({5: [], 6: []}))
    d = resultado.diagnostico
    assert d.nao_apuradas == [] and d.residuos == []
    assert d.duracao_ms >= 0


def test_nenhuma_conta_literal_no_apurador():
    """Scenario: mapa é a única fonte de regra."""
    import re
    from pathlib import Path

    raiz = Path(__file__).resolve().parent.parent.parent / "app"
    padrao = re.compile(r"\b[5-6]\d{8}\b|\b[5-6](\.\d){3}\.\d\.\d\d\.\d\d\b")
    infratores = []
    for arquivo in raiz.rglob("*.py"):
        if arquivo.match("*/infra/pcasp/*"):
            continue
        for numero, linha in enumerate(arquivo.read_text(encoding="utf-8").splitlines(), 1):
            if padrao.search(linha) and not linha.lstrip().startswith("#"):
                infratores.append(f"{arquivo.name}:{numero}")
    assert infratores == [], "conta contábil literal fora da base canônica: " + ", ".join(
        infratores)
