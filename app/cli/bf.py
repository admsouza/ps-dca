"""Apura o Quadro Principal do BF e imprime a matriz.

    python -m app.cli.bf <cod_ibge> <exercicio> [--competencia 1..12]
                         [--fonte siconfi|publicsoft] [--json]
                         [--anterior msce|manual] [--anterior-arquivo <json>]

Mesmo papel do CLI do BO: torna a F1 verificável sem rota, sem banco e sem container.
"""
from __future__ import annotations

import argparse
import json
import sys
from decimal import Decimal
from pathlib import Path

from app.services.bf.quadro_principal import Anterior, apurar


def _fonte(nome: str, token: str):
    if nome == "publicsoft":
        from app.infra.msc.publicsoft import PublicSoftMSC

        return PublicSoftMSC(token=token)
    from app.infra.msc.siconfi import SiconfiMSC

    return SiconfiMSC()


def _valores_anteriores(caminho: str | None) -> dict[str, Decimal] | None:
    """`{"L1": "803288054.29", ...}` — valor por linha do IPC 06, informado pelo usuário."""
    if not caminho:
        return None
    dados = json.loads(Path(caminho).read_text(encoding="utf-8"))
    return {codigo: Decimal(str(valor)) for codigo, valor in dados.items()}


def _br(valor: Decimal) -> str:
    """1.234.567,89 — a moeda como o demonstrativo publica."""
    return f"{valor:>20,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")


QUADROS = {"principal": ("QUADRO_PRINCIPAL",), "anexo": ("QUADRO_ANEXO",),
           "todos": ("QUADRO_PRINCIPAL", "QUADRO_ANEXO")}


def _texto(resultado, quadro: str = "todos") -> str:
    """O filtro é só de **exibição**: o resultado apurado traz sempre os dois quadros."""
    escolhidos = QUADROS[quadro]
    por_id = {linha.id: linha for linha in resultado.mapa.linhas
              if linha.quadro in escolhidos}
    exercicio = resultado.procedencia.exercicio
    linhas = [f"{'':>4} {'':<48} {exercicio:>22} {exercicio - 1:>22}", ""]
    for rule_id, celulas in resultado.matriz.items():
        linha = por_id.get(rule_id)
        if linha is None:
            continue
        valores = "  ".join(
            "não apurada".rjust(20) if valor is None else _br(valor)
            for valor in celulas.values()
        )
        linhas.append(f"{linha.codigo:>4} {linha.rotulo[:48]:<48} {valores}")

    p, d = resultado.procedencia, resultado.diagnostico
    if d.conferencia_anexo:
        linhas += ["", f"Conferência   anexo L14 {_br(d.conferencia_anexo['anexo_l14_saldo'])} × "
                   f"principal L1 {_br(d.conferencia_anexo['principal_l1'])} · "
                   f"diferença {_br(d.conferencia_anexo['diferenca'])}"]
    linhas += [
        "",
        f"Procedência   {p.documento} {p.edicao} · exercício {p.exercicio} "
        f"competência {p.competencia:02d} · matriz {p.matriz}/{p.tipo_saldo} · "
        f"classes {','.join(str(c) for c in p.classes)} · {p.regras_aplicadas} regras · "
        f"coluna anterior: {p.origem_exercicio_anterior} · versao_regras {p.versao_regras[:12]}…",
        f"Diagnóstico   {len(d.nao_apuradas)} célula(s) não apurada(s) · {d.duracao_ms} ms"
        + ("  · SEM DADOS DA FONTE" if d.sem_dados else "")
        + ("  · SEM DADOS DO EXERCÍCIO ANTERIOR" if d.sem_dados_exercicio_anterior else ""),
    ]
    linhas += [f"  ! {aviso}" for aviso in d.nao_apuradas]
    linhas += [f"  ~ policy declarada e não aplicada: {p_}" for p_ in d.policies_nao_aplicadas]
    return "\n".join(linhas)


def _json(resultado) -> str:
    """Mesma serialização da rota e do worker (`services/pipeline/resultado.py`).

    Cópia própria aqui faria a saída do terminal divergir da da API em silêncio — e é justamente
    no BF que ela divergiria mais, porque a procedência e o diagnóstico dele trazem campos que o
    BO não tem.
    """
    from app.services.pipeline.resultado import para_dados

    return json.dumps(para_dados(resultado), ensure_ascii=False, indent=2)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="app.cli.bf", description="Apura o BF (IPC 06)")
    parser.add_argument("ente", type=int, help="código IBGE do ente")
    parser.add_argument("exercicio", type=int)
    parser.add_argument("--competencia", type=int, default=12, choices=range(1, 13))
    parser.add_argument("--fonte", default="siconfi", choices=("siconfi", "publicsoft"))
    parser.add_argument("--token", default="", help="token da PublicSoft")
    parser.add_argument("--anterior", default="msce", choices=("msce", "manual"),
                        help="origem da coluna do exercício anterior")
    parser.add_argument("--anterior-arquivo", default="",
                        help="JSON {linha: valor} para --anterior manual")
    parser.add_argument("--quadro", default="todos",
                        choices=("principal", "anexo", "todos"),
                        help="qual quadro imprimir; o resultado apurado traz sempre os dois")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    resultado = apurar(
        args.ente, args.exercicio, _fonte(args.fonte, args.token),
        competencia=args.competencia,
        anterior=Anterior.MANUAL if args.anterior == "manual" else Anterior.MSCE,
        valores_anteriores=_valores_anteriores(args.anterior_arquivo),
    )
    print(_json(resultado) if args.json else _texto(resultado, args.quadro))
    return 0


if __name__ == "__main__":
    sys.exit(main())
