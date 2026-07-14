import sqlite3

from app.db.text_utils import normaliza_semac

# O hinário não é mais uma tabela: é uma categoria (`type='hymnal'`) que aponta para um álbum,
# e o número do hino é a faixa dentro dele.
SLUG_POR_EDICAO = {
    "atual": "hymnal",
    "1996": "hymnal_1996",
}

_SELECT = """
    SELECT m.id_music, m.name AS titulo, am.track AS numero,
           a.id_album, a.name AS album,
           m.id_file_music, m.id_file_instrumental_music
    FROM categories c
    JOIN categories_albums ca ON ca.id_category = c.id_category
    JOIN albums a ON a.id_album = ca.id_album
    JOIN albums_musics am ON am.id_album = a.id_album
    JOIN musics m ON m.id_music = am.id_music
    WHERE c.slug = ?
"""


def _slug(edicao: str) -> str:
    return SLUG_POR_EDICAO.get(edicao, SLUG_POR_EDICAO["atual"])


def listar_hinario(conn: sqlite3.Connection, edicao: str = "atual") -> list[sqlite3.Row]:
    return conn.execute(_SELECT + " ORDER BY am.track, m.name", (_slug(edicao),)).fetchall()


def buscar_hinario(
    conn: sqlite3.Connection, valor: str, edicao: str = "atual"
) -> list[sqlite3.Row]:
    valor = (valor or "").strip()
    if not valor:
        return listar_hinario(conn, edicao)

    if valor.isdigit():
        # O número não é único: no Hinário Adventista a faixa 587 tem duas variantes.
        sql = _SELECT + " AND am.track = ? ORDER BY m.name"
        params = (_slug(edicao), int(valor))
    else:
        sql = _SELECT + " AND semac(m.name) LIKE ? ORDER BY am.track, m.name"
        params = (_slug(edicao), f"%{normaliza_semac(valor)}%")

    return conn.execute(sql, params).fetchall()
