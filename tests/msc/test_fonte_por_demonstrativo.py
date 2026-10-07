"""Cenários de `dca/fonte-msc` — de onde cada demonstrativo lê os saldos.

Sem rede: os adapters são exercitados com um transporte fake, e a tabela é dado puro. A
equivalência entre os pares (337 células × 2 entes) é **medição**, registrada em
`docs/evidencia-matriz-mscc-vs-msce.md`, não teste de suíte.
"""
from __future__ import annotations

import pytest


@pytest.fixture
def fonte_de():
    from app.infra.msc.fonte import fonte_de as f
    return f


@pytest.fixture
def enums():
    from app.infra.msc.fonte import Matriz, TipoSaldo
    return Matriz, TipoSaldo


# ─── Par declarado por demonstrativo e competência ───────────────────────────

def test_balanco_patrimonial_e_a_unica_excecao(fonte_de, enums):
    """Scenario: o Balanço Patrimonial é a única exceção."""
    Matriz, TipoSaldo = enums
    assert fonte_de("BP").tipo_saldo is TipoSaldo.ENCERRAMENTO
    for demonstrativo in ("BO", "BF", "DVP", "DFC"):
        assert fonte_de(demonstrativo).tipo_saldo is TipoSaldo.ABERTURA
    for demonstrativo in ("BO", "BF", "BP", "DVP", "DFC"):
        assert fonte_de(demonstrativo).matriz is Matriz.ENCERRAMENTO


def test_combinacao_errada_e_inexprimivel(fonte_de, enums):
    """Scenario: combinação errada é inexprimível."""
    Matriz, TipoSaldo = enums
    for demonstrativo in ("BO", "BF", "DVP", "DFC"):
        fonte = fonte_de(demonstrativo)
        assert not (fonte.matriz is Matriz.ENCERRAMENTO
                    and fonte.tipo_saldo is TipoSaldo.ENCERRAMENTO)


def test_demonstrativo_desconhecido(fonte_de):
    """Scenario: demonstrativo desconhecido."""
    with pytest.raises(LookupError) as erro:
        fonte_de("XPTO")
    mensagem = str(erro.value)
    assert "XPTO" in mensagem
    for conhecido in ("BO", "BF", "BP", "DVP", "DFC"):
        assert conhecido in mensagem


def test_competencia_mensal_usa_a_matriz_consolidada(fonte_de, enums):
    """Scenario: competência mensal usa a matriz consolidada."""
    Matriz, TipoSaldo = enums
    mensal = fonte_de("BO", competencia=6)
    assert mensal.matriz is Matriz.CONSOLIDADA
    assert mensal.tipo_saldo is TipoSaldo.ENCERRAMENTO

    anual = fonte_de("BO", competencia=12)
    assert anual.matriz is Matriz.ENCERRAMENTO
    assert anual.tipo_saldo is TipoSaldo.ABERTURA


@pytest.mark.parametrize("competencia", [1, 3, 6, 9, 11])
def test_matriz_de_encerramento_nao_existe_fora_de_dezembro(fonte_de, enums, competencia):
    """Scenario: a matriz de encerramento não existe fora de dezembro."""
    Matriz, _ = enums
    assert fonte_de("BP", competencia=competencia).matriz is Matriz.CONSOLIDADA


def test_competencia_invalida_e_recusada(fonte_de):
    """Requisito: competência fora de 1–12 é recusada na entrada."""
    for invalida in (0, 13, -1):
        with pytest.raises(ValueError):
            fonte_de("BO", competencia=invalida)


def test_classes_lidas_por_demonstrativo(fonte_de):
    """Requisito: as classes contábeis lidas entram na mesma tabela do par."""
    assert fonte_de("BO").classes == (5, 6)
    # BP: `L5` Passivo Financeiro lê RP e créditos empenhados a liquidar, da classe 6 (D3).
    assert fonte_de("BP").classes == (1, 2, 6)
    assert fonte_de("DVP").classes == (3, 4)
    assert set(fonte_de("BF").classes) == {1, 2, 3, 4, 5, 6}


# ─── Saldo de abertura do exercício ──────────────────────────────────────────

def test_abertura_do_exercicio_vem_do_exercicio_anterior():
    """Scenario: abertura do exercício em João Pessoa 2025."""
    from app.infra.msc.fonte import leitura_de_abertura_do_exercicio

    assert leitura_de_abertura_do_exercicio(2025) == (2024, 12)


# ─── Tradução no adapter ─────────────────────────────────────────────────────

class TransporteFake:
    """Registra as chamadas e devolve uma página vazia."""

    def __init__(self, paginas=None):
        self.chamadas: list[dict] = []
        self._paginas = paginas or {}

    def __call__(self, url, params, timeout):
        self.chamadas.append(dict(params))
        return self._paginas.get(params.get("offset", 0), {"items": [], "hasMore": False})


def test_traducao_no_adapter(enums):
    """Scenario: tradução no adapter."""
    from app.infra.msc.siconfi import SiconfiMSC

    Matriz, TipoSaldo = enums
    http = TransporteFake()
    SiconfiMSC(http=http).registros(
        ente=2505204, ano=2025, mes=12, classe=6,
        matriz=Matriz.ENCERRAMENTO, tipo_saldo=TipoSaldo.ABERTURA,
    )
    assert http.chamadas[0]["co_tipo_matriz"] == "MSCE"
    assert http.chamadas[0]["id_tv"] == "beginning_balance"


def test_dominio_nao_conhece_a_api():
    """Scenario: tradução no adapter — o núcleo não menciona os nomes da API."""
    from pathlib import Path

    raiz = Path(__file__).resolve().parents[2] / "app" / "domain"
    proibidos = ("id_tv", "MSCC", "MSCE", "beginning_balance", "ending_balance")
    for arquivo in raiz.rglob("*.py"):
        texto = arquivo.read_text(encoding="utf-8")
        for termo in proibidos:
            assert termo not in texto, f"{arquivo.name} menciona {termo}"


# ─── Resiliência ─────────────────────────────────────────────────────────────

class TransporteInstavel:
    """Falha `quedas` vezes por offset antes de responder."""

    def __init__(self, quedas: int, paginas: dict):
        self.quedas = quedas
        self._paginas = paginas
        self._falhas: dict[int, int] = {}
        self.chamadas = 0

    def __call__(self, url, params, timeout):
        self.chamadas += 1
        offset = params.get("offset", 0)
        vistas = self._falhas.get(offset, 0)
        if vistas < self.quedas:
            self._falhas[offset] = vistas + 1
            raise ConnectionError("conexão abortada pelo host remoto")
        return self._paginas[offset]


def _item(conta: str) -> dict:
    return {"conta_contabil": conta, "natureza_conta": "C", "valor": "10.00"}


def test_reset_de_conexao_no_meio_da_paginacao(enums):
    """Scenario: reset de conexão no meio da paginação."""
    from app.infra.msc.siconfi import SiconfiMSC

    Matriz, TipoSaldo = enums
    paginas = {
        0: {"items": [_item("621200000")] * 3, "hasMore": True},
        5000: {"items": [_item("621300000")] * 2, "hasMore": False},
    }
    http = TransporteInstavel(quedas=2, paginas=paginas)
    registros = SiconfiMSC(http=http, espera=lambda _s: None).registros(
        ente=1, ano=2025, mes=12, classe=6,
        matriz=Matriz.CONSOLIDADA, tipo_saldo=TipoSaldo.ENCERRAMENTO,
    )
    assert len(registros) == 5


def test_tentativas_esgotadas(enums):
    """Scenario: tentativas esgotadas."""
    from app.infra.msc.siconfi import SiconfiMSC

    Matriz, TipoSaldo = enums
    http = TransporteInstavel(quedas=99, paginas={0: {"items": [], "hasMore": False}})
    with pytest.raises(ConnectionError) as erro:
        SiconfiMSC(http=http, espera=lambda _s: None).registros(
            ente=1, ano=2025, mes=12, classe=5,
            matriz=Matriz.CONSOLIDADA, tipo_saldo=TipoSaldo.ENCERRAMENTO,
        )
    mensagem = str(erro.value)
    assert "classe 5" in mensagem and "offset 0" in mensagem
