import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Query

from app.db.connection import get_db
from app.db.musicas import TIPOS_PADRAO, buscar_musicas, obter_musica
from app.db.slides import get_slides

router = APIRouter(prefix="/api/musicas", tags=["musicas"])


def _slide_para_api(slide: dict) -> dict:
    out = dict(slide)
    imagem = out.pop("imagem", None)
    out["imagem_fundo"] = f"/data/imagens/{imagem}" if imagem else None
    return out


@router.get("/busca")
def busca(
    q: str = Query(default=""),
    tipos: str = Query(default=",".join(TIPOS_PADRAO)),
    conn: sqlite3.Connection = Depends(get_db),
):
    tipos_tuple = tuple(t for t in tipos.split(",") if t)
    rows = buscar_musicas(conn, q, tipos_tuple)
    return [dict(r) for r in rows]


@router.get("/{origem}/{ref_id}/slides")
def slides(origem: str, ref_id: int, conn: sqlite3.Connection = Depends(get_db)):
    return [_slide_para_api(s) for s in get_slides(conn, origem, ref_id)]


@router.get("/{origem}/{ref_id}")
def detalhe(origem: str, ref_id: int, conn: sqlite3.Connection = Depends(get_db)):
    if origem != "MUSICAS":
        raise HTTPException(status_code=400, detail="Use /api/hinario para HINARIO_ADVENTISTA")
    row = obter_musica(conn, ref_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Música não encontrada")
    return dict(row)
