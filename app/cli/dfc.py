"""Apura a DFC (IPC 08) e imprime os quatro quadros.

    python -m app.cli.dfc <cod_ibge> <exercicio> [--fonte siconfi|publicsoft] [--token ...]
                          [--informado L16=12345.67] [--json]

Mesmo papel dos CLIs do BO, BF, BP e DVP: a DFC verificável sem rota, sem banco e sem container.
"""
from __future__ import annotations

import argparse
import sys

from app.cli.bf import _br, _fonte, _json
from app.services.dfc.quadro_principal import apurar
from app.services.pipeline.resultado import template


def _texto(resultado) -> str:
    exercicio = resultado.procedencia.exercicio
    linhas = [f"{'':>4} {'':<48} {exercicio:>20}  {exercicio - 1:>20}"]
    quadro = grupo = None
    for linha in template(resultado.mapa):
        if linha["quadro"] != quadro:
            quadro = linha["quadro"]
            linhas += ["", f"== {quadro}"]
        if linha["grupo"] != grupo:
            grupo = linha["grupo"]
            if grupo:
                linhas += ["", grupo]
        valores = "  ".join("não apurada".rjust(20) if v is None else _br(v)
                            for v in resultado.matriz[linha["rule_id"]].values())
        linhas.append(f"{linha['codigo']:>4} {linha['rotulo'][:48]:<48} {valores}")

    p, d = resultado.procedencia, resultado.diagnostico
    linhas += [
        "",
        f"Procedência   {p.documento} {p.edicao} · exercício {p.exercicio} · "
        f"{p.regras_aplicadas} regras · versao_regras {p.versao_regras[:12]}…",
        f"Informáveis   {', '.join(d.informaveis)} (item 17 — o ente preenche)",
        f"Diagnóstico   {len(d.nao_apuradas)} célula(s) não apurada(s) · {d.duracao_ms} ms"
        + ("  · SEM DADOS DA FONTE" if d.sem_dados else "")
        + ("  · SEM CAIXA DO EXERCÍCIO ANTERIOR" if d.sem_dados_exercicio_anterior else ""),
    ]
    linhas += [f"  ! {aviso}" for aviso in d.nao_apuradas]
    return "\n".join(linhas)


def _informados(pares: list[str]) -> dict[str, str]:
    """`L16=12345.67` → `{"L16": "12345.67"}`."""
    valores = {}
    for par in pares:
        codigo, _, valor = par.partition("=")
        if not valor:
            raise SystemExit(f"--informado espera CODIGO=VALOR, recebi {par!r}")
        valores[codigo.strip().upper()] = valor.strip()
    return valores


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="app.cli.dfc", description="Apura a DFC (IPC 08)")
    parser.add_argument("ente", type=int, help="código IBGE do ente")
    parser.add_argument("exercicio", type=int)
    parser.add_argument("--fonte", default="siconfi", choices=("siconfi", "publicsoft"))
    parser.add_argument("--token", default="", help="token da PublicSoft")
    parser.add_argument("--informado", action="append", default=[], metavar="CODIGO=VALOR",
                        help="linha do item 17 preenchida pelo ente (L16, L21, L30)")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    resultado = apurar(args.ente, args.exercicio, _fonte(args.fonte, args.token),
                       valores_informados=_informados(args.informado))
    print(_json(resultado) if args.json else _texto(resultado))
    return 0


if __name__ == "__main__":
    sys.exit(main())
