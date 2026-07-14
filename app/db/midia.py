import sqlite3

_SQL_ARQUIVO = "SELECT id_file, type, dir, file_name, size, duration FROM files WHERE id_file = ?"

_SQL_AUDIO_DA_MUSICA = """
    SELECT m.id_file_music, m.id_file_instrumental_music,
           cantado.duration AS duracao_cantado,
           playback.duration AS duracao_playback
    FROM musics m
    LEFT JOIN files cantado ON cantado.id_file = m.id_file_music
    LEFT JOIN files playback ON playback.id_file = m.id_file_instrumental_music
    WHERE m.id_music = ?
"""


def obter_arquivo(conn: sqlite3.Connection, id_file: int) -> sqlite3.Row | None:
    return conn.execute(_SQL_ARQUIVO, (id_file,)).fetchone()


def audio_da_musica(conn: sqlite3.Connection, id_music: int) -> sqlite3.Row | None:
    return conn.execute(_SQL_AUDIO_DA_MUSICA, (id_music,)).fetchone()
