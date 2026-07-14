import sqlite3


def listar_albuns(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    sql = """
        SELECT a.id_album, a.name AS titulo, a.id_file_image,
               COUNT(am.id_music) AS total_musicas
        FROM albums a
        LEFT JOIN albums_musics am ON am.id_album = a.id_album
        GROUP BY a.id_album
        ORDER BY a.name
    """
    return conn.execute(sql).fetchall()


def musicas_do_album(conn: sqlite3.Connection, id_album: int) -> list[sqlite3.Row]:
    sql = """
        SELECT m.id_music, m.name AS titulo, am.track AS numero,
               m.id_file_music, m.id_file_instrumental_music
        FROM albums_musics am
        JOIN musics m ON m.id_music = am.id_music
        WHERE am.id_album = ?
        ORDER BY am.track, m.name
    """
    return conn.execute(sql, (id_album,)).fetchall()
