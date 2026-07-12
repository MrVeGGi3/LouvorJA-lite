from datetime import date, datetime
from pathlib import Path
from typing import Optional

from app.config import LITURGIAS_DIR
from app.liturgia.models import Liturgia


def _path_for(week_of: date) -> Path:
    return LITURGIAS_DIR / f"{week_of.isoformat()}.json"


def _write_atomic(path: Path, conteudo: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(conteudo, encoding="utf-8")
    tmp.replace(path)


def salvar(liturgia: Liturgia) -> None:
    liturgia.atualizado_em = datetime.now()
    _write_atomic(_path_for(liturgia.week_of), liturgia.model_dump_json(indent=2))


def carregar(week_of: date) -> Optional[Liturgia]:
    path = _path_for(week_of)
    if not path.exists():
        return None
    return Liturgia.model_validate_json(path.read_text(encoding="utf-8"))


def remover(week_of: date) -> bool:
    path = _path_for(week_of)
    if not path.exists():
        return False
    path.unlink()
    return True


def listar() -> list[Liturgia]:
    if not LITURGIAS_DIR.exists():
        return []
    return [
        Liturgia.model_validate_json(f.read_text(encoding="utf-8"))
        for f in sorted(LITURGIAS_DIR.glob("*.json"))
    ]
