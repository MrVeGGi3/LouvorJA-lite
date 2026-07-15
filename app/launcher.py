"""Ponto de entrada do executável: sobe o servidor local e abre o navegador na tela de controle."""

import shutil
import socket
import sys
import threading
import time
import webbrowser

import uvicorn

from app.config import DATA_DIR, DB_PATH
from app.main import app

HOST = "127.0.0.1"
PORTA_PADRAO = 8000
TENTATIVAS = 20

# A colocação automática da projeção no monitor externo usa a Window Management API, que só existe
# em navegadores Chromium. Por isso preferimos abrir num deles; se nenhum estiver instalado, cai no
# navegador padrão do sistema (onde a projeção abre em janela normal, pra arrastar até o telão).
NAVEGADORES_CHROMIUM = [
    "google-chrome",
    "google-chrome-stable",
    "chromium",
    "chromium-browser",
    "microsoft-edge",
    "microsoft-edge-stable",
    "brave-browser",
    "vivaldi-stable",
]


def _livre(porta: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind((HOST, porta))
            return True
        except OSError:
            return False


def porta_livre() -> int:
    """Mesma porta sempre que possível.

    Sortear uma porta a cada abertura faz a URL da projeção mudar toda vez, e aí a janela que
    está no telão (ou o favorito do operador) quebra assim que o app reinicia. Uma porta estável
    mantém o mesmo endereço entre execuções; só se ela estiver ocupada é que andamos para a
    seguinte.
    """
    for porta in range(PORTA_PADRAO, PORTA_PADRAO + TENTATIVAS):
        if _livre(porta):
            return porta

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, 0))
        return s.getsockname()[1]


def _navegador_preferido() -> "webbrowser.BaseBrowser | None":
    for nome in NAVEGADORES_CHROMIUM:
        caminho = shutil.which(nome)
        if caminho:
            return webbrowser.BackgroundBrowser(caminho)
    return None


def abrir_navegador(url: str) -> None:
    # Dá um instante para o uvicorn começar a aceitar conexões antes de o navegador bater na porta.
    time.sleep(1.0)
    navegador = _navegador_preferido()
    try:
        if navegador is not None:
            navegador.open(url)
        else:
            webbrowser.open(url)
    except Exception:
        # Qualquer falha ao abrir o Chromium escolhido: cai no navegador padrão do sistema.
        webbrowser.open(url)


def main() -> None:
    if not DB_PATH.exists():
        print(f"database.db não encontrado em {DB_PATH}.", file=sys.stderr)
        print(
            "Coloque a pasta 'data/' ao lado do executável, ou aponte a variável "
            "LOUVORJA_LITE_DATA_DIR para ela.",
            file=sys.stderr,
        )
        raise SystemExit(1)

    porta = porta_livre()
    url = f"http://{HOST}:{porta}/controle"

    # flush explícito: congelado e com a saída redirecionada, o buffer do stdout só seria
    # descarregado no fim, e quem abre pelo terminal nunca veria o endereço.
    print(f"LouvorJA Lite — dados em {DATA_DIR}", flush=True)
    print(f"Controle:  {url}", flush=True)
    print(f"Projeção:  http://{HOST}:{porta}/projecao", flush=True)
    print("Feche esta janela para encerrar.", flush=True)

    threading.Thread(target=abrir_navegador, args=(url,), daemon=True).start()

    # Passar o objeto `app` (e não a string "app.main:app"): congelado, não há import por string.
    uvicorn.run(app, host=HOST, port=porta, log_level="warning")


if __name__ == "__main__":
    main()
