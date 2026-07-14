import asyncio
from typing import Literal

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.config import PROJECAO_STATE_PATH
from app.projecao.state import EstadoProjecao, carregar_estado, salvar_estado

router = APIRouter(prefix="/api/projecao", tags=["projecao"])

INTERVALO_STREAM = 0.1


class NavegarRequest(BaseModel):
    direcao: Literal["prox", "ant"]


class SlideRequest(BaseModel):
    slide_index: int


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


@router.post("/slide")
def ir_para_slide(req: SlideRequest):
    """Salta direto para um slide. É por aqui que o áudio conduz a projeção.

    Separado de /navegar para o auto-advance não precisar reenviar os slides todos a cada virada.
    """
    atual = carregar_estado()
    if not (0 <= req.slide_index < max(atual.total_slides, 1)):
        raise HTTPException(status_code=400, detail="Fora do intervalo de slides")
    atual.slide_index = req.slide_index
    salvar_estado(atual)
    return atual.model_dump(mode="json")


@router.post("/parar")
def parar():
    vazio = EstadoProjecao()
    salvar_estado(vazio)
    return vazio.model_dump(mode="json")


@router.get("/stream")
async def stream():
    """Empurra o estado para a projeção assim que ele muda.

    O polling de 500 ms da projeção é imperceptível num clique, mas atrasa demais a virada de
    slide sincronizada com o áudio. A projeção mantém o polling como plano B se o SSE cair.
    """

    async def eventos():
        ultimo_mtime = None
        while True:
            try:
                mtime = PROJECAO_STATE_PATH.stat().st_mtime if PROJECAO_STATE_PATH.exists() else 0
            except OSError:
                mtime = 0

            if mtime != ultimo_mtime:
                ultimo_mtime = mtime
                yield f"data: {carregar_estado().model_dump_json()}\n\n"

            await asyncio.sleep(INTERVALO_STREAM)

    return StreamingResponse(
        eventos(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
