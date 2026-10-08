"""O Balanço Patrimonial servido pelo mesmo pipeline do BO e do BF.

O defeito que interessa é silencioso: o worker apura pela vigência **publicada no banco**, não pelo
YAML. Campo que `_achatar`/`_linha` não levam — o atributo F/P do termo, o bloqueio da linha — some
na ida e volta, e o BP sai com números plausíveis e errados.
"""
from __future__ import annotations


def _mapa():
    from app.infra.regras.carregador import carregar
    return carregar(2025, demonstrativo="bp")


def test_bp_esta_no_conjunto_fechado_de_anexos():
    """Scenario: resumo deixa de reportar sem_cache"""
    from app.services.pipeline.registry import anexo, implementado, validar_anexo

    assert validar_anexo("bp") == "BP"
    assert implementado("BP")
    assert anexo("BP").servico == "app.services.bp.quadro_principal:apurar"
    assert anexo("BP").base_canonica == "bp"


def test_bp_sai_na_ordem_do_ipc04():
    """Requisito: template — principal, F/P, compensação e superávit, nesta ordem."""
    from app.services.pipeline.resultado import template

    linhas = template(_mapa())
    sequencia = [linha["quadro"] for linha in linhas]
    blocos = [q for i, q in enumerate(sequencia) if i == 0 or q != sequencia[i - 1]]
    assert blocos == ["QUADRO_PRINCIPAL", "ATIVOS_PASSIVOS_FINANCEIROS",
                      "CONTAS_COMPENSACAO", "SUPERAVIT_DEFICIT"]
    principal = [linha for linha in linhas if linha["quadro"] == "QUADRO_PRINCIPAL"]
    assert principal[0]["codigo"] == "L1" and principal[-1]["codigo"] == "L40"


def test_vigencia_publicada_preserva_atributo_e_bloqueio():
    """Requisito: D2/D2b — ida e volta pelo shape do banco sem perder o atributo nem o bloqueio."""
    from app.infra.regras.vigencias import _achatar, _linha

    por_id = {linha.id: linha for linha in _mapa().linhas}
    for rule_id in ("bp.ativos_passivos_financeiros.l5", "bp.contas_compensacao.l2"):
        assert _linha(_achatar(por_id[rule_id])) == por_id[rule_id], rule_id
    l5 = por_id["bp.ativos_passivos_financeiros.l5"]
    assert {c.financeiro_permanente for c in l5.colunas[0].contas} == {"F", ""}
    assert por_id["bp.contas_compensacao.l2"].bloqueio


def test_ancoras_do_iab_apontam_linhas_do_ipc04():
    """Scenario: âncoras de João Pessoa 2025 — o de-para fixo do `I-AB` aponta linhas que existem.

    A medição em si (apurado × publicado, conta a conta) é homologação de rede, registrada em
    `docs/depara-bp-iab-ipc04.md`. Aqui se garante que o de-para não envelhece contra o mapa.
    """
    import re

    from tests.conftest import RAIZ_REPO

    texto = (RAIZ_REPO / "docs" / "depara-bp-iab-ipc04.md").read_text(encoding="utf-8")
    quadro = {"Principal": "QUADRO_PRINCIPAL", "F/P": "ATIVOS_PASSIVOS_FINANCEIROS"}
    alvos = re.findall(r"^\| `[^|/]+` \| (Principal|F/P) `(L\d+)`", texto, re.M)
    alvos += [("F/P", c) for par in re.findall(r"^\| `\w+` / `\w+` \| F/P `(L\d+)` / `(L\d+)`",
                                                texto, re.M) for c in par]
    existentes = {(linha.quadro, linha.codigo) for linha in _mapa().linhas}
    assert len(alvos) == 11
    for nome, codigo in alvos:
        assert (quadro[nome], codigo) in existentes, (nome, codigo)


def test_bo_publica_o_mesmo_shape_de_antes():
    """Requisito: regressão — campo novo vazio fica fora do shape; a vigência do BO não muda."""
    from app.infra.regras.carregador import carregar
    from app.infra.regras.vigencias import _achatar

    for linha in carregar(2025).linhas:
        dado = _achatar(linha)
        assert "bloqueio" not in dado
        for coluna in dado["colunas"]:
            for conta in coluna["contas"]:
                assert set(conta) == {"cc", "operacao", "natureza_saldo"}
