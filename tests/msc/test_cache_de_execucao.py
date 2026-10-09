"""Cenários da memória de execução da MSC: identidade do recorte e tempo de vida do dado.

Sem Redis e sem rede: a fonte conta as chamadas que recebe. O ponto sob teste é que **nada** do
que se lê da MSC sobrevive ao job — o ente retifica declaração já publicada, e dado guardado entre
execuções serviria o número anterior à retificação.
"""
from __future__ import annotations

import hashlib

ENTE = 2507507
CLASSE = 5
EXERCICIO = 2025


class FonteFake:
    """Devolve sempre o mesmo registro e registra cada consulta recebida."""

    def __init__(self):
        self.chamadas = []

    def registros(self, ente, ano, mes, classe, matriz=None, tipo_saldo=None):
        self.chamadas.append((ente, ano, mes, classe, matriz, tipo_saldo))
        from app.domain.bo.modelo import Registro

        return [Registro(conta="521110000", natureza="C", valor=1)]


def chave_do_rreo(**parametros) -> str:
    """`build_cache_key` do RREO reimplementada — o formato que a identidade do recorte segue.

    Se o RREO mudar a construção, este teste é o que avisa; sem ele, a divergência só apareceria
    como identidade que não corresponde a recorte nenhum dos irmãos.
    """
    itens = sorted((k, "" if v is None else str(v))
                   for k, v in parametros.items() if v is not None)
    base = "|".join(f"{k}:{v}" for k, v in itens)
    return f"msc_cache:{hashlib.md5(base.encode('utf-8')).hexdigest()}"  # noqa: S324


# ─── Identidade do recorte ───────────────────────────────────────────────────

def test_identidade_segue_o_formato_do_rreo():
    """Scenario: a identidade do recorte é a mesma que os irmãos usam."""
    from app.infra.msc.cache import _chave

    nossa = _chave(ENTE, EXERCICIO, 12, CLASSE, None, None, "siconfi")
    assert nossa == chave_do_rreo(id_ente=ENTE, an_referencia=EXERCICIO, mes=12, classe=CLASSE,
                                  id_tv="ending_balance", fonte_dados="siconfi")


def test_fonte_e_matriz_distinguem_o_recorte():
    """Scenario: recortes de origens diferentes não se confundem.

    O BF lê três origens do mesmo ente e exercício; se o par (matriz, tipo de saldo) ou a fonte
    ficassem de fora, a segunda leitura receberia o dado da primeira.
    """
    from app.infra.msc.cache import _chave
    from app.infra.msc.fonte import Matriz, TipoSaldo

    distintas = {
        _chave(ENTE, EXERCICIO, 12, CLASSE, None, None, "siconfi"),
        _chave(ENTE, EXERCICIO, 12, CLASSE, None, None, "publicsoft"),
        _chave(ENTE, EXERCICIO, 12, CLASSE, Matriz.ENCERRAMENTO, TipoSaldo.ABERTURA, "siconfi"),
        _chave(ENTE, EXERCICIO, 12, CLASSE, Matriz.ENCERRAMENTO, TipoSaldo.ENCERRAMENTO,
               "siconfi"),
    }
    assert len(distintas) == 4


# ─── Tempo de vida do dado ───────────────────────────────────────────────────

def test_leitura_vale_para_o_job_e_morre_com_ele():
    """Scenario: o dado lido não atravessa execuções.

    Dentro do job, o recorte é lido uma vez e reaproveitado; o job seguinte lê de novo da fonte,
    porque a declaração pode ter sido retificada nesse meio-tempo.
    """
    from app.infra.msc.cache import ler_ou_baixar
    from app.infra.msc.escopo import escopo

    fonte = FonteFake()

    with escopo():
        for _ in range(3):
            ler_ou_baixar(fonte=fonte, ente=ENTE, ano=EXERCICIO, mes=12, classe=CLASSE)
    assert len(fonte.chamadas) == 1, "leituras repetidas dentro do job foram à fonte de novo"

    with escopo():
        ler_ou_baixar(fonte=fonte, ente=ENTE, ano=EXERCICIO, mes=12, classe=CLASSE)
    assert len(fonte.chamadas) == 2, "o dado do job anterior sobreviveu ao job"


def test_nada_e_gravado_em_redis():
    """Scenario: nenhum dado da MSC é persistido.

    Verificado na superfície do módulo: não há porta de cache persistente a que ligar um adapter.
    """
    import app.infra.fila.redis_adapters as adapters
    import app.infra.msc.cache as cache

    assert not hasattr(adapters, "CacheMscRedis"), "voltou um adapter de cache de dados da MSC"
    assert "cache" not in ler_parametros(cache.ler_ou_baixar)


def ler_parametros(funcao) -> set[str]:
    from inspect import signature

    return set(signature(funcao).parameters)


def test_sem_escopo_nada_e_memorizado():
    """Scenario: fora de um job, o comportamento é consultar a fonte a cada chamada."""
    from app.infra.msc.cache import ler_ou_baixar

    fonte = FonteFake()
    for _ in range(2):
        ler_ou_baixar(fonte=fonte, ente=ENTE, ano=EXERCICIO, mes=12, classe=CLASSE)

    assert len(fonte.chamadas) == 2


def test_publicsoft_nao_pre_checa_auditoria():
    """Scenario: o worker não consulta `/auditorias` — o endpoint exige JWT (401 com token_ps).

    Regressão de produção (2026-10-06). O gate fica no 409 do `base-demonstrativos`; uma
    leitura por classe, nenhuma chamada extra.
    """
    from app.infra.msc.publicsoft import PublicSoftMSC

    chamadas = []

    def http(url, params=None, headers=None, timeout=None):
        chamadas.append(url)
        return {"items": []}

    fonte = PublicSoftMSC(http=http, url_saldos="s")
    for classe in (1, 2, 3, 4, 5, 6):
        fonte.registros(ENTE, EXERCICIO, 12, classe)

    # Base por UG desde `pipeline-dca-por-unidade-gestora`; ainda uma leitura por classe.
    assert chamadas == ["s/unidades-gestoras"] * 6
