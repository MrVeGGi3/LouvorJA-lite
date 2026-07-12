from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.projecao.state import EstadoProjecao, carregar_estado, salvar_estado

router = APIRouter(prefix="/api/projecao", tags=["projecao"])


class NavegarRequest(BaseModel):
    direcao: Literal["prox", "ant"]


@router.get("/estado")
def estado():
    return carregar_estado().model_dump(mode="json")


@router.post("/estado")
def definir_estado(novo: EstadoProjecao):
    salvar_estado(novo)
    return novo.model_dump(mode="json")


@router.post("/navegar")
def navegar(req: NavegarRequest):
    atual = carregar_estado()
    novo_index = atual.slide_index + (1 if req.direcao == "prox" else -1)
    if not (0 <= novo_index < max(atual.total_slides, 1)):
        raise HTTPException(status_code=400, detail="Fora do intervalo de slides")
    atual.slide_index = novo_index
    salvar_estado(atual)
    return atual.model_dump(mode="json")


@router.post("/parar")
def parar():
    vazio = EstadoProjecao()
    salvar_estado(vazio)
    return vazio.model_dump(mode="json")
