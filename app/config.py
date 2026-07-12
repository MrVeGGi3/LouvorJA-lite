import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DATA_DIR = Path(
    os.environ.get("LOUVORJA_LITE_DATA_DIR", PROJECT_ROOT / "data")
).expanduser().resolve()

DB_PATH = DATA_DIR / "database.db"
CAPAS_DIR = DATA_DIR / "capas"
IMAGENS_DIR = DATA_DIR / "imagens"
LITURGIAS_DIR = DATA_DIR / "liturgias"
PROJECAO_STATE_PATH = DATA_DIR / "projecao_estado.json"

DEFAULT_SOURCE_DIR = Path(
    os.environ.get("LOUVORJA_CONFIG_DIR", "~/.local/share/LouvorJA/config")
).expanduser()
