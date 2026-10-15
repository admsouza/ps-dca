"""A decisão de servir do cache ou enfileirar job. Um service, para os oito anexos.

Quatro caminhos, e o que cada um responde:

| Estado da identidade | Resposta |
|---|---|
| `ok` (atual ou desatualizado) | **200** com o resultado e os motivos de desatualização |
| `processando`, com job vivo | **202 + `job_id` do job em voo**, `estado_job="already_queued"` |
| ausente, `erro`, ou `forcar` | **202 + `job_id`**, `estado_job="processing"` |
| `processando` com lock órfão | libera, loga, e cria job novo |

**O job em voo é devolvido com `job_id`, e quem diz que ele não é seu é `estado_job`.** Medido no
consumidor, não escolhido: `front-declaracoes/src/utils/rgfAnexoJob.ts` **lança erro** em `202` sem
`job_id` ("job iniciado sem ID de rastreamento"), e a UI já renderiza `status: "already_queued"`
como "Já existe um cálculo em andamento. Acompanhe o progresso."
(`components/rgf/RGFDialog.tsx`). Omitir o `job_id` custaria a stream SSE e, no caminho
compartilhado do front, viraria erro na tela em vez de "aguarde".

**Ver nunca processa** (`pipeline-visualizar-sem-reprocessar`, decisão do PO de 2026-10-07): sem
`forcar`, resultado `ok` é servido mesmo com código, regra ou pedido diferentes, marcado com o
motivo. Reapurar o que já existe é ação explícita — `reprocessar` ou o percurso.

Não há HTTP aqui: a rota transporta o `status`. É o que permite trocar de framework sem reescrever
a decisão, e é o mesmo motivo pelo qual a apuração é alcançável sem rota e sem worker.
"""
from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol

from app.infra.fila import job_manager
from app.infra.fila import lock as trava_lock
from app.services.pipeline.registry import validar_anexo

logger = logging.getLogger(__name__)


# Estado do job na resposta, no vocabulário que RREO e RGF já publicam e o front já consome.
PROCESSING = "processing"
ALREADY_QUEUED = "already_queued"

MSG_EM_VOO = "Já existe um cálculo em andamento. Acompanhe o progresso."


@dataclass
class Resposta:
    """O que a rota devolve.

    `status` é o código HTTP; `estado_job` é o que a rota publica como `status` no corpo — são
    coisas distintas, e juntá-las num campo só foi o que confundiu a primeira versão disto.
    """

    status: int
    estado_job: str = PROCESSING
    resultado: dict | None = None
    job_id: str | None = None
    poll_url: str | None = None
    sse_url: str | None = None
    anexo: str | None = None
    mensagem: str | None = None
    # `versao_api` | `versao_regras` | `pedido`. Vazio = cache atual.
    motivos_desatualizado: list[str] | None = None


class Repo(Protocol):
    def obter(self, ente: str, exercicio: int, anexo: str) -> Any: ...
    def gravar(self, registro: Any) -> None: ...


class Fila(Protocol):
    def enfileirar(self, ente: str, exercicio: int, anexo: str, job_id: str,
                   **parametros) -> None: ...


def identidade_do_pedido(*, anexo: str, competencia: int = 12,
                         valores_sem_mapeamento=None, fonte: str = "",
                         anterior_por_recorte: dict | None = None, **_ignorados) -> str:
    """O que, além de ente/exercício/anexo, distingue dois resultados do mesmo demonstrativo.

    `versao_api` e `versao_regras` invalidam o cache quando **código** ou **regra** mudam. Há
    escolhas que mudam o **valor** sem mudar nenhum dos dois: a competência apurada e, no BF e no
    BP, a origem por unidade da coluna do exercício anterior — o consolidado não tem origem própria
    (`pipeline-consolidado-anterior-soma-unidades`), e sai sempre da soma das unidades.

    `anterior_por_recorte` (`{unidade: {origem, valores?}}`) entra por último, como `ar-<hash>`, e
    só com escolha explícita: a origem que o padrão resolve não é escolha, e fica de fora.
    """
    import hashlib

    partes = [validar_anexo(anexo), f"c{int(competencia)}"]
    if valores_sem_mapeamento:
        pares = ";".join(f"{codigo}={valor}"
                         for codigo, valor in sorted(valores_sem_mapeamento.items()))
        partes.append("g8-" + hashlib.sha256(pares.encode("utf-8")).hexdigest()[:16])
    if fonte:
        partes.append(f"f={fonte}")      # SICONFI e PublicSoft dão números diferentes
    if anterior_por_recorte:
        partes.append(_sufixo_das_escolhas(anterior_por_recorte))
    return ":".join(partes)


def _sufixo_das_escolhas(escolhas: dict[str, dict]) -> str:
    import hashlib

    pares = ";".join(
        f"{unidade}={escolha['origem']}|"
        + ",".join(f"{codigo}={valor}" for codigo, valor in sorted(
            (escolha.get("valores") or {}).items()))
        for unidade, escolha in sorted(escolhas.items()))
    return "ar-" + hashlib.sha256(pares.encode("utf-8")).hexdigest()[:16]


def parametros_efetivos(pedido: dict | None, registro, anexo: str = "") -> dict:
    """O que o anexo vai apurar: o G8 do consolidado e as escolhas por unidade.

    O consolidado não tem origem própria (`pipeline-consolidado-anterior-soma-unidades`): a coluna
    anterior dele é sempre a soma das colunas resolvidas das unidades, abaixo.

    O mapa G8 do atual é independente disso (D2): pedido com a chave `valores_sem_mapeamento`
    vale o que veio (vazio limpa); pedido sem a chave reaplica `procedencia.valores_sem_mapeamento`.

    Por unidade (`anterior_por_recorte`): vale a gravada nos recortes, com o pedido por cima.
    """
    pedido = dict(pedido or {})
    saida: dict = {}
    if "valores_sem_mapeamento" in pedido:
        g8 = pedido["valores_sem_mapeamento"]
        if g8:
            saida["valores_sem_mapeamento"] = dict(g8)
    else:
        g8_salvo = _g8_salvo(registro)
        if g8_salvo:
            saida["valores_sem_mapeamento"] = g8_salvo
    if pedido.get("fonte"):
        saida["fonte"] = pedido["fonte"]
    saida.update(_por_unidade(pedido, registro))
    return saida


def _por_unidade(pedido: dict, registro) -> dict:
    """`anterior_por_recorte`: o gravado nos recortes, com o pedido por cima (`padrao` limpa).

    `anterior_agora` são as unidades que o pedido escolheu — só elas viram erro quando o
    `processado` não encontra N−1; o gravado cai em `msce`.
    """
    escolhas = escolhas_gravadas(registro)
    pedidas = pedido.get("anterior_por_recorte") or {}
    for unidade, escolha in pedidas.items():
        if escolha["origem"] == "padrao":
            escolhas.pop(unidade, None)
        else:
            escolhas[unidade] = escolha
    saida = {"anterior_por_recorte": escolhas} if escolhas else {}
    if pedidas:
        saida["anterior_agora"] = sorted(pedidas)
    return saida


def escolhas_gravadas(registro) -> dict[str, dict]:
    """Escolhas da linha: procedência de topo (sobrevive a erro) ou, em cache antigo, recortes."""
    procedencia = getattr(registro, "procedencia", None)
    topo = procedencia.get("anterior_por_recorte") if isinstance(procedencia, dict) else None
    if topo:
        return {unidade: dict(escolha) for unidade, escolha in topo.items()}
    return escolhas_do_resultado(getattr(registro, "resultado", None))


def escolhas_do_resultado(resultado) -> dict[str, dict]:
    """As escolhas explícitas que a procedência de cada recorte gravou (`escolha_anterior`)."""
    gravados = resultado.get("recortes") if isinstance(resultado, dict) else None
    saida = {}
    for unidade, recorte in (gravados or {}).items():
        procedencia = (recorte.get("resultado") or {}).get("procedencia") or {}
        escolha = procedencia.get("escolha_anterior")
        if escolha:
            saida[unidade] = dict(escolha)
    return saida


def _g8_salvo(registro) -> dict[str, str]:
    procedencia = getattr(registro, "procedencia", None) or {}
    if not isinstance(procedencia, dict):
        return {}
    valores = procedencia.get("valores_sem_mapeamento")
    return {str(c): str(v) for c, v in valores.items()} if isinstance(valores, dict) else {}


def versao_do_pedido(versao_regras: str, anexo: str, parametros: dict | None) -> str:
    """Versão de cache com a identidade do pedido. Rota e worker têm de gravar a mesma:
    sem o sufixo, a leitura seguinte não reconhece o cache e enfileira de novo."""
    if not parametros:
        return versao_regras
    return f"{versao_regras}|{identidade_do_pedido(anexo=anexo, **parametros)}"


def versao_apos_apurar(versao_regras: str, dados: dict) -> str:
    """A versão a gravar: o `ar-<hash>` refeito com as escolhas que o job de fato gravou.

    A rota e o worker identificam o pedido antes de saber quais unidades existem: escolha de unidade
    inexistente é descartada na apuração, e a leitura seguinte reconstrói a identidade só do que
    ficou gravado. Sem refazer, ela marcaria `pedido` sem motivo.
    """
    regras, separador, pedido = versao_regras.partition("|")
    if not separador:
        return versao_regras
    partes = [p for p in pedido.split(":") if not p.startswith("ar-")]
    if escolhas := escolhas_do_resultado(dados):
        partes.append(_sufixo_das_escolhas(escolhas))
    return f"{regras}|{':'.join(partes)}"


def _url_de_job(job_id: str, base: str = "") -> tuple[str, str]:
    raiz = base.rstrip("/")
    return f"{raiz}/jobs/{job_id}", f"{raiz}/sse/jobs/{job_id}"


def com_resultado(registro) -> bool:
    """Há o que mostrar: `ok` com resultado. A leitura serve, atual ou não."""
    return registro is not None and registro.status == "ok" and bool(registro.resultado)


def motivos_desatualizado(registro, versao_api: str, versao_regras: str) -> list[str]:
    """Por que o resultado gravado não é o que se apuraria agora.

    `versao_regras` vem como `<hash das regras>|<identidade do pedido>` (`versao_do_pedido`): a
    primeira parte separa "a regra mudou" de "o pedido é outro" (fonte, competência, origem do
    anterior). Uma correção de conta em `knowledge/rules/**.yaml` sem bump de código desatualiza o
    cache, ou o ente veria número velho sem aviso.
    """
    gravada_regra, _, gravado_pedido = (registro.versao_regras or "").partition("|")
    atual_regra, _, atual_pedido = versao_regras.partition("|")
    motivos = []
    if registro.versao_api != versao_api:
        motivos.append("versao_api")
    if gravada_regra != atual_regra:
        motivos.append("versao_regras")
    if gravado_pedido != atual_pedido:
        motivos.append("pedido")
    return motivos


def servivel(registro, versao_api: str, versao_regras: str) -> bool:
    """Com resultado e atual — o critério do percurso, que processa o que não estiver atual."""
    return com_resultado(registro) and not motivos_desatualizado(
        registro, versao_api, versao_regras)


def ler_ou_enfileirar(*, ente: str, exercicio: int, anexo: str, repo: Repo, fila: Fila,
                      lock, versao_api: str, versao_regras: str, jobs=None,
                      forcar: bool = False, solicitado_por: int | None = None,
                      base_url: str = "", parametros: dict | None = None,
                      guardar_credencial: Callable[[str], None] | None = None) -> Resposta:
    """Decide entre servir o cache e criar job. Nunca apura — a apuração é do worker.

    `parametros` são as escolhas do pedido que **mudam o valor** sem mudar código nem regra — a
    competência e, no BF, a origem da coluna do exercício anterior. Elas entram na identidade
    (senão o resultado de um mês seria servido a quem pediu outro) e no payload do job (senão o
    worker apuraria dezembro qualquer que fosse o pedido).
    """
    anexo = validar_anexo(anexo)
    parametros = parametros or {}
    versao_regras = versao_do_pedido(versao_regras, anexo, parametros)
    registro = repo.obter(ente, exercicio, anexo)

    if not forcar and com_resultado(registro):
        return Resposta(status=200, resultado=registro.resultado, anexo=anexo,
                        motivos_desatualizado=motivos_desatualizado(
                            registro, versao_api, versao_regras))

    job_id = job_manager.novo_id()
    em_voo = trava_lock.adquirir_com_recuperacao(
        lock, jobs, ente=ente, exercicio=exercicio, anexo=anexo, job_id=job_id
    )
    if em_voo:
        # O job é de outro requisitante, e o `job_id` vai preenchido para ele poder acompanhar:
        # `estado_job` é o que diz que o job não é dele. Nenhum segundo job é enfileirado.
        logger.info("job em voo para a identidade | anexo=%s ente=%s job=%s",
                    anexo, ente, em_voo)
        poll, sse = _url_de_job(em_voo, base_url)
        return Resposta(status=202, estado_job=ALREADY_QUEUED, job_id=em_voo,
                        poll_url=poll, sse_url=sse, anexo=anexo, mensagem=MSG_EM_VOO)

    if registro is not None and registro.status == "processando":
        # Lock livre com cache em `processando`: o worker anterior morreu sem gravar desfecho.
        logger.warning(
            "cache em processando sem job vivo — lock órfão recuperado | anexo=%s ente=%s "
            "exercicio=%s", anexo, ente, exercicio,
        )

    # `processando` é gravado ANTES do enfileiramento — visibilidade imediata mesmo com fila
    # lenta, e um segundo cliente no mesmo instante não cria segundo job.
    _marcar_processando(repo, registro, ente, exercicio, anexo,
                        versao_api, versao_regras, solicitado_por)
    try:
        if guardar_credencial is not None:
            # No cofre, cifrada e com o `job_id`: o payload da fila não carrega segredo.
            guardar_credencial(job_id)
        fila.enfileirar(ente, exercicio, anexo, job_id, **parametros)
    except Exception as falha:
        # Fila fora do ar não pode virar `202` mentiroso, nem deixar a identidade presa em
        # `processando`: o cliente esperaria um job que ninguém vai executar.
        detalhe = f"fila indisponível: {type(falha).__name__}: {falha}"
        logger.error("falha ao enfileirar | anexo=%s ente=%s -> %s", anexo, ente, detalhe)
        _marcar_erro(repo, repo.obter(ente, exercicio, anexo), ente, exercicio, anexo, detalhe)
        lock.liberar(ente, exercicio, anexo)
        raise RuntimeError(detalhe) from falha

    if jobs is not None:
        job_manager.criar(jobs, job_id, ente=ente, exercicio=exercicio, anexo=anexo)

    logger.info("job enfileirado | anexo=%s ente=%s exercicio=%s job=%s forcar=%s",
                anexo, ente, exercicio, job_id, forcar)
    poll, sse = _url_de_job(job_id, base_url)
    return Resposta(status=202, estado_job=PROCESSING, job_id=job_id,
                    poll_url=poll, sse_url=sse, anexo=anexo)


def _marcar_processando(repo: Repo, registro, ente: str, exercicio: int, anexo: str,
                        versao_api: str, versao_regras: str,
                        solicitado_por: int | None) -> None:
    """Grava `processando` **antes** de a resposta sair, preservando o resultado anterior.

    Duas coisas de uma vez:

    - um segundo cliente no mesmo instante encontra `processando` e não cria segundo job;
    - o resultado anterior **continua legível** durante a reapuração. Apagá-lo abriria uma janela
      de minutos em que o ente vê o anexo vazio, e o requisito proíbe.
    """
    if registro is None:
        registro = _novo_registro(repo, ente, exercicio, anexo)

    registro.status = "processando"
    registro.erro_detalhe = None
    registro.versao_api = versao_api
    registro.versao_regras = versao_regras
    if solicitado_por is not None:
        registro.solicitado_por = solicitado_por
    repo.gravar(registro)


def _marcar_erro(repo: Repo, registro, ente: str, exercicio: int, anexo: str,
                 detalhe: str) -> None:
    """Desfaz o `processando` quando o job não chegou a existir."""
    if registro is None:
        registro = _novo_registro(repo, ente, exercicio, anexo)
    registro.status = "erro"
    registro.erro_detalhe = detalhe
    repo.gravar(registro)


def _novo_registro(repo: Repo, ente: str, exercicio: int, anexo: str):
    """Constrói o registro na classe que o próprio repositório usa — fake ou SQLAlchemy."""
    try:
        from app.infra.cache.repositorio import Registro
    except ImportError:                                  # pragma: no cover - infra ausente
        Registro = None

    modelo = getattr(repo, "Registro", None) or Registro
    return modelo(id_ente=ente, an_referencia=exercicio, anexo=anexo,
                  status="processando", resultado=None)
