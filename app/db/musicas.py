import sqlite3

from app.db.introspect import has_table
from app.db.text_utils import normaliza_semac

TIPOS_PADRAO = ("HASD", "JA", "CD")


def buscar_musicas(
    conn: sqlite3.Connection, valor: str, tipos: tuple[str, ...] = TIPOS_PADRAO
) -> list[sqlite3.Row]:
    if not has_table("LISTA_MUSICAS_TODAS"):
        return []
    like = f"%{normaliza_semac(valor)}%"
    tipos_csv = ",".join(tipos)
    sql = """
        SELECT * FROM LISTA_MUSICAS_TODAS
        WHERE (',' || ? || ',') LIKE ('%,' || TIPO || ',%')
          AND (NOME_SEMAC LIKE ? OR NOME_ALBUM_COM_SEMAC LIKE ?)
        ORDER BY NOME
    """
    return conn.execute(sql, (tipos_csv, like, like)).fetchall()


def obter_musica(conn: sqlite3.Connection, musica_id: int) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM MUSICAS WHERE ID = ?", (musica_id,)).fetchone()
