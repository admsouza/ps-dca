"""Direção do saldo por conta folha, lida do PCASP oficial.

Implementa a porta `DirecaoSaldo`. A tabela `docs/contas-stn/PCASP.md` traz a coluna
`NATUREZA DO SALDO` para cada uma das 6.119 contas — a direção é **dado**, não heurística.

Medido no próprio arquivo: a classe 5 tem 54 contas devedoras e 22 credoras; a classe 6 tem 56
credoras e 7 devedoras. Inferir por classe erra 29 contas; por prefixo do IPC, erra as 5
dedutoras de `6.2.1.3`.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

RAIZ_REPO = Path(__file__).resolve().parents[3]
TABELA = RAIZ_REPO / "docs" / "contas-stn" / "PCASP.md"

COLUNA_CONTA = 7
COLUNA_NATUREZA = 10


class DirecaoPCASP:
    """Consulta a natureza do saldo por conta folha de 9 dígitos."""

    def __init__(self, por_conta: dict[str, bool], redutoras: frozenset[str] = frozenset()):
        self._por_conta = por_conta
        self._redutoras = redutoras

    def credora(self, conta: str) -> bool | None:
        return self._por_conta.get(_digitos(conta))

    def credora_prefixo(self, prefixo: str) -> bool | None:
        """Direção predominante das contas sob um prefixo — a direção do grupo.

        Dentro de um grupo, a conta redutora tem natureza **oposta** e título com `(-)`:
        `522190109 (-) REDUÇÃO` é credora entre devedoras; `621310100 (-) FUNDEB` é devedora
        entre credoras. Predominância dá a direção do grupo, e a redutora entra subtraindo por
        consequência — que é como o STN compõe as colunas.
        """
        alvo = _digitos(prefixo)
        if not alvo:
            return None
        direta = self._por_conta.get(alvo)
        if direta is not None and len(alvo) == 9:
            return direta

        sob = sorted(c for c in self._por_conta if c.startswith(alvo))
        if not sob:
            return None
        # A direção do grupo é a das contas **principais**: as redutoras (`(-)` no título) têm
        # natureza oposta de propósito. Contar por maioria erraria em `5.2.1.1`, onde há mais
        # contas de dedução do que de previsão.
        principais = [c for c in sob if c not in self._redutoras]
        return self._por_conta[(principais or sob)[0]]

    def __len__(self) -> int:
        return len(self._por_conta)


def _digitos(valor: str) -> str:
    return "".join(c for c in valor if c.isdigit())


@lru_cache(maxsize=4)
def do_pcasp(tabela: Path | None = None) -> DirecaoPCASP:
    """Carrega a tabela uma vez por processo — são 6 mil linhas lidas a cada apuração."""
    caminho = tabela or TABELA
    por_conta: dict[str, bool] = {}
    redutoras: set[str] = set()

    with caminho.open(encoding="utf-8") as fh:
        for linha in fh:
            if not linha.startswith("|"):
                continue
            celulas = [c.strip() for c in linha.strip().strip("|").split("|")]
            if len(celulas) <= COLUNA_NATUREZA or set(celulas[0]) <= {"-"}:
                continue
            conta = _digitos(celulas[COLUNA_CONTA])
            natureza = celulas[COLUNA_NATUREZA].strip().lower()
            if not conta or natureza not in ("credora", "devedora"):
                continue
            por_conta[conta] = natureza == "credora"
            if celulas[COLUNA_CONTA + 1].strip().startswith("(-)"):
                redutoras.add(conta)

    return DirecaoPCASP(por_conta, frozenset(redutoras))
