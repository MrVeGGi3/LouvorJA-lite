import pytest

from app.db.arquivos import arquivo_completo, caminho_local, caminho_remoto


def test_caminho_da_musica_descarta_o_idioma_e_mantem_o_album():
    rel = caminho_remoto("music", "/musics/pt/Hinário Adventista", "'Stavas Lá.mp3")
    assert rel == "config/musicas/Hinário Adventista/'Stavas Lá.mp3"


def test_caminho_das_imagens():
    assert caminho_remoto("image_album", "/covers", "hasd.bmp") == "config/capas/hasd.bmp"
    assert caminho_remoto("image_music", "/images", "hasd_018.jpg") == "config/imagens/hasd_018.jpg"


def test_tipo_desconhecido_estoura():
    with pytest.raises(ValueError):
        caminho_remoto("video", "/videos", "x.mp4")


def test_caminho_local_espelha_o_remoto(tmp_path):
    local = caminho_local(tmp_path, "music", "/musics/pt/Adoradores 3", "Canção.mp3")
    assert local == tmp_path / "musicas" / "Adoradores 3" / "Canção.mp3"


def _arquivo(tmp_path, bytes_):
    caminho = tmp_path / "x.mp3"
    caminho.write_bytes(b"a" * bytes_)
    return caminho


def test_arquivo_truncado_nao_conta_como_completo(tmp_path):
    assert arquivo_completo(_arquivo(tmp_path, 500), 1000) is False


def test_arquivo_no_tamanho_exato_esta_completo(tmp_path):
    assert arquivo_completo(_arquivo(tmp_path, 1000), 1000) is True


def test_arquivo_maior_que_o_catalogo_conta_como_completo(tmp_path):
    """O servidor troca arquivos por versões melhores sem atualizar `files.size`.

    Aconteceu de verdade com 'Hoje é o Tempo': o catálogo diz 6.114.101 bytes e o servidor entrega
    um mp3 de 256 kbps com 7.743.449. Exigir igualdade exata jogaria fora o arquivo bom.
    """
    assert arquivo_completo(_arquivo(tmp_path, 7_743_449), 6_114_101) is True


def test_arquivo_inexistente(tmp_path):
    assert arquivo_completo(tmp_path / "nao-existe.mp3", 10) is False
