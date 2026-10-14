"""Coluna do exercício anterior por unidade — origem, leitura de N−1 e transposição.

Regra do pipeline, comum ao BF e ao BP (`pipeline-anterior-por-recorte`): este módulo não conhece
o anexo. Recebe o resultado gravado em N−1 e devolve a coluna pronta, que o serviço do anexo só
casa por (quadro, código). O grupo de poder não tem origem: soma as unidades.
"""
from __future__ import annotations

import re
from decimal import Decimal
from enum import StrEnum
from typing import Any, NamedTuple

from app.domain.recorte import CONSOLIDADO


class OrigemAnterior(StrEnum):
    PROCESSADO = "processado_exercicio_anterior"
    MSCE = "msce_exercicio_anterior"
    MANUAL = "manual"


PADRAO = "padrao"
SOMA_DAS_UNIDADES = "soma_das_unidades"
_UNIDADE = re.compile(r"ug:\d+|po:(\d{5})?")


class ProcessadoSemAnterior(Exception):
    """`processado_exercicio_anterior` pedido e N−1 sem resultado `ok` (ou sem o recorte)."""


class N1(NamedTuple):
    exercicio: int           # o exercício anterior
    registro: Any            # linha do cache, só quando `ok` e com resultado
    motivo: str | None       # por que não serve, quando o cache existe mas não está `ok`


def ler_n1(repo, ente, exercicio: int, anexo: str) -> N1:
    """O resultado de N−1 do mesmo anexo. `repo` ausente (CLI, teste) equivale a cache vazio."""
    anterior = exercicio - 1
    registro = repo.obter(str(ente), anterior, anexo) if repo is not None else None
    if registro is None:
        return N1(anterior, None, None)
    if registro.status == "ok" and registro.resultado:
        return N1(anterior, registro, None)
    motivo = {"processando": "exercício anterior em processamento",
              "erro": "exercício anterior com erro"}.get(registro.status)
    return N1(anterior, None, motivo)


def recorte_de(n1: N1, chave: str) -> dict | None:
    """O resultado do recorte em N−1, ou `None` se N−1 não serve ou não tem o recorte."""
    if n1.registro is None:
        return None
    dados = n1.registro.resultado
    if chave == CONSOLIDADO:
        return dados
    gravado = (dados.get("recortes") or {}).get(chave)
    return gravado["resultado"] if gravado else None


def exigir(n1: N1, chave: str) -> dict:
    """O recorte de N−1 para uma escolha pedida agora: sem ele, o erro do pedido."""
    dados = recorte_de(n1, chave)
    if dados is None:
        raise ProcessadoSemAnterior(f"processe {n1.exercicio} antes")
    return dados


def resolver(chave: str, escolha: dict | None, agora: bool,
             n1: N1) -> tuple[OrigemAnterior, str | None]:
    """A origem resolvida da unidade e o aviso que o diagnóstico registra, se houver.

    Escolha explícita vale; sem ela, o padrão é o processado quando N−1 o tem, senão a MSC.
    `processado` pedido agora sem N−1 é erro; o gravado cai em MSC com o motivo.
    """
    origem = OrigemAnterior(escolha["origem"]) if escolha else None
    if origem in (None, OrigemAnterior.PROCESSADO):
        if recorte_de(n1, chave) is not None:
            return OrigemAnterior.PROCESSADO, None
        if origem is not None and agora:
            raise ProcessadoSemAnterior(f"processe {n1.exercicio} antes")
        motivo = n1.motivo or ("exercício anterior sem resultado processado" if origem else None)
        return OrigemAnterior.MSCE, f"{chave}: {motivo}" if motivo else None
    return origem, None


def procedencia_do_processado(n1: N1, dados: dict) -> dict:
    """De qual resultado de N−1 veio a coluna: o que reproduz o retrato, e só ele."""
    registro, procedencia = n1.registro, dados["procedencia"]
    calculado = registro.calculado_em
    saida = {"exercicio": n1.exercicio,
             "calculado_em": (calculado.isoformat() if hasattr(calculado, "isoformat")
                              else calculado),
             "versao_regras": procedencia["versao_regras"],
             "fonte": _fonte_da_identidade(registro.versao_regras)}
    for estorno in ("estorno_receita_extra", "estorno_despesa_extra"):
        if procedencia.get(estorno):
            saida[estorno] = procedencia[estorno]
    return saida


def _fonte_da_identidade(versao_regras: str | None) -> str | None:
    pedido = (versao_regras or "").partition("|")[2]
    return next((parte[2:] for parte in pedido.split(":") if parte.startswith("f=")), None)


def pronto(dados: dict, de: str = "_atual") -> dict:
    """A coluna `<x><de>` do resultado como coluna anterior de N, por (quadro, código).

    De N−1: `_atual → _anterior`. De uma unidade já apurada (soma do grupo): `_anterior` fica.
    No BP leva também cada visão e o saldo sem fonte (`fonte_vazia`).
    """
    saida: dict = {"matriz": _celulas(dados, dados["matriz"], de)}
    visoes = {nome: _celulas(dados, visao["matriz"], de)
              for nome, visao in (dados.get("visoes") or {}).items()}
    if visoes:
        saida["visoes"] = visoes
    vazio = (dados["diagnostico"].get("fonte_vazia") or {}).get(f"exercicio{de}")
    saida["fonte_vazia"] = Decimal(vazio) if vazio else Decimal("0.00")
    return saida


def _celulas(dados: dict, matriz: dict, de: str) -> dict[tuple[str, str], dict]:
    saida = {}
    for linha in dados["linhas"]:
        celulas = matriz.get(linha["rule_id"]) or {}
        saida[(linha["quadro"], linha["codigo"])] = {
            coluna[: -len(de)] + "_anterior": None if valor is None else Decimal(valor)
            for coluna, valor in celulas.items() if coluna.endswith(de)}
    return saida


def somar(partes: list[dict]) -> dict:
    """Soma, célula a célula, as colunas prontas das unidades do grupo.

    Linha ausente numa unidade (fonte do Superávit) conta 0,00; célula não apurada em qualquer
    unidade deixa a do grupo não apurada. As totalizadoras são somadas como as folhas: pela
    aditividade, é o que a calculation daria sobre as folhas somadas.
    """
    saida: dict = {"matriz": _somar_celulas([p["matriz"] for p in partes]),
                   "fonte_vazia": sum((p["fonte_vazia"] for p in partes), Decimal("0.00"))}
    nomes = {nome for p in partes for nome in p.get("visoes", {})}
    if nomes:
        saida["visoes"] = {nome: _somar_celulas([p.get("visoes", {}).get(nome, p["matriz"])
                                                 for p in partes]) for nome in sorted(nomes)}
    return saida


def _somar_celulas(listas: list[dict]) -> dict:
    zero = Decimal("0.00")
    saida: dict = {}
    for chave in {chave for lista in listas for chave in lista}:
        colunas = {c for lista in listas for c in lista.get(chave, {})}
        saida[chave] = {}
        for coluna in colunas:
            valores = [lista.get(chave, {}).get(coluna, zero) for lista in listas]
            saida[chave][coluna] = (None if any(v is None for v in valores)
                                    else sum(valores, zero))
    return saida


def validar_escolhas(anexo: str, exercicio: int, escolhas: dict[str, Any]) -> dict[str, dict]:
    """`anterior_por_recorte` do pedido, validado e normalizado (`ValueError` → 422).

    Só unidades (`ug:`/`po:`): grupo e `consolidado` derivam. `padrao` limpa a escolha gravada.
    """
    if anexo not in ("BF", "BP"):
        raise ValueError(f"{anexo} não tem coluna anterior por unidade")
    saida: dict[str, dict] = {}
    for chave, escolha in escolhas.items():
        if not _UNIDADE.fullmatch(chave):
            raise ValueError(f"anterior_por_recorte aceita só ug:<id> e po:<código>: {chave}")
        origem = escolha.origem
        if origem == PADRAO:
            saida[chave] = {"origem": PADRAO}
        elif origem == OrigemAnterior.MANUAL:
            if not escolha.valores:
                raise ValueError(f"{chave}: manual exige valores")
            _validar_manual(anexo, exercicio, escolha.valores)
            saida[chave] = {"origem": origem, "valores": dict(escolha.valores)}
        elif origem in (OrigemAnterior.PROCESSADO, OrigemAnterior.MSCE):
            saida[chave] = {"origem": origem}
        else:
            raise ValueError(f"{chave}: origem desconhecida: {origem}")
    return saida


def _validar_manual(anexo: str, exercicio: int, valores: dict[str, str]) -> None:
    if anexo == "BP":
        from app.services.bp.informados import validar_valores_anteriores
    else:
        from app.services.bf.informados import validar_valores_anteriores
    validar_valores_anteriores(exercicio, valores)
