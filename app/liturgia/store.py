from datetime import datetime
from pathlib import Path
from typing import Optional

from app.config import LITURGIAS_DIR
from app.liturgia.models import DIAS, Liturgia


def _path_for(dia: str) -> Path:
    return LITURGIAS_DIR / f"{dia}.json"


def _write_atomic(path: Path, conteudo: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(conteudo, encoding="utf-8")
    tmp.replace(path)


def salvar(liturgia: Liturgia) -> None:
    liturgia.atualizado_em = datetime.now()
    _write_atomic(_path_for(liturgia.dia), liturgia.model_dump_json(indent=2))


def carregar(dia: str) -> Optional[Liturgia]:
    path = _path_for(dia)
    if not path.exists():
        return None
    return Liturgia.model_validate_json(path.read_text(encoding="utf-8"))


def remover(dia: str) -> bool:
    path = _path_for(dia)
    if not path.exists():
        return False
    path.unlink()
    return True


def listar() -> list[Liturgia]:
    if not LITURGIAS_DIR.exists():
        return []
    liturgias = [
        Liturgia.model_validate_json(_path_for(dia).read_text(encoding="utf-8"))
        for dia in DIAS
        if _path_for(dia).exists()
    ]
    return liturgias
