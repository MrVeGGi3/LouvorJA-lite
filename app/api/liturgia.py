from datetime import date

from fastapi import APIRouter, Body, HTTPException
from pydantic import BaseModel

from app.liturgia import store
from app.liturgia.models import ItemLiturgia, Liturgia

router = APIRouter(prefix="/api/liturgias", tags=["liturgia"])


class AtualizarTitulo(BaseModel):
    titulo: str


@router.get("")
def listar():
    return [l.model_dump(mode="json") for l in store.listar()]


@router.get("/{week_of}")
def detalhe(week_of: date):
    liturgia = store.carregar(week_of)
    if liturgia is None:
        raise HTTPException(status_code=404, detail="Liturgia não encontrada")
    return liturgia.model_dump(mode="json")


@router.post("")
def criar(liturgia: Liturgia):
    if store.carregar(liturgia.week_of) is not None:
        raise HTTPException(status_code=409, detail="Já existe liturgia para essa semana")
    store.salvar(liturgia)
    return liturgia.model_dump(mode="json")


@router.put("/{week_of}")
def atualizar_titulo(week_of: date, corpo: AtualizarTitulo):
    liturgia = store.carregar(week_of)
    if liturgia is None:
        raise HTTPException(status_code=404, detail="Liturgia não encontrada")
    liturgia.titulo = corpo.titulo
    store.salvar(liturgia)
    return liturgia.model_dump(mode="json")


@router.delete("/{week_of}")
def remover(week_of: date):
    if not store.remover(week_of):
        raise HTTPException(status_code=404, detail="Liturgia não encontrada")
    return {"status": "ok"}


@router.post("/{week_of}/itens")
def adicionar_item(week_of: date, item: ItemLiturgia):
    liturgia = store.carregar(week_of)
    if liturgia is None:
        liturgia = Liturgia(week_of=week_of, titulo=f"Culto de {week_of.isoformat()}")
    item.ordem = len(liturgia.itens) + 1
    liturgia.itens.append(item)
    store.salvar(liturgia)
    return liturgia.model_dump(mode="json")


@router.put("/{week_of}/itens/{item_id}")
def editar_item(week_of: date, item_id: str, item: ItemLiturgia):
    liturgia = store.carregar(week_of)
    if liturgia is None:
        raise HTTPException(status_code=404, detail="Liturgia não encontrada")
    for i, existente in enumerate(liturgia.itens):
        if existente.id == item_id:
            item.id = item_id
            liturgia.itens[i] = item
            store.salvar(liturgia)
            return liturgia.model_dump(mode="json")
    raise HTTPException(status_code=404, detail="Item não encontrado")


@router.delete("/{week_of}/itens/{item_id}")
def remover_item(week_of: date, item_id: str):
    liturgia = store.carregar(week_of)
    if liturgia is None:
        raise HTTPException(status_code=404, detail="Liturgia não encontrada")
    liturgia.itens = [i for i in liturgia.itens if i.id != item_id]
    for idx, item in enumerate(liturgia.itens, start=1):
        item.ordem = idx
    store.salvar(liturgia)
    return liturgia.model_dump(mode="json")


@router.put("/{week_of}/reordenar")
def reordenar(week_of: date, ordem_ids: list[str] = Body(...)):
    liturgia = store.carregar(week_of)
    if liturgia is None:
        raise HTTPException(status_code=404, detail="Liturgia não encontrada")
    por_id = {item.id: item for item in liturgia.itens}
    if set(ordem_ids) != set(por_id.keys()):
        raise HTTPException(status_code=400, detail="Lista de IDs não bate com os itens existentes")
    novos = []
    for idx, item_id in enumerate(ordem_ids, start=1):
        item = por_id[item_id]
        item.ordem = idx
        novos.append(item)
    liturgia.itens = novos
    store.salvar(liturgia)
    return liturgia.model_dump(mode="json")
