from fastapi.testclient import TestClient

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


def test_ordem_e_renumerada_ao_salvar():
    lista = client.get("/api/fixos").json()
    lista["itens"] = list(reversed(lista["itens"]))
    itens = client.put("/api/fixos", json=lista).json()["itens"]
    assert [i["ordem"] for i in itens] == [1, 2, 3]
    assert itens[0]["nome"] == MOMENTOS_PADRAO[-1]
