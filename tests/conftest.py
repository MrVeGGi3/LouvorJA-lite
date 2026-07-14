import sqlite3
from pathlib import Path

import pytest

# DDL copiado do banco real (VERSAO_BD >= 181). A fixture antiga inventava um esquema que não
# existe mais, e por isso a suíte ficava verde com o app quebrado contra o banco de verdade.
DDL = """
CREATE TABLE musics (
    id_music INTEGER PRIMARY KEY, name VARCHAR, id_file_image INTEGER,
    id_file_music INTEGER, id_file_instrumental_music INTEGER, id_language VARCHAR NOT NULL
);
CREATE TABLE files (
    id_file INTEGER PRIMARY KEY, name VARCHAR NOT NULL, type VARCHAR NOT NULL,
    size INTEGER NOT NULL, dir VARCHAR NOT NULL, file_name VARCHAR NOT NULL,
    image_position INTEGER, duration TIME, version INTEGER NOT NULL
);
CREATE TABLE lyrics (
    id_lyric INTEGER PRIMARY KEY, id_music INTEGER NOT NULL, lyric VARCHAR NOT NULL,
    aux_lyric VARCHAR, id_file_image INTEGER, "time" TIME NOT NULL,
    instrumental_time TIME NOT NULL, show_slide TINYINT(1) NOT NULL,
    "order" INTEGER NOT NULL, id_language VARCHAR NOT NULL
);
CREATE TABLE albums (
    id_album INTEGER PRIMARY KEY, name VARCHAR, id_file_image INTEGER,
    color VARCHAR NOT NULL, id_language VARCHAR NOT NULL
);
CREATE TABLE albums_musics (
    id_album_music INTEGER PRIMARY KEY, id_album INTEGER NOT NULL, id_music INTEGER NOT NULL,
    track INTEGER NOT NULL, id_language VARCHAR NOT NULL
);
CREATE TABLE categories (
    id_category INTEGER PRIMARY KEY, name VARCHAR, slug VARCHAR, "order" INTEGER NOT NULL,
    type VARCHAR, id_language VARCHAR NOT NULL
);
CREATE TABLE categories_albums (
    id_category_album INTEGER PRIMARY KEY, id_category INTEGER NOT NULL,
    id_album INTEGER NOT NULL, name VARCHAR NOT NULL, "order" INTEGER NOT NULL,
    id_language VARCHAR NOT NULL
);
"""

# id_file 900/901 = áudio cantado e playback do hino 1; 910 = imagem de fundo; 920 = capa.
DADOS = """
INSERT INTO files (id_file, name, type, size, dir, file_name, duration, version) VALUES
    (900, 'cantado', 'music', 2048, '/musics/pt/Hinário Adventista', 'Hino Um.mp3', '00:02:17', 1),
    (901, 'playback', 'music', 2048, '/musics/pt/Hinário Adventista', 'Hino Um - PB.mp3', '00:02:17', 1),
    (910, 'fundo', 'image_music', 512, '/images', 'fundo1.jpg', NULL, 1),
    (911, 'fundo-musica', 'image_music', 512, '/images', 'fundo-musica.jpg', NULL, 1),
    (920, 'capa', 'image_album', 256, '/covers', 'capa1.jpg', NULL, 1);

INSERT INTO albums (id_album, name, id_file_image, color, id_language) VALUES
    (712, 'Hinário Adventista', 920, '', 'pt'),
    (629, 'Hinário Adventista 1996', NULL, '', 'pt'),
    (500, 'Coletânea de Teste', NULL, '', 'pt');

INSERT INTO categories (id_category, name, slug, "order", type, id_language) VALUES
    (3, 'Hinário Adventista', 'hymnal', 1, 'hymnal', 'pt'),
    (4, 'Hinário Adventista 1996', 'hymnal_1996', 2, 'hymnal', 'pt'),
    (6, 'Coletâneas', 'aym', 10, 'collection', 'pt');

INSERT INTO categories_albums (id_category_album, id_category, id_album, name, "order", id_language) VALUES
    (1, 3, 712, 'Hinário Adventista', 1, 'pt'),
    (2, 4, 629, 'Hinário Adventista 1996', 1, 'pt'),
    (3, 6, 500, 'Coletânea de Teste', 1, 'pt');

-- A música 1 tem cantado + playback; a 2 não tem áudio nenhum; 3 e 4 dividem a mesma faixa
-- (o Hinário Adventista real tem a faixa 587 duplicada em duas variantes).
INSERT INTO musics (id_music, name, id_file_image, id_file_music, id_file_instrumental_music, id_language) VALUES
    (1, 'Hino de Teste Um', 911, 900, 901, 'pt'),
    (2, 'Hino de Teste Dois', NULL, NULL, NULL, 'pt'),
    (3, 'Variante A', NULL, NULL, NULL, 'pt'),
    (4, 'Variante B', NULL, NULL, NULL, 'pt'),
    (5, 'Canção da Coletânea', NULL, NULL, NULL, 'pt');

INSERT INTO albums_musics (id_album_music, id_album, id_music, track, id_language) VALUES
    (1, 712, 1, 1, 'pt'),
    (2, 712, 2, 2, 'pt'),
    (3, 712, 3, 587, 'pt'),
    (4, 712, 4, 587, 'pt'),
    (5, 629, 2, 1, 'pt'),
    (6, 500, 5, 1, 'pt');

-- A música 1 tem 2 slides visíveis e 1 oculto (show_slide=0), que não pode aparecer na projeção.
-- O slide de ordem 1 tem imagem própria; o de ordem 2 cai na imagem da música (COALESCE).
INSERT INTO lyrics (id_lyric, id_music, lyric, aux_lyric, id_file_image, "time", instrumental_time, show_slide, "order", id_language) VALUES
    (1, 1, 'Primeira estrofe do hino de teste', 'Verso auxiliar', 910, '00:00:09', '00:00:11', 1, 1, 'pt'),
    (2, 1, 'Segunda estrofe do hino de teste', NULL, NULL, '00:00:20', '00:00:24', 1, 2, 'pt'),
    (3, 1, 'Estrofe que não deve virar slide', NULL, NULL, '00:00:30', '00:00:30', 0, 3, 'pt'),
    (4, 2, 'Estrofe única da música sem áudio', NULL, NULL, '00:00:00', '00:00:00', 1, 1, 'pt');
"""


def _build_fixture_db(path: Path) -> None:
    conn = sqlite3.connect(path)
    conn.executescript(DDL)
    conn.executescript(DADOS)
    conn.commit()
    conn.close()


@pytest.fixture(autouse=True)
def _fresh_data_dir(tmp_path, monkeypatch):
    import app.config as config
    import app.db.connection as connection
    import app.db.introspect as introspect
    import app.liturgia.store as store
    import app.projecao.state as state

    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "database.db")
    monkeypatch.setattr(config, "CAPAS_DIR", tmp_path / "capas")
    monkeypatch.setattr(config, "IMAGENS_DIR", tmp_path / "imagens")
    monkeypatch.setattr(config, "LITURGIAS_DIR", tmp_path / "liturgias")
    monkeypatch.setattr(config, "PROJECAO_STATE_PATH", tmp_path / "projecao_estado.json")

    monkeypatch.setattr(connection, "DB_PATH", tmp_path / "database.db")
    monkeypatch.setattr(introspect, "DB_PATH", tmp_path / "database.db")
    introspect._tables_for_mtime.cache_clear()
    monkeypatch.setattr(store, "LITURGIAS_DIR", tmp_path / "liturgias")
    monkeypatch.setattr(state, "PROJECAO_STATE_PATH", tmp_path / "projecao_estado.json")

    _build_fixture_db(tmp_path / "database.db")
    yield
