import sqlite3
from collections.abc import Iterator

from fastapi import HTTPException

from app.config import DB_PATH
from app.db.text_utils import normaliza_semac


def get_connection() -> sqlite3.Connection:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"database.db não encontrado em {DB_PATH}.")
    uri = f"file:{DB_PATH}?mode=ro&immutable=1"
    conn = sqlite3.connect(uri, uri=True, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    # O esquema não tem coluna sem acento (a antiga NOME_SEMAC não existe mais), então a
    # normalização vai para dentro do SQL. Depois de remover os acentos sobra ASCII, e o LIKE
    # do SQLite já é case-insensitive para ASCII.
    conn.create_function("semac", 1, normaliza_semac, deterministic=True)
    return conn


def get_db() -> Iterator[sqlite3.Connection]:
    """Conexão por requisição. Sem banco em disco não é erro de servidor — é o estado normal de
    quem abriu o app pela primeira vez, e a tela reage a esse código abrindo o download."""
    if not DB_PATH.exists():
        raise HTTPException(
            status_code=503,
            detail={
                "codigo": "sem_banco",
                "mensagem": "O catálogo de hinos ainda não foi baixado.",
            },
        )

    conn = get_connection()
    try:
        yield conn
    finally:
        conn.close()
