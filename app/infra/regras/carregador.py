"""Carrega o mapa vigente a partir da base canônica em `knowledge/rules/<demonstrativo>/`.

O **exercício é parâmetro**, não constante implícita (P8 da change de plataforma). Hoje só a
edição `2020-01` responde, e o resultado é idêntico ao de fixar a edição no código — a
diferença aparece quando o STN publicar a próxima, e aí o retrofit atravessaria carregador,
service, chave de cache e todo resultado já apurado.

O YAML é a fonte nesta fase; na F3 entra a implementação de banco (`dca_regra_mapeamento`)
atrás da mesma função, e o YAML fica como semente.
"""
from __future__ import annotations

import hashlib
import json
from datetime import date
from functools import lru_cache
from pathlib import Path

import yaml

try:  # libyaml: ~7x mais rápido que o parser puro-Python
    from yaml import CSafeLoader as _Loader
except ImportError:  # pragma: no cover - roda sem libyaml compilado
    from yaml import SafeLoader as _Loader

from app.domain.bo.modelo import (
    Coluna,
    ContaCC,
    Filtro,
    Linha,
    MapaBO,
    RefColuna,
    RefLinha,
    Vigencia,
)

RAIZ_REPO = Path(__file__).resolve().parents[3]
KNOWLEDGE = RAIZ_REPO / "knowledge"
CONTAS_STN = RAIZ_REPO / "docs" / "contas-stn"


class SemVigencia(LookupError):
    """Nenhuma edição cobre o exercício pedido. Não se aproxima a mais próxima."""


def _regras(arquivo: Path) -> list[dict]:
    return (yaml.load(arquivo.read_text(encoding="utf-8"), _Loader) or {}).get("rules", [])


def carregar(exercicio: int, base: Path | None = None, demonstrativo: str = "bo") -> MapaBO:
    """Mapa vigente para o exercício, com a procedência do que foi carregado.

    `demonstrativo` escolhe a base canônica: `bo` (IPC 07) ou `bf` (IPC 06). Era fixo em `bo`,
    e o BF tem a mesma forma de regra — mesmo tradutor, mesma vigência, mesmo hash.
    """
    raiz = base or KNOWLEDGE
    edicoes = _vigencias(raiz, demonstrativo)

    aplicaveis = [v for v in edicoes if _cobre(v, exercicio)]
    if not aplicaveis:
        disponiveis = ", ".join(f"{v['edicao']} (desde {v['valid_from']})" for v in edicoes)
        raise SemVigencia(
            f"nenhuma vigência cobre o exercício {exercicio}. Disponíveis: {disponiveis or '—'}"
        )
    escolhida = max(aplicaveis, key=lambda v: v["valid_from"])

    linhas = tuple(
        _linha(regra)
        for arquivo in sorted((raiz / "rules" / demonstrativo).glob("*.yaml"))
        for regra in _regras(arquivo)
        if regra.get("version", {}).get("edition") == escolhida["edicao"]
    )

    tabelas = _hashes_das_tabelas(raiz)
    return MapaBO(
        linhas=linhas,
        vigencia=Vigencia(escolhida["documento"], escolhida["edicao"], exercicio),
        versao_regras=_hash_canonico(raiz, escolhida["edicao"], tabelas, demonstrativo),
        tabelas_stn=tabelas,
    )


# ─── vigência ────────────────────────────────────────────────────────────────

def _vigencias(raiz: Path, demonstrativo: str = "bo") -> list[dict]:
    """Edições declaradas pelas próprias regras, pelo bloco `version`."""
    vistas: dict[str, dict] = {}
    for arquivo in sorted((raiz / "rules" / demonstrativo).glob("*.yaml")):
        for regra in _regras(arquivo):
            versao = regra.get("version") or {}
            edicao = versao.get("edition")
            if not edicao or edicao in vistas:
                continue
            vistas[edicao] = {
                "documento": versao.get("source_document", ""),
                "edicao": edicao,
                "valid_from": str(versao.get("valid_from") or ""),
                "valid_until": versao.get("valid_until"),
            }
    return sorted(vistas.values(), key=lambda v: v["valid_from"])


def _cobre(vigencia: dict, exercicio: int) -> bool:
    inicio = _ano(vigencia["valid_from"])
    fim = _ano(vigencia["valid_until"]) if vigencia["valid_until"] else None
    if inicio is None:
        return False
    return inicio <= exercicio and (fim is None or exercicio <= fim)


def _ano(valor) -> int | None:
    if isinstance(valor, date):
        return valor.year
    texto = str(valor or "")[:4]
    return int(texto) if texto.isdigit() else None


# ─── identidade do conteúdo carregado (P-D7) ─────────────────────────────────

def _hash_canonico(raiz: Path, edicao: str, tabelas: dict[str, str],
                   demonstrativo: str = "bo") -> str:
    """SHA-256 do conteúdo **parseado** e reserializado de forma estável.

    Nunca dos bytes do arquivo: um `git checkout` que troque LF por CRLF mudaria o hash e
    invalidaria todo o cache sem regra nenhuma ter mudado.

    Entram as regras vigentes **e** os hashes das tabelas STN usadas: a apuração depende das
    duas coisas, e uma tabela de natureza de receita corrigida muda o resultado sem que
    nenhuma regra tenha mudado. Sem isso, o cache serviria valor velho.
    """
    regras = []
    for arquivo in sorted((raiz / "rules" / demonstrativo).glob("*.yaml")):
        for regra in _regras(arquivo):
            if (regra.get("version") or {}).get("edition") == edicao:
                regras.append(regra)
    conteudo = {"regras": regras, "tabelas_stn": tabelas}
    canonico = json.dumps(conteudo, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(canonico.encode("utf-8")).hexdigest()


def _hashes_das_tabelas(raiz: Path) -> dict[str, str]:
    meta = raiz / "sources" / "stn" / "metadata.yaml"
    if not meta.is_file():
        return {}
    dados = yaml.load(meta.read_text(encoding="utf-8"), _Loader) or {}
    return {Path(t["file"]).name: t["sha256"] for t in dados.get("tables") or []}


# ─── tradução YAML -> modelo do domínio ──────────────────────────────────────

def _linha(regra: dict) -> Linha:
    return Linha(
        id=regra["rule_id"],
        codigo=regra["linha"]["codigo"],
        rotulo=regra["linha"]["descricao"],
        quadro=regra["quadro"]["codigo"],
        grupo=(regra.get("grupo") or {}).get("codigo", ""),
        filtros=tuple(_filtro(f) for f in regra.get("filters") or []),
        exclusoes=tuple(
            tuple(_filtro(f) for f in grupo) for grupo in regra.get("exclusion_groups") or []
        ),
        colunas=tuple(_coluna(nome, dados) for nome, dados in (regra.get("columns") or {}).items()),
        referencias=tuple(
            RefLinha(r["rule"], r["sign"], r.get("column"))
            for r in (regra.get("calculation") or {}).get("references") or []
            if "rule" in r
        ),
        condicao=((regra.get("calculation") or {}).get("condition") or {}).get("when"),
        condicao_coluna=((regra.get("calculation") or {}).get("condition") or {}).get("column"),
        nivel=int(regra["linha"].get("nivel") or 0),
        ordem=int(regra["linha"].get("ordem") or 0),
        apenas_natureza=_apenas_natureza(regra.get("apenas_natureza")),
        bloqueio=_bloqueio(regra),
    )


def _bloqueio(regra: dict) -> str:
    """Motivo da regra `review_required`. Vazio nas demais."""
    if regra.get("status") != "review_required":
        return ""
    return str((regra.get("review") or {}).get("blocker") or "")


def _apenas_natureza(valor: str | None) -> str | None:
    """`credito|debito` do YAML -> "C"/"D" do lançamento (L28/L61, D1)."""
    return {"credito": "C", "debito": "D"}.get(valor)


def _filtro(dados: dict) -> Filtro:
    return Filtro(
        campo=dados["field"],
        operador=dados["operator"],
        valores=tuple(v["pattern"] for v in dados.get("values") or [] if v.get("pattern")),
        visao=dados.get("visao", ""),
    )


def _coluna(nome: str, dados: dict) -> Coluna:
    return Coluna(
        id=nome,
        rotulo=dados.get("label", nome),
        contas=tuple(
            ContaCC(c["pattern"], c.get("sign", "+"), c.get("financeiro_permanente") or "")
            for c in dados.get("accounts") or []
            if c.get("pattern")
        ),
        derivada=tuple(
            RefColuna(r["column"], r["sign"])
            for r in (dados.get("calculation") or {}).get("references") or []
            if "column" in r
        ),
    )


@lru_cache(maxsize=16)
def carregar_em_cache(exercicio: int, demonstrativo: str = "bo") -> MapaBO:
    """Mesma carga, memorizada — a base não muda em execução."""
    return carregar(exercicio, demonstrativo=demonstrativo)
