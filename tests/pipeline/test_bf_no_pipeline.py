"""O Balanço Financeiro servido pelo mesmo pipeline do BO.

O defeito que estes testes existem para pegar é **silencioso**: o envelope que envolve a fonte na
memória da execução foi escrito quando só havia o BO, que lê uma origem de saldo. O BF lê três. Se
o envelope não repassar o par de leitura, as três viram uma, e `L25`, `L26` e `L29`–`L32` saem com
números plausíveis e errados — sem exceção, sem log, sem célula não apurada.
"""
from __future__ import annotations

import pytest

from app.infra.msc.fonte import Matriz, TipoSaldo


class FonteEspiã:
    """Registra cada pedido, para asserção sobre o que chegou à fonte."""

    def __init__(self):
        self.pedidos: list[dict] = []

    def registros(self, ente, ano, mes, classe, matriz=None, tipo_saldo=None):
        self.pedidos.append({"ente": ente, "ano": ano, "mes": mes, "classe": classe,
                             "matriz": matriz, "tipo_saldo": tipo_saldo})
        return []


def test_envelope_de_cache_repassa_o_par_de_leitura():
    """Scenario: as três origens do BF chegam à fonte"""
    from app.services.pipeline.apuracao import _NoEscopo

    fonte = FonteEspiã()
    envelope = _NoEscopo(fonte, "siconfi")
    envelope.registros(1, 2025, 12, 1, matriz=Matriz.ENCERRAMENTO, tipo_saldo=TipoSaldo.ABERTURA)
    envelope.registros(1, 2025, 12, 1, matriz=Matriz.ENCERRAMENTO,
                       tipo_saldo=TipoSaldo.ENCERRAMENTO)
    envelope.registros(1, 2024, 12, 1, matriz=Matriz.ENCERRAMENTO, tipo_saldo=TipoSaldo.ABERTURA)

    assert [p["tipo_saldo"] for p in fonte.pedidos] == [
        TipoSaldo.ABERTURA, TipoSaldo.ENCERRAMENTO, TipoSaldo.ABERTURA]
    assert [p["ano"] for p in fonte.pedidos] == [2025, 2025, 2024]


def test_envelope_nao_inventa_o_par_de_leitura():
    """Scenario: o par de leitura não é inventado pelo envelope"""
    from app.services.pipeline.apuracao import _NoEscopo

    fonte = FonteEspiã()
    _NoEscopo(fonte, "siconfi").registros(1, 2025, 12, 5)
    assert fonte.pedidos[0]["matriz"] is None
    assert fonte.pedidos[0]["tipo_saldo"] is None


def test_bf_esta_no_conjunto_fechado_de_anexos():
    """Scenario: a rota do BF responde"""
    from app.services.pipeline.registry import anexo, implementado, validar_anexo

    assert validar_anexo("bf") == "BF"
    assert validar_anexo("B-F") == "BF"
    assert implementado("BF")
    assert anexo("BF").servico == "app.services.bf.quadro_principal:apurar"


def test_bf_sai_na_ordem_do_ipc06():
    """Scenario: o BF sai na ordem do IPC 06"""
    from app.infra.regras.carregador import carregar
    from app.services.pipeline.resultado import template

    linhas = template(carregar(2025, demonstrativo="bf"))
    grupos = [linha["grupo"] for linha in linhas if linha["quadro"] == "QUADRO_PRINCIPAL"]
    assert grupos[0] == "INGRESSOS"
    assert "DISPENDIOS" in grupos
    assert grupos.index("DISPENDIOS") > len(grupos) - grupos.count("DISPENDIOS") - 1
    codigos = [linha["codigo"] for linha in linhas if linha["quadro"] == "QUADRO_PRINCIPAL"]
    assert codigos[0] == "L1" and codigos[-1] == "L66"


def test_bo_mantem_a_ordem_que_ja_publicava():
    """Scenario: o BO mantém a ordem que já publicava"""
    from app.infra.regras.carregador import carregar
    from app.services.pipeline.resultado import template

    linhas = template(carregar(2025))
    assert linhas[0]["grupo"] == "RECEITAS"
    assert linhas[0]["quadro"] == "QUADRO_PRINCIPAL"
    assert [linha["quadro"] for linha in linhas][-1] == "RP_PROCESSADOS"


def test_origens_diferentes_da_coluna_anterior_nao_se_misturam():
    """Scenario: origens diferentes não se misturam no cache

    A origem da coluna anterior é por unidade (`anterior_por_recorte`); o consolidado não tem mais
    origem própria (`pipeline-consolidado-anterior-soma-unidades`)."""
    from app.services.pipeline.cache import identidade_do_pedido

    msce = identidade_do_pedido(
        anexo="BF", competencia=12,
        anterior_por_recorte={"ug:1": {"origem": "msce_exercicio_anterior"}})
    manual = identidade_do_pedido(
        anexo="BF", competencia=12,
        anterior_por_recorte={"ug:1": {"origem": "manual", "valores": {"L2": "1.00"}}})
    assert msce != manual


def test_dois_preenchimentos_manuais_sao_resultados_diferentes():
    """Scenario: dois preenchimentos manuais diferentes são resultados diferentes"""
    from app.services.pipeline.cache import identidade_do_pedido

    um = identidade_do_pedido(
        anexo="BF", competencia=12,
        anterior_por_recorte={"ug:1": {"origem": "manual", "valores": {"L2": "1.00"}}})
    outro = identidade_do_pedido(
        anexo="BF", competencia=12,
        anterior_por_recorte={"ug:1": {"origem": "manual", "valores": {"L2": "2.00"}}})
    assert um != outro


@pytest.mark.parametrize("campo", ["origens_por_linha", "origem_exercicio_anterior"])
def test_procedencia_do_bf_chega_ao_cliente(campo):
    """Scenario: o cliente sabe por que a célula está vazia"""
    from app.services.bf.quadro_principal import apurar
    from app.services.pipeline.resultado import para_dados
    from tests.bf.conftest import fonte_com

    resultado = apurar(2611606, 2025, fonte_com(a2025={}, e2025={}, a2024={}))
    corpo = para_dados(resultado)
    assert campo in corpo["procedencia"]
    assert "policies_nao_aplicadas" in corpo["diagnostico"]


def test_rota_e_cli_publicam_o_mesmo_json():
    """Scenario: a rota e o CLI publicam o mesmo JSON"""
    import json

    from app.cli.bf import _json
    from app.services.bf.quadro_principal import apurar
    from app.services.pipeline.resultado import para_dados
    from tests.bf.conftest import fonte_com

    resultado = apurar(2611606, 2025, fonte_com(a2025={}, e2025={}, a2024={}))
    assert json.loads(_json(resultado)) == para_dados(resultado)


def test_apurador_usa_o_servico_declarado_no_registry():
    """Requisito: o apurador do anexo chama o serviço que o registry declara, não o do BO.

    A fábrica importava `app.services.bo.quadro_principal` de forma fixa: o BF seria apurado pelas
    regras do IPC 07 sobre as classes do BO — resultado errado, sem erro.
    """
    from app.services.pipeline.apuracao import _servico_de

    assert _servico_de("BF").__module__ == "app.services.bf.quadro_principal"
    assert _servico_de("BO").__module__ == "app.services.bo.quadro_principal"


def test_mapa_vigente_carrega_a_base_do_anexo():
    """Requisito: o mapa do BF vem de `rules/bf`, não de `rules/bo`."""
    from app.services.pipeline.apuracao import mapa_vigente

    assert mapa_vigente(2025, "BF").vigencia.documento == "IPC06"
    assert mapa_vigente(2025, "BO").vigencia.documento == "IPC07"


def test_parametros_do_anexo_entram_na_identidade_e_no_job(monkeypatch):
    """Requisito: competência e origem da coluna anterior viajam no job e distinguem o cache.

    São escolhas que mudam o **valor** sem mudar `versao_api` nem `versao_regras`. Fora da
    identidade, o resultado de um mês seria servido a quem pediu outro; fora do payload do job,
    o worker apuraria dezembro qualquer que fosse o pedido.
    """
    from app.services.pipeline.cache import ler_ou_enfileirar

    class FilaEspiã:
        def __init__(self):
            self.chamadas = []

        def enfileirar(self, ente, exercicio, anexo, job_id, **parametros):
            self.chamadas.append(parametros)

    class LockFake:
        def adquirir(self, *a, **k):
            return True

        def liberar(self, *a, **k):
            return None

    class RepoVazio:
        def obter(self, *a):
            return None

        def gravar(self, registro):
            return None

    fila = FilaEspiã()
    ler_ou_enfileirar(ente="2611606", exercicio=2025, anexo="BF", repo=RepoVazio(), fila=fila,
                      lock=LockFake(), versao_api="1", versao_regras="r",
                      parametros={"competencia": 6, "origem_anterior": "manual"})
    assert fila.chamadas and fila.chamadas[0]["competencia"] == 6
    assert fila.chamadas[0]["origem_anterior"] == "manual"


def test_apurador_repassa_so_o_que_o_servico_aceita():
    """Requisito: um job só, parametrizado — o apurador não quebra com parâmetro alheio.

    O BF aceita `anterior` e `valores_anteriores`; o BO não. Repassar cegamente levantaria
    `TypeError` no worker, e o anexo ficaria preso em `processando`.
    """
    from app.services.bf.quadro_principal import apurar as apurar_bf
    from app.services.bo.quadro_principal import apurar as apurar_bo
    from app.services.pipeline.apuracao import _aceitos_por

    pedido = {"competencia": 6, "anterior": "manual", "valores_anteriores": {}}
    assert _aceitos_por(apurar_bf, pedido) == pedido
    assert _aceitos_por(apurar_bo, pedido) == {"competencia": 6}
