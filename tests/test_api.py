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


def test_adicionar_video_a_liturgia():
    client.post("/api/liturgias", json={"dia": "terca", "titulo": "Culto"})
    item = {
        "ordem": 1, "tipo": "video", "titulo_exibicao": "",
        "descricao": "Louvor especial", "url_video": "https://youtu.be/abc123",
    }
    resp = client.post("/api/liturgias/terca/itens", json=item)
    assert resp.status_code == 200

    salvo = resp.json()["itens"][0]
    assert salvo["tipo"] == "video"
    assert salvo["url_video"] == "https://youtu.be/abc123"
    assert salvo["descricao"] == "Louvor especial"
    assert salvo["ref_id"] is None


def test_momento_sem_hino_recebe_e_devolve_o_hino():
    """O momento nasce só com o nome, ganha um hino e volta a ser nota pelo "⌫"."""
    client.post("/api/liturgias", json={"dia": "sabado", "titulo": "Culto"})
    nota = {"ordem": 0, "tipo": "nota", "titulo_exibicao": "", "descricao": ""}
    item = client.post("/api/liturgias/sabado/itens", json=nota).json()["itens"][0]
    assert item["tipo"] == "nota"

    url = f"/api/liturgias/sabado/itens/{item['id']}"
    cheio = {**item, "tipo": "hino", "origem": "hinario", "ref_id": 1,
             "titulo_exibicao": "1 - Hino de Teste Um", "descricao": "Ofertas"}
    assert client.put(url, json=cheio).json()["itens"][0]["ref_id"] == 1

    # Esvaziar mantém a descrição e o lugar na ordem — só o hino sai.
    vazio = {**cheio, "tipo": "nota", "origem": None, "ref_id": None, "titulo_exibicao": ""}
    voltou = client.put(url, json=vazio).json()["itens"][0]
    assert voltou["tipo"] == "nota"
    assert voltou["ref_id"] is None
    assert voltou["descricao"] == "Ofertas"
    assert voltou["ordem"] == 1


def test_item_nao_aceita_hino_e_video_juntos():
    client.post("/api/liturgias", json={"dia": "quinta", "titulo": "Culto"})
    item = {
        "ordem": 1, "tipo": "video", "ref_id": 1, "titulo_exibicao": "1 - Hino",
        "url_video": "https://youtu.be/abc123",
    }
    assert client.post("/api/liturgias/quinta/itens", json=item).status_code == 422


def test_editar_item_guarda_descricao():
    client.post("/api/liturgias", json={"dia": "segunda", "titulo": "Culto"})
    item = {"ordem": 1, "tipo": "hino", "origem": "hinario", "ref_id": 1,
            "titulo_exibicao": "1 - Hino de Teste Um"}
    item_id = client.post("/api/liturgias/segunda/itens", json=item).json()["itens"][0]["id"]

    resp = client.put(
        f"/api/liturgias/segunda/itens/{item_id}", json={**item, "descricao": "Doxologia"}
    )
    assert resp.status_code == 200
    assert resp.json()["itens"][0]["descricao"] == "Doxologia"

    # A descrição precisa sobreviver ao disco, não só à resposta.
    assert client.get("/api/liturgias/segunda").json()["itens"][0]["descricao"] == "Doxologia"


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
