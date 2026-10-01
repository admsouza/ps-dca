"""Rastreabilidade: um teste por cenário do delta spec de `dca/balanco-financeiro`.

Os cenários cujo aceite é **medição contra dado real** — equivalência entre matrizes, aceite do
caso de referência, divergência registrada — são verificados aqui pelo registro documental que a
medição produziu, não por chamada de rede: é a mesma convenção que `dca/fonte-msc` já adota.
"""
from __future__ import annotations

import re
from decimal import Decimal
from pathlib import Path

import pytest

from tests.bf.conftest import ENTE, EXERCICIO, fonte_com
from tests.bo.conftest import registro, saldo

RAIZ = Path(__file__).resolve().parents[2]
EVIDENCIA = RAIZ / "docs" / "evidencia-bf-medicao-2026-09-18.md"
AUDITORIAS = sorted((RAIZ / "docs" / "entes-homologacao").glob("*/auditoria-bf-2025.md"))


def _codigos(resultado, quadro="QUADRO_PRINCIPAL"):
    return {linha.codigo: resultado.matriz[linha.id]
            for linha in resultado.mapa.linhas if linha.quadro == quadro}


# ─── fonte de recursos ───────────────────────────────────────────────────────

@pytest.mark.parametrize("fonte_msc,padrao,casa", [
    ("1500", "500", True),      # Scenario: fonte do exercício corrente casa com o código principal
    ("2500", "500", True),      # exercício anterior: mesmo código principal
    ("3500", "500", True),      # condicionado: idem
    ("9500", "500", True),
    ("1501", "500", False),
])
def test_fonte_casa_pelo_codigo_principal(fonte_msc, padrao, casa):
    """Scenario: fonte do exercício corrente casa com o código principal

    Cobre também o cenário `o mesmo código principal em exercícios anteriores e condicionados`:
    o 1º dígito é o exercício da vinculação, e a linha do IPC 06 é a mesma nos três casos.
    """
    from app.domain.bo.modelo import Filtro
    from app.domain.bo.saldo import atende

    reg = registro("621200000", "C", "10.00", fonte_recursos=fonte_msc)
    assert atende(reg, [Filtro("fonte_recurso", "in", (padrao,))]) is casa


def test_detalhamento_do_ente_nao_entra_no_casamento():
    """Scenario: detalhamento do ente após o código principal

    Medido: `fonte_recursos` tem sempre 4 dígitos e o detalhamento do ente vai em coluna separada
    (`complemento_fonte`), que a apuração não lê.
    """
    from app.domain.bo.modelo import Filtro
    from app.domain.bo.saldo import atende

    reg = registro("621200000", "C", "10.00", fonte_recursos="1500")
    assert atende(reg, [Filtro("fonte_recurso", "in", ("500",))])


def test_prefixo_solto_e_rejeitado_no_casamento_da_fonte():
    """Scenario: casamento por prefixo solto é rejeitado"""
    from app.domain.bo.modelo import Filtro
    from app.domain.bo.saldo import atende

    reg = registro("621200000", "C", "10.00", fonte_recursos="1500")
    assert not atende(reg, [Filtro("fonte_recurso", "in", ("50",))])


def test_campo_singular_nao_silencia_o_casamento():
    """Scenario: campo singular não silencia o casamento

    A regra declara `fonte_recurso` e o registro traz `fonte_recursos`. Sem religar o campo,
    `getattr` devolveria `""` e **nenhuma** linha casaria — zeradas, sem erro.
    """
    from app.domain.bo.saldo import _campo

    reg = registro("621200000", "C", "10.00", fonte_recursos="1500")
    assert _campo(reg, "fonte_recurso") == "500"


def test_fonte_fora_dos_subgrupos_do_ipc(apurar_bf):
    """Scenario: fonte fora dos subgrupos do IPC 06"""
    fonte = fonte_com(a2025={6: [saldo("621200000", "70.00", fonte_recursos="1999")]},
                      e2025={}, a2024={})
    resultado = apurar_bf(ENTE, EXERCICIO, fonte)
    assert _codigos(resultado)["L1"]["exercicio_atual"] == Decimal("0.00")


# ─── saldo em data ───────────────────────────────────────────────────────────

def test_l30_le_o_saldo_de_abertura_do_exercicio(apurar_bf):
    """Scenario: L30 lê o saldo de abertura do exercício

    Cobre `saldo do exercício anterior lido do ano anterior`.
    Cobre `o saldo de abertura vem do exercício anterior`: a abertura do exercício apurado é a
    posição **final**, que é `L62`.
    """
    fonte = fonte_com(a2025={1: [saldo("111110100", "1308763064.41")]},
                      a2024={1: [saldo("111110100", "802570332.31")]}, e2025={})
    linhas = _codigos(apurar_bf(ENTE, EXERCICIO, fonte))
    assert linhas["L30"]["exercicio_atual"] == Decimal("802570332.31")
    assert linhas["L63"]["exercicio_atual"] == Decimal("1308763064.41")


def test_as_duas_pontas_do_exercicio_fecham_entre_si(apurar_bf):
    """Scenario: as duas pontas do exercício fecham entre si

    `L29` do exercício apurado é `L62` do exercício anterior — a mesma conta, lida um ano antes.
    """
    fonte = fonte_com(a2025={1: [saldo("111110100", "500.00")]},
                      a2024={1: [saldo("111110100", "300.00")]}, e2025={}, e2024={}, a2023={})
    linhas = _codigos(apurar_bf(ENTE, EXERCICIO, fonte))
    assert linhas["L29"]["exercicio_atual"] == Decimal("300.00")
    assert linhas["L62"]["exercicio_anterior"] == Decimal("300.00")


def test_tipo_de_valor_nao_suportado_pela_fonte():
    """Scenario: tipo de valor não suportado pela fonte

    A fonte falha nomeando o tipo pedido, em vez de devolver o saldo de encerramento no lugar.
    """
    from app.infra.msc.fonte import Matriz
    from app.infra.msc.siconfi import SiconfiMSC

    with pytest.raises((KeyError, ValueError)):
        SiconfiMSC(http=lambda *a, **k: {"items": []}, espera=lambda _s: None).registros(
            ente=1, ano=2025, mes=12, classe=1, matriz=Matriz.ENCERRAMENTO,
            tipo_saldo="inexistente")


# ─── depósitos restituíveis ──────────────────────────────────────────────────

def test_depositos_restituiveis_apurados_pelo_saldo_declarado(apurar_bf):
    """Scenario: depósitos restituíveis apurados pelo saldo declarado"""
    fonte = fonte_com(a2025={2: [saldo("218810101", "300.00", fonte_recursos="1860")]},
                      e2025={}, a2024={})
    linhas = _codigos(apurar_bf(ENTE, EXERCICIO, fonte))
    assert linhas["L27"]["exercicio_atual"] == Decimal("300.00")
    assert linhas["L60"]["exercicio_atual"] == Decimal("300.00")


def test_nenhuma_linha_do_bf_depende_de_movimento_bruto(mapa_bf):
    """Scenario: nenhuma linha do BF depende de movimento bruto"""
    assert all(not getattr(coluna, "movimento", None)
               for linha in mapa_bf.linhas for coluna in linha.colunas)


# ─── classes, matriz e procedência ───────────────────────────────────────────

def test_classes_lidas(apurar_bf):
    """Scenario: classes lidas

    Cobre `transferências financeiras existem na matriz de encerramento lida pela abertura`: são
    as classes 3 e 4, que só respondem nesse par.
    """
    from app.infra.msc.fonte import fonte_de

    fonte = fonte_com(a2025={}, e2025={}, a2024={})
    resultado = apurar_bf(ENTE, EXERCICIO, fonte)
    assert resultado.procedencia.classes == (1, 2, 3, 4, 5, 6)
    assert fonte_de("BO", 12).classes == (5, 6)
    classes_pedidas = {c["classe"] for c in fonte.chamadas}
    assert {3, 4} <= classes_pedidas


def test_a_procedencia_diz_sobre_o_que_foi_apurado(apurar_bf):
    """Scenario: a procedência diz sobre o que foi apurado

    Cobre `a procedência nomeia a origem de cada linha`.
    """
    p = apurar_bf(ENTE, EXERCICIO, fonte_com(a2025={}, e2025={}, a2024={})).procedencia
    assert p.matriz and p.tipo_saldo and p.competencia == 12
    assert p.origens_por_linha["L25"] != p.origens_por_linha["L1"]
    assert p.origens_por_linha["L29"] != p.origens_por_linha["L1"]


def test_matriz_de_encerramento_pela_abertura_e_o_par_do_bf():
    """Scenario: a matriz de encerramento lida pela abertura é equivalente

    Cobre `a matriz de encerramento lida pelo encerramento zera as classes de resultado`.
    Cobre `o saldo de caixa não depende do tipo de matriz`. A equivalência é **medição** — 337
    células em dois entes, em `docs/evidencia-matriz-mscc-vs-msce.md`; o que a suíte garante é que
    o par declarado para o BF é o medido, e que a combinação errada não é exprimível.
    """
    from app.infra.msc.fonte import Matriz, TipoSaldo, fonte_de

    escolhido = fonte_de("BF", 12)
    assert (escolhido.matriz, escolhido.tipo_saldo) == (Matriz.ENCERRAMENTO, TipoSaldo.ABERTURA)
    assert (RAIZ / "docs" / "evidencia-matriz-mscc-vs-msce.md").is_file()


def test_apuracao_de_um_mes_que_nao_e_dezembro(apurar_bf):
    """Scenario: apuração de um mês que não é dezembro"""
    fonte = fonte_com(a2025={}, e2025={}, a2024={})
    resultado = apurar_bf(ENTE, EXERCICIO, fonte, competencia=6)
    assert resultado.procedencia.competencia == 6
    # L28/L61 leem `period_change` nas 12 competências, independente de `competencia` (D2) — o
    # snapshot do resto do BF é que respeita o parâmetro.
    snapshot = [c for c in fonte.chamadas
               if getattr(c["tipo_saldo"], "name", str(c["tipo_saldo"])) != "PERIODO"]
    assert {c["mes"] for c in snapshot} == {6}


# ─── linhas sem mapeamento e totais ──────────────────────────────────────────

def test_total_de_um_grupo_inteiramente_bloqueado(apurar_bf):
    """Scenario: total de um grupo inteiramente bloqueado"""
    linhas = _codigos(apurar_bf(ENTE, EXERCICIO, fonte_com(a2025={}, e2025={}, a2024={})))
    assert linhas["L21"]["exercicio_atual"] == Decimal("0.00")
    assert linhas["L22"]["exercicio_atual"] is None
    assert linhas["L23"]["exercicio_atual"] is None


def test_total_com_parcela_bloqueada_entre_parcelas_apuradas(apurar_bf):
    """Scenario: total com parcela bloqueada entre parcelas apuradas"""
    fonte = fonte_com(a2025={2: [saldo("218810101", "300.00", fonte_recursos="1860")]},
                      e2025={5: [saldo("531700000", "100.00")]}, a2024={})
    linhas = _codigos(apurar_bf(ENTE, EXERCICIO, fonte))
    assert linhas["L22"]["exercicio_atual"] is None, "L22 não tem conta no IPC 06"
    assert linhas["L24"]["exercicio_atual"] == Decimal("400.00"), "soma L25, L26 e L27"


def test_bloqueio_nao_vira_zero_na_propria_linha(apurar_bf):
    """Scenario: bloqueio não vira zero na própria linha"""
    resultado = apurar_bf(ENTE, EXERCICIO, fonte_com(a2025={}, e2025={}, a2024={}))
    linhas = _codigos(resultado)
    for codigo in ("L22", "L23", "L55", "L56"):
        assert linhas[codigo]["exercicio_atual"] is None
    motivos = {a.rule_id for a in resultado.diagnostico.nao_apuradas}
    assert len(motivos) >= 4


# ─── equilíbrio ──────────────────────────────────────────────────────────────

def test_demonstrativo_equilibrado(apurar_bf):
    """Scenario: demonstrativo equilibrado"""
    resultado = apurar_bf(ENTE, EXERCICIO, fonte_com(a2025={}, e2025={}, a2024={}))
    assert resultado.diagnostico.equilibrio["exercicio_atual"] == Decimal("0.00")
    assert resultado.diagnostico.equilibrio["exercicio_anterior"] == Decimal("0.00")


def test_desequilibrio_e_medido_nao_corrigido(apurar_bf):
    """Scenario: desequilíbrio é medido, não corrigido

    Receita sem dispêndio correspondente desequilibra o demonstrativo. Os dois totais mantêm o
    valor apurado, e a diferença é publicada com sinal.
    """
    fonte = fonte_com(a2025={6: [saldo("621200000", "1000.00", fonte_recursos="1500")]},
                      e2025={}, a2024={})
    resultado = apurar_bf(ENTE, EXERCICIO, fonte)
    linhas = _codigos(resultado)
    diferenca = resultado.diagnostico.equilibrio["exercicio_atual"]
    assert diferenca == Decimal("1000.00")
    assert linhas["L33"]["exercicio_atual"] - linhas["L66"]["exercicio_atual"] == diferenca


# ─── carregador e vigência ───────────────────────────────────────────────────

def test_carga_do_bf(mapa_bf):
    """Scenario: carga do BF"""
    assert len(mapa_bf.linhas) == 80
    assert all(linha.id.startswith("bf.") for linha in mapa_bf.linhas)


def test_exercicio_anterior_a_edicao_do_ipc06(carregar_mapa):
    """Scenario: exercício anterior à edição do IPC 06"""
    from app.infra.regras.carregador import SemVigencia

    with pytest.raises(SemVigencia, match="2024-06"):
        carregar_mapa(exercicio=2023, demonstrativo="bf")


def test_versao_de_regras_e_propria_de_cada_demonstrativo(carregar_mapa):
    """Scenario: versão de regras é própria de cada demonstrativo"""
    assert (carregar_mapa(exercicio=EXERCICIO, demonstrativo="bf").versao_regras
            != carregar_mapa(exercicio=EXERCICIO).versao_regras)


# ─── resultado publicado ─────────────────────────────────────────────────────

def test_ordem_de_apresentacao_do_bf(mapa_bf):
    """Scenario: ordem de apresentação do BF"""
    from app.services.pipeline.resultado import template

    linhas = template(mapa_bf)
    principal = [linha for linha in linhas if linha["quadro"] == "QUADRO_PRINCIPAL"]
    assert principal[0]["codigo"] == "L1" and principal[0]["grupo"] == "INGRESSOS"
    assert principal[-1]["codigo"] == "L66"
    assert linhas[-1]["quadro"] == "QUADRO_ANEXO"


def test_diagnostico_vazio_e_declarado(apurar_bf):
    """Scenario: diagnóstico vazio é declarado

    Consumidor que não encontra a chave não sabe se a apuração fechou ou se a versão do produtor
    não a produzia.
    """
    d = apurar_bf(ENTE, EXERCICIO, fonte_com(a2025={}, e2025={}, a2024={})).diagnostico
    for campo in ("nao_apuradas", "residuos", "equilibrio", "policies_nao_aplicadas"):
        assert hasattr(d, campo)
    assert d.sem_dados is True, "fonte sem registros é declarada, não inferida"


def test_regressao_do_bo(carregar_mapa):
    """Scenario: regressão do BO

    O BF usa o mesmo motor; o contrato do BO não muda por causa disso.
    """
    from app.infra.msc.fonte import fonte_de

    assert len(carregar_mapa(exercicio=EXERCICIO).linhas) == 69
    assert fonte_de("BO", 12).classes == (5, 6)


def test_nenhum_modulo_duplicado():
    """Scenario: nenhum módulo duplicado

    O BF não pode ter cópia do motor: matriz, saldo e modelo vivem num lugar só.
    """
    assert not (RAIZ / "app" / "domain" / "bf").exists()
    servico = (RAIZ / "app" / "services" / "bf" / "quadro_principal.py").read_text(encoding="utf-8")
    assert "from app.domain.bo.matriz import" in servico


# ─── aceite e auditoria ──────────────────────────────────────────────────────

def test_aceite_do_caso_de_referencia():
    """Scenario: aceite do caso de referência

    O `tt/dca` não publica o BF: o aceite se apoia nas identidades do demonstrativo, no RREO do
    próprio ente e no BF do SIAFIC. O registro está no relatório de auditoria de cada ente.
    """
    assert AUDITORIAS, "nenhum relatório de auditoria gerado"
    recife = next(a for a in AUDITORIAS if a.parent.name == "recife").read_text(encoding="utf-8")
    assert "Identidades do IPC 06 sobre o apurado" in recife
    assert "Conferência cruzada com o RREO" in recife
    assert "**DIVERGE**" not in recife.split("## Identidades")[1].split("## ")[0]


def test_divergencia_e_registrada_nao_escondida():
    """Scenario: divergência é registrada, não escondida"""
    for relatorio in AUDITORIAS:
        texto = relatorio.read_text(encoding="utf-8")
        assert "## Divergências" in texto
        assert re.search(r"\| Linha IPC 06 \| .*Coluna", texto), relatorio.parent.name
    assert EVIDENCIA.is_file()


def test_exercicio_anterior_sem_dados_na_fonte(apurar_bf):
    """Scenario: exercício anterior sem dados na fonte"""
    fonte = fonte_com(a2025={6: [saldo("621200000", "1000.00", fonte_recursos="1500")]},
                      e2025={}, a2024={})
    resultado = apurar_bf(ENTE, EXERCICIO, fonte)
    linhas = _codigos(resultado)
    assert linhas["L2"]["exercicio_atual"] == Decimal("1000.00")
    assert linhas["L2"]["exercicio_anterior"] == Decimal("0.00")
    assert resultado.diagnostico.sem_dados_exercicio_anterior is True
