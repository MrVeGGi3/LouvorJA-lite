"""O seek do player depende de Range HTTP.

O suporte a Range no FileResponse só existe no Starlette >= 0.45 e não dá erro quando falta —
o navegador simplesmente baixa o arquivo inteiro e a barra de progresso para de funcionar. Estes
testes são o que impede essa regressão de passar despercebida.
"""

import pytest
from fastapi.testclient import TestClient

from app import config
from app.main import app

client = TestClient(app)

# Precisa ter exatamente os 2048 bytes que a fixture do banco declara em files.size — é por esse
# tamanho que o app decide se a faixa está baixada.
CONTEUDO = (b"cabecalho-falso-de-mp3" + bytes(range(256)) * 8)[:2048]


@pytest.fixture
def mp3(tmp_path):
    """Planta em disco o arquivo que a fixture do banco diz existir (id_file 900)."""
    caminho = config.DATA_DIR / "musicas" / "Hinário Adventista" / "Hino Um.mp3"
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_bytes(CONTEUDO)
    yield caminho


def test_audio_completo(mp3):
    resp = client.get("/api/audio/900")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "audio/mpeg"
    assert resp.content == CONTEUDO


def test_audio_responde_range_com_206(mp3):
    resp = client.get("/api/audio/900", headers={"Range": "bytes=10-19"})
    assert resp.status_code == 206, "sem Range o seek do player não funciona"
    assert resp.content == CONTEUDO[10:20]
    assert resp.headers["content-range"] == f"bytes 10-19/{len(CONTEUDO)}"
    assert resp.headers["accept-ranges"] == "bytes"


def test_audio_range_aberto_vai_ate_o_fim(mp3):
    resp = client.get("/api/audio/900", headers={"Range": "bytes=100-"})
    assert resp.status_code == 206
    assert resp.content == CONTEUDO[100:]


def test_audio_nao_baixado_da_404_legivel():
    resp = client.get("/api/audio/900")
    assert resp.status_code == 404
    assert "não foi baixado" in resp.json()["detail"]


def test_audio_de_id_inexistente():
    assert client.get("/api/audio/99999").status_code == 404


def test_imagem_nao_serve_arquivo_de_audio(mp3):
    # /api/imagem só aceita imagens; pedir um mp3 por ali não pode devolver o arquivo.
    assert client.get("/api/imagem/900").status_code == 404


def test_audio_da_musica_lista_as_faixas(mp3):
    dados = client.get("/api/musicas/1/audio").json()

    assert dados["cantado"]["id_file"] == 900
    assert dados["cantado"]["duracao"] == "00:02:17"
    assert dados["cantado"]["disponivel"] is True
    assert dados["cantado"]["url"] == "/api/audio/900"

    # O playback está no catálogo, mas não foi baixado.
    assert dados["playback"]["id_file"] == 901
    assert dados["playback"]["disponivel"] is False


def test_musica_sem_audio_no_catalogo():
    dados = client.get("/api/musicas/2/audio").json()
    assert dados == {"cantado": None, "playback": None}


def test_slide_traz_imagem_por_id():
    slides = client.get("/api/musicas/1/slides").json()
    assert slides[0]["imagem_fundo"] == "/api/imagem/910"
    assert slides[1]["imagem_fundo"] == "/api/imagem/911"


def test_ir_para_slide_absoluto():
    slides = client.get("/api/musicas/1/slides").json()
    client.post(
        "/api/projecao/estado",
        json={"titulo_item": "Hino", "slides": slides, "slide_index": 0},
    )

    resp = client.post("/api/projecao/slide", json={"slide_index": 1})
    assert resp.status_code == 200
    assert resp.json()["slide_index"] == 1

    assert client.post("/api/projecao/slide", json={"slide_index": 9}).status_code == 400
