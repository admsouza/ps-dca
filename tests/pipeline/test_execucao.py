"""Contrato de execução da plataforma — lock, isolamento de estado e quem pode calcular.

Bloco 1 da fase TEST. O que estes testes fixam é **onde** o cálculo roda e **de quem** é o estado
de execução, não o cálculo em si — esse já está verificado na F1.

Contrato que a F2/F3 tem de satisfazer, e que só existe aqui até ser implementado:

    app.services.pipeline.job.executar(ente, exercicio, anexo, repo, lock, apurador,
                                       versao_api, versao_regras)
    app.services.pipeline.startup.preparar(lock)          -> nº de órfãos liberados
    app.services.pipeline.resultado.para_dados(Resultado)  -> dict serializável
    app.infra.fila.chaves        FILA · PREFIXO · job/lock/resultado · PREFIXO_MSC · msc
    app.infra.fila.serializacao  serializar/desserializar · PayloadInvalido
    app.infra.msc.cache.ler_ou_baixar(fonte, cache, ente, ano, mes, classe)

Imports de `app.` são tardios de propósito: a fase TEST falha no comportamento, com a coleta
funcionando. Exceções são sempre nomeadas — `pytest.raises(Exception)` ficaria verde no
`ModuleNotFoundError` e não testaria nada.
"""
from __future__ import annotations

import logging
import pickle
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from tests.bo.conftest import FonteFake, saldo
from tests.conftest import RAIZ_REPO
from tests.pipeline.conftest import (
    ANEXO,
    ENTE,
    EXERCICIO,
    VERSAO_API,
    VERSAO_REGRAS,
    RegistroFake,
)
from tests.test_fronteira_camadas import _fecho_de, _importados

ENTE_NUM = int(ENTE)


class CacheFake:
    """Dublê do Redis de dados: dicionário puro, sem TTL nem serialização."""

    def __init__(self, conteudo: dict | None = None):
        self.conteudo = dict(conteudo or {})

    def obter(self, chave: str):
        return self.conteudo.get(chave)

    def gravar(self, chave: str, valor) -> None:
        self.conteudo[chave] = valor


CONTA_RECEITA = "521110000"
CONTA_DESPESA = "621200000"
NR = "1100.00.00"


@pytest.fixture
def fonte():
    """Fonte mínima, com saldo em uma conta real de receita e uma de despesa."""
    return FonteFake({
        5: [saldo(CONTA_RECEITA, "100000.00", natureza_receita=NR)],
        6: [saldo(CONTA_DESPESA, "80000.00", natureza_receita=NR)],
    })


@pytest.fixture
def apurador(fonte):
    """O apurador que rota, worker e CLI compartilham, já com a fonte ligada.

    Direção do saldo vem do PCASP real: aqui o que está sob teste é o caminho de execução, e
    substituir a direção por dublê testaria o dublê.
    """
    def _apurar(ente: int, exercicio: int):
        from app.services.bo.quadro_principal import apurar
        return apurar(ente, exercicio, fonte=fonte)
    return _apurar


# ─── Requirement: Rota e worker apenas orquestram ────────────────────────────

def test_apuracao_alcancavel_sem_rota_e_sem_worker(apurador):
    """Scenario: apuração é alcançável sem rota e sem worker.

    Chamada direta produz resultado completo, e nenhuma etapa do cálculo depende de código que só
    existe na rota ou no worker — verificado pelo fecho transitivo dos imports do serviço.
    """
    from app.services.pipeline.resultado import para_dados

    dados = para_dados(apurador(ENTE_NUM, EXERCICIO))
    assert dados["matriz"], "apuração direta não produziu matriz"
    assert dados["procedencia"]["versao_regras"], "resultado incompleto: sem procedência"
    assert "diagnostico" in dados

    fecho = _fecho_de(RAIZ_REPO / "app" / "services" / "bo")
    intrusos = [m for m in fecho if m.startswith(("app.routes", "app.api", "worker"))]
    assert not intrusos, f"apuração depende de código de transporte: {intrusos}"


def test_rota_nao_consulta_a_fonte_de_dados():
    """Scenario: fonte de dados não é consultada pela rota.

    Fecho transitivo de `app/routes/`: nenhuma consulta à MSC pode partir do processo da API — nem
    por adapter, nem por `requests` direto. A rota lê cache, enfileira e responde.
    """
    rotas = RAIZ_REPO / "app" / "routes"
    assert rotas.is_dir(), "app/routes/ não existe (F2 não implementada)"

    fecho = _fecho_de(rotas)
    violacoes = [
        f"{modulo} importa {nome}"
        for modulo, caminho in sorted(fecho.items())
        for nome in sorted(_importados(caminho))
        if nome.startswith("app.infra.msc") or nome.split(".")[0] == "requests"
    ]
    assert not violacoes, "a rota alcança a fonte de dados:\n  " + "\n  ".join(violacoes)


# ─── Requirement: Lock por identidade com recuperação de órfão ───────────────

def test_segundo_job_para_a_mesma_identidade(pedido, repo, fila, lock):
    """Scenario: segundo job para a mesma identidade.

    A requisição recebe o `job_id` **existente**, e `estado_job="already_queued"` a informa de que
    o job é de outro requisitante. A tensão com o `Scenario: processamento já em voo` do ciclo
    ("`202` sem `job_id`") foi resolvida medindo o consumidor: o front trata `202` sem `job_id`
    como erro no caminho compartilhado, e já sabe renderizar `already_queued`.
    """
    repo.gravar(RegistroFake(ENTE, EXERCICIO, ANEXO, status="processando", resultado=None))
    lock.adquirir(ENTE, EXERCICIO, ANEXO, "job-em-voo")

    r = pedido()
    assert r.status == 202
    assert r.job_id == "job-em-voo"
    assert r.estado_job == "already_queued"
    assert fila.enfileirados == [], "segundo job enfileirado para identidade já em voo"


def test_worker_reiniciado_deixa_lock_orfao(pedido, repo, fila, lock, caplog):
    """Scenario: worker reiniciado deixa lock órfão.

    Lock cujo job não está mais em execução é liberado, o evento é logado e um job novo nasce. Sem
    isso a identidade fica bloqueada até alguém apagar a chave à mão.
    """
    identidade = (ENTE, EXERCICIO, ANEXO)
    repo.gravar(RegistroFake(ENTE, EXERCICIO, ANEXO, status="processando", resultado=None))
    lock.adquirir(*identidade, "job-morto")
    lock.orfaos.add(identidade)

    with caplog.at_level(logging.WARNING):
        r = pedido()

    assert r.status == 202
    assert r.job_id and r.job_id != "job-morto"
    assert len(fila.enfileirados) == 1
    assert lock.tomados[identidade] == r.job_id, "identidade ficou bloqueada pelo lock órfão"
    assert any("órf" in m.lower() or "orf" in m.lower() for m in caplog.messages), \
        "liberação de lock órfão não foi logada"


def test_limpeza_no_startup_do_worker(lock):
    """Scenario: limpeza no startup do worker.

    `preparar` é service, não `worker.py`: o worker segue wrapper fino que delega, e o startup
    fica testável sem `arq` no processo do teste.
    """
    from app.services.pipeline.startup import preparar

    lock.tomados[(ENTE, EXERCICIO, ANEXO)] = "job-morto"
    lock.orfaos.add((ENTE, EXERCICIO, ANEXO))

    assert preparar(lock) == 1
    assert lock.limpezas == 1
    assert lock.tomados == {}


# ─── Requirement: Apuração não roda no processo da API ───────────────────────

def test_cache_miss_nao_bloqueia_a_resposta(pedido, fila, monkeypatch):
    """Scenario: cache miss não bloqueia a resposta.

    A apuração é sabotada: se o ciclo da requisição a chamar, o teste quebra com a mensagem abaixo
    em vez de passar por acidente de rapidez.
    """
    import app.services.bo.quadro_principal as qp

    def explodir(*_a, **_k):
        raise AssertionError("apuração executada no ciclo da requisição")

    monkeypatch.setattr(qp, "apurar", explodir)

    r = pedido()
    assert r.status == 202
    assert r.job_id
    assert fila.enfileirados == [((ENTE, EXERCICIO, ANEXO), r.job_id)], \
        "apuração não foi delegada ao worker"


def test_redeploy_da_api_nao_interrompe_job(pedido, repo, lock, apurador):
    """Scenario: redeploy da API não interrompe job.

    O estado do job vive no repositório e no lock, não no processo da API. O worker termina e
    grava; o cliente que volta a consultar recebe 200.
    """
    from app.services.pipeline.job import executar

    primeira = pedido()
    assert primeira.status == 202 and primeira.job_id

    # A API "reinicia": nada do ciclo anterior sobrevive em memória, só repo, fila e lock.
    executar(ente=ENTE, exercicio=EXERCICIO, anexo=ANEXO, repo=repo, lock=lock,
             apurador=apurador, versao_api=VERSAO_API, versao_regras=VERSAO_REGRAS)

    gravado = repo.obter(ENTE, EXERCICIO, ANEXO)
    assert gravado.status == "ok" and gravado.resultado
    assert lock.tomados == {}, "lock não liberado ao fim do job"

    depois = pedido()
    assert depois.status == 200
    assert depois.resultado == gravado.resultado


def test_reapuracao_recarimba_calculado_em(repo, lock, apurador):
    """Requisito: reapuração recarimba `calculado_em` — o front lê daqui o "processado em"."""
    from app.services.pipeline.job import executar

    antiga = datetime(2020, 1, 1, tzinfo=UTC)
    repo.gravar(RegistroFake(id_ente=ENTE, an_referencia=EXERCICIO, anexo=ANEXO,
                             status="ok", resultado={"x": 1}, calculado_em=antiga))
    executar(ente=ENTE, exercicio=EXERCICIO, anexo=ANEXO, repo=repo, lock=lock,
             apurador=apurador, versao_api=VERSAO_API, versao_regras=VERSAO_REGRAS)

    assert repo.obter(ENTE, EXERCICIO, ANEXO).calculado_em > antiga


# ─── Requirement: Serviço de apuração chamável por rota, worker e CLI ───────

def test_mesma_apuracao_por_caminhos_diferentes(repo, lock, apurador):
    """Scenario: mesma apuração por caminhos diferentes.

    Worker e linha de comando chamam o mesmo serviço e serializam pela mesma função. Cópia própria
    da serialização no CLI faria as duas saídas divergirem em silêncio.
    """
    from app.services.pipeline.job import executar
    from app.services.pipeline.resultado import para_dados

    executar(ente=ENTE, exercicio=EXERCICIO, anexo=ANEXO, repo=repo, lock=lock,
             apurador=apurador, versao_api=VERSAO_API, versao_regras=VERSAO_REGRAS)
    pelo_worker = repo.obter(ENTE, EXERCICIO, ANEXO).resultado

    pela_linha_de_comando = para_dados(apurador(ENTE_NUM, EXERCICIO))

    assert pelo_worker["matriz"] == pela_linha_de_comando["matriz"]
    assert pelo_worker["procedencia"] == pela_linha_de_comando["procedencia"]

    fonte_cli = (RAIZ_REPO / "app" / "cli" / "bo.py").read_text(encoding="utf-8")
    assert "para_dados" in fonte_cli, "o CLI mantém serialização própria, que vai divergir"


# ─── Requirement: Estado de execução isolado; cache de dados compartilhado ──

def test_job_nao_vaza_entre_pipelines():
    """Scenario: job não vaza entre pipelines.

    Fila própria e prefixo próprio para job, lock e resultado. O cache de dados da MSC é o único
    espaço compartilhado, e por isso mora em outro prefixo.
    """
    from app.infra.fila import chaves

    assert chaves.FILA == "arq:queue:dca"
    assert chaves.PREFIXO == "dca:"

    produzidas = (chaves.job("job-1"),
                  chaves.lock(ENTE, EXERCICIO, ANEXO),
                  chaves.resultado("job-1"))
    assert all(c.startswith(chaves.PREFIXO) for c in produzidas), produzidas
    assert not any(c.startswith(("rreo", "rgf", chaves.PREFIXO_MSC)) for c in produzidas)


def test_dado_de_msc_ja_em_cache_e_reaproveitado(fonte):
    """Scenario: dado de MSC já em cache é reaproveitado.

    O recorte foi cacheado por outro pipeline, sob o prefixo comum. A DCA lê do cache e **não**
    consulta a fonte — é o reuso que justifica compartilhar `msc_cache:`.
    """
    from app.infra.fila import chaves
    from app.infra.msc.cache import ler_ou_baixar

    recorte = dict(ente=ENTE_NUM, ano=EXERCICIO, mes=12, classe=5)
    chave = chaves.msc(**recorte)
    assert chave.startswith("msc_cache:"), chave

    ja_baixado = [{"conta": CONTA_RECEITA, "natureza": "C", "valor": "1.00"}]
    cache = CacheFake({chave: ja_baixado})

    # O que volta é `Registro` do domínio, não o dict cru: o cache guarda dado (nunca objeto
    # serializado), e a reidratação usa o mesmo normalizador dos adapters de fonte.
    devolvidos = ler_ou_baixar(fonte=fonte, cache=cache, **recorte)
    assert [r.conta for r in devolvidos] == [CONTA_RECEITA]
    assert fonte.chamadas == [], "consultou a fonte com o recorte já em cache"


def test_recortes_diferentes_nao_se_confundem(fonte):
    """Scenario: recortes diferentes não se confundem.

    Classe e competência entram na chave. Uma chave por ente/exercício devolveria despesa onde se
    pediu receita.
    """
    from app.infra.fila import chaves
    from app.infra.msc.cache import ler_ou_baixar

    cache = CacheFake({
        chaves.msc(ENTE_NUM, EXERCICIO, 12, 5): [{"conta": CONTA_RECEITA, "natureza": "C"}],
        chaves.msc(ENTE_NUM, EXERCICIO, 12, 6): [{"conta": CONTA_DESPESA, "natureza": "D"}],
        chaves.msc(ENTE_NUM, EXERCICIO, 11, 5): [],
    })

    assert len({chaves.msc(ENTE_NUM, EXERCICIO, m, c)
                for m in (11, 12) for c in (5, 6)}) == 4, "chave não distingue os recortes"

    devolvidos = ler_ou_baixar(fonte=fonte, cache=cache, ente=ENTE_NUM, ano=EXERCICIO,
                               mes=12, classe=6)
    assert [r.conta for r in devolvidos] == [CONTA_DESPESA], "veio o recorte de outra classe"
    assert fonte.chamadas == []


# ─── Requirement: Estado do job é serializado sem execução de código ────────

def test_payload_de_job_nao_executa_codigo():
    """Scenario: payload de job não executa código.

    Ida e volta em formato de dados, e recusa explícita de payload que executaria código na
    leitura. `Decimal` atravessa como string — o valor em centavos não pode virar float.
    """
    from app.infra.fila.serializacao import PayloadInvalido, desserializar, serializar

    bruto = serializar({"matriz": {"L1": {"receitas_realizadas": Decimal("100000.00")}}})
    assert isinstance(bruto, (bytes, str))
    assert desserializar(bruto) == {"matriz": {"L1": {"receitas_realizadas": "100000.00"}}}

    with pytest.raises(PayloadInvalido):
        desserializar(pickle.dumps({"matriz": {}}))

    fecho = _fecho_de(RAIZ_REPO / "app" / "infra" / "fila")
    violacoes = [f"{modulo} importa pickle" for modulo, caminho in sorted(fecho.items())
                 if "pickle" in _importados(caminho)]
    assert not violacoes, "\n  ".join(violacoes)
