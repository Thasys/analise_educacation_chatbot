"""Dependency injection da conexao DuckDB.

A API mantem uma conexao raiz read-only criada no lifespan da aplicacao.
Cada request recebe um cursor independente via `cursor()`, permitindo
queries concorrentes sem conflito de transacao.
"""

from __future__ import annotations

import duckdb
from fastapi import HTTPException, Request


def get_duckdb_conn(request: Request) -> duckdb.DuckDBPyConnection:
    """Retorna um cursor isolado da conexao DuckDB do app.

    Uso:
        @router.get(...)
        def endpoint(conn: Annotated[..., Depends(get_duckdb_conn)]):
            return conn.execute("SELECT ...").fetchall()

    O cursor e fechado quando a request termina (garbage collection
    do FastAPI; nao precisa try/finally explicito).
    """
    root = getattr(request.app.state, "duckdb_conn", None)
    if root is None:
        raise HTTPException(
            status_code=503,
            detail=(
                "DuckDB nao disponivel. Verifique se `dbt build` foi executado "
                "e o arquivo data/duckdb/education.duckdb existe."
            ),
        )
    return root.cursor()
