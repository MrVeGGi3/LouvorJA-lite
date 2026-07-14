from datetime import datetime
from pathlib import Path

from app.config import FIXOS_PATH
from app.fixos.models import HinoFixo, ListaFixos

# Os momentos que quase toda igreja tem. Servem só de ponto de partida: dá para renomear,
# remover e acrescentar à vontade.
MOMENTOS_PADRAO = ["Doxologia", "Oração Intercessória", "Ofertas"]


def _write_atomic(path: Path, conteudo: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(conteudo, encoding="utf-8")
    tmp.replace(path)


def _padrao() -> ListaFixos:
    return ListaFixos(
        itens=[HinoFixo(ordem=i, nome=nome) for i, nome in enumerate(MOMENTOS_PADRAO, start=1)]
    )


def salvar(lista: ListaFixos) -> ListaFixos:
    for idx, item in enumerate(lista.itens, start=1):
        item.ordem = idx
    lista.atualizado_em = datetime.now()
    _write_atomic(FIXOS_PATH, lista.model_dump_json(indent=2))
    return lista


def carregar() -> ListaFixos:
    if not FIXOS_PATH.exists():
        return _padrao()
    return ListaFixos.model_validate_json(FIXOS_PATH.read_text(encoding="utf-8"))
