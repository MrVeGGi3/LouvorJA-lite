"""A tela de download precisa funcionar justamente quando não há banco nenhum.

Nenhum teste aqui toca a rede: a sessão do servidor de mídia é trocada por uma falsa que escreve
bytes em disco. O que está sendo verificado é o contrato com a interface — o status, os códigos de
erro e as transições de estado do trabalho em segundo plano.
"""

import threading

import pytest
from fastapi.testclient import TestClient

from app import config
from app.db.arquivos import caminho_local
from app.main import app
from app.sync import midia
from app.sync.gerenciador import Gerenciador, JaEmAndamento
from app.sync.gerenciador import gerenciador as gerenciador_global

client = TestClient(app)


class SessaoFalsa:
    """Grava exatamente o tamanho que o catálogo declara, sem sair da máquina."""

    def __init__(self, antes_de_baixar=None):
        self.baixados = []
        self.antes_de_baixar = antes_de_baixar

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return None

    def baixar(self, caminho, destino, tamanho_esperado=None, tentativas=4):
        if self.antes_de_baixar is not None:
            self.antes_de_baixar(caminho)
        destino.parent.mkdir(parents=True, exist_ok=True)
        conteudo = b"x" * (tamanho_esperado or 16)
        destino.write_bytes(conteudo)
        self.baixados.append(caminho)
        return len(conteudo)


@pytest.fixture(autouse=True)
def _gerenciador_limpo(monkeypatch):
    """Cada teste começa com um gerenciador zerado — o global é compartilhado entre as rotas."""
    monkeypatch.setattr(gerenciador_global, "_progresso", type(gerenciador_global._progresso)())
    monkeypatch.setattr(gerenciador_global, "_parar", threading.Event())
    midia.invalidar_resumo()
    yield
    midia.invalidar_resumo()


def _esperar_fim(ger=gerenciador_global, limite=5.0):
    thread = ger._thread
    if thread is not None:
        thread.join(timeout=limite)
    assert not ger.rodando, "o trabalho não terminou dentro do limite"
    return ger.snapshot()


# --- status ----------------------------------------------------------------


def test_status_sem_banco_nao_estoura():
    config.DB_PATH.unlink()

    resp = client.get("/api/atualizacao/status")

    assert resp.status_code == 200
    dados = resp.json()
    assert dados["banco"]["presente"] is False
    assert dados["albuns"] == []
    assert dados["catalogo"]["total"] == 0


def test_status_conta_arquivos_por_album():
    resp = client.get("/api/atualizacao/status")

    assert resp.status_code == 200
    dados = resp.json()
    assert dados["banco"]["presente"] is True
    por_id = {a["id_album"]: a for a in dados["albuns"]}
    # O álbum 712 referencia as duas faixas do hino 1, a imagem da música, a do slide e a capa.
    assert por_id[712]["total"] == 5
    assert por_id[712]["prontos"] == 0
    assert dados["catalogo"]["total"] == 5


def test_status_ve_o_que_ja_esta_em_disco():
    caminho = caminho_local(
        config.DATA_DIR, "music", "/musics/pt/Hinário Adventista", "Hino Um.mp3"
    )
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_bytes(b"x" * 2048)
    midia.invalidar_resumo()

    dados = client.get("/api/atualizacao/status").json()

    por_id = {a["id_album"]: a for a in dados["albuns"]}
    assert por_id[712]["prontos"] == 1
    assert por_id[712]["bytes_prontos"] == 2048


def test_hinario_vai_no_topo_da_lista():
    dados = client.get("/api/atualizacao/status").json()

    assert dados["albuns"][0]["id_album"] == midia.ALBUM_HINARIO


# --- rotas de download -----------------------------------------------------


def test_midia_sem_banco_devolve_409():
    config.DB_PATH.unlink()

    resp = client.post("/api/atualizacao/midia", json={})

    assert resp.status_code == 409


def test_baixar_album_grava_os_arquivos(monkeypatch):
    sessao = SessaoFalsa()
    monkeypatch.setattr(gerenciador_global, "fabrica_sessao", lambda: sessao)

    resp = client.post("/api/atualizacao/midia", json={"album": 712, "escopo": "Hinário"})
    assert resp.status_code == 202

    job = _esperar_fim()
    assert job["estado"] == "concluido"
    assert job["arquivos_prontos"] == 5
    assert job["falhas"] == []
    assert caminho_local(
        config.DATA_DIR, "music", "/musics/pt/Hinário Adventista", "Hino Um.mp3"
    ).exists()


def test_baixar_arquivo_avulso(monkeypatch):
    sessao = SessaoFalsa()
    monkeypatch.setattr(gerenciador_global, "fabrica_sessao", lambda: sessao)

    resp = client.post("/api/atualizacao/arquivo/900")
    assert resp.status_code == 202

    job = _esperar_fim()
    assert job["estado"] == "concluido"
    assert sessao.baixados == ["config/musicas/Hinário Adventista/Hino Um.mp3"]


def test_segundo_download_concorrente_devolve_409(monkeypatch):
    liberar = threading.Event()
    sessao = SessaoFalsa(antes_de_baixar=lambda _: liberar.wait(timeout=5))
    monkeypatch.setattr(gerenciador_global, "fabrica_sessao", lambda: sessao)

    assert client.post("/api/atualizacao/midia", json={}).status_code == 202
    try:
        resp = client.post("/api/atualizacao/midia", json={})
        assert resp.status_code == 409
    finally:
        liberar.set()
    _esperar_fim()


def test_cancelar_para_no_meio(monkeypatch):
    # O cancelamento é conferido entre arquivos: pedir a parada durante o primeiro download faz o
    # trabalho terminar antes do segundo.
    sessao = SessaoFalsa(antes_de_baixar=lambda _: gerenciador_global.cancelar())
    monkeypatch.setattr(gerenciador_global, "fabrica_sessao", lambda: sessao)

    client.post("/api/atualizacao/midia", json={})

    job = _esperar_fim()
    assert job["estado"] == "cancelado"
    assert len(sessao.baixados) == 1


def test_falha_de_um_arquivo_nao_derruba_o_resto(monkeypatch):
    from app.sync import louvorja_api

    def explodir_no_primeiro(caminho):
        if caminho.endswith("Hino Um.mp3"):
            raise louvorja_api.ErroDeConexao("servidor caiu")

    sessao = SessaoFalsa(antes_de_baixar=explodir_no_primeiro)
    monkeypatch.setattr(gerenciador_global, "fabrica_sessao", lambda: sessao)

    client.post("/api/atualizacao/midia", json={})

    job = _esperar_fim()
    assert job["estado"] == "concluido"
    assert len(job["falhas"]) == 1
    assert job["falhas"][0]["arquivo"] == "Hino Um.mp3"
    assert job["arquivos_prontos"] == 4


# --- gerenciador -----------------------------------------------------------


def test_gerenciador_recusa_dois_trabalhos():
    ger = Gerenciador()
    liberar = threading.Event()
    ger.fabrica_sessao = lambda: SessaoFalsa(antes_de_baixar=lambda _: liberar.wait(timeout=5))

    ger.iniciar_midia()
    try:
        with pytest.raises(JaEmAndamento):
            ger.iniciar_midia()
    finally:
        liberar.set()
    _esperar_fim(ger)


def test_nada_a_baixar_quando_tudo_esta_em_disco(monkeypatch):
    arquivos = midia.listar_arquivos(config.DB_PATH)
    for a in arquivos:
        caminho = caminho_local(config.DATA_DIR, a["type"], a["dir"], a["file_name"])
        caminho.parent.mkdir(parents=True, exist_ok=True)
        caminho.write_bytes(b"x" * a["size"])
    midia.invalidar_resumo()

    sessao = SessaoFalsa()
    monkeypatch.setattr(gerenciador_global, "fabrica_sessao", lambda: sessao)
    client.post("/api/atualizacao/midia", json={})

    job = _esperar_fim()
    assert job["estado"] == "concluido"
    assert sessao.baixados == []


# --- reação da interface ao banco ausente ----------------------------------


def test_rota_que_precisa_do_banco_devolve_codigo_estruturado():
    config.DB_PATH.unlink()

    resp = client.get("/api/hinario", params={"q": "1"})

    assert resp.status_code == 503
    assert resp.json()["detail"]["codigo"] == "sem_banco"


def test_audio_nao_baixado_diz_qual_arquivo_falta():
    resp = client.get("/api/audio/900")

    assert resp.status_code == 404
    detalhe = resp.json()["detail"]
    assert detalhe["codigo"] == "nao_baixado"
    assert detalhe["id_file"] == 900
