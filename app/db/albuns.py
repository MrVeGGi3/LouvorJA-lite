import sqlite3


def listar_albuns(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute("SELECT * FROM ALBUM ORDER BY NOME").fetchall()


def musicas_do_album(conn: sqlite3.Connection, album_id: int) -> list[sqlite3.Row]:
    sql = """
        SELECT M.*, AM.FAIXA AS FAIXA_ALBUM
        FROM MUSICAS M
        JOIN ALBUM_MUSICAS AM ON AM.ID_MUSICA = M.ID
        WHERE AM.ID_ALBUM = ?
        ORDER BY AM.FAIXA
    """
    return conn.execute(sql, (album_id,)).fetchall()
