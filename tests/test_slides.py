from app.db.connection import get_connection
from app.db.slides import get_slides


def test_get_slides_from_musicas_slide():
    conn = get_connection()
    try:
        slides = get_slides(conn, "MUSICAS", 1)
    finally:
        conn.close()
    assert len(slides) == 2
    assert slides[0]["letra"].startswith("Grande é o Senhor")
    assert slides[0]["cor_letra"] == "#efb400"
    assert slides[0]["cor_fundo"] == "#000000"


def test_get_slides_resolves_hinario_by_nome():
    conn = get_connection()
    try:
        slides = get_slides(conn, "HINARIO_ADVENTISTA", 1)
    finally:
        conn.close()
    assert len(slides) == 2


def test_get_slides_falls_back_to_musicas_letra():
    conn = get_connection()
    try:
        slides = get_slides(conn, "MUSICAS", 2)
    finally:
        conn.close()
    assert len(slides) == 1
    assert slides[0]["letra"] == "Letra do sistema antigo"
    assert slides[0]["cor_letra"] == "#ffffff"


def test_get_slides_unknown_returns_empty():
    conn = get_connection()
    try:
        slides = get_slides(conn, "MUSICAS", 999)
    finally:
        conn.close()
    assert slides == []
