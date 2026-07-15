from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_busca_hinario_por_numero():
    resp = client.get("/api/hinario", params={"q": "1"})
    assert resp.status_code == 200
    dados = resp.json()
    assert len(dados) == 1
    assert dados[0]["numero"] == 1
    assert dados[0]["id_music"] == 1


def test_busca_hinario_por_numero_duplicado_traz_as_duas_variantes():
    resp = client.get("/api/hinario", params={"q": "587"})
    assert resp.status_code == 200
    assert [h["titulo"] for h in resp.json()] == ["Variante A", "Variante B"]


def test_busca_hinario_por_nome_ignora_acento():
    resp = client.get("/api/hinario", params={"q": "hino de teste"})
    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_busca_hinario_1996_usa_outro_album():
    resp = client.get("/api/hinario", params={"q": "1", "edicao": "1996"})
    assert resp.status_code == 200
    dados = resp.json()
    assert len(dados) == 1
    assert dados[0]["id_music"] == 2


def test_busca_musicas_encontra_por_album():
    resp = client.get("/api/musicas/busca", params={"q": "coletanea"})
    assert resp.status_code == 200
    assert [m["id_music"] for m in resp.json()] == [5]


def test_slides_de_musica():
    resp = client.get("/api/musicas/1/slides")
    assert resp.status_code == 200
    slides = resp.json()
    # capa + 2 slides de letra
    assert len(slides) == 3
    assert slides[0]["tipo"] == "capa"
    assert slides[0]["imagem_fundo"] == "/api/imagem/911"
    assert slides[1]["imagem_fundo"] == "/api/imagem/910"
    assert slides[2]["imagem_fundo"] == "/api/imagem/911"


def test_detalhe_de_musica_inexistente():
    assert client.get("/api/musicas/999").status_code == 404


def test_criar_e_listar_liturgia():
    payload = {"dia": "sabado", "titulo": "Culto de Sábado", "itens": []}
    resp = client.post("/api/liturgias", json=payload)
    assert resp.status_code == 200

    resp = client.get("/api/liturgias/sabado")
    assert resp.status_code == 200
    assert resp.json()["titulo"] == "Culto de Sábado"


def test_criar_duplicada_retorna_conflito():
    payload = {"dia": "sexta", "titulo": "A"}
    assert client.post("/api/liturgias", json=payload).status_code == 200
    assert client.post("/api/liturgias", json=payload).status_code == 409


def test_adicionar_item_e_projetar():
    resp = client.post("/api/liturgias", json={"dia": "domingo", "titulo": "Culto"})
    liturgia_id = resp.json()["id"]

    item = {
        "ordem": 1, "tipo": "hino", "origem": "hinario", "ref_id": 1,
        "titulo_exibicao": "1 - Hino de Teste Um",
    }
    resp = client.post("/api/liturgias/domingo/itens", json=item)
    assert resp.status_code == 200
    assert len(resp.json()["itens"]) == 1

    slides = client.get("/api/musicas/1/slides").json()
    estado = {
        "liturgia_id": liturgia_id,
        "dia": "domingo",
        "item_index": 0,
        "titulo_item": "1 - Hino de Teste Um",
        "slides": slides,
        "slide_index": 0,
    }
    resp = client.post("/api/projecao/estado", json=estado)
    assert resp.status_code == 200
    assert resp.json()["total_slides"] == 3

    resp = client.post("/api/projecao/navegar", json={"direcao": "prox"})
    assert resp.status_code == 200
    assert resp.json()["slide_index"] == 1

    resp = client.get("/api/projecao/estado")
    assert resp.json()["slide_index"] == 1

    # último slide (capa + 2 letras = 3)
    assert client.post("/api/projecao/navegar", json={"direcao": "prox"}).json()["slide_index"] == 2
    assert client.post("/api/projecao/navegar", json={"direcao": "prox"}).status_code == 400


def test_reordenar_itens():
    client.post("/api/liturgias", json={"dia": "quarta", "titulo": "Culto"})
    item1 = {"ordem": 1, "tipo": "nota", "titulo_exibicao": "Item 1", "texto": "a"}
    item2 = {"ordem": 2, "tipo": "nota", "titulo_exibicao": "Item 2", "texto": "b"}
    client.post("/api/liturgias/quarta/itens", json=item1)
    resp = client.post("/api/liturgias/quarta/itens", json=item2)
    ids = [i["id"] for i in resp.json()["itens"]]

    resp = client.put("/api/liturgias/quarta/reordenar", json=list(reversed(ids)))
    assert resp.status_code == 200
    novos_titulos = [i["titulo_exibicao"] for i in resp.json()["itens"]]
    assert novos_titulos == ["Item 2", "Item 1"]
