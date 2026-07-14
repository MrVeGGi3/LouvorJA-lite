import sqlite3

COR_LETRA = "#ffffff"
# O LouvorJA usa este dourado para o título, para o texto auxiliar e para marcar repetição
# (default de 'Cor Titulo'/'Cor Texto Repetido' em fmMenu.pas:9003).
COR_DESTAQUE = "#efb400"
COR_FUNDO = "#000000"

# Tamanhos em % da altura da tela, como no original (fmMenu.pas:9008 e 9527).
TAMANHO_TITULO = 18
TAMANHO_LETRA = 14
TAMANHO_LETRA_AUX = 10

_SQL_MUSICA = """
    SELECT m.id_music, m.name, m.id_file_image,
           (SELECT am.track
              FROM albums_musics am
              JOIN categories_albums ca ON ca.id_album = am.id_album
              JOIN categories c ON c.id_category = ca.id_category
             WHERE am.id_music = m.id_music AND c.type = 'hymnal'
             LIMIT 1) AS numero
    FROM musics m
    WHERE m.id_music = ?
"""

# `show_slide = 0` marca linhas que existem para a letra impressa mas não devem virar slide.
_SQL_SLIDES = """
    SELECT l."order" AS ordem,
           l.lyric AS letra,
           l.aux_lyric AS letra_aux,
           l."time" AS tempo,
           l.instrumental_time AS tempo_instrumental,
           f.id_file AS imagem_id
    FROM lyrics l
    JOIN musics m ON m.id_music = l.id_music
    LEFT JOIN files f ON f.id_file = COALESCE(l.id_file_image, m.id_file_image)
    WHERE l.id_music = ? AND l.show_slide = 1
    ORDER BY l."order"
"""


def _titulo(musica: sqlite3.Row) -> str:
    if musica["numero"]:
        return f"{musica['numero']} - {musica['name']}"
    return musica["name"] or ""


def _slide_capa(musica: sqlite3.Row) -> dict:
    """Slide de título, que o LouvorJA mostra antes da letra (o TIPO='CAPA' do esquema legado).

    Fica no tempo 0, então enquanto a introdução da música toca é ele que aparece.
    """
    return {
        "tipo": "capa",
        "ordem": 0,
        "letra": _titulo(musica),
        "letra_aux": None,
        "imagem_id": musica["id_file_image"],
        "tempo": "00:00:00",
        "tempo_instrumental": "00:00:00",
        "cor_letra": COR_DESTAQUE,
        "cor_letra_aux": COR_DESTAQUE,
        "cor_fundo": COR_FUNDO,
        "tamanho_letra": TAMANHO_TITULO,
        "tamanho_letra_aux": TAMANHO_LETRA_AUX,
    }


def _cores_das_letras(rows: list[sqlite3.Row]) -> list[str]:
    """Pinta de dourado o verso que repete o anterior — é como o original marca a repetição.

    Numa sequência de três slides iguais, o terceiro volta ao branco: o alternador existe para
    que o operador enxergue a virada entre um slide e o seguinte, não para colorir o refrão
    inteiro (fmMenu.pas:13757).
    """
    cores: list[str] = []
    anterior = ""
    destacado = False

    for row in rows:
        atual = (row["letra"] or "").strip().upper()
        if anterior and atual == anterior and not destacado:
            cores.append(COR_DESTAQUE)
            destacado = True
        else:
            cores.append(COR_LETRA)
            destacado = False
        anterior = atual

    return cores


def get_slides(conn: sqlite3.Connection, id_music: int) -> list[dict]:
    musica = conn.execute(_SQL_MUSICA, (id_music,)).fetchone()
    if musica is None:
        return []

    rows = conn.execute(_SQL_SLIDES, (id_music,)).fetchall()
    if not rows:
        return []

    cores = _cores_das_letras(rows)

    slides = [_slide_capa(musica)]
    for ordem, (row, cor) in enumerate(zip(rows, cores), start=1):
        slides.append(
            {
                "tipo": "letra",
                "ordem": ordem,
                "letra": row["letra"] or "",
                "letra_aux": row["letra_aux"] or None,
                "imagem_id": row["imagem_id"],
                "tempo": row["tempo"],
                "tempo_instrumental": row["tempo_instrumental"],
                "cor_letra": cor,
                "cor_letra_aux": COR_DESTAQUE,
                "cor_fundo": COR_FUNDO,
                "tamanho_letra": TAMANHO_LETRA,
                "tamanho_letra_aux": TAMANHO_LETRA_AUX,
            }
        )
    return slides
