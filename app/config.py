import json
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

CONGELADO = getattr(sys, "frozen", False)

# A escolha da pasta de dados mora fora dela — se morasse dentro, seria preciso saber onde ela
# está para descobrir onde ela está.
CONFIG_PATH = (
    Path(os.environ.get("XDG_CONFIG_HOME", "~/.config")).expanduser() / "louvorja-lite" / "config.json"
)


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


def data_dir_portatil() -> Path | None:
    """O `data/` ao lado do executável — o modo pendrive. `None` quando rodando do código-fonte."""
    if not CONGELADO:
        return None
    return _dir_do_executavel() / "data"


def data_dir_pessoal() -> Path:
    return Path("~/.local/share/louvorja-lite").expanduser().resolve()


def ler_config() -> dict:
    if not CONFIG_PATH.exists():
        return {}
    try:
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        # Config ilegível não pode impedir o app de abrir: cai nos padrões e o usuário reescolhe.
        return {}


def gravar_data_dir(caminho: Path) -> None:
    """Fixa a pasta de dados escolhida pelo usuário na primeira execução."""
    dados = ler_config()
    dados["data_dir"] = str(caminho)
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = CONFIG_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(dados, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(CONFIG_PATH)


def _resolver_data_dir() -> Path:
    if (definido := os.environ.get("LOUVORJA_LITE_DATA_DIR")):
        return Path(definido).expanduser().resolve()

    if CONGELADO:
        # A escolha do usuário só vale para o app instalado. Rodando do código-fonte, `data/` do
        # repositório continua sendo a resposta óbvia — senão um config gravado ao testar o
        # AppImage sequestraria silenciosamente o ambiente de desenvolvimento.
        if (escolhido := ler_config().get("data_dir")):
            return Path(escolhido).expanduser().resolve()

        # Modo portátil: `data/` ao lado do executável (o cenário do pendrive) tem precedência.
        portatil = data_dir_portatil()
        if portatil is not None and portatil.is_dir():
            return portatil
        return data_dir_pessoal()

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
