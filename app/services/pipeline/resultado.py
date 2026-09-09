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


def _posicao(linha) -> tuple[int, int, int]:
    """Quadro, grupo e ordem — quadro ou grupo desconhecido vai para o fim, sem quebrar."""
    quadro = (ORDEM_QUADROS.index(linha.quadro) if linha.quadro in ORDEM_QUADROS
              else len(ORDEM_QUADROS))
    grupo = (ORDEM_GRUPOS.index(linha.grupo) if linha.grupo in ORDEM_GRUPOS
             else len(ORDEM_GRUPOS))
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
        for linha in sorted(mapa.linhas, key=_posicao)
    ]


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
        },
        "diagnostico": {
            # Declarado sempre, vazio inclusive: consumidor que não encontra a chave não sabe se a
            # apuração fechou ou se a versão do produtor não a produzia.
            "nao_apuradas": [str(a) for a in diagnostico.nao_apuradas],
            "residuos": [str(r) for r in diagnostico.residuos],
            "duracao_ms": diagnostico.duracao_ms,
            "sem_dados": diagnostico.sem_dados,
        },
    }
