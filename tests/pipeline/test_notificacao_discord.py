"""Mensagens do canal de operação no padrão do RREO e do RGF.

O embed é montado sobre um `http` dublê — nada sai para o Discord. O rótulo do ente vem de um
`consultar` dublê no lugar de `public.unidade_gestora`.
"""
from __future__ import annotations

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

VERDE, CINZA, VERMELHO, AZUL, ROXO, LARANJA = (0x2ECC71, 0x95A5A6, 0xE74C3C, 0x3498DB,
                                              0x9B59B6, 0xF39C12)
CUITEGI = "2505204"
UNIDADES = {CUITEGI: "Cuitegi - PB"}


class Webhook:
    """Captura o corpo que iria ao Discord."""

    def __init__(self):
        self.corpos: list[dict] = []

    def __call__(self, url, json, timeout):
        self.corpos.append(json)

    @property
    def embed(self) -> dict:
        return self.corpos[-1]["embeds"][0]


@pytest.fixture
def webhook():
    return Webhook()


@pytest.fixture
def discord(webhook):
    from app.infra.notificacao.discord import DiscordNotificador

    return DiscordNotificador("https://webhook.teste", http=webhook,
                              rotulo=lambda cod: UNIDADES.get(cod, cod))


def _campos(embed: dict) -> dict[str, str]:
    return {c["name"]: c["value"] for c in embed.get("fields", [])}


# ─── Requirement: Conclusão de job é notificada ─────────────────────────────

def test_anexo_concluido_no_formato_do_rgf(discord, webhook):
    """Scenario: job concluído com sucesso — título, corpo e cor do RGF."""
    from app.services.pipeline.notificacao import notificar_fim

    notificar_fim(discord, ente=CUITEGI, exercicio=2025, anexo="BF", duracao_ms=18_700,
                  desfecho="sucesso")

    assert webhook.embed["title"] == "DCA BF — Concluído ✅"
    assert webhook.embed["description"] == "**Cuitegi - PB** | 2025 | Tempo: 18.7s"
    assert webhook.embed["color"] == VERDE


def test_anexo_com_falha_traz_o_motivo_truncado(discord, webhook):
    """Requisito: falha em vermelho, com o motivo em bloco de código, até 900 caracteres."""
    from app.services.pipeline.notificacao import notificar_fim

    notificar_fim(discord, ente=CUITEGI, exercicio=2025, anexo="BP", duracao_ms=10,
                  desfecho="erro", erro="x" * 2000)

    assert webhook.embed["title"] == "DCA BP — Falhou ❌"
    assert webhook.embed["color"] == VERMELHO
    assert webhook.embed["description"] == "**Cuitegi - PB** | 2025\n```" + "x" * 900 + "```"


def test_anexo_do_cache(discord, webhook):
    """Requisito: anexo servido do cache sai em cinza, com `Dados já em cache`."""
    from app.services.pipeline.notificacao import notificar_fim

    notificar_fim(discord, ente=CUITEGI, exercicio=2025, anexo="BF", duracao_ms=0,
                  desfecho="cache")

    assert webhook.embed["title"] == "DCA BF — Cache ✅"
    assert webhook.embed["description"] == "**Cuitegi - PB** | 2025 | Dados já em cache"
    assert webhook.embed["color"] == CINZA


def test_ente_ausente_da_tabela_de_unidades():
    """Scenario: ente ausente da tabela de unidades"""
    from app.infra.notificacao.ente import rotulo_ente

    assert rotulo_ente("9999999", consultar=lambda _cod: None) == "9999999"
    assert rotulo_ente(CUITEGI, consultar=lambda _cod: ("Cuitegi", "PB")) == "Cuitegi - PB"


def test_banco_indisponivel_ao_resolver_o_ente(webhook):
    """Scenario: banco indisponível ao resolver o ente"""
    from app.infra.notificacao.discord import DiscordNotificador
    from app.infra.notificacao.ente import rotulo_ente
    from app.services.pipeline.notificacao import notificar_fim

    def fora_do_ar(_cod):
        raise ConnectionError("banco fora")

    assert rotulo_ente("1234567", consultar=fora_do_ar) == "1234567"

    discord = DiscordNotificador("https://webhook.teste", http=webhook,
                                 rotulo=lambda cod: rotulo_ente(cod, consultar=fora_do_ar))
    assert notificar_fim(discord, ente="1234567", exercicio=2025, anexo="BO", duracao_ms=5,
                         desfecho="sucesso") is True
    assert webhook.embed["description"].startswith("**1234567** | 2025")


def test_duracao_no_padrao_dos_irmaos():
    """Scenario: duração no padrão dos irmãos"""
    from app.infra.notificacao.discord import formatar_duracao

    assert [formatar_duracao(ms) for ms in (850, 18_700, 73_000, 128_000)] == [
        "0.9s", "18.7s", "1m 13s", "2m 8s"]


# ─── Requirement: Progresso do percurso é acompanhável (resumo) ──────────────

def _percurso(discord, anexos, falhas=0):
    from app.services.pipeline.notificacao import notificar_percurso

    notificar_percurso(discord, ente=CUITEGI, exercicio=2025, duracao_ms=7_900, falhas=falhas,
                       anexos=anexos, solicitante="jackson@x", fonte="siconfi")


def test_resumo_do_percurso_sem_none(discord, webhook):
    """Scenario: conclusão do percurso é notificada uma vez — resumo legível, sem `None`."""
    _percurso(discord, [
        {"anexo": "BO", "status": "ok", "duracao_ms": 3_300, "erro_detalhe": None},
        {"anexo": "BF", "status": "em_cache", "duracao_ms": None, "erro_detalhe": None},
        {"anexo": "BP", "status": "ok", "duracao_ms": 4_400, "erro_detalhe": None},
    ])

    embed = webhook.embed
    assert embed["title"] == "✅ Cuitegi - PB  2025 [Anual] — jackson@x"
    assert embed["description"] == "3 anexo(s) concluído(s) com sucesso."
    assert embed["color"] == ROXO
    campos = _campos(embed)
    assert campos["Fonte MSC"] == "SICONFI"
    assert campos["Tempo total"] == "7.9s"
    assert campos["Detalhamento"] == "BO — 3.3s ✅\nBF — cache ✅\nBP — 4.4s ✅"
    assert "Erros" not in campos
    assert "None" not in str(embed)


def test_percurso_com_falha(discord, webhook):
    """Scenario: percurso com falha"""
    _percurso(discord, [
        {"anexo": "BO", "status": "ok", "duracao_ms": 3_300, "erro_detalhe": None},
        {"anexo": "BF", "status": "erro", "duracao_ms": 1_000,
         "erro_detalhe": "fonte fora do ar"},
    ], falhas=1)

    embed = webhook.embed
    assert embed["title"].startswith("⚠️ Cuitegi - PB")
    assert embed["description"] == "Fila concluída com 1 falha(s)."
    assert embed["color"] == LARANJA
    assert _campos(embed)["Erros"] == "**BF:** fonte fora do ar"
    assert "BF — 1.0s ❌" in _campos(embed)["Detalhamento"]


# ─── Requirement: Requisição recebida é notificada ───────────────────────────

@pytest.fixture
def api(repo, lock, jobs, notificador):
    """Rotas reais com portas fakes; o JWT traz o e-mail em `sub`."""
    from app.routes import anexos as rotas
    from app.routes.dependencias import repositorio, unidade_autorizada

    def autorizada(request: Request) -> str:
        request.state.claims = {"sub": "jackson@x"}   # o que `unidade_autorizada` grava
        request.state.poderes = ("consolidado",)
        return CUITEGI

    class Fila:
        pendente = None

        def __init__(self):
            self.enfileirados = []

        def enfileirar(self, *args, **kwargs):
            self.enfileirados.append((args, kwargs))

        def enfileirar_percurso(self, *args, **kwargs):
            self.enfileirados.append((args, kwargs))

    fila = Fila()
    app = FastAPI()
    app.include_router(rotas.router)
    app.dependency_overrides[repositorio] = lambda: repo
    app.dependency_overrides[unidade_autorizada] = autorizada
    app.state.portas = {"fila_async": lambda: fila, "lock": lock, "jobs": jobs,
                        "repo_vigencias": None, "base_url": "", "notificador": notificador}
    return TestClient(app, raise_server_exceptions=False), fila


HDR = {"Authorization": "Bearer t", "X-Unidade-Id": CUITEGI}


def test_anexo_enfileirado(api, notificador):
    """Scenario: anexo enfileirado"""
    cliente, _ = api
    resposta = cliente.post(f"/dca/BP/reprocessar?anReferencia=2025&id_ente={CUITEGI}"
                            "&use_siconfi=true", headers=HDR)

    assert resposta.status_code == 202, resposta.text
    recebidas = [m for m in notificador.enviadas if m.get("tipo") == "recebida"]
    assert len(recebidas) == 1
    m = recebidas[0]
    assert (m["ente"], m["exercicio"], m["anexos"]) == (CUITEGI, 2025, ["BP"])
    assert (m["percurso"], m["forcar"], m["solicitante"], m["fonte"]) == (
        False, True, "jackson@x", "siconfi")


def test_percurso_enfileirado(api, notificador, repo):
    """Scenario: percurso enfileirado"""
    cliente, fila = api
    resposta = cliente.post(f"/batch-jobs?anReferencia=2025&id_ente={CUITEGI}", headers=HDR)

    assert resposta.status_code == 202, resposta.text
    recebidas = [m for m in notificador.enviadas if m.get("tipo") == "recebida"]
    assert len(recebidas) == 1
    assert recebidas[0]["percurso"] is True
    assert recebidas[0]["anexos"] == ["BO", "BF", "BP", "I-HI"]
    assert fila.enfileirados[0][1]["solicitante_email"] == "jackson@x"


def test_requisicao_recebida_no_formato_do_rgf(discord, webhook):
    """Requisito: a mensagem azul de requisição recebida, para anexo e para percurso."""
    from app.services.pipeline.notificacao import notificar_recebida

    notificar_recebida(discord, ente=CUITEGI, exercicio=2025, anexos=["BP"], percurso=False,
                       forcar=True, solicitante="jackson@x", fonte="siconfi")
    assert webhook.embed["title"] == (
        "DCA BP — Requisição Recebida (Reprocessar) [Anual] — jackson@x")
    assert webhook.embed["color"] == AZUL
    assert webhook.embed["description"] == (
        "Solicitação aceita e BP enfileirado.\n"
        "Ente: **Cuitegi - PB** | Exercício: **2025**\n"
        "Fonte MSC: **SICONFI**\n"
        "Fila => BP")

    notificar_recebida(discord, ente=CUITEGI, exercicio=2025, anexos=["BO", "BF", "BP"],
                       percurso=True, forcar=False, solicitante=None, fonte="publicsoft")
    assert webhook.embed["title"] == (
        "DCA — Requisição Recebida (Processar) [Anual] — desconhecido")
    assert "Fonte MSC: **MSC-SIAFIC**" in webhook.embed["description"]
    assert webhook.embed["description"].endswith("Fila => BO, BF, BP")


def test_leitura_servida_do_cache_nao_notifica(api, notificador, repo):
    """Scenario: leitura servida do cache não notifica"""
    from app.services.pipeline import apuracao
    from app.services.pipeline.cache import versao_do_pedido
    from tests.pipeline.conftest import RegistroFake

    versao = versao_do_pedido(apuracao.versao_regras(2025, "BP", None), "BP", {"fonte": "siconfi"})
    repo.gravar(RegistroFake(CUITEGI, 2025, "BP", status="ok", resultado={"matriz": {"x": {}}},
                             versao_api=apuracao.VERSAO_API, versao_regras=versao))
    cliente, _ = api
    resposta = cliente.get(f"/dca/BP?anReferencia=2025&id_ente={CUITEGI}&use_siconfi=true",
                           headers=HDR)

    assert resposta.status_code == 200, resposta.text
    assert [m for m in notificador.enviadas if m.get("tipo") == "recebida"] == []
