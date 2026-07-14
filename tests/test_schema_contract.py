"""Confere que um banco REAL tem as tabelas e colunas que as queries do app usam.

O resto da suíte roda contra uma fixture, e uma fixture só prova que o código concorda consigo
mesmo. Foi exatamente esse ponto cego que deixou o app quebrado contra o banco de verdade: a
fixture descrevia um esquema que o LouvorJA Desktop já tinha abandonado.

Pulado por padrão. Para rodar:

    LOUVORJA_REAL_DB=~/.local/share/LouvorJA/config/database.db pytest tests/test_schema_contract.py
"""

import os
import sqlite3
from pathlib import Path

import pytest

_REAL_DB = os.environ.get("LOUVORJA_REAL_DB")

pytestmark = pytest.mark.skipif(
    not _REAL_DB, reason="defina LOUVORJA_REAL_DB para checar o contrato contra um banco real"
)

COLUNAS_EXIGIDAS = {
    "musics": {"id_music", "name", "id_file_image", "id_file_music", "id_file_instrumental_music"},
    "lyrics": {"id_lyric", "id_music", "lyric", "aux_lyric", "id_file_image", "time",
               "instrumental_time", "show_slide", "order"},
    "files": {"id_file", "type", "size", "dir", "file_name", "duration"},
    "albums": {"id_album", "name", "id_file_image"},
    "albums_musics": {"id_album", "id_music", "track"},
    "categories": {"id_category", "slug", "type"},
    "categories_albums": {"id_category", "id_album"},
}


@pytest.fixture(scope="module")
def real_conn():
    caminho = Path(_REAL_DB).expanduser()
    if not caminho.exists():
        pytest.skip(f"banco real não encontrado em {caminho}")
    conn = sqlite3.connect(f"file:{caminho}?mode=ro", uri=True)
    try:
        yield conn
    finally:
        conn.close()


@pytest.mark.parametrize("tabela", sorted(COLUNAS_EXIGIDAS))
def test_tabela_tem_as_colunas_que_o_app_usa(real_conn, tabela):
    colunas = {r[1] for r in real_conn.execute(f'PRAGMA table_info("{tabela}")')}
    assert colunas, f"tabela {tabela} não existe no banco real"
    faltando = COLUNAS_EXIGIDAS[tabela] - colunas
    assert not faltando, f"{tabela} não tem as colunas {sorted(faltando)}"


def test_hinario_resolve_para_um_album_com_faixas(real_conn):
    sql = """
        SELECT COUNT(*)
        FROM categories c
        JOIN categories_albums ca ON ca.id_category = c.id_category
        JOIN albums_musics am ON am.id_album = ca.id_album
        WHERE c.slug = ?
    """
    for slug in ("hymnal", "hymnal_1996"):
        (total,) = real_conn.execute(sql, (slug,)).fetchone()
        assert total > 500, f"categoria {slug} deveria ter as faixas do hinário, tem {total}"


def test_os_tipos_de_arquivo_tem_layout_conhecido(real_conn):
    from app.db.arquivos import SUBPASTA_POR_TIPO

    tipos = {r[0] for r in real_conn.execute("SELECT DISTINCT type FROM files")}
    desconhecidos = tipos - set(SUBPASTA_POR_TIPO)
    assert not desconhecidos, f"tipos de arquivo sem layout definido: {sorted(desconhecidos)}"
