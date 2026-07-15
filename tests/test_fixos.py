from fastapi.testclient import TestClient

from app.fixos import store
from app.fixos.store import MOMENTOS_PADRAO
from app.main import app

client = TestClient(app)


def test_comeca_com_os_momentos_padrao():
    dados = client.get("/api/fixos").json()
    assert [i["nome"] for i in dados["itens"]] == MOMENTOS_PADRAO
    # Momento existe mesmo sem hino escolhido — é o nome que identifica o item.
    assert all(i["ref_id"] is None for i in dados["itens"])


def test_renomear_e_atribuir_hino():
    lista = client.get("/api/fixos").json()
    lista["itens"][0]["nome"] = "Hino de Entrada"
    lista["itens"][0]["ref_id"] = 1
    lista["itens"][0]["titulo_exibicao"] = "1 - Hino de Teste Um"

    resp = client.put("/api/fixos", json=lista)
    assert resp.status_code == 200

    salvos = client.get("/api/fixos").json()["itens"]
    assert salvos[0]["nome"] == "Hino de Entrada"
    assert salvos[0]["ref_id"] == 1


def test_adicionar_e_remover_momento():
    resp = client.post("/api/fixos/itens", json={"nome": "Ceia", "ref_id": 2})
    itens = resp.json()["itens"]
    assert itens[-1]["nome"] == "Ceia"
    novo_id = itens[-1]["id"]

    restantes = client.delete(f"/api/fixos/itens/{novo_id}").json()["itens"]
    assert novo_id not in [i["id"] for i in restantes]
    assert len(restantes) == len(MOMENTOS_PADRAO)


def test_remover_inexistente():
    assert client.delete("/api/fixos/itens/nao-existe").status_code == 404


def test_origem_do_hino_chega_na_liturgia_da_semana():
    """O momento fixo é copiado para o dia, e o item de lá carrega a origem do hino."""
    fixo = client.post(
        "/api/fixos/itens",
        json={
            "nome": "Ceia",
            "origem": "hinario_1996",
            "ref_id": 2,
            "titulo_exibicao": "1 - Hino de Teste Dois",
        },
    ).json()["itens"][-1]
    assert fixo["origem"] == "hinario_1996"

    resp = client.post(
        "/api/liturgias/sexta/itens",
        json={
            "ordem": 0,
            "tipo": "hino",
            "origem": fixo["origem"],
            "ref_id": fixo["ref_id"],
            "titulo_exibicao": fixo["titulo_exibicao"],
        },
    )
    assert resp.status_code == 200
    assert resp.json()["itens"][-1]["origem"] == "hinario_1996"


def test_momento_com_video_em_vez_de_hino():
    itens = client.post(
        "/api/fixos/itens",
        json={"nome": "Louvor especial", "url_video": "https://youtu.be/abc123"},
    ).json()["itens"]
    assert itens[-1]["url_video"] == "https://youtu.be/abc123"
    assert itens[-1]["ref_id"] is None

    salvos = client.get("/api/fixos").json()["itens"]
    assert salvos[-1]["url_video"] == "https://youtu.be/abc123"


def test_momento_nao_aceita_hino_e_video_juntos():
    """São dois jeitos de preencher o mesmo espaço — ter os dois deixa ambíguo o que o momento toca."""
    resp = client.post(
        "/api/fixos/itens",
        json={"nome": "Ofertas", "ref_id": 1, "url_video": "https://youtu.be/abc123"},
    )
    assert resp.status_code == 422


def test_link_de_video_precisa_ser_navegavel():
    resp = client.post(
        "/api/fixos/itens",
        json={"nome": "Ofertas", "url_video": "youtube.com/watch?v=abc"},
    )
    assert resp.status_code == 422


def test_json_gravado_antes_da_origem_continua_carregando():
    store.FIXOS_PATH.write_text(
        '{"itens": [{"id": "fixo-728a4f8d", "ordem": 1, "nome": "Doxologia", "ref_id": 1810,'
        ' "titulo_exibicao": "73 - Castelo Forte"}],'
        ' "atualizado_em": "2026-07-14T13:23:53.802928"}',
        encoding="utf-8",
    )
    item = client.get("/api/fixos").json()["itens"][0]
    assert item["ref_id"] == 1810
    assert item["origem"] is None


def test_ordem_e_renumerada_ao_salvar():
    lista = client.get("/api/fixos").json()
    lista["itens"] = list(reversed(lista["itens"]))
    itens = client.put("/api/fixos", json=lista).json()["itens"]
    assert [i["ordem"] for i in itens] == [1, 2, 3]
    assert itens[0]["nome"] == MOMENTOS_PADRAO[-1]
