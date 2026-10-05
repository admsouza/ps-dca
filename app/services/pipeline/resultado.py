"""Serialização do resultado apurado — **uma** função, usada por rota, worker e CLI.

O resultado publica **valores e template**: `matriz` indexada por `rule_id` e `linhas` na ordem de
apresentação da norma. Sem `linhas`, quem renderiza declara os 69 rótulos, níveis e ordens por fora
e cria uma segunda fonte da verdade para a transcrição normativa.

Se o CLI tivesse a sua própria cópia, as duas saídas divergiriam em silêncio, e a divergência
apareceria como "o número do terminal não é o da tela".

`Decimal` vira **string**. Em `float`, `6.043.181.131,90` perde centavo, e o aceite do projeto é
1:1 em centavos contra o STN.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any


def _valor(v: Any) -> Any:
    return str(v) if isinstance(v, Decimal) else v


# Ordem de apresentação dos quadros, como o IPC 07 os publica: quadro principal (p. 8-11),
# b) Restos a Pagar Não Processados (p. 12), c) Restos a Pagar Processados (p. 13). A ordem
# alfabética e a de inserção das chaves são as duas a inversa entre os dois quadros de RP.
ORDEM_QUADROS = ("QUADRO_PRINCIPAL", "RP_NAO_PROCESSADOS", "RP_PROCESSADOS")

# Dentro do quadro principal, receitas antes de despesas; `ordem` é relativa ao grupo.
ORDEM_GRUPOS = ("RECEITAS", "DESPESAS")

# A ordem é do **documento normativo**, não do serializador: `RECEITAS`/`DESPESAS` é vocabulário do
# IPC 07 e `INGRESSOS`/`DISPENDIOS` do IPC 06. Documento desconhecido cai no padrão do IPC 07 e,
# dentro dele, quadro ou grupo desconhecido vai para o fim — sem quebrar a serialização.
ORDEM_POR_DOCUMENTO = {
    "IPC06": (("QUADRO_PRINCIPAL", "QUADRO_ANEXO"), ("INGRESSOS", "DISPENDIOS")),
}


def _posicao(linha, ordens=(ORDEM_QUADROS, ORDEM_GRUPOS)) -> tuple[int, int, int]:
    """Quadro, grupo e ordem — quadro ou grupo desconhecido vai para o fim, sem quebrar."""
    quadros, grupos = ordens
    quadro = quadros.index(linha.quadro) if linha.quadro in quadros else len(quadros)
    grupo = grupos.index(linha.grupo) if linha.grupo in grupos else len(grupos)
    return (quadro, grupo, linha.ordem)


def template(mapa) -> list[dict]:
    """O demonstrativo como estrutura de apresentação, na ordem da norma.

    `nivel` e `ordem` são os declarados na transcrição — **não** derivados da árvore de composição,
    que dá resultado diferente (`Reserva do RPPS` é nível 2 na norma, e a composição sugeriria 1).
    `totalizadora` é publicada porque é o que decide o destaque visual: quem renderiza não deve
    reimplementar a regra de "esta linha soma outras".
    """
    if mapa is None:
        return []
    return [
        {
            "rule_id": linha.id,
            "codigo": linha.codigo,
            "rotulo": linha.rotulo,
            "quadro": linha.quadro,
            "grupo": linha.grupo,
            "nivel": linha.nivel,
            "ordem": linha.ordem,
            "totalizadora": bool(linha.referencias),
        }
        for linha in sorted(mapa.linhas, key=lambda linha: _posicao(linha, _ordens(mapa)))
    ]


def _ordens(mapa) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Ordem de quadros e grupos do documento que produziu o mapa."""
    documento = getattr(getattr(mapa, "vigencia", None), "documento", "")
    return ORDEM_POR_DOCUMENTO.get(documento, (ORDEM_QUADROS, ORDEM_GRUPOS))


def _especificos(origem, campos: tuple[str, ...]) -> dict:
    """Campos que o demonstrativo publica e os demais não têm — omitidos quando ausentes."""
    saida = {}
    for campo in campos:
        valor = getattr(origem, campo, None)
        if valor is None:
            continue
        saida[campo] = list(valor) if isinstance(valor, tuple) else valor
    return saida


def para_dados(resultado) -> dict:
    """`Resultado` como dado puro, pronto para JSONB: valores, template e rastro."""
    procedencia = resultado.procedencia
    diagnostico = resultado.diagnostico
    return {
        "linhas": template(resultado.mapa),
        "matriz": {
            rule_id: {coluna: _valor(valor) for coluna, valor in celulas.items()}
            for rule_id, celulas in resultado.matriz.items()
        },
        "procedencia": {
            "documento": procedencia.documento,
            "edicao": procedencia.edicao,
            "exercicio": procedencia.exercicio,
            "versao_regras": procedencia.versao_regras,
            "regras_aplicadas": procedencia.regras_aplicadas,
            "tabelas_stn": dict(procedencia.tabelas_stn),
            "matriz": getattr(procedencia, "matriz", ""),
            "tipo_saldo": getattr(procedencia, "tipo_saldo", ""),
            "competencia": getattr(procedencia, "competencia", 12),
            "classes": list(getattr(procedencia, "classes", ())),
            # Campos que só alguns demonstrativos produzem. Publicados quando existem, em vez de
            # listados aqui um a um: o serializador não deve aprender o vocabulário de cada norma.
            **_especificos(procedencia, ("origens_por_linha", "origem_exercicio_anterior",
                                         "valores_anteriores", "estorno_receita_extra")),
        },
        "diagnostico": {
            # Declarado sempre, vazio inclusive: consumidor que não encontra a chave não sabe se a
            # apuração fechou ou se a versão do produtor não a produzia.
            "nao_apuradas": [str(a) for a in diagnostico.nao_apuradas],
            "residuos": [str(r) for r in diagnostico.residuos],
            "duracao_ms": diagnostico.duracao_ms,
            "sem_dados": diagnostico.sem_dados,
            **_especificos(diagnostico, ("sem_dados_exercicio_anterior",
                                         "policies_nao_aplicadas")),
        },
    }
