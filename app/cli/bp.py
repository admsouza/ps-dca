"""Apura o Balanço Patrimonial e imprime a matriz.

    python -m app.cli.bp <cod_ibge> <exercicio> [--fonte siconfi|publicsoft] [--token ...] [--json]

Mesmo papel dos CLIs do BO e do BF: o BP verificável sem rota, sem banco e sem container.
"""
from __future__ import annotations

import argparse
import sys

from app.cli.bf import _br, _fonte, _json
from app.services.bp.quadro_principal import apurar
from app.services.pipeline.resultado import template


def _texto(resultado) -> str:
    exercicio = resultado.procedencia.exercicio
    linhas = [f"{'':>4} {'':<48} {exercicio:>20}  {exercicio - 1:>20}"]
    quadro = None
    for linha in template(resultado.mapa):
        if linha["quadro"] != quadro:
            quadro = linha["quadro"]
            linhas += ["", quadro]
        valores = "  ".join("não apurada".rjust(20) if v is None else _br(v)
                            for v in resultado.matriz[linha["rule_id"]].values())
        linhas.append(f"{linha['codigo']:>4} {linha['rotulo'][:48]:<48} {valores}")

    p, d = resultado.procedencia, resultado.diagnostico
    equilibrio = " · ".join(f"{coluna} {_br(valor).strip()}"
                            for coluna, valor in d.equilibrio.items())
    linhas += [
        "",
        f"Procedência   {p.documento} {p.edicao} · exercício {p.exercicio} · "
        f"matriz {p.matriz}/{p.tipo_saldo} · classes {','.join(map(str, p.classes))} · "
        f"versao_regras {p.versao_regras[:12]}…",
        f"Equilíbrio    L1 − L15: {equilibrio or 'não apurado'}",
        f"Diagnóstico   {len(d.nao_apuradas)} célula(s) não apurada(s) · {d.duracao_ms} ms"
        + ("  · SEM DADOS DA FONTE" if d.sem_dados else "")
        + ("  · SEM DADOS DO EXERCÍCIO ANTERIOR" if d.sem_dados_exercicio_anterior else "")
        + ("  · SEM ATRIBUTO F/P NA MSC" if d.sem_atributo_fp else ""),
    ]
    linhas += [f"  ~ resíduo {r}" for r in d.residuos]
    linhas += [f"  ~ policy declarada e não aplicada: {p_}" for p_ in d.policies_nao_aplicadas]
    return "\n".join(linhas)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="app.cli.bp", description="Apura o BP (IPC 04)")
    parser.add_argument("ente", type=int, help="código IBGE do ente")
    parser.add_argument("exercicio", type=int)
    parser.add_argument("--fonte", default="siconfi", choices=("siconfi", "publicsoft"))
    parser.add_argument("--token", default="", help="token da PublicSoft")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    resultado = apurar(args.ente, args.exercicio, _fonte(args.fonte, args.token))
    print(_json(resultado) if args.json else _texto(resultado))
    return 0


if __name__ == "__main__":
    sys.exit(main())
