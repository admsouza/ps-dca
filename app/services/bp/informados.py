"""Validação dos valores informados da coluna anterior do BP — sem tocar na fonte de dados.

Espelha `bf/informados.py`: a rota recusa o manual inválido **antes** de enfileirar o job, e o
fecho de `app/routes/` não pode alcançar `app.infra.msc`.

Chaves: `P:<codigo>` (QUADRO_PRINCIPAL), `FP:<codigo>` (ATIVOS_PASSIVOS_FINANCEIROS),
`C:<codigo>` (CONTAS_COMPENSACAO) e `S:<fonte de 4 dígitos>` (SUPERAVIT_DEFICIT). Os códigos `L<n>`
se repetem entre os quadros, por isso o prefixo.
"""
from __future__ import annotations

import re
from decimal import Decimal

from app.domain.bo.modelo import MapaBO
from app.infra.regras.carregador import carregar_em_cache
from app.services.bf.informados import decimal_informado
from app.services.bp.fontes import fonte_oficial

QUADROS = {"P": "QUADRO_PRINCIPAL", "FP": "ATIVOS_PASSIVOS_FINANCEIROS",
           "C": "CONTAS_COMPENSACAO"}
PREFIXO_FONTE = "S"
_FONTE = re.compile(r"\d{4}")


def partir(valores: dict[str, str]) -> tuple[dict[tuple[str, str], Decimal], dict[str, Decimal]]:
    """`{(quadro, codigo): valor}` das folhas e `{fonte: valor}` do Superávit.

    Recusa prefixo desconhecido, fonte que não tem 4 dígitos e valor não decimal.
    """
    folhas: dict[tuple[str, str], Decimal] = {}
    fontes: dict[str, Decimal] = {}
    for chave, bruto in valores.items():
        prefixo, _, codigo = chave.partition(":")
        valor = decimal_informado(chave, bruto)
        if prefixo == PREFIXO_FONTE:
            if not _FONTE.fullmatch(codigo):
                raise ValueError(f"fonte de {chave} deve ter 4 dígitos")
            if not fonte_oficial(codigo):
                raise ValueError(f"fonte de {chave} não existe no catálogo oficial")
            fontes[codigo] = valor
        elif prefixo in QUADROS and codigo:
            folhas[(QUADROS[prefixo], codigo)] = valor
        else:
            raise ValueError(f"prefixo desconhecido em {chave}: use P:, FP:, C: ou S:")
    return folhas, fontes


def validar_valores_anteriores(exercicio: int, valores: dict[str, str]) -> None:
    """Código inexistente e linha totalizadora são recusados, junto com o que `partir` recusa."""
    folhas, _ = partir(valores)
    mapa = mapa_bp(exercicio)
    por_chave = {(linha.quadro, linha.codigo): linha for linha in mapa.linhas}
    for quadro, codigo in folhas:
        linha = por_chave.get((quadro, codigo))
        if linha is None:
            raise ValueError(f"linha {codigo} não existe em {quadro}")
        if linha.referencias:
            raise ValueError(f"linha {codigo} de {quadro} é totalizadora: informe as folhas")


def mapa_bp(exercicio: int) -> MapaBO:
    return carregar_em_cache(exercicio, demonstrativo="bp")
