import json

from app.liturgia import store
from app.liturgia.models import ItemLiturgia, Liturgia


def test_salvar_e_carregar_liturgia():
    liturgia = Liturgia(
        dia="sabado",
        titulo="Culto de Sábado",
        itens=[
            ItemLiturgia(
                ordem=1, tipo="hino", origem="hinario",
                ref_id=1, titulo_exibicao="1 - Hino de Teste Um",
            )
        ],
    )
    store.salvar(liturgia)

    carregada = store.carregar("sabado")
    assert carregada is not None
    assert carregada.titulo == "Culto de Sábado"
    assert len(carregada.itens) == 1
    assert carregada.itens[0].ref_id == 1


def test_json_gravado_antes_da_descricao_continua_carregando():
    liturgia = Liturgia(dia="sexta", titulo="Culto")
    store.salvar(liturgia)

    # Reescreve o arquivo como ele era antes de `descricao`/`url_video` existirem.
    caminho = store._path_for("sexta")
    dados = json.loads(caminho.read_text(encoding="utf-8"))
    dados["itens"] = [
        {"id": "item-antigo", "ordem": 1, "tipo": "hino", "origem": "hinario",
         "ref_id": 1, "titulo_exibicao": "1 - Hino de Teste Um", "observacao": ""}
    ]
    caminho.write_text(json.dumps(dados), encoding="utf-8")

    item = store.carregar("sexta").itens[0]
    assert item.descricao == ""
    assert item.url_video is None


def test_carregar_inexistente_retorna_none():
    assert store.carregar("domingo") is None


def test_listar_inclui_liturgias_salvas():
    store.salvar(Liturgia(dia="sabado", titulo="A"))
    store.salvar(Liturgia(dia="domingo", titulo="B"))
    dias = {l.dia for l in store.listar()}
    assert "sabado" in dias
    assert "domingo" in dias


def test_remover_liturgia():
    store.salvar(Liturgia(dia="quarta", titulo="C"))
    assert store.remover("quarta") is True
    assert store.carregar("quarta") is None
    assert store.remover("quarta") is False
