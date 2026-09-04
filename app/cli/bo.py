"""Apura o quadro principal do BO e imprime a matriz.

    python -m app.cli.bo <cod_ibge> <exercicio> [--fonte siconfi|publicsoft] [--json]

É o que torna a F1 verificável sem rota, sem banco e sem container: a mesma função que o worker
vai chamar na F3, chamada aqui direto.
"""
from __future__ import annotations

import argparse
import json
import sys
from decimal import Decimal

from app.services.bo.quadro_principal import apurar


def _fonte(nome: str, token: str):
    if nome == "publicsoft":
        from app.infra.msc.publicsoft import PublicSoftMSC

        return PublicSoftMSC(token=token)
    from app.infra.msc.siconfi import SiconfiMSC

    return SiconfiMSC()


def _texto(resultado) -> str:
    linhas = []
    for rule_id, celulas in resultado.matriz.items():
        if not celulas:
            linhas.append(f"{rule_id:44} (linha sem coluna de valor)")
            continue
        for coluna, valor in celulas.items():
            mostrado = "não apurada" if valor is None else f"{valor:>20,.2f}"
            linhas.append(f"{rule_id:44} {coluna:24} {mostrado}")

    p = resultado.procedencia
    d = resultado.diagnostico
    linhas += [
        "",
        f"Procedência   {p.documento} {p.edicao} · exercício {p.exercicio} · "
        f"{p.regras_aplicadas} regras · versao_regras {p.versao_regras[:12]}…",
        f"Diagnóstico   {len(d.nao_apuradas)} célula(s) não apurada(s) · "
        f"{len(d.residuos)} resíduo(s) · {d.duracao_ms} ms"
        + ("  · SEM DADOS DA FONTE" if d.sem_dados else ""),
    ]
    for aviso in d.nao_apuradas:
        linhas.append(f"  ! {aviso}")
    for residuo in d.residuos:
        linhas.append(f"  ~ resíduo {residuo}")
    return "\n".join(linhas)


def _json(resultado) -> str:
    def serializar(valor):
        return str(valor) if isinstance(valor, Decimal) else valor

    return json.dumps(
        {
            "matriz": {
                rule_id: {c: serializar(v) for c, v in celulas.items()}
                for rule_id, celulas in resultado.matriz.items()
            },
            "procedencia": {
                "documento": resultado.procedencia.documento,
                "edicao": resultado.procedencia.edicao,
                "exercicio": resultado.procedencia.exercicio,
                "versao_regras": resultado.procedencia.versao_regras,
                "regras_aplicadas": resultado.procedencia.regras_aplicadas,
                "tabelas_stn": resultado.procedencia.tabelas_stn,
            },
            "diagnostico": {
                "nao_apuradas": [str(a) for a in resultado.diagnostico.nao_apuradas],
                "residuos": [str(r) for r in resultado.diagnostico.residuos],
                "duracao_ms": resultado.diagnostico.duracao_ms,
                "sem_dados": resultado.diagnostico.sem_dados,
            },
        },
        ensure_ascii=False,
        indent=2,
    )


def main(argv: list[str] | None = None) -> int:
    for fluxo in (sys.stdout, sys.stderr):
        if hasattr(fluxo, "reconfigure"):
            fluxo.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(prog="python -m app.cli.bo")
    parser.add_argument("ente", type=int, help="código IBGE de 7 dígitos")
    parser.add_argument("exercicio", type=int)
    parser.add_argument("--fonte", choices=("siconfi", "publicsoft"), default="siconfi")
    parser.add_argument("--token", default="", help="token do ente (PublicSoft)")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    resultado = apurar(
        ente=args.ente, exercicio=args.exercicio, fonte=_fonte(args.fonte, args.token)
    )
    print(_json(resultado) if args.json else _texto(resultado))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
