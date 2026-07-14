import sqlite3

from app.db.text_utils import normaliza_semac

_SELECT = """
    SELECT m.id_music, m.name AS titulo, am.track AS numero,
           a.id_album, a.name AS album,
           m.id_file_music, m.id_file_instrumental_music
    FROM musics m
    LEFT JOIN albums_musics am ON am.id_music = m.id_music
    LEFT JOIN albums a ON a.id_album = am.id_album
"""


def buscar_musicas(conn: sqlite3.Connection, valor: str) -> list[sqlite3.Row]:
    valor = (valor or "").strip()
    if not valor:
        return []
    like = f"%{normaliza_semac(valor)}%"
    sql = _SELECT + """
        WHERE semac(m.name) LIKE ? OR semac(COALESCE(a.name, '')) LIKE ?
        GROUP BY m.id_music
        ORDER BY m.name
    """
    return conn.execute(sql, (like, like)).fetchall()


def obter_musica(conn: sqlite3.Connection, id_music: int) -> sqlite3.Row | None:
    return conn.execute(_SELECT + " WHERE m.id_music = ? LIMIT 1", (id_music,)).fetchone()
