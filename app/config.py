import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

CONGELADO = getattr(sys, "frozen", False)


def _dir_do_executavel() -> Path:
    """Pasta onde o executável de fato está, do ponto de vista do usuário.

    Dentro de um AppImage, `sys.executable` aponta para o mount temporário somente-leitura
    (`/tmp/.mount_XXXX/...`), não para o arquivo `.AppImage` que a pessoa clicou. Quem sabe o
    caminho real é a variável APPIMAGE — e é o vizinho *dela* que interessa, porque é lá (no
    pendrive) que fica a pasta `data/`.
    """
    appimage = os.environ.get("APPIMAGE")
    if appimage:
        return Path(appimage).resolve().parent
    return Path(sys.executable).resolve().parent


def _resolver_data_dir() -> Path:
    if (definido := os.environ.get("LOUVORJA_LITE_DATA_DIR")):
        return Path(definido).expanduser().resolve()

    if CONGELADO:
        # Modo portátil: `data/` ao lado do executável (o cenário do pendrive) tem precedência.
        portatil = _dir_do_executavel() / "data"
        if portatil.is_dir():
            return portatil
        return Path("~/.local/share/louvorja-lite").expanduser().resolve()

    return (PROJECT_ROOT / "data").resolve()


def resource_path(*partes: str) -> Path:
    """Caminho de um asset embutido no bundle (somente leitura), como app/static."""
    base = Path(getattr(sys, "_MEIPASS", PROJECT_ROOT))
    return base.joinpath(*partes)


DATA_DIR = _resolver_data_dir()

DB_PATH = DATA_DIR / "database.db"
CAPAS_DIR = DATA_DIR / "capas"
IMAGENS_DIR = DATA_DIR / "imagens"
MUSICAS_DIR = DATA_DIR / "musicas"
LITURGIAS_DIR = DATA_DIR / "liturgias"
FIXOS_PATH = DATA_DIR / "fixos.json"
PROJECAO_STATE_PATH = DATA_DIR / "projecao_estado.json"

DEFAULT_SOURCE_DIR = Path(
    os.environ.get("LOUVORJA_CONFIG_DIR", "~/.local/share/LouvorJA/config")
).expanduser()
