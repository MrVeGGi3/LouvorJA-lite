from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_busca_hinario_por_numero():
    resp = client.get("/api/hinario", params={"q": "1"})
    assert resp.status_code == 200
    dados = resp.json()
    assert len(dados) == 1
    assert dados[0]["FAIXA"] == 1


def test_busca_hinario_por_nome():
    resp = client.get("/api/hinario", params={"q": "grande"})
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_slides_de_musica():
    resp = client.get("/api/musicas/MUSICAS/1/slides")
    assert resp.status_code == 200
    slides = resp.json()
    assert len(slides) == 2
    assert slides[0]["imagem_fundo"] == "/data/imagens/fundo1.jpg"


def test_criar_e_listar_liturgia():
    payload = {"week_of": "2026-07-12", "titulo": "Culto de Sábado", "itens": []}
    resp = client.post("/api/liturgias", json=payload)
    assert resp.status_code == 200

    resp = client.get("/api/liturgias/2026-07-12")
    assert resp.status_code == 200
    assert resp.json()["titulo"] == "Culto de Sábado"


def test_criar_duplicada_retorna_conflito():
    payload = {"week_of": "2026-07-13", "titulo": "A"}
    assert client.post("/api/liturgias", json=payload).status_code == 200
    assert client.post("/api/liturgias", json=payload).status_code == 409


def test_adicionar_item_e_projetar():
    resp = client.post("/api/liturgias", json={"week_of": "2026-07-19", "titulo": "Culto"})
    liturgia_id = resp.json()["id"]

    item = {
        "ordem": 1, "tipo": "hino", "origem": "MUSICAS", "ref_id": 1,
        "titulo_exibicao": "Grande é o Senhor",
    }
    resp = client.post("/api/liturgias/2026-07-19/itens", json=item)
    assert resp.status_code == 200
    assert len(resp.json()["itens"]) == 1

    slides = client.get("/api/musicas/MUSICAS/1/slides").json()
    estado = {
        "liturgia_id": liturgia_id,
        "week_of": "2026-07-19",
        "item_index": 0,
        "titulo_item": "Grande é o Senhor",
        "slides": slides,
        "slide_index": 0,
    }
    resp = client.post("/api/projecao/estado", json=estado)
    assert resp.status_code == 200
    assert resp.json()["total_slides"] == 2

    resp = client.post("/api/projecao/navegar", json={"direcao": "prox"})
    assert resp.status_code == 200
    assert resp.json()["slide_index"] == 1

    resp = client.get("/api/projecao/estado")
    assert resp.json()["slide_index"] == 1

    resp = client.post("/api/projecao/navegar", json={"direcao": "prox"})
    assert resp.status_code == 400


def test_reordenar_itens():
    client.post("/api/liturgias", json={"week_of": "2026-08-02", "titulo": "Culto"})
    item1 = {"ordem": 1, "tipo": "nota", "titulo_exibicao": "Item 1", "texto": "a"}
    item2 = {"ordem": 2, "tipo": "nota", "titulo_exibicao": "Item 2", "texto": "b"}
    client.post("/api/liturgias/2026-08-02/itens", json=item1)
    resp = client.post("/api/liturgias/2026-08-02/itens", json=item2)
    ids = [i["id"] for i in resp.json()["itens"]]

    resp = client.put("/api/liturgias/2026-08-02/reordenar", json=list(reversed(ids)))
    assert resp.status_code == 200
    novos_titulos = [i["titulo_exibicao"] for i in resp.json()["itens"]]
    assert novos_titulos == ["Item 2", "Item 1"]
