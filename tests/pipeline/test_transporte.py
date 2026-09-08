"""Acompanhamento, resumo agregado, diagnóstico, notificação e autorização.

Bloco 3 da fase TEST. É a camada que o cliente vê: como acompanha o job, o que o resumo responde
antes de existir apuração, o que o resultado declara sobre o que **não** fechou, o que a operação
recebe ao fim do job e quem pode pedir o quê.

Nenhum destes testes sobe FastAPI. O que a spec fixa é a decisão de autorizar, resumir e notificar
— a rota transporta. `autorizar` recebe a verificação de token por parâmetro (`verificar`), o que
mantém o teste sem `jose` e sem `SECRET_KEY` e é a mesma inversão que o domínio já usa.

Contrato que a F2/F3 tem de satisfazer, e que só existe aqui até ser implementado:

    app.infra.fila.job_manager.criar(jobs, job_id, ente, exercicio, anexo)  -> estado inicial
    app.infra.fila.job_manager.estado(jobs, job_id) -> {"status", "resultado", "erro", ...}
    app.infra.fila.job_manager.STATUS_JOB = ("processing", "done", "error") · JobDesconhecido
    app.infra.fila.credencial.guardar(cofre, job_id, token, ttl) / ler(cofre, job_id)
    app.services.pipeline.resumo.resumir(ente, exercicio, repo)  -> lista na ordem de ANEXOS
    app.services.pipeline.notificacao.notificar_fim(notificador, **fato)
    app.services.pipeline.job.executar(..., jobs=None, job_id=None, notificador=None)
    app.auth.autorizacao.autorizar(token, unidade, ente, verificar=None)
    app.auth.autorizacao.NaoAutenticado · NaoAutorizado · CredencialDeFonteRecusada
    app.auth.autorizacao.recusar_credencial_de_fonte(cabecalhos) · CABECALHOS_DE_FONTE
"""
from __future__ import annotations

import logging

import pytest
from cryptography.fernet import Fernet

from app.core.config import config
from tests.bo.conftest import DirecaoFake, FonteFake, registro, saldo
from tests.pipeline.conftest import (
    ANEXO,
    ENTE,
    EXERCICIO,
    VERSAO_API,
    VERSAO_REGRAS,
    RegistroFake,
)

ENTE_NUM = int(ENTE)
OUTRO_ENTE = "3550308"
CONTA_RECEITA = "521110000"
CONTA_DESPESA = "621200000"
NR = "1100.00.00"
JOB = "job-1"


class CofreFake:
    """Dublê do Redis onde o token de fonte espera pelo job: valor e TTL, nada mais."""

    def __init__(self):
        self.valores: dict[str, tuple[str, int]] = {}

    def gravar(self, chave: str, valor: str, ttl: int) -> None:
        self.valores[chave] = (valor, ttl)

    def obter(self, chave: str) -> str | None:
        par = self.valores.get(chave)
        return par[0] if par else None

    def ttl(self, chave: str) -> int | None:
        par = self.valores.get(chave)
        return par[1] if par else None


@pytest.fixture
def fonte():
    return FonteFake({
        5: [saldo(CONTA_RECEITA, "100000.00", natureza_receita=NR)],
        6: [saldo(CONTA_DESPESA, "80000.00", natureza_receita=NR)],
    })


@pytest.fixture
def apurador(fonte):
    def _apurar(ente: int, exercicio: int):
        from app.services.bo.quadro_principal import apurar
        return apurar(ente, exercicio, fonte=fonte)
    return _apurar


@pytest.fixture
def apurador_que_falha():
    def _apurar(ente: int, exercicio: int):
        raise RuntimeError("fonte devolveu 500")
    return _apurar


@pytest.fixture
def verificar_token():
    """Porta de verificação de JWT. Só `bom` é válido, e devolve a unidade autorizada."""
    def _verificar(token):
        return {"sub": 42, "unidade": ENTE} if token == "bom" else None
    return _verificar


# ─── Requirement: Acompanhamento por polling e por stream ───────────────────

def test_polling_ate_a_conclusao(repo, lock, jobs, apurador):
    """Scenario: polling até a conclusão.

    O estado evolui de `processing` para `done`, e o resultado só aparece na conclusão. Job que
    nasce `done` vazio faria o cliente parar de esperar antes de existir número.
    """
    from app.infra.fila.job_manager import STATUS_JOB, criar, estado

    criar(jobs, JOB, ente=ENTE, exercicio=EXERCICIO, anexo=ANEXO)
    em_voo = estado(jobs, JOB)
    assert em_voo["status"] == "processing"
    assert em_voo["resultado"] is None

    from app.services.pipeline.job import executar

    executar(ente=ENTE, exercicio=EXERCICIO, anexo=ANEXO, repo=repo, lock=lock,
             apurador=apurador, versao_api=VERSAO_API, versao_regras=VERSAO_REGRAS,
             jobs=jobs, job_id=JOB)

    concluido = estado(jobs, JOB)
    assert concluido["status"] == "done"
    assert concluido["resultado"]["matriz"]
    assert set(STATUS_JOB) == {"processing", "done", "error"}


def test_job_com_erro_expoe_o_motivo(repo, lock, jobs, apurador_que_falha):
    """Scenario: job com erro expõe o motivo.

    O motivo tem de estar nos dois lugares: no estado do job, que o cliente consulta, e no cache da
    identidade, que a próxima requisição lê. Um erro só no log obriga acesso ao servidor para
    responder "por que não veio o número".
    """
    from app.infra.fila.job_manager import criar, estado
    from app.services.pipeline.job import executar

    criar(jobs, JOB, ente=ENTE, exercicio=EXERCICIO, anexo=ANEXO)
    executar(ente=ENTE, exercicio=EXERCICIO, anexo=ANEXO, repo=repo, lock=lock,
             apurador=apurador_que_falha, versao_api=VERSAO_API, versao_regras=VERSAO_REGRAS,
             jobs=jobs, job_id=JOB)

    falho = estado(jobs, JOB)
    assert falho["status"] == "error"
    assert "500" in falho["erro"]

    gravado = repo.obter(ENTE, EXERCICIO, ANEXO)
    assert gravado.status == "erro"
    assert gravado.erro_detalhe == falho["erro"]
    assert lock.tomados == {}, "lock não liberado no caminho de erro"


# ─── Requirement: Resumo agregado responde sempre ───────────────────────────

def test_bootstrap_sem_nenhum_cache(repo, fila):
    """Scenario: bootstrap sem nenhum cache.

    `200` com os oito anexos em `sem_cache`, na ordem canônica, e **nenhum** job enfileirado — o
    resumo é leitura. Anexo sem implementação aparece, não é omitido.
    """
    from app.services.pipeline.registry import ANEXOS
    from app.services.pipeline.resumo import resumir

    resumo = resumir(ente=ENTE, exercicio=EXERCICIO, repo=repo)

    assert [e["anexo"] for e in resumo] == list(ANEXOS)
    assert {e["status"] for e in resumo} == {"sem_cache"}
    assert fila.enfileirados == [], "o resumo enfileirou job"


def test_metadados_sem_payload(repo, fila):
    """Scenario: metadados sem payload.

    Status, data de cálculo, versões e duração — e nenhuma entrada com o resultado. Devolver o
    demonstrativo em um resumo de oito anexos entrega megabytes onde se pediu um cabeçalho.
    """
    from app.services.pipeline.resumo import resumir

    repo.gravar(RegistroFake(ENTE, EXERCICIO, ANEXO, status="ok",
                             resultado={"matriz": {"L1": {"previsao_atualizada": "1.00"}}},
                             diagnostico={"duracao_ms": 812, "nao_apuradas": [], "residuos": []}))

    resumo = resumir(ente=ENTE, exercicio=EXERCICIO, repo=repo)
    bo = next(e for e in resumo if e["anexo"] == ANEXO)

    assert bo["status"] == "ok"
    assert bo["calculado_em"] and bo["duracao_ms"] == 812
    assert bo["versao_api"] == VERSAO_API and bo["versao_regras"] == VERSAO_REGRAS
    assert not any("resultado" in e or "matriz" in e for e in resumo), \
        "o resumo devolveu o resultado do demonstrativo"
    assert fila.enfileirados == []


# ─── Requirement: Diagnóstico da apuração acompanha o resultado ─────────────

def test_celula_nao_apurada_e_visivel_ao_consumidor(repo, lock):
    """Scenario: célula não apurada é visível ao consumidor.

    Conta fora do PCASP: sem direção conhecida, a célula é `None` com motivo — nunca `0`. O motivo
    viaja no resultado gravado, e não só no log.
    """
    from app.services.bo.quadro_principal import apurar
    from app.services.pipeline.job import executar

    desconhecida = FonteFake({5: [registro("999999999", "C", "1.00", natureza_receita=NR)], 6: []})

    def apurador(ente, exercicio):
        return apurar(ente, exercicio, fonte=desconhecida, direcao=DirecaoFake())

    executar(ente=ENTE, exercicio=EXERCICIO, anexo=ANEXO, repo=repo, lock=lock,
             apurador=apurador, versao_api=VERSAO_API, versao_regras=VERSAO_REGRAS)

    diagnostico = repo.obter(ENTE, EXERCICIO, ANEXO).diagnostico
    assert diagnostico["nao_apuradas"], "célula sem direção não foi declarada"
    assert any("999999999" in str(a) or "direção" in str(a).lower()
               for a in diagnostico["nao_apuradas"]), diagnostico["nao_apuradas"]


def test_apuracao_integra_tambem_declara_diagnostico(repo, lock, apurador):
    """Scenario: apuração íntegra também declara diagnóstico.

    Vazio **declarado**, não omitido: consumidor que não encontra a chave não sabe se a apuração
    fechou ou se a versão do produtor não a produzia.
    """
    from app.services.pipeline.job import executar

    executar(ente=ENTE, exercicio=EXERCICIO, anexo=ANEXO, repo=repo, lock=lock,
             apurador=apurador, versao_api=VERSAO_API, versao_regras=VERSAO_REGRAS)

    diagnostico = repo.obter(ENTE, EXERCICIO, ANEXO).diagnostico
    assert diagnostico is not None
    assert set(diagnostico) >= {"nao_apuradas", "residuos", "duracao_ms"}
    assert diagnostico["residuos"] == []
    assert isinstance(diagnostico["duracao_ms"], int)


# ─── Requirement: Conclusão de job é notificada ─────────────────────────────

def test_job_concluido_com_sucesso(repo, lock, notificador, apurador):
    """Scenario: job concluído com sucesso.

    Ente, exercício, anexo, duração e desfecho — o suficiente para a operação saber o que rodou sem
    abrir o banco.
    """
    from app.services.pipeline.job import executar

    executar(ente=ENTE, exercicio=EXERCICIO, anexo=ANEXO, repo=repo, lock=lock,
             apurador=apurador, versao_api=VERSAO_API, versao_regras=VERSAO_REGRAS,
             notificador=notificador)

    assert len(notificador.enviadas) == 1
    aviso = notificador.enviadas[0]
    assert (aviso["ente"], aviso["exercicio"], aviso["anexo"]) == (ENTE, EXERCICIO, ANEXO)
    assert aviso["desfecho"] == "sucesso"
    assert isinstance(aviso["duracao_ms"], int)


def test_job_com_erro_tambem_notifica(repo, lock, notificador, apurador_que_falha):
    """Scenario: job com erro também notifica.

    Notificar só o sucesso é o pior arranjo possível: silêncio passa a significar duas coisas —
    nada rodou, ou rodou e quebrou.
    """
    from app.services.pipeline.job import executar

    executar(ente=ENTE, exercicio=EXERCICIO, anexo=ANEXO, repo=repo, lock=lock,
             apurador=apurador_que_falha, versao_api=VERSAO_API, versao_regras=VERSAO_REGRAS,
             notificador=notificador)

    assert len(notificador.enviadas) == 1
    aviso = notificador.enviadas[0]
    assert aviso["desfecho"] == "erro"
    assert "500" in aviso["erro"]


def test_canal_de_notificacao_indisponivel(repo, lock, notificador, apurador, caplog):
    """Scenario: canal de notificação indisponível.

    O resultado permanece gravado e a falha do canal vai para o log. Deixar a exceção do webhook
    subir transformaria job concluído em job perdido.
    """
    from app.services.pipeline.job import executar

    notificador.falhar = True

    with caplog.at_level(logging.WARNING):
        executar(ente=ENTE, exercicio=EXERCICIO, anexo=ANEXO, repo=repo, lock=lock,
                 apurador=apurador, versao_api=VERSAO_API, versao_regras=VERSAO_REGRAS,
                 notificador=notificador)

    gravado = repo.obter(ENTE, EXERCICIO, ANEXO)
    assert gravado.status == "ok" and gravado.resultado
    assert notificador.enviadas == []
    assert any("notific" in m.lower() for m in caplog.messages), \
        "falha de notificação não foi logada"


def test_notificacao_nao_configurada(repo, lock, apurador):
    """Scenario: notificação não configurada.

    Sem canal, o job roda igual e nada é notificado — ambiente local não precisa de webhook para
    apurar.
    """
    from app.services.pipeline.job import executar

    executar(ente=ENTE, exercicio=EXERCICIO, anexo=ANEXO, repo=repo, lock=lock,
             apurador=apurador, versao_api=VERSAO_API, versao_regras=VERSAO_REGRAS,
             notificador=None)

    assert repo.obter(ENTE, EXERCICIO, ANEXO).status == "ok"


# ─── Requirement: Autorização por unidade em toda rota de anexo ─────────────

def test_token_ausente_ou_invalido(fila, verificar_token):
    """Scenario: token ausente ou inválido.

    `401` nos dois casos, e nenhum job criado — autenticar depois de enfileirar deixaria anônimo
    consumindo worker.
    """
    from app.auth.autorizacao import NaoAutenticado, autorizar

    for token in (None, "", "lixo"):
        with pytest.raises(NaoAutenticado):
            autorizar(token=token, unidade=ENTE, ente=ENTE, verificar=verificar_token)

    assert fila.enfileirados == []


def test_ente_diferente_do_autorizado(fila, verificar_token):
    """Scenario: ente diferente do autorizado.

    `403` e nenhum dado do ente devolvido. A unidade vem do token verificado, não do cabeçalho
    cru: aceitar `X-Unidade-Id` sem confrontar o token deixaria qualquer autenticado ler qualquer
    ente.
    """
    from app.auth.autorizacao import NaoAutorizado, autorizar

    with pytest.raises(NaoAutorizado):
        autorizar(token="bom", unidade=ENTE, ente=OUTRO_ENTE, verificar=verificar_token)

    with pytest.raises(NaoAutorizado):
        autorizar(token="bom", unidade=OUTRO_ENTE, ente=OUTRO_ENTE, verificar=verificar_token)

    assert autorizar(token="bom", unidade=ENTE, ente=ENTE,
                     verificar=verificar_token)["unidade"] == ENTE
    assert fila.enfileirados == []


def test_credencial_de_fonte_vinda_do_browser():
    """Scenario: credencial de fonte vinda do browser.

    `x-authorization` e `token_ps` chegando na requisição são recusados, e a credencial não é usada
    para consultar a fonte. Herdado de RREO/RGF sem exceção.
    """
    from app.auth.autorizacao import (
        CABECALHOS_DE_FONTE,
        CredencialDeFonteRecusada,
        recusar_credencial_de_fonte,
    )

    assert set(CABECALHOS_DE_FONTE) >= {"x-authorization", "token_ps"}

    for cabecalho in CABECALHOS_DE_FONTE:
        with pytest.raises(CredencialDeFonteRecusada):
            recusar_credencial_de_fonte({cabecalho: "segredo-do-browser"})
        with pytest.raises(CredencialDeFonteRecusada):
            recusar_credencial_de_fonte({cabecalho.upper(): "segredo-do-browser"})

    recusar_credencial_de_fonte({"authorization": "Bearer bom", "x-unidade-id": ENTE})


def test_token_de_fonte_no_armazenamento_do_job(monkeypatch):
    """Scenario: token de fonte no armazenamento do job.

    Cifrado e com TTL do job: acesso ao Redis não pode virar acesso ao token da fonte (OWASP A02).
    O teste procura o segredo em claro no armazenamento — é o que um `dump` do Redis mostraria.
    """
    from app.infra.fila.credencial import guardar, ler

    # Chave dedicada de teste. O produto **exige** `TOKEN_ENCRYPTION_KEY` e não tem fallback
    # silencioso: cifra sem chave configurada seria segurança de fachada.
    monkeypatch.setenv("TOKEN_ENCRYPTION_KEY", Fernet.generate_key().decode())
    config.cache_clear()

    cofre, segredo = CofreFake(), "token-da-publicsoft-123"
    chave = guardar(cofre, job_id=JOB, token=segredo, ttl=3600)

    assert chave.startswith("dca:")
    assert cofre.ttl(chave) == 3600, "credencial sem TTL sobrevive ao job"
    assert segredo not in str(cofre.valores), "token gravado em claro"
    assert ler(cofre, job_id=JOB) == segredo
    assert ler(cofre, job_id="job-inexistente") is None
