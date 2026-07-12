import sqlite3
from pathlib import Path

import pytest


def _build_fixture_db(path: Path) -> None:
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE HINARIO_ADVENTISTA (
            ID INTEGER PRIMARY KEY, NOME TEXT, NOME_COM TEXT, NOME_SEMAC TEXT,
            FAIXA INTEGER, ALBUM TEXT, TIPO_HASD TEXT, TIPO_JA TEXT
        );
        CREATE TABLE MUSICAS (
            ID INTEGER PRIMARY KEY, ALBUM INTEGER, NOME TEXT, IMAGEM TEXT,
            URL TEXT, URL_INSTRUMENTAL TEXT, LETRA TEXT
        );
        CREATE TABLE MUSICAS_SLIDE (
            MUSICA_ID INTEGER, ORDEM INTEGER, LETRA TEXT, LETRA_AUX TEXT,
            IMAGEM TEXT, COR_LETRA TEXT, COR_FUNDO TEXT, TAMANHO_LETRA INTEGER,
            FUNDO_LETRA INTEGER
        );
        CREATE TABLE MUSICAS_LETRA (
            ID INTEGER PRIMARY KEY, MUSICA INTEGER, LETRA TEXT, LETRA_AUX TEXT,
            ORDEM INTEGER, IMAGEM TEXT
        );
        CREATE TABLE LISTA_MUSICAS_TODAS (
            ID INTEGER, NOME TEXT, NOME_SEMAC TEXT, LETRA_SEMAC TEXT,
            NOME_ALBUM_COM_SEMAC TEXT, TIPO TEXT
        );

        INSERT INTO HINARIO_ADVENTISTA VALUES
            (1, '1 - Grande e o Senhor', 'Grande é o Senhor', 'GRANDE E O SENHOR', 1, 'Hinario', 'S', 'S'),
            (2, '2 - Sem Slides', 'Hino Sem Slides', 'HINO SEM SLIDES', 2, 'Hinario', 'S', 'S');

        INSERT INTO MUSICAS VALUES
            (1, 10, 'Grande é o Senhor', 'capa1.jpg', 'audio1.mp3', NULL, 'Grande é o Senhor...'),
            (2, 10, 'Hino Sem Slides', NULL, NULL, NULL, 'letra antiga');

        INSERT INTO MUSICAS_SLIDE VALUES
            (1, 1, 'Grande é o Senhor,
e mui digno de louvor', NULL, 'fundo1.jpg', '$000b4ef', '$0000000', 44, 0),
            (1, 2, 'Na cidade do nosso Deus', NULL, 'fundo1.jpg', '$000b4ef', '$0000000', 44, 0);

        INSERT INTO MUSICAS_LETRA VALUES
            (1, 2, 'Letra do sistema antigo', NULL, 1, NULL);

        INSERT INTO LISTA_MUSICAS_TODAS VALUES
            (1, 'Grande é o Senhor', 'GRANDE E O SENHOR', 'GRANDE E O SENHOR', 'HINARIO', 'HASD');
        """
    )
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
