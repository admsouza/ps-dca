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
from collections.abc import Callable, Sequence
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
        senão da fonte bruta — o SICONFI não o tem, e o BF não abate."""
        if nome.startswith("estorno_") and self._estorno is not None:
            return getattr(self._estorno, nome)
        return getattr(self._bruta, nome)


# Anexos apurados também por recorte (change `pipeline-dca-por-unidade-gestora`). O BF fica fora:
# os estornos de receita/despesa extra são do ente, sem UG.
RECORTAVEIS = ("BO", "BP")


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
    """Repassa os registros e anota as unidades que aparecem: `{unidade: (nome, {poder_orgao})}`."""

    def __init__(self, fonte) -> None:
        super().__init__(fonte)
        self.unidades: dict[str, tuple[str, set[str]]] = {}

    def registros(self, *args, **kwargs):
        from app.domain.recorte import unidade

        lidos = self._fonte.registros(*args, **kwargs)
        for registro in lidos:
            nome, poderes = self.unidades.setdefault(
                unidade(registro), (registro.nome_unidade_gestora, set()))
            poderes.add(registro.poder_orgao)
        return lidos


class _Filtrada(_Repasse):
    """Só os registros das `unidades` do recorte.

    ponytail: filtra a lista inteira a cada leitura — O(registros × recortes). Particionar uma vez
    por leitura se o job de um ente grande pesar.
    """

    def __init__(self, fonte, unidades: set[str]) -> None:
        super().__init__(fonte)
        self._unidades = unidades

    def registros(self, *args, **kwargs):
        from app.domain.recorte import unidade

        return [r for r in self._fonte.registros(*args, **kwargs) if unidade(r) in self._unidades]


def com_recortes(apurar: Callable, ente: int, exercicio: int, fonte, **extras) -> Any:
    """O consolidado de hoje e, em `.recortes`, cada grupo de poder e cada unidade.

    Cada recorte é o mesmo `apurar` sobre a fonte filtrada: dentro do `escopo()` do job a leitura já
    está memorizada, então nada volta à fonte. No BP, fora do consolidado, a coluna anterior é a
    MSC do recorte — a DCA publicada só existe consolidada.

    ponytail: unidade que só existe no ano anterior não vira recorte quando o consolidado do BP usa
    o publicado (ela nunca é lida). Ler a MSC anterior para descobri-la se aparecer o caso.
    """
    from app.domain import recorte as dominio

    observada = _Observada(fonte)
    resultado = apurar(ente, exercicio, fonte=observada, **extras)
    extras_recorte = {**extras, **_aceitos_por(apurar, {"anterior": "msce_exercicio_anterior"})}
    extras_recorte.pop("dca", None)

    # Unidade com mais de um PO não pertence a um poder só: fica fora dos grupos.
    poder_orgao = {u: next(iter(pos)) if len(pos) == 1 else ""
                   for u, (_, pos) in observada.unidades.items()}
    resultado.recortes = {
        chave: Recorte(
            tipo=dominio.tipo(chave),
            rotulo=_rotulo(chave, observada.unidades),
            poder_orgao="" if chave in dominio.GRUPOS else poder_orgao[chave],
            resultado=apurar(ente, exercicio, fonte=_Filtrada(fonte, membros), **extras_recorte),
        )
        for chave, membros in dominio.recortes(poder_orgao).items()
        if membros         # grupo sem unidade (ex.: ente sem registro da Câmara): nada a emitir
    }
    return resultado


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
             repo_vigencias=None, parametros: dict | None = None) -> Callable[[int, int], Any]:
    """A função `(ente, exercicio) -> Resultado` que o worker executa.

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

    def _apurar(ente: int, exercicio: int):
        mapa = mapa_vigente(exercicio, descricao.codigo, repo_vigencias)
        if descricao.codigo in RECORTAVEIS:
            return com_recortes(apurar, ente, exercicio, dados, mapa=mapa, **extras)
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
