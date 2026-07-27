"""Download do catálogo e da mídia pela interface.

Nenhuma rota aqui depende de `get_db`: elas precisam funcionar justamente quando não existe banco
nenhum, que é o estado de quem acabou de abrir o AppImage pela primeira vez.
"""

import asyncio
import json
import os
import shutil
import sys
import threading
from pathlib import Path

from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app import config
from app.sync import midia
from app.sync.gerenciador import JaEmAndamento, gerenciador

router = APIRouter(prefix="/api/atualizacao", tags=["atualizacao"])

INTERVALO_STREAM = 0.5


class MidiaRequest(BaseModel):
    album: int | None = None
    only: str = "all"
    escopo: str = ""


class LocalRequest(BaseModel):
    caminho: str


def _gravavel(pasta: Path) -> bool:
    """A pasta aceita escrita? Um pendrive montado somente-leitura não aceita."""
    alvo = pasta
    while not alvo.exists() and alvo.parent != alvo:
        alvo = alvo.parent
    return os.access(alvo, os.W_OK)


def _espaco_livre(pasta: Path) -> int:
    alvo = pasta
    while not alvo.exists() and alvo.parent != alvo:
        alvo = alvo.parent
    try:
        return shutil.disk_usage(alvo).free
    except OSError:
        return 0


@router.get("/status")
def status():
    dest = config.DATA_DIR
    db_path = config.DB_PATH
    resumo = midia.resumo(db_path, dest)

    return {
        "banco": {
            "presente": db_path.exists(),
            "caminho": str(db_path),
            "atualizado_em": db_path.stat().st_mtime if db_path.exists() else None,
        },
        "data_dir": str(dest),
        "gravavel": _gravavel(dest),
        "espaco_livre": _espaco_livre(dest),
        "album_hinario": midia.ALBUM_HINARIO,
        **resumo,
        "job": gerenciador.snapshot(),
    }


@router.post("/banco", status_code=202)
def baixar_banco():
    try:
        gerenciador.iniciar_banco()
    except JaEmAndamento as erro:
        raise HTTPException(status_code=409, detail=str(erro)) from erro
    return gerenciador.snapshot()


@router.post("/midia", status_code=202)
def baixar_midia(req: MidiaRequest):
    if not config.DB_PATH.exists():
        raise HTTPException(
            status_code=409, detail="Baixe o catálogo de hinos antes de baixar as músicas."
        )
    if req.only not in ("music", "image", "all"):
        raise HTTPException(status_code=422, detail="only deve ser music, image ou all")
    try:
        gerenciador.iniciar_midia(req.album, req.only, req.escopo)
    except JaEmAndamento as erro:
        raise HTTPException(status_code=409, detail=str(erro)) from erro
    return gerenciador.snapshot()


@router.post("/arquivo/{id_file}", status_code=202)
def baixar_arquivo(id_file: int):
    if not config.DB_PATH.exists():
        raise HTTPException(status_code=409, detail="Baixe o catálogo de hinos primeiro.")
    try:
        gerenciador.iniciar_arquivo(id_file)
    except JaEmAndamento as erro:
        raise HTTPException(status_code=409, detail=str(erro)) from erro
    return gerenciador.snapshot()


@router.post("/cancelar", status_code=204)
def cancelar():
    gerenciador.cancelar()
    return Response(status_code=204)


@router.get("/stream")
async def stream():
    """Empurra o progresso para a tela. A tela mantém polling como plano B se o SSE cair."""

    async def eventos():
        ultima_versao = None
        while True:
            atual = gerenciador.snapshot()
            if atual["versao"] != ultima_versao:
                ultima_versao = atual["versao"]
                yield f"data: {json.dumps(atual, ensure_ascii=False)}\n\n"
            await asyncio.sleep(INTERVALO_STREAM)

    return StreamingResponse(
        eventos(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ---------------------------------------------------------------------------
# Onde guardar os dados (primeira execução)
# ---------------------------------------------------------------------------


@router.get("/local")
def local():
    """As opções de pasta oferecidas na primeira execução, e qual está em uso."""
    opcoes = []
    portatil = config.data_dir_portatil()
    if portatil is not None:
        opcoes.append({
            "chave": "portatil",
            "caminho": str(portatil),
            "rotulo": "Ao lado do programa (pendrive)",
            "ajuda": "Leva os hinos junto de um computador para outro.",
            "gravavel": _gravavel(portatil),
            "espaco_livre": _espaco_livre(portatil),
        })
    pessoal = config.data_dir_pessoal()
    opcoes.append({
        "chave": "pessoal",
        "caminho": str(pessoal),
        "rotulo": "Na minha pasta pessoal",
        "ajuda": "Fica neste computador.",
        "gravavel": _gravavel(pessoal),
        "espaco_livre": _espaco_livre(pessoal),
    })

    return {
        "atual": str(config.DATA_DIR),
        "fixado_por_variavel": bool(os.environ.get("LOUVORJA_LITE_DATA_DIR")),
        "opcoes": opcoes,
    }


@router.post("/local")
def definir_local(req: LocalRequest):
    if os.environ.get("LOUVORJA_LITE_DATA_DIR"):
        raise HTTPException(
            status_code=409,
            detail="A pasta está fixada pela variável LOUVORJA_LITE_DATA_DIR.",
        )

    escolhido = Path(req.caminho).expanduser()
    try:
        escolhido.mkdir(parents=True, exist_ok=True)
    except OSError as erro:
        raise HTTPException(status_code=400, detail=f"Não consegui criar {escolhido}: {erro}") from erro
    if not _gravavel(escolhido):
        raise HTTPException(status_code=400, detail=f"Sem permissão de escrita em {escolhido}.")

    escolhido = escolhido.resolve()
    config.gravar_data_dir(escolhido)

    # DATA_DIR foi resolvido no import e está espalhado por stores e pelo mount de /data. Quando a
    # escolha bate com o que já está em uso — o caso comum, a pasta pessoal — não há o que fazer.
    # Quando não bate, o processo se relança: é a única forma honesta de trocar tudo de uma vez.
    if escolhido == config.DATA_DIR:
        return {"caminho": str(escolhido), "reiniciar": False}

    if not config.CONGELADO:
        raise HTTPException(
            status_code=409,
            detail="Rodando do código-fonte, use a variável LOUVORJA_LITE_DATA_DIR para trocar de pasta.",
        )

    threading.Timer(0.5, _relancar).start()
    return {"caminho": str(escolhido), "reiniciar": True}


def _relancar() -> None:
    # O launcher já exportou a porta em LOUVORJA_LITE_PORT, e o processo novo herda o ambiente:
    # ele volta no mesmo endereço, então a aba aberta só precisa recarregar e a janela de projeção
    # no telão não perde a URL.
    os.execv(sys.executable, [sys.executable, *sys.argv[1:]])
