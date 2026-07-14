import pytest

from app.db.connection import get_connection
from app.db.slides import get_slides


@pytest.fixture
def conn():
    conexao = get_connection()
    try:
        yield conexao
    finally:
        conexao.close()


def test_ignora_linhas_com_show_slide_zero(conn):
    slides = get_slides(conn, 1)
    assert len(slides) == 2
    assert [s["ordem"] for s in slides] == [1, 2]


def test_imagem_do_slide_tem_precedencia_sobre_a_da_musica(conn):
    slides = get_slides(conn, 1)
    assert slides[0]["imagem_arquivo"] == "fundo1.jpg"


def test_slide_sem_imagem_propria_cai_na_imagem_da_musica(conn):
    slides = get_slides(conn, 1)
    assert slides[1]["imagem_arquivo"] == "fundo-musica.jpg"


def test_traz_os_tempos_para_o_auto_advance(conn):
    slides = get_slides(conn, 1)
    assert [s["tempo"] for s in slides] == ["00:00:09", "00:00:20"]
    assert [s["tempo_instrumental"] for s in slides] == ["00:00:11", "00:00:24"]


def test_musica_inexistente_retorna_vazio(conn):
    assert get_slides(conn, 999) == []
