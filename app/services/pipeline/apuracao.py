"""Monta o apurador de um anexo: mapa vigente + fonte de dados + direção do saldo.

Um lugar só, chamado por rota (para descobrir a versão vigente), worker (para apurar) e CLI. O
apurador que sai daqui é uma função de `(ente, exercicio)` — o worker não sabe de onde vieram o
mapa nem a fonte, e é isso que torna a apuração testável sem infraestrutura.

A versão de regras vem daqui, não de constante: é a chave de invalidação do cache, e uma correção
de conta em `knowledge/rules/**.yaml` tem de invalidar sozinha.
"""
from __future__ import annotations

import hashlib
import logging
from collections.abc import Callable, Collection, Sequence
from decimal import Decimal
from pathlib import Path
from typing import Any, NamedTuple

from app.core.config import config

logger = logging.getLogger(__name__)

# Código que muda o número. Rota, auth e cache ficam de fora: alteração ali não muda célula.
_RAIZ_APP = Path(__file__).resolve().parents[2]
_CODIGO_DA_APURACAO = (
    _RAIZ_APP / "domain",               # motor (bo/) e recortes por unidade (recorte.py)
    _RAIZ_APP / "services" / "bf",
    _RAIZ_APP / "services" / "bo",
    _RAIZ_APP / "services" / "bp",
    _RAIZ_APP / "infra" / "msc",
    _RAIZ_APP / "infra" / "siconfi",    # DCA publicada (BP, coluna anterior)
    _RAIZ_APP / "infra" / "pcasp",      # direção do saldo
    _RAIZ_APP / "infra" / "regras",     # montagem do mapa a partir do YAML/banco
    # ponytail: pasta inteira por causa de `apuracao.py`; job/cache também invalidam — custa
    # reprocessamento, nunca número errado.
    _RAIZ_APP / "services" / "pipeline",
)


def versao_do_codigo(raiz: Path, pastas: Sequence[Path]) -> str:
    """Hash do fonte que produz a célula. LF, para um checkout Windows não invalidar o cache."""
    digest = hashlib.sha256()
    raiz = raiz.resolve()
    relativos = {
        arquivo.resolve().relative_to(raiz).as_posix(): arquivo
        for pasta in pastas
        for arquivo in pasta.rglob("*.py")
        if "__pycache__" not in arquivo.parts
    }
    for relativo, arquivo in sorted(relativos.items()):
        texto = arquivo.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")
        digest.update(relativo.encode())
        digest.update(b"\0")
        digest.update(texto)
    return digest.hexdigest()


# Muda sozinha quando o código da apuração muda. `versao_regras` cobre o YAML.
VERSAO_API = versao_do_codigo(_RAIZ_APP, _CODIGO_DA_APURACAO)


def fonte(nome: str | None = None, token: str | None = None):
    """Adapter de MSC pelo nome, com a memória da execução por cima."""
    from app.infra.msc.publicsoft import PublicSoftMSC

    escolhido = (nome or config().fonte_padrao).strip().lower()
    estorno = None
    if escolhido == "publicsoft":
        bruta = PublicSoftMSC(token=token or "")
    else:
        from app.infra.msc.siconfi import SiconfiMSC

        bruta = SiconfiMSC()
        # O SICONFI não tem o relatório de estorno: vem da PublicSoft, com o token_ps do ente.
        # Sem token (ente só SICONFI), não abate.
        estorno = PublicSoftMSC(token=token) if token else None

    return _NoEscopo(bruta, escolhido, estorno)


class _NoEscopo:
    """Envolve a fonte na memória da execução, sem que a fonte saiba disso.

    Nada é persistido: o recorte lido vale para o job que o leu e some com ele — o ente retifica
    declaração já publicada, e dado guardado entre execuções serviria o número anterior à
    retificação (`app/infra/msc/cache.py`).
    """

    def __init__(self, bruta, nome: str = "", estorno=None) -> None:
        self._bruta = bruta
        self._nome = nome
        self._estorno = estorno

    def registros(self, ente: int, ano: int, mes: int, classe: int,
                  matriz=None, tipo_saldo=None):
        """Repassa o par de leitura **como recebido**.

        Omiti-lo é falha silenciosa: um demonstrativo que lê três origens — o BF lê a abertura do
        exercício, o encerramento e a abertura do exercício anterior — receberia três vezes a
        mesma, e `L25`, `L26` e `L29`–`L32` sairiam com números plausíveis e errados, sem exceção
        e sem célula não apurada. `ler_ou_baixar` já inclui o par na chave; faltava chegar até ele.
        """
        from app.infra.msc.cache import ler_ou_baixar

        return ler_ou_baixar(fonte=self._bruta, ente=ente, ano=ano, mes=mes, classe=classe,
                             matriz=matriz, tipo_saldo=tipo_saldo, fonte_nome=self._nome)

    def __getattr__(self, nome: str):
        """O que a fonte sabe fazer além de `registros`. O estorno vem de `estorno` quando houver;
        senão da fonte bruta — o SICONFI não o tem, e o BF não abate. O estorno é memorizado no
        escopo, como a MSC: uma chamada por exercício e tipo, qualquer que seja o nº de recortes."""
        if not nome.startswith("estorno_"):
            return getattr(self._bruta, nome)
        from app.infra.msc.escopo import obter_ou_buscar

        origem = self._estorno if self._estorno is not None else self._bruta
        consultar = getattr(origem, nome)
        return lambda exercicio: obter_ou_buscar(
            f"estorno:{self._nome}:{nome}:{exercicio}", lambda: consultar(exercicio))


# Anexos apurados também por recorte (changes `pipeline-dca-por-unidade-gestora` e
# `bf-por-unidade-gestora`).
RECORTAVEIS = ("BO", "BP", "BF")


class Recorte(NamedTuple):
    tipo: str              # poder | ug | po
    rotulo: str
    poder_orgao: str       # vazio em grupo de poder
    resultado: Any


class _Repasse:
    """Base das fontes que só mexem nos registros; estorno e afins seguem para a fonte real."""

    def __init__(self, fonte) -> None:
        self._fonte = fonte

    def __getattr__(self, nome: str):
        return getattr(self._fonte, nome)


class _Observada(_Repasse):
    """Repassa os registros e anota as unidades de cada exercício:
    `{ano: {unidade: (nome, {poder_orgao})}}`."""

    def __init__(self, fonte, exercicio: int) -> None:
        super().__init__(fonte)
        self._exercicio = exercicio
        self.por_exercicio: dict[int, dict[str, tuple[str, set[str]]]] = {}

    def registros(self, ente, ano, *args, **kwargs):
        from app.domain.recorte import unidade

        lidos = self._fonte.registros(ente, ano, *args, **kwargs)
        unidades = self.por_exercicio.setdefault(ano, {})
        for registro in lidos:
            nome, poderes = unidades.setdefault(
                unidade(registro), (registro.nome_unidade_gestora, set()))
            poderes.add(registro.poder_orgao)
        return lidos

    @property
    def tipo(self) -> str:
        """`ug` se algum registro do exercício atual traz a UG; senão `po`. Quem decide é o
        exercício atual: N−1 lido pela base oficial (CSV) não vira unidade `po:` num job por UG."""
        atual = self.por_exercicio.get(self._exercicio, {})
        return "ug" if any(u.startswith("ug:") for u in atual) else "po"

    @property
    def unidades(self) -> dict[str, tuple[str, set[str]]]:
        """`{unidade: (nome, {poder_orgao})}` do tipo do job, de todos os exercícios lidos."""
        saida: dict[str, tuple[str, set[str]]] = {}
        for unidades in self.por_exercicio.values():
            for chave, (nome, poderes) in unidades.items():
                if chave.startswith(f"{self.tipo}:"):
                    saida.setdefault(chave, (nome, set()))[1].update(poderes)
        return saida


class _Filtrada(_Repasse):
    """Só os registros das `unidades` do recorte — e, no BF, só o estorno delas.

    ponytail: filtra a lista inteira a cada leitura — O(registros × recortes). Particionar uma vez
    por leitura se o job de um ente grande pesar.
    """

    def __init__(self, fonte, unidades: set[str]) -> None:
        super().__init__(fonte)
        self._unidades = unidades

    def registros(self, *args, **kwargs):
        from app.domain.recorte import unidade

        return [r for r in self._fonte.registros(*args, **kwargs) if unidade(r) in self._unidades]

    def __getattr__(self, nome: str):
        consultar = super().__getattr__(nome)
        if not nome.startswith("estorno_"):
            return consultar
        return lambda exercicio: self._do_recorte(consultar(exercicio))

    def _do_recorte(self, estorno):
        """`ug:` pela instituição; `po:` pelas instituições do `poderOrgao`."""
        from dataclasses import replace

        from app.infra.msc.publicsoft import EstornoSemPoderOrgao

        por_unidade: dict[str, Decimal] = {}
        for unidade in self._unidades:
            if unidade.startswith("ug:"):
                if unidade in estorno.por_unidade:
                    por_unidade[unidade] = estorno.por_unidade[unidade]
            elif estorno.poder_orgao is None:
                if estorno.total > 0:
                    raise EstornoSemPoderOrgao("estorno sem poder/órgão")
            else:
                por_unidade.update({u: v for u, v in estorno.por_unidade.items()
                                    if estorno.poder_orgao.get(u) == unidade[3:]})
        return replace(estorno, total=sum(por_unidade.values(), Decimal("0")),
                       por_unidade=por_unidade)


def com_recortes(apurar: Callable, ente: int, exercicio: int, fonte, *, repo=None, anexo: str = "",
                 escolhas: dict | None = None, agora: Collection[str] = (),
                 valores_atuais_por_recorte: dict | None = None, **extras) -> Any:
    """O consolidado de hoje e, em `.recortes`, cada grupo de poder e cada unidade.

    Cada recorte é o mesmo `apurar` sobre a fonte filtrada: dentro do `escopo()` do job a leitura já
    está memorizada, então nada volta à fonte. No BP e no BF, fora do consolidado, a coluna anterior
    é da unidade (`pipeline-anterior-por-recorte`): `escolhas` (`{unidade: {origem, valores?}}`) ou,
    sem escolha, o processado de N−1 em `repo` ou a MSC de N−1. `agora` são as unidades que o pedido
    escolheu neste job.

    O consolidado não tem origem própria (`pipeline-consolidado-anterior-soma-unidades`): como o
    grupo de poder, a coluna anterior dele é a soma das colunas já resolvidas das unidades do job.

    ponytail: unidade que só existe no ano anterior não vira recorte (ela nunca é lida). Ler a MSC
    anterior para descobri-la se aparecer o caso.
    """
    from dataclasses import replace

    from app.domain import recorte as dominio
    from app.services.pipeline import anterior as ant
    from app.services.pipeline.resultado import para_dados

    escolhas = escolhas or {}
    valores_atuais_por_recorte = valores_atuais_por_recorte or {}
    por_unidade = "anterior" in _aceitos_por(apurar, {"anterior": None})     # BF e BP
    n1 = ant.ler_n1(repo, ente, exercicio, anexo) if por_unidade else None
    # Origem própria do consolidado (`anterior`/`anterior_pronto`/`valores_anteriores`/`dca`) não é
    # mais aceita: a primeira passada só observa os registros e apura o exercício atual, em MSCE —
    # a mais barata, e nunca lê N−1 nem o publicado (a coluna sai da soma das unidades, abaixo).
    extras_base = extras
    if por_unidade:
        extras_base = {k: v for k, v in extras.items()
                      if k not in ("anterior", "anterior_pronto", "valores_anteriores", "dca")}
        extras_base["anterior"] = ant.OrigemAnterior.MSCE.value

    observada = _Observada(fonte, exercicio)
    resultado = apurar(ente, exercicio, fonte=observada, **extras_base)
    # O que foi digitado para o ente (G8) vale só no consolidado.
    extras_recorte = {**extras_base, **_aceitos_por(apurar, {"anterior": "msce_exercicio_anterior",
                                                             "g8_so_no_consolidado": True})}
    extras_recorte.pop("valores_sem_mapeamento", None)

    # Unidade com mais de um PO não pertence a um poder só: fica fora dos grupos.
    unidades = observada.unidades
    poder_orgao = {u: next(iter(pos)) if len(pos) == 1 else "" for u, (_, pos) in unidades.items()}
    # Grupo sem unidade (ex.: ente sem registro da Câmara): nada a emitir.
    membros_de = {chave: membros for chave, membros in dominio.recortes(poder_orgao).items()
                  if membros}

    def apurar_recorte(chave: str, **kwargs) -> Any:
        return apurar(ente, exercicio, fonte=_Filtrada(observada, membros_de[chave]), **kwargs)

    def da_unidade(chave: str) -> Any:
        if not por_unidade:
            return apurar_recorte(chave, **extras_recorte)
        escolha = escolhas.get(chave)
        origem, aviso = ant.resolver(chave, escolha, n1, exigir_processado=repo is not None)
        kwargs = dict(extras_recorte)
        if chave in valores_atuais_por_recorte:
            kwargs.update(_aceitos_por(apurar, {"valores_atuais":
                                                valores_atuais_por_recorte[chave]}))
        retrato = None
        if origem is ant.OrigemAnterior.PROCESSADO:
            retrato = ant.recorte_de(n1, chave)
            kwargs.update(anterior=origem.value, anterior_pronto=ant.pronto(retrato))
        elif origem is ant.OrigemAnterior.MANUAL:
            kwargs.update(anterior=origem.value, valores_anteriores=escolha["valores"])
        r = apurar_recorte(chave, **kwargs)
        # BP: a unidade sem MSC em N−1, num job que leu N−1, sai em zero (PO 2026-10-13).
        zero = _aceitos_por(apurar, {"zero_sem_anterior": True})
        leu_n1 = observada.por_exercicio.get(exercicio - 1)
        if (origem is ant.OrigemAnterior.MSCE and zero and leu_n1
                and r.diagnostico.sem_dados_exercicio_anterior):
            r = apurar_recorte(chave, **kwargs, **zero)
        r.procedencia = replace(
            r.procedencia, escolha_anterior=dict(escolha) if escolha else None,
            anterior_processado=(ant.procedencia_do_processado(n1, retrato) if retrato else None))
        if aviso:
            r.diagnostico.avisos_anterior = [aviso]
        return r

    feitos = {chave: da_unidade(chave) for chave in membros_de if chave not in dominio.GRUPOS}
    if por_unidade and not feitos:
        raise ant.ParcelaSemUnidade(f"{anexo}: exercício sem nenhuma unidade ug:/po: a consolidar")

    def do_grupo(chave: str) -> Any:
        if not por_unidade:
            return apurar_recorte(chave, **extras_recorte)
        soma = ant.somar([ant.pronto(para_dados(feitos[u]), "_anterior")
                          for u in sorted(membros_de[chave])])
        atual = ant.somar([ant.pronto(para_dados(feitos[u]))
                           for u in sorted(membros_de[chave])])
        r = apurar_recorte(chave, **{**extras_recorte,
                                     "anterior": ant.OrigemAnterior.PROCESSADO.value,
                                     "anterior_pronto": soma,
                                     **_aceitos_por(apurar, {"atual_pronto": atual})})
        r.procedencia = replace(r.procedencia, origem_exercicio_anterior=ant.SOMA_DAS_UNIDADES)
        r.diagnostico.sem_dados_exercicio_anterior = any(
            feitos[u].diagnostico.sem_dados_exercicio_anterior for u in membros_de[chave])
        return r

    if por_unidade:
        # O consolidado é mais um grupo, de todas as unidades do job: nunca lê N−1 nem manual
        # próprios (`pipeline-consolidado-anterior-soma-unidades`).
        soma = ant.somar([ant.pronto(para_dados(feitos[u]), "_anterior") for u in sorted(feitos)])
        atual = ant.somar([ant.pronto(para_dados(feitos[u])) for u in sorted(feitos)])
        resultado = apurar(ente, exercicio, fonte=observada,
                          **{**extras_base, "anterior": ant.OrigemAnterior.PROCESSADO.value,
                             "anterior_pronto": soma,
                             **_aceitos_por(apurar, {"atual_pronto": atual})})
        mudancas = {"origem_exercicio_anterior": ant.SOMA_DAS_UNIDADES}
        if hasattr(resultado.procedencia, "valores_atuais_por_recorte"):
            mudancas["valores_atuais_por_recorte"] = {
                chave: dict(valores_atuais_por_recorte[chave])
                for chave in sorted(feitos) if chave in valores_atuais_por_recorte
            }
        resultado.procedencia = replace(resultado.procedencia, **mudancas)
        resultado.diagnostico.sem_dados_exercicio_anterior = any(
            feitos[u].diagnostico.sem_dados_exercicio_anterior for u in feitos)

    resultado.recortes = {
        chave: Recorte(
            tipo=dominio.tipo(chave),
            rotulo=_rotulo(chave, unidades),
            poder_orgao="" if chave in dominio.GRUPOS else poder_orgao[chave],
            resultado=do_grupo(chave) if chave in dominio.GRUPOS else feitos[chave],
        )
        for chave in membros_de
    }
    # Os anos do próprio consolidado (atual) mais o anterior, quando houver unidade (ele não lê
    # mais N−1 diretamente, então o próprio ano some da procedência se ninguém pedir `processado`).
    anos_estorno = set(getattr(resultado.procedencia, "estorno_receita_extra", None) or {}) | set(
        getattr(resultado.procedencia, "estorno_despesa_extra", None) or {})
    if por_unidade:
        anos_estorno.add(str(exercicio - 1))
    sem_unidade = _estorno_sem_unidade(fonte, observada, anos_estorno)
    # Só a coluna anterior (ano = exercício − 1) é escopo desta change: o atual é diagnóstico, como
    # antes (`bf-por-unidade-gestora`).
    if por_unidade and any(s["exercicio"] == exercicio - 1 for s in sem_unidade):
        raise ant.ParcelaSemUnidade(
            f"{anexo}: contribuição da coluna anterior sem unidade ({len(sem_unidade)})")
    if sem_unidade:
        resultado.diagnostico.estorno_sem_unidade = sem_unidade
    if ignoradas := [c for c in sorted(agora) if c in escolhas and c not in feitos]:
        resultado.diagnostico.avisos_anterior = [
            f"{c}: unidade ausente no job, escolha ignorada" for c in ignoradas]
    return resultado


def _estorno_sem_unidade(fonte, observada: _Observada, anos) -> list[dict]:
    """Estorno que entra no total do consolidado e não cai em nenhuma unidade (só BF).

    Por UG: instituição sem registro na MSC do exercício. Por PO: `poderOrgao` nulo, ou PO sem
    registro no exercício. Declarado, nunca rateado. Lê o relatório já memorizado no escopo —
    fonte sem o relatório (`estorno_*` ausente) não é checada.
    """
    saida = []
    for tipo in ("receita", "despesa"):
        nome = f"estorno_{tipo}_extra"
        consultar = getattr(fonte, nome, None)
        if consultar is None:
            continue
        for ano in anos:
            estorno = consultar(int(ano))
            vistas = observada.por_exercicio.get(int(ano), {})
            for unidade, valor in estorno.por_unidade.items():
                if observada.tipo == "ug":
                    sem = unidade not in vistas
                elif estorno.poder_orgao is None:   # `ps-erp` antigo: os `po:` já saem não apurados
                    sem = False
                else:
                    po = estorno.poder_orgao.get(unidade)
                    sem = po is None or f"po:{po}" not in vistas
                if sem and valor:
                    saida.append({"exercicio": int(ano), "tipo": tipo, "unidade": unidade,
                                  "valor": format(valor, ".2f")})
    return saida


def _rotulo(chave: str, unidades: dict[str, tuple[str, set[str]]]) -> str:
    from app.domain.recorte import NOMES_PO, ROTULOS

    if chave in ROTULOS:
        return ROTULOS[chave]
    codigo = chave.split(":", 1)[1]
    if chave.startswith("ug:"):
        return unidades[chave][0] or f"Unidade gestora {codigo}"
    return NOMES_PO.get(codigo, f"Poder/Órgão {codigo}")


def mapa_vigente(exercicio: int, anexo: str = "BO", repo_vigencias=None):
    """Mapa do anexo para o exercício. Do banco quando houver repositório; do YAML na semente.

    O YAML continua servindo de semente e de fallback de boot: um banco recém-criado ainda não tem
    vigência, e recusar a apuração nesse instante deixaria a DCA sem responder até alguém rodar o
    seed à mão.
    """
    if repo_vigencias is not None:
        from app.infra.regras.carregador import SemVigencia
        from app.infra.regras.vigencias import carregar as carregar_do_banco

        try:
            return carregar_do_banco(repo_vigencias, anexo, exercicio)
        except SemVigencia:
            logger.warning(
                "sem vigência publicada para %s/%s — caindo no YAML versionado (semente)",
                anexo, exercicio,
            )

    from app.infra.regras.carregador import carregar
    from app.services.pipeline.registry import anexo as descrever

    return carregar(exercicio, demonstrativo=descrever(anexo).base_canonica)


def apurador(anexo: str = "BO", *, fonte_nome: str | None = None, token: str | None = None,
             repo_vigencias=None, parametros: dict | None = None,
             repo=None) -> Callable[[int, int], Any]:
    """A função `(ente, exercicio) -> Resultado` que o worker executa.

    `repo` é o cache dos resultados: o BF e o BP leem dele o processado de N−1 por unidade.

    A versão de regras **não** sai daqui: ela depende do exercício, e quem precisa dela antes de
    apurar (a rota, para decidir invalidação) chama `versao_regras(exercicio)`.
    """
    from app.services.pipeline.registry import anexo as descrever

    descricao = descrever(anexo)
    if descricao.servico is None:
        raise NotImplementedError(f"anexo {descricao.codigo} ainda não tem serviço de apuração")

    dados = fonte(fonte_nome, token)

    apurar = _servico_de(descricao.codigo)
    # `fonte` do pedido já virou `dados`; repassá-la colidiria com o `fonte=` do serviço.
    extras = _aceitos_por(apurar, {k: v for k, v in (parametros or {}).items() if k != "fonte"})
    por_unidade = {"repo": repo, "anexo": descricao.codigo,
                   "escolhas": (parametros or {}).get("anterior_por_recorte"),
                   "agora": (parametros or {}).get("anterior_agora") or (),
                   "valores_atuais_por_recorte":
                       (parametros or {}).get("valores_atuais_por_recorte")}

    def _apurar(ente: int, exercicio: int):
        mapa = mapa_vigente(exercicio, descricao.codigo, repo_vigencias)
        if descricao.codigo in RECORTAVEIS:
            return com_recortes(apurar, ente, exercicio, dados, mapa=mapa, **por_unidade, **extras)
        return apurar(ente, exercicio, fonte=dados, mapa=mapa, **extras)

    return _apurar


def _aceitos_por(servico: Callable, parametros: dict) -> dict:
    """Só os parâmetros que a assinatura do serviço declara.

    Um job para todos os anexos significa um payload que serve a todos: o BF aceita a origem da
    coluna do exercício anterior e o BO não. Repassar cegamente levantaria `TypeError` dentro do
    worker, e o anexo ficaria preso em `processando` até o lock expirar.
    """
    from inspect import signature

    aceitos = signature(servico).parameters
    return {nome: valor for nome, valor in parametros.items() if nome in aceitos}


def _servico_de(anexo: str):
    """A função de apuração que o registry declara para o anexo.

    Era o serviço do BO, importado de forma fixa: o BF seria apurado pelas regras do IPC 07 sobre
    as classes do BO — número errado, sem erro nenhum.
    """
    from importlib import import_module

    from app.services.pipeline.registry import anexo as descrever

    servico = descrever(anexo).servico
    if servico is None:
        raise NotImplementedError(f"anexo {anexo} ainda não tem serviço de apuração")
    modulo, funcao = servico.split(":")
    return getattr(import_module(modulo), funcao)


def versao_regras(exercicio: int, anexo: str = "BO", repo_vigencias=None) -> str:
    """A versão vigente, para a rota decidir invalidação sem apurar nada."""
    return mapa_vigente(exercicio, anexo, repo_vigencias).versao_regras
