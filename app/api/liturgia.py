from fastapi import APIRouter, Body, HTTPException
from pydantic import BaseModel

from app.liturgia import store
from app.liturgia.models import DIAS, ItemLiturgia, Liturgia, rotulo_dia

router = APIRouter(prefix="/api/liturgias", tags=["liturgia"])


class AtualizarTitulo(BaseModel):
    titulo: str


def _validar_dia(dia: str) -> None:
    if dia not in DIAS:
        raise HTTPException(status_code=404, detail="Dia da semana inválido")


@router.get("")
def listar():
    return [l.model_dump(mode="json") for l in store.listar()]


@router.get("/{dia}")
def detalhe(dia: str):
    _validar_dia(dia)
    liturgia = store.carregar(dia)
    if liturgia is None:
        raise HTTPException(status_code=404, detail="Liturgia não encontrada")
    return liturgia.model_dump(mode="json")


@router.post("")
def criar(liturgia: Liturgia):
    if store.carregar(liturgia.dia) is not None:
        raise HTTPException(status_code=409, detail="Já existe liturgia para esse dia")
    store.salvar(liturgia)
    return liturgia.model_dump(mode="json")


@router.put("/{dia}")
def atualizar_titulo(dia: str, corpo: AtualizarTitulo):
    _validar_dia(dia)
    liturgia = store.carregar(dia)
    if liturgia is None:
        raise HTTPException(status_code=404, detail="Liturgia não encontrada")
    liturgia.titulo = corpo.titulo
    store.salvar(liturgia)
    return liturgia.model_dump(mode="json")


@router.delete("/{dia}")
def remover(dia: str):
    _validar_dia(dia)
    if not store.remover(dia):
        raise HTTPException(status_code=404, detail="Liturgia não encontrada")
    return {"status": "ok"}


@router.post("/{dia}/itens")
def adicionar_item(dia: str, item: ItemLiturgia):
    _validar_dia(dia)
    liturgia = store.carregar(dia)
    if liturgia is None:
        liturgia = Liturgia(dia=dia, titulo=f"Liturgia de {rotulo_dia(dia)}")
    item.ordem = len(liturgia.itens) + 1
    liturgia.itens.append(item)
    store.salvar(liturgia)
    return liturgia.model_dump(mode="json")


@router.put("/{dia}/itens/{item_id}")
def editar_item(dia: str, item_id: str, item: ItemLiturgia):
    _validar_dia(dia)
    liturgia = store.carregar(dia)
    if liturgia is None:
        raise HTTPException(status_code=404, detail="Liturgia não encontrada")
    for i, existente in enumerate(liturgia.itens):
        if existente.id == item_id:
            item.id = item_id
            liturgia.itens[i] = item
            store.salvar(liturgia)
            return liturgia.model_dump(mode="json")
    raise HTTPException(status_code=404, detail="Item não encontrado")


@router.delete("/{dia}/itens/{item_id}")
def remover_item(dia: str, item_id: str):
    _validar_dia(dia)
    liturgia = store.carregar(dia)
    if liturgia is None:
        raise HTTPException(status_code=404, detail="Liturgia não encontrada")
    liturgia.itens = [i for i in liturgia.itens if i.id != item_id]
    for idx, item in enumerate(liturgia.itens, start=1):
        item.ordem = idx
    store.salvar(liturgia)
    return liturgia.model_dump(mode="json")


@router.put("/{dia}/reordenar")
def reordenar(dia: str, ordem_ids: list[str] = Body(...)):
    _validar_dia(dia)
    liturgia = store.carregar(dia)
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
