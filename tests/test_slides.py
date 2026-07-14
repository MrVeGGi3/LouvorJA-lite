import pytest

from app.db.connection import get_connection
from app.db.slides import COR_DESTAQUE, COR_LETRA, TAMANHO_LETRA, TAMANHO_TITULO, get_slides


@pytest.fixture
def conn():
    conexao = get_connection()
    try:
        yield conexao
    finally:
        conexao.close()


def test_primeiro_slide_e_a_capa_com_numero_e_nome(conn):
    capa = get_slides(conn, 1)[0]
    assert capa["tipo"] == "capa"
    assert capa["letra"] == "1 - Hino de Teste Um"
    assert capa["cor_letra"] == COR_DESTAQUE
    assert capa["tamanho_letra"] == TAMANHO_TITULO
    # A capa fica no tempo 0: é ela que aparece enquanto a introdução toca.
    assert capa["tempo"] == "00:00:00"


def test_capa_usa_a_imagem_da_musica(conn):
    assert get_slides(conn, 1)[0]["imagem_id"] == 911


def test_ignora_linhas_com_show_slide_zero(conn):
    slides = get_slides(conn, 1)
    # capa + 2 slides visíveis (o terceiro tem show_slide=0)
    assert len(slides) == 3
    assert [s["tipo"] for s in slides] == ["capa", "letra", "letra"]


def test_letra_comum_e_branca_e_no_tamanho_da_letra(conn):
    letra = get_slides(conn, 1)[1]
    assert letra["cor_letra"] == COR_LETRA
    assert letra["tamanho_letra"] == TAMANHO_LETRA


def test_imagem_do_slide_tem_precedencia_sobre_a_da_musica(conn):
    assert get_slides(conn, 1)[1]["imagem_id"] == 910


def test_slide_sem_imagem_propria_cai_na_imagem_da_musica(conn):
    assert get_slides(conn, 1)[2]["imagem_id"] == 911


def test_traz_os_tempos_para_o_auto_advance(conn):
    slides = get_slides(conn, 1)
    assert [s["tempo"] for s in slides] == ["00:00:00", "00:00:09", "00:00:20"]
    assert [s["tempo_instrumental"] for s in slides] == ["00:00:00", "00:00:11", "00:00:24"]


def test_texto_auxiliar_sai_dourado(conn):
    slide = get_slides(conn, 1)[1]
    assert slide["letra_aux"] == "Verso auxiliar"
    assert slide["cor_letra_aux"] == COR_DESTAQUE


def test_verso_que_repete_o_anterior_sai_dourado(conn):
    # capa, depois 3 slides de texto idêntico e 1 diferente. O alternador do original faz o
    # segundo sair dourado e o terceiro voltar ao branco — a comparação ignora caixa.
    cores = [s["cor_letra"] for s in get_slides(conn, 6)]
    assert cores == [COR_DESTAQUE, COR_LETRA, COR_DESTAQUE, COR_LETRA, COR_LETRA]


def test_musica_fora_do_hinario_usa_so_o_nome_na_capa(conn):
    assert get_slides(conn, 5)[0]["letra"] == "Canção da Coletânea"


def test_musica_inexistente_retorna_vazio(conn):
    assert get_slides(conn, 999) == []
