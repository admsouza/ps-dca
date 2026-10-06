"""A versão da API é o hash do código que produz a célula."""
from __future__ import annotations

from pathlib import Path

from app.services.pipeline.apuracao import VERSAO_API, versao_do_codigo


def _escrever(raiz: Path, relativo: str, texto: str) -> None:
    destino = raiz / relativo
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_bytes(texto.encode())


def test_quebra_de_linha_nao_muda_o_hash(tmp_path: Path):
    lf = tmp_path / "lf"
    crlf = tmp_path / "crlf"
    _escrever(lf, "domain/bo/matriz.py", "def apurar():\n    return 1\n")
    _escrever(crlf, "domain/bo/matriz.py", "def apurar():\r\n    return 1\r\n")

    assert versao_do_codigo(lf, [lf / "domain" / "bo"]) == versao_do_codigo(
        crlf, [crlf / "domain" / "bo"]
    )


def test_codigo_diferente_muda_o_hash(tmp_path: Path):
    base = tmp_path / "a"
    outro = tmp_path / "b"
    _escrever(base, "services/bf/quadro_principal.py", "def apurar():\n    return 1\n")
    _escrever(outro, "services/bf/quadro_principal.py", "def apurar():\n    return 2\n")
    pasta = "services/bf"

    assert versao_do_codigo(base, [base / pasta]) != versao_do_codigo(outro, [outro / pasta])


def test_arquivo_novo_muda_o_hash(tmp_path: Path):
    raiz = tmp_path / "app"
    pasta = raiz / "infra" / "msc"
    _escrever(raiz, "infra/msc/publicsoft.py", "def estorno():\n    return 1\n")
    antes = versao_do_codigo(raiz, [pasta])
    _escrever(raiz, "infra/msc/extra.py", "def outro():\n    return 0\n")

    assert versao_do_codigo(raiz, [pasta]) != antes


def test_versao_da_aplicacao_e_o_hash_do_codigo_real():
    assert len(VERSAO_API) == 64
    assert all(c in "0123456789abcdef" for c in VERSAO_API)


# Alcançados pela apuração, mas sem efeito no valor da célula.
_FORA_DO_HASH_DE_PROPOSITO = {
    "app/core/config.py",          # leitura de env
    "app/core/database.py",        # engine/sessão
    "app/infra/cache/modelo.py",   # ORM do cache; vigências importam só a constante de origens
    "app/infra/fila/chaves.py",    # nome de chave Redis da MSC
}


def _alcancados_pela_apuracao() -> set[str]:
    """Arquivos `app/**` importados, direta ou transitivamente, pelos serviços do registry."""
    import ast

    from app.services.pipeline.registry import REGISTRY

    raiz = Path(__file__).resolve().parents[2]

    def arquivo_de(modulo: str) -> Path | None:
        base = raiz / Path(*modulo.split("."))
        for candidato in (base.with_suffix(".py"), base / "__init__.py"):
            if candidato.is_file():
                return candidato
        return None

    pendentes = [a.servico.split(":")[0] for a in REGISTRY if a.servico]
    pendentes.append("app.services.pipeline.apuracao")  # fonte e mapa vigente
    vistos: set[str] = set()
    while pendentes:
        arquivo = arquivo_de(pendentes.pop())
        if arquivo is None:
            continue
        relativo = arquivo.relative_to(raiz).as_posix()
        if relativo in vistos:
            continue
        vistos.add(relativo)
        for no in ast.walk(ast.parse(arquivo.read_text(encoding="utf-8"))):
            if isinstance(no, ast.ImportFrom) and no.module and no.module.startswith("app."):
                pendentes.append(no.module)
                # `from pacote import modulo` — nome que não é arquivo é descartado adiante.
                pendentes.extend(f"{no.module}.{n.name}" for n in no.names)
            elif isinstance(no, ast.Import):
                pendentes.extend(n.name for n in no.names if n.name.startswith("app."))
    return {v for v in vistos if not v.endswith("__init__.py")}


def test_todo_codigo_alcancado_pela_apuracao_entra_no_hash():
    """Requisito: `versao_api` invalida o cache quando o código da apuração muda.

    Módulo novo importado pela apuração e fora do hash = cache servindo número velho.
    """
    from app.services.pipeline.apuracao import _CODIGO_DA_APURACAO, _RAIZ_APP

    raiz = _RAIZ_APP.parent
    pastas = [p.relative_to(raiz).as_posix() + "/" for p in _CODIGO_DA_APURACAO]
    fora = {
        arquivo for arquivo in _alcancados_pela_apuracao()
        if not arquivo.startswith(tuple(pastas)) and arquivo not in _FORA_DO_HASH_DE_PROPOSITO
    }
    assert not fora, f"entram na apuração e não no hash de VERSAO_API: {sorted(fora)}"
