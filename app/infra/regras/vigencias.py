"""Repositório de vigências do mapeamento — INSERT-only, uma tabela para todos os anexos.

Segunda implementação da mesma porta do carregador de YAML (`app/infra/regras/carregador.py`): a de
banco, usada em produção; a de YAML, usada na semente e nos testes da F1, que assim não precisam de
Postgres. O domínio não sabe de qual das duas veio o mapa.

O YAML não deixa de existir — ele é a **semente**. `semear()` publica o que está versionado em
`knowledge/rules/**` como vigência de origem `seed-yaml`.

`SemVigencia` é reusada do carregador de propósito: "não aproxima a mais próxima" é a mesma regra,
venha do arquivo ou do banco, e duplicar a exceção deixaria uma das metades sem teste.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

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
from app.infra.cache.modelo import ORIGENS_VIGENCIA
from app.infra.regras.carregador import SemVigencia
from app.infra.regras.carregador import carregar as carregar_do_yaml

logger = logging.getLogger(__name__)

TABELA = "dca_regra_mapeamento"
ORIGENS = ORIGENS_VIGENCIA


class PublicacaoDestrutiva(RuntimeError):
    """Tentativa de alterar ou remover vigência publicada. Corrigir é publicar outra."""


class RepoVigencias(Protocol):
    """Porta do repositório. Sem `atualizar` e sem `remover` — a ausência é o contrato."""

    def inserir(self, registro: dict) -> dict: ...
    def listar(self, anexo: str) -> list[dict]: ...


def publicar(repo: RepoVigencias, *, anexo: str, ano: int, mes: int = 1,
             linhas: list[dict], origem: str, usuario_id: int | None = None) -> dict:
    """Acrescenta uma vigência. Nunca sobrescreve a anterior."""
    if origem not in ORIGENS:
        raise ValueError(f"origem inválida: {origem!r} — esperado um de {', '.join(ORIGENS)}")
    if origem == "api-admin" and usuario_id is None:
        raise ValueError("publicação administrativa exige o usuário que a publicou")

    registro = {
        "anexo": anexo,
        "ano_vigencia": ano,
        "mes_vigencia": mes,
        "versao": f"{ano}-{mes:02d}",
        "linhas": list(linhas),
        "origem": origem,
        "criado_em": datetime.now(UTC).isoformat(),
        "criado_por_usuario_id": usuario_id,
    }
    try:
        publicado = repo.inserir(registro)
    except Exception as erro:                      # PK duplicada no banco, KeyError no fake
        if _e_conflito_de_chave(erro):
            raise PublicacaoDestrutiva(
                f"vigência {anexo} {ano}-{mes:02d} já publicada. Publique uma vigência nova em vez "
                f"de reescrever a existente — quem apurou com ela precisa continuar podendo lê-la."
            ) from erro
        raise

    logger.info("vigência publicada | anexo=%s %s-%02d origem=%s usuario=%s",
                anexo, ano, mes, origem, usuario_id)
    return publicado


def _e_conflito_de_chave(erro: Exception) -> bool:
    if isinstance(erro, KeyError):
        return True
    try:
        from sqlalchemy.exc import IntegrityError
    except ImportError:
        return False
    return isinstance(erro, IntegrityError)


def resolver(repo: RepoVigencias, anexo: str, exercicio: int, mes: int = 12) -> dict:
    """Maior vigência `<=` à competência pedida. Falha nomeando as disponíveis."""
    publicadas = repo.listar(anexo)
    aplicaveis = [v for v in publicadas
                  if (v["ano_vigencia"], v["mes_vigencia"]) <= (exercicio, mes)]
    if not aplicaveis:
        disponiveis = ", ".join(f"{v['ano_vigencia']}-{v['mes_vigencia']:02d}" for v in publicadas)
        raise SemVigencia(
            f"nenhuma vigência de {anexo} cobre o exercício {exercicio}. "
            f"Disponíveis: {disponiveis or '—'}"
        )
    return max(aplicaveis, key=lambda v: (v["ano_vigencia"], v["mes_vigencia"]))


def carregar(repo: RepoVigencias, anexo: str, exercicio: int) -> MapaBO:
    """Mapa vigente lido do banco — mesma forma que o carregador de YAML devolve.

    **As tabelas de referência da STN não vêm do banco**, e é deliberado: elas são versionadas em
    `knowledge/sources/stn/`, mudam por deploy, e a vigência do mapeamento não as governa. Ler daí
    mantém duas propriedades que a procedência precisa: o resultado declara a versão das tabelas
    que usou, e uma tabela corrigida entra em `versao_regras` — invalidando o cache sem que
    nenhuma regra tenha mudado.
    """
    from app.infra.regras.carregador import KNOWLEDGE, _hashes_das_tabelas

    vigente = resolver(repo, anexo, exercicio)
    linhas = _completar_apresentacao(tuple(_linha(dado) for dado in vigente["linhas"]), exercicio)
    tabelas = _hashes_das_tabelas(KNOWLEDGE)
    # Hash do mapa efetivo (já completado). Senão a semente INSERT-only antiga não invalida o cache
    # quando a transcrição ganha coluna — medido: L26 sem `saldo` no jsonb, YAML já tinha.
    efetivo = {**vigente, "linhas": [_achatar(linha) for linha in linhas]}
    return MapaBO(
        linhas=linhas,
        vigencia=Vigencia(vigente.get("documento", "IPC 07"), vigente["versao"], exercicio),
        versao_regras=_hash_do_conteudo(efetivo, tabelas),
        tabelas_stn=tabelas,
    )


def _completar_apresentacao(linhas: tuple[Linha, ...], exercicio: int) -> tuple[Linha, ...]:
    """Completa apresentação e colunas ausentes com a transcrição versionada.

    A tabela é **INSERT-only**: a semente de 2020-01 não é reescrita no boot. Completar aqui
    evita que uma coluna nova no YAML (ex.: `L26.saldo`) fique de fora da apuração.

    Linha que a transcrição não contém — publicada por via administrativa — conserva o que veio
    do banco, e nunca falha a carga.
    """
    try:
        da_norma = {linha.id: linha for linha in carregar_do_yaml(exercicio).linhas}
    except Exception:
        logger.warning("transcrição indisponível para completar vigência", exc_info=True)
        return linhas

    completadas, sem_correspondente, colunas_extra = [], [], 0
    for posicao, linha in enumerate(linhas, start=1):
        referencia = da_norma.get(linha.id)
        if referencia is None:
            sem_correspondente.append(linha.id)
            completadas.append(linha._replace(
                nivel=linha.nivel or 1,
                ordem=linha.ordem or posicao,
            ))
            continue
        ids = {c.id for c in linha.colunas}
        extras = tuple(c for c in referencia.colunas if c.id not in ids)
        if extras:
            colunas_extra += len(extras)
        completadas.append(linha._replace(
            nivel=linha.nivel or referencia.nivel,
            ordem=linha.ordem or referencia.ordem,
            colunas=linha.colunas + extras,
        ))

    if any(not (origem.nivel and origem.ordem) for origem in linhas) or colunas_extra:
        logger.info(
            "vigência completada pela transcrição | nivel_ordem=%s colunas_extra=%d sem_correspondente=%d",
            sum(1 for x in linhas if not (x.nivel and x.ordem)),
            colunas_extra,
            len(sem_correspondente),
        )
    return tuple(completadas)


def semear(repo: RepoVigencias, base: Path | None = None, exercicio: int | None = None) -> int:
    """Publica o mapeamento versionado como vigência de origem `seed-yaml`.

    Idempotente: vigência já publicada é mantida — o `PRIMARY KEY` recusa a segunda, e a recusa é
    tratada como "já semeado", não como erro de boot.
    """
    from app.services.pipeline.registry import ANEXO_BO

    mapa = carregar_do_yaml(exercicio or datetime.now(UTC).year, base=base)
    ano = _ano_da_edicao(mapa.vigencia.edicao)

    try:
        publicar(
            repo,
            anexo=ANEXO_BO,
            ano=ano,
            mes=1,
            linhas=[_achatar(linha) for linha in mapa.linhas],
            origem="seed-yaml",
        )
    except PublicacaoDestrutiva:
        logger.info("semente já aplicada para %s %s — nada a fazer", ANEXO_BO, ano)
        return 0
    return 1


# ─── tradução entre o shape achatado (jsonb) e o modelo do domínio ───────────
#
# Correspondência 1:1 com `app/domain/bo/modelo.py` — `design.md` § 4bis. A transcrição normativa
# (página, evidência, hash do PDF) **não** entra: ela fica no YAML e não é lida ao apurar.

def _achatar(linha: Linha) -> dict:
    return {
        "id": linha.id,
        "codigo": linha.codigo,
        "rotulo": linha.rotulo,
        "quadro": linha.quadro,
        "grupo": linha.grupo,
        "condicao": linha.condicao,
        "condicao_coluna": linha.condicao_coluna,
        "nivel": linha.nivel,
        "ordem": linha.ordem,
        "filtros": [{"campo": f.campo, "operador": f.operador, "valores": list(f.valores)}
                    for f in linha.filtros],
        "exclusoes": [[{"campo": f.campo, "operador": f.operador, "valores": list(f.valores)}
                       for f in grupo] for grupo in linha.exclusoes],
        "colunas": [
            {
                "id": c.id,
                "rotulo": c.rotulo,
                "contas": [{"cc": conta.cc, "operacao": conta.operacao, "natureza_saldo": None}
                           for conta in c.contas],
                "derivada": [{"coluna": r.coluna, "sinal": r.sinal} for r in c.derivada],
            }
            for c in linha.colunas
        ],
        "referencias": [{"regra": r.regra, "sinal": r.sinal, "column": r.coluna}
                        for r in linha.referencias],
    }


def _linha(dado: dict) -> Linha:
    return Linha(
        id=dado["id"],
        codigo=dado["codigo"],
        rotulo=dado.get("rotulo", ""),
        quadro=dado.get("quadro", ""),
        grupo=dado.get("grupo", ""),
        filtros=tuple(_filtro(f) for f in dado.get("filtros") or []),
        exclusoes=tuple(tuple(_filtro(f) for f in grupo)
                        for grupo in dado.get("exclusoes") or []),
        colunas=tuple(_coluna(c) for c in dado.get("colunas") or []),
        referencias=tuple(RefLinha(r["regra"], r["sinal"], r.get("column"))
                          for r in dado.get("referencias") or []),
        condicao=dado.get("condicao"),
        condicao_coluna=dado.get("condicao_coluna"),
        nivel=int(dado.get("nivel") or 0),
        ordem=int(dado.get("ordem") or 0),
    )


def _filtro(dado: dict) -> Filtro:
    return Filtro(campo=dado["campo"], operador=dado["operador"],
                  valores=tuple(dado.get("valores") or []))


def _coluna(dado: dict) -> Coluna:
    return Coluna(
        id=dado["id"],
        rotulo=dado.get("rotulo", dado["id"]),
        contas=tuple(ContaCC(c["cc"], c.get("operacao", "+"))
                     for c in dado.get("contas") or []),
        derivada=tuple(RefColuna(r["coluna"], r["sinal"]) for r in dado.get("derivada") or []),
    )


def _ano_da_edicao(edicao: str) -> int:
    """`2020-01` -> 2020. Edição sem ano reconhecível não pode virar vigência silenciosamente."""
    inicio = str(edicao)[:4]
    if not inicio.isdigit():
        raise ValueError(f"edição sem ano reconhecível: {edicao!r}")
    return int(inicio)


def _hash_do_conteudo(vigente: dict[str, Any], tabelas: dict[str, str]) -> str:
    """Hash do conteúdo carregado do banco, canonicalizado.

    Sobre o array `linhas` **e** os hashes das tabelas STN, com chaves ordenadas — o mesmo critério
    do `_hash_canonico` da F1 (task 1.3), sem a armadilha de fim de linha que arquivos têm. As
    tabelas entram porque a apuração depende delas: uma natureza de receita corrigida muda o
    resultado sem que nenhuma regra mude, e sem isso o cache serviria valor velho.
    """
    import hashlib
    import json

    conteudo = {"linhas": vigente["linhas"], "tabelas_stn": tabelas}
    canonico = json.dumps(conteudo, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(canonico.encode("utf-8")).hexdigest()
