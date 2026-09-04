"""Cenários de direção do saldo e composição da célula — o núcleo da apuração.

Todos ancorados na medição de João Pessoa 12/2025 (`docs/validacao-bo-jp-2025.md`), onde os
valores bateram em centavos contra `DCA-Anexo I-C`, `I-D` e `RREO-Anexo 01`.
"""
from __future__ import annotations

from decimal import Decimal

import pytest

from tests.bo.conftest import DirecaoFake, registro, saldo

# Contas do caso real e a natureza de saldo de cada uma no PCASP.
FUNDEB = "621310100"        # Deduções — FUNDEB · Devedora
OUTRAS_DEDUCOES = "621390000"  # Outras Deduções da Receita · Devedora
RECEITA_BRUTA = "621200000"    # Receitas Realizadas · Credora


# ─── Direção do saldo resolvida por conta folha na tabela PCASP ──────────────

def test_conta_devedora_de_classe_6(saldo_da_conta):
    """Scenario: conta devedora de classe 6."""
    registros = [
        registro(FUNDEB, "D", "332643194.90"),
        registro(FUNDEB, "C", "0.00"),
    ]
    assert saldo_da_conta(registros, credora=False) == Decimal("332643194.90")

    outras = [registro(OUTRAS_DEDUCOES, "D", "44846513.57")]
    assert saldo_da_conta(outras, credora=False) == Decimal("44846513.57")


def test_heuristica_de_classe_e_rejeitada(apurar_quadro, carregar_mapa):
    """Scenario: heurística de classe é rejeitada.

    `621310100` e `621390000` são classe 6 e devedoras. Tratadas como credoras — o que a
    heurística `_CLASSES_CREDORAS = {2,6,8}` do `regras-rgf-api` faria — sairiam negativas.
    """
    from app.domain.bo import saldo as modulo

    fonte = ""
    for atributo in dir(modulo):
        fonte += atributo
    assert "CLASSES_CREDORAS" not in fonte.upper(), (
        "o módulo de saldo não pode conhecer conjunto de classes credoras"
    )


def test_contas_de_mesmo_prefixo_com_direcoes_opostas(saldo_da_conta):
    """Scenario: contas de mesmo prefixo com direções opostas (prefixo 6.2.1.3)."""
    credora = [registro("621300000", "C", "10.00")]
    devedora = [registro(FUNDEB, "D", "10.00")]
    assert saldo_da_conta(credora, credora=True) == Decimal("10.00")
    assert saldo_da_conta(devedora, credora=False) == Decimal("10.00")


def test_natureza_do_lancamento_nao_determina_a_direcao(saldo_da_conta):
    """Scenario: natureza do lançamento não determina a direção."""
    registros = [
        registro(RECEITA_BRUTA, "C", "100.00"),
        registro(RECEITA_BRUTA, "D", "30.00"),
        registro(RECEITA_BRUTA, "D", "20.00"),
    ]
    # Credora: Σ C − Σ D = 100 − 50, mesmo com mais lançamentos a débito.
    assert saldo_da_conta(registros, credora=True) == Decimal("50.00")


def test_direcao_vem_da_tabela_pcasp(direcao_do_pcasp):
    """Requisito: a direção é lida do `PCASP.md`, por conta folha de 9 dígitos."""
    direcao = direcao_do_pcasp()
    assert direcao.credora(FUNDEB) is False
    assert direcao.credora(OUTRAS_DEDUCOES) is False
    assert direcao.credora(RECEITA_BRUTA) is True
    assert direcao.credora("999999999") is None


# ─── Saldo da célula por soma de saldos, com a operação da regra ─────────────

def test_coluna_com_uma_conta(apurar_matriz, carregar_mapa, direcao_do_pcasp):
    """Scenario: coluna com uma conta — Despesas Pagas, `622130400`, JP 12/2025."""
    registros = [saldo("622130400", "4529794533.11", natureza_despesa="3.1.00.00.00")]
    matriz = apurar_matriz(carregar_mapa(exercicio=2025), registros, direcao_do_pcasp())
    assert matriz.valores["bo.quadro_principal.despesas.l32"]["pagas"] == Decimal(
        "4529794533.11")


def test_coluna_com_varias_contas_somadas(apurar_matriz, carregar_mapa, direcao_do_pcasp):
    """Scenario: coluna com várias contas somadas — Despesas Empenhadas."""
    registros = [
        saldo("622130400", "4529794533.11", natureza_despesa="3.1.00.00.00"),
        saldo("622130500", "281307109.52", natureza_despesa="3.1.00.00.00"),
        saldo("622130700", "39255202.67", natureza_despesa="3.1.00.00.00"),
    ]
    matriz = apurar_matriz(carregar_mapa(exercicio=2025), registros, direcao_do_pcasp())
    celulas = matriz.valores["bo.quadro_principal.despesas.l32"]
    assert celulas["empenhadas"] == Decimal("4850356845.30")
    assert celulas["liquidadas"] == Decimal("4569049735.78")


def test_conta_com_sinal_negativo_na_formula(apurar_matriz, carregar_mapa, direcao_do_pcasp):
    """Scenario: conta com sinal negativo na fórmula — Dotação Atualizada."""
    registros = [
        saldo("522110100", "5314144648.00", natureza_despesa="3.1.00.00.00"),
        saldo("522120100", "828005403.02", natureza_despesa="3.1.00.00.00"),
        saldo("522120201", "161060637.16", natureza_despesa="3.1.00.00.00"),
        saldo("522190400", "260029556.28", natureza_despesa="3.1.00.00.00"),
    ]
    matriz = apurar_matriz(carregar_mapa(exercicio=2025), registros, direcao_do_pcasp())
    assert matriz.valores["bo.quadro_principal.despesas.l32"]["dotacao_atualizada"] == Decimal(
        "6043181131.90")


def test_valores_sao_decimal_nunca_float(apurar_matriz, carregar_mapa, direcao_do_pcasp):
    """Requisito: `Decimal` em todo o cálculo; o aceite da DCA é 1:1 em centavos."""
    registros = [saldo("622130400", "0.10", natureza_despesa="3.1.00.00.00")]
    matriz = apurar_matriz(carregar_mapa(exercicio=2025), registros, direcao_do_pcasp())
    for celulas in matriz.valores.values():
        for valor in celulas.values():
            assert valor is None or isinstance(valor, Decimal)


# ─── Casamento de conta por conta folha declarada ────────────────────────────

def test_conta_irma_de_controle_paralelo_nao_entra(apurar_matriz, carregar_mapa,
                                                   direcao_do_pcasp):
    """Scenario: conta irmã de controle paralelo não entra.

    `522139900` é irmã de `522130100` sob o prefixo `5.2.2.1.3`. Casar por prefixo a captura e
    infla a coluna de `L29` em R$ 729.036.483,90 — medido em JP 12/2025.
    """
    registros = [
        saldo("522130100", "470338332.64"),
        registro("522139900", "C", "729036483.90"),   # bifront: sem direção única
    ]
    matriz = apurar_matriz(carregar_mapa(exercicio=2025), registros, direcao_do_pcasp())
    valor = matriz.valores["bo.quadro_principal.receitas.l29"]["previsao_atualizada"]
    assert valor == Decimal("470338332.64")


def test_contas_bifront_ficam_fora_das_colunas(apurar_matriz, carregar_mapa, direcao_do_pcasp):
    """Scenario: contas bifront ficam fora das colunas."""
    registros = [
        saldo("522110100", "5314144648.00", natureza_despesa="3.1.00.00.00"),
        saldo("522120100", "828005403.02", natureza_despesa="3.1.00.00.00"),
        saldo("522120201", "161060637.16", natureza_despesa="3.1.00.00.00"),
        saldo("522190400", "260029556.28", natureza_despesa="3.1.00.00.00"),
        registro("522139900", "C", "729036483.90", natureza_despesa="3.1.00.00.00"),
        registro("621100000", "C", "454467502.93", natureza_receita="1100.00.00"),
    ]
    matriz = apurar_matriz(carregar_mapa(exercicio=2025), registros, direcao_do_pcasp())
    assert matriz.valores["bo.quadro_principal.despesas.l32"][
        "dotacao_atualizada"] == Decimal("6043181131.90")


# ─── Célula sem direção conhecida não é apurada ──────────────────────────────

def test_conta_sem_natureza_conhecida(apurar_matriz, carregar_mapa):
    """Scenario: conta sem natureza conhecida — célula `None`, com aviso nomeando o contexto."""
    direcao = DirecaoFake(credoras={"622130500", "622130700"})  # `622130400` fica sem direção
    registros = [
        registro("622130400", "C", "10.00", natureza_despesa="3.1.00.00.00"),
        registro("622130500", "C", "20.00", natureza_despesa="3.1.00.00.00"),
    ]
    matriz = apurar_matriz(carregar_mapa(exercicio=2025), registros, direcao)
    celulas = matriz.valores["bo.quadro_principal.despesas.l32"]
    assert celulas["pagas"] is None

    aviso = " ".join(str(a) for a in matriz.nao_apuradas)
    assert "622130400" in aviso
    assert "bo.quadro_principal.despesas.l32" in aviso and "pagas" in aviso
    # As demais células continuam apuradas.
    assert matriz.valores["bo.quadro_principal.despesas.l33"] is not None


def test_zero_legitimo_e_distinguido_de_nao_apurado(apurar_matriz, carregar_mapa,
                                                    direcao_do_pcasp):
    """Scenario: zero legítimo é distinguido de não apurado."""
    matriz = apurar_matriz(carregar_mapa(exercicio=2025), [], direcao_do_pcasp())
    celulas = matriz.valores["bo.quadro_principal.despesas.l32"]
    assert celulas["pagas"] == Decimal("0.00")

    # Sem escrituração nenhuma, nenhuma **célula** fica sem apurar. As pendências que restam são
    # das 4 linhas que cruzam receita e despesa (C5), que não dependem de dado.
    de_celula = [a for a in matriz.nao_apuradas if a.coluna != "-"]
    assert de_celula == []


# ─── Coluna (a) do quadro de RP Não Processados — termo `5.3.1.3` removido ───
#
# Direção conforme o PCASP: `5.3.1.*` é Devedora nas 4 contas do grupo, `6.3.1.6` é Credora.
# A fixture antiga declarava as `531*` como credoras, contra a tabela (D4 do design).
DIRECAO_RP = DirecaoFake(
    devedoras={"531100000", "531200000", "531600000", "531700000"},
    credoras={"631600000"},
)
COLUNA_A = "inscritos_exerc_anteriores"


def _contas_da_coluna_a(mapa, rule_id: str) -> list[str]:
    linha = next(linha for linha in mapa.linhas if linha.id == rule_id)
    coluna = next(c for c in linha.colunas if c.id == COLUNA_A)
    return [conta.cc for conta in coluna.contas]


def _folhas_do_quadro(mapa, quadro: str) -> list[str]:
    """As linhas que declaram coluna. `L1`, `L5` e `L9` são compostas e agregam as folhas."""
    return [
        linha.id for linha in mapa.linhas
        if linha.id.startswith(f"bo.{quadro}.") and not linha.composta
    ]


def test_coluna_a_do_rpnp_declara_tres_contas(carregar_mapa):
    """Scenario: coluna com contas de sinal negativo.

    O literal do IPC 07 p. 12 tem 4 termos, mas `5.3.1.3` foi descontinuada e o que ela guardava
    está em `5.3.1.2` — que já é o primeiro termo. Declarar as duas duplicaria `5.3.1.2`, porque
    `saldo_da_celula` soma por conta declarada e não deduplica.
    """
    mapa = carregar_mapa(exercicio=2025)
    folhas = _folhas_do_quadro(mapa, "rp_nao_processados")
    assert len(folhas) == 6, "6 folhas declaram a coluna; L1, L5 e L9 agregam"
    for rule_id in folhas:
        contas = _contas_da_coluna_a(mapa, rule_id)
        assert contas == ["5312", "5316", "6316"], f"{rule_id} declara {contas}"
        assert "5313" not in contas


def test_coluna_a_e_simetrica_nos_dois_quadros(carregar_mapa):
    """Scenario: a fórmula fica simétrica à do quadro de RP Processados.

    O grupo `5.3.2` não tem `5.3.2.3`, e a fórmula de RP Processados sempre teve 3 termos. Com o
    termo removido, os dois quadros declaram as mesmas posições de família.
    """
    mapa = carregar_mapa(exercicio=2025)
    nao_processados = _contas_da_coluna_a(mapa, "bo.rp_nao_processados.l2")
    processados = _contas_da_coluna_a(mapa, "bo.rp_processados.l2")
    assert nao_processados == ["5312", "5316", "6316"]
    assert processados == ["5322", "5326", "6326"]
    # Mesma posição de família: o dígito que difere é o do subgrupo (índice 2).
    assert [c[:2] + c[3:] for c in nao_processados] == [c[:2] + c[3:] for c in processados]


def test_conta_descontinuada_nao_apaga_a_celula(apurar_matriz, carregar_mapa):
    """Scenario: escrituração em conta descontinuada não apaga a célula.

    Nenhum ente medido escritura `5.3.1.3` — zero ocorrências em ~185.000 registros de classe 5
    em 9 entes (`docs/evidencia-c6-c7.md`). Se algum escriturar, o registro é ignorado por não
    casar com conta declarada, e as 9 linhas seguem apuradas. Antes desta change a mesma entrada
    tornava a célula inteira `None`, por direção desconhecida.
    """
    registros = [registro("531300000", "C", "10.00", natureza_despesa="3.1.00.00")]
    matriz = apurar_matriz(carregar_mapa(exercicio=2025), registros, DIRECAO_RP)

    celula = matriz.valores["bo.rp_nao_processados.l2"][COLUNA_A]
    assert celula == Decimal("0.00"), "o registro não casa com conta declarada e não é somado"

    apagadas = [
        a for a in matriz.nao_apuradas
        if a.rule_id.startswith("bo.rp_nao_processados.") and a.coluna == COLUNA_A
    ]
    assert apagadas == [], "nenhuma das 9 linhas pode ficar sem apurar por causa de 5.3.1.3"


# ─── Exemplo documental do IPC 07 p. 8 (fixture da task 2.2) ─────────────────

def test_exemplo_documental_l2(apurar_matriz, carregar_mapa, exemplo_l2, direcao_l2):
    """Requisito: o exemplo do item 23 do IPC 07 apura as 4 colunas de `L2`.

    Cobre numa só passagem: conta credora, conta devedora e coluna derivada.
    """
    matriz = apurar_matriz(carregar_mapa(exercicio=2025), exemplo_l2, direcao_l2)
    celulas = matriz.valores["bo.quadro_principal.receitas.l2"]
    assert celulas["previsao_inicial"] == Decimal("1000.00")
    assert celulas["previsao_atualizada"] == Decimal("1200.00")
    assert celulas["receitas_realizadas"] == Decimal("800.00")
    assert celulas["saldo"] == Decimal("-400.00")


@pytest.mark.parametrize("conta,esperado", [("621310100", False), ("621390000", False)])
def test_deducoes_de_classe_6_sao_devedoras_no_pcasp(direcao_do_pcasp, conta, esperado):
    """Requisito: a tabela é a fonte da direção — as duas deduções são devedoras."""
    assert direcao_do_pcasp().credora(conta) is esperado
