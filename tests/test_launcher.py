import pytest

from app import launcher


@pytest.fixture
def sem_efeitos(monkeypatch):
    """Registra o que o main() faria, sem abrir navegador nem subir servidor."""
    chamadas = {"navegador": [], "uvicorn": []}
    monkeypatch.delenv("LOUVORJA_LITE_PORT", raising=False)
    monkeypatch.setattr(launcher, "abrir_navegador", lambda url: chamadas["navegador"].append(url))
    monkeypatch.setattr(launcher.threading, "Thread", _ThreadImediata)
    monkeypatch.setattr(
        launcher.uvicorn, "run", lambda app, host, port, **kw: chamadas["uvicorn"].append(port)
    )
    return chamadas


class _ThreadImediata:
    def __init__(self, target, args=(), daemon=None):
        self._alvo, self._args = target, args

    def start(self):
        self._alvo(*self._args)


def test_instancia_aberta_so_abre_o_navegador(monkeypatch, sem_efeitos):
    monkeypatch.setattr(launcher, "_livre", lambda porta: porta != 8000)
    monkeypatch.setattr(launcher, "instancia_aberta", lambda porta: True)

    launcher.main()

    assert sem_efeitos["uvicorn"] == []
    assert sem_efeitos["navegador"] == ["http://127.0.0.1:8000/controle"]


def test_porta_ocupada_por_outro_programa_segue_para_a_proxima(monkeypatch, sem_efeitos):
    monkeypatch.setattr(launcher, "_livre", lambda porta: porta != 8000)
    monkeypatch.setattr(launcher, "instancia_aberta", lambda porta: False)

    launcher.main()

    assert sem_efeitos["uvicorn"] == [8001]


def test_relancamento_nao_procura_instancia(monkeypatch, sem_efeitos):
    monkeypatch.setenv("LOUVORJA_LITE_PORT", "8000")
    monkeypatch.setattr(launcher, "_livre", lambda porta: True)

    def nao_deveria_checar(porta):
        raise AssertionError("o relançamento não deve procurar outra instância")

    monkeypatch.setattr(launcher, "instancia_aberta", nao_deveria_checar)

    launcher.main()

    assert sem_efeitos["uvicorn"] == [8000]


def test_porta_sem_ninguem_nao_e_instancia():
    assert launcher.instancia_aberta(1) is False
