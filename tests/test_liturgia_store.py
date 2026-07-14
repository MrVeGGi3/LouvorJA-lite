from datetime import date

from app.liturgia import store
from app.liturgia.models import ItemLiturgia, Liturgia


def test_salvar_e_carregar_liturgia():
    liturgia = Liturgia(
        week_of=date(2026, 7, 12),
        titulo="Culto de Sábado",
        itens=[
            ItemLiturgia(
                ordem=1, tipo="hino", origem="hinario",
                ref_id=1, titulo_exibicao="1 - Hino de Teste Um",
            )
        ],
    )
    store.salvar(liturgia)

    carregada = store.carregar(date(2026, 7, 12))
    assert carregada is not None
    assert carregada.titulo == "Culto de Sábado"
    assert len(carregada.itens) == 1
    assert carregada.itens[0].ref_id == 1


def test_carregar_inexistente_retorna_none():
    assert store.carregar(date(2099, 1, 1)) is None


def test_listar_inclui_liturgias_salvas():
    store.salvar(Liturgia(week_of=date(2026, 7, 12), titulo="A"))
    store.salvar(Liturgia(week_of=date(2026, 7, 19), titulo="B"))
    semanas = {l.week_of for l in store.listar()}
    assert date(2026, 7, 12) in semanas
    assert date(2026, 7, 19) in semanas


def test_remover_liturgia():
    store.salvar(Liturgia(week_of=date(2026, 8, 1), titulo="C"))
    assert store.remover(date(2026, 8, 1)) is True
    assert store.carregar(date(2026, 8, 1)) is None
    assert store.remover(date(2026, 8, 1)) is False
