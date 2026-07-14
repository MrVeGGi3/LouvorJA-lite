import sqlite3

DEFAULT_COR_LETRA = "#ffffff"
DEFAULT_COR_FUNDO = "#000000"

# `show_slide = 0` marca linhas que existem para a letra impressa mas não devem virar slide.
# Sem esse filtro entram milhares de slides fantasma na projeção.
_SQL_SLIDES = """
    SELECT l."order" AS ordem,
           l.lyric AS letra,
           l.aux_lyric AS letra_aux,
           l."time" AS tempo,
           l.instrumental_time AS tempo_instrumental,
           f.id_file AS imagem_id,
           f.file_name AS imagem_arquivo
    FROM lyrics l
    JOIN musics m ON m.id_music = l.id_music
    LEFT JOIN files f ON f.id_file = COALESCE(l.id_file_image, m.id_file_image)
    WHERE l.id_music = ? AND l.show_slide = 1
    ORDER BY l."order"
"""


def _normaliza(row: sqlite3.Row) -> dict:
    return {
        "ordem": row["ordem"],
        "letra": row["letra"] or "",
        "letra_aux": row["letra_aux"] or None,
        "imagem_id": row["imagem_id"],
        "imagem_arquivo": row["imagem_arquivo"],
        "tempo": row["tempo"],
        "tempo_instrumental": row["tempo_instrumental"],
        # O esquema novo não guarda cor nem tamanho de letra — a projeção usa os defaults.
        "cor_letra": DEFAULT_COR_LETRA,
        "cor_letra_aux": None,
        "cor_fundo": DEFAULT_COR_FUNDO,
        "fundo_letra": False,
    }


def get_slides(conn: sqlite3.Connection, id_music: int) -> list[dict]:
    rows = conn.execute(_SQL_SLIDES, (id_music,)).fetchall()
    return [_normaliza(r) for r in rows]
