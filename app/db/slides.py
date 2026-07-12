import sqlite3

from app.db.colors import delphi_color_to_css
from app.db.introspect import has_table

DEFAULT_COR_LETRA = "#ffffff"
DEFAULT_COR_FUNDO = "#000000"
DEFAULT_TAMANHO_LETRA = 40


def _resolve_musica_id(conn: sqlite3.Connection, origem: str, ref_id: int) -> int | None:
    """Localiza o MUSICA_ID correspondente a um item de liturgia.

    Para origem='MUSICAS' o ref_id já É o ID. Para hinário, MUSICAS_SLIDE/MUSICAS_LETRA
    não compartilham espaço de ID com HINARIO_ADVENTISTA — o casamento é feito por
    NOME_COM. Essa heurística precisa ser revalidada contra um banco real (ver README).
    """
    if origem == "MUSICAS":
        return ref_id

    tabela = "HINARIO_ADVENTISTA" if origem == "HINARIO_ADVENTISTA" else "HINARIO_ADVENTISTA_1996"
    hino = conn.execute(f"SELECT NOME_COM FROM {tabela} WHERE ID = ?", (ref_id,)).fetchone()
    if hino is None:
        return None

    musica = conn.execute(
        "SELECT ID FROM MUSICAS WHERE NOME = ? LIMIT 1", (hino["NOME_COM"],)
    ).fetchone()
    return musica["ID"] if musica else None


def _col(row: sqlite3.Row, nome: str):
    return row[nome] if nome in row.keys() else None


def _normaliza_slide_novo(row: sqlite3.Row) -> dict:
    cor_letra_aux = _col(row, "COR_LETRA_AUX")
    return {
        "ordem": row["ORDEM"],
        "letra": row["LETRA"] or "",
        "letra_aux": _col(row, "LETRA_AUX"),
        "imagem": _col(row, "IMAGEM"),
        "cor_letra": delphi_color_to_css(_col(row, "COR_LETRA"), DEFAULT_COR_LETRA),
        "cor_letra_aux": delphi_color_to_css(cor_letra_aux, DEFAULT_COR_LETRA) if cor_letra_aux else None,
        "cor_fundo": delphi_color_to_css(_col(row, "COR_FUNDO"), DEFAULT_COR_FUNDO),
        "tamanho_letra": _col(row, "TAMANHO_LETRA") or DEFAULT_TAMANHO_LETRA,
        "fundo_letra": bool(_col(row, "FUNDO_LETRA")),
    }


def _normaliza_slide_legado(row: sqlite3.Row) -> dict:
    return {
        "ordem": row["ORDEM"],
        "letra": row["LETRA"] or "",
        "letra_aux": _col(row, "LETRA_AUX"),
        "imagem": _col(row, "IMAGEM"),
        "cor_letra": DEFAULT_COR_LETRA,
        "cor_letra_aux": None,
        "cor_fundo": DEFAULT_COR_FUNDO,
        "tamanho_letra": DEFAULT_TAMANHO_LETRA,
        "fundo_letra": False,
    }


def get_slides(conn: sqlite3.Connection, origem: str, ref_id: int) -> list[dict]:
    musica_id = _resolve_musica_id(conn, origem, ref_id)
    if musica_id is None:
        return []

    if has_table("MUSICAS_SLIDE"):
        rows = conn.execute(
            "SELECT * FROM MUSICAS_SLIDE WHERE MUSICA_ID = ? ORDER BY ORDEM", (musica_id,)
        ).fetchall()
        if rows:
            return [_normaliza_slide_novo(r) for r in rows]

    if has_table("MUSICAS_LETRA"):
        rows = conn.execute(
            "SELECT * FROM MUSICAS_LETRA WHERE MUSICA = ? ORDER BY ORDEM", (musica_id,)
        ).fetchall()
        return [_normaliza_slide_legado(r) for r in rows]

    return []
