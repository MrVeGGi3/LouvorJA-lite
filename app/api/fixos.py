from fastapi import APIRouter, HTTPException

from app.fixos import store
from app.fixos.models import HinoFixo, ListaFixos

router = APIRouter(prefix="/api/fixos", tags=["fixos"])


@router.get("")
def listar():
    return store.carregar().model_dump(mode="json")


@router.put("")
def substituir(lista: ListaFixos):
    """Grava a lista inteira — é por aqui que renomear, reordenar e trocar o hino passam."""
    return store.salvar(lista).model_dump(mode="json")


@router.post("/itens")
def adicionar(item: HinoFixo):
    lista = store.carregar()
    lista.itens.append(item)
    return store.salvar(lista).model_dump(mode="json")


@router.delete("/itens/{item_id}")
def remover(item_id: str):
    lista = store.carregar()
    restantes = [i for i in lista.itens if i.id != item_id]
    if len(restantes) == len(lista.itens):
        raise HTTPException(status_code=404, detail="Item fixo não encontrado")
    lista.itens = restantes
    return store.salvar(lista).model_dump(mode="json")
