import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Query

from app.db.connection import get_db
from app.db.musicas import buscar_musicas, obter_musica
from app.db.slides import get_slides

router = APIRouter(prefix="/api/musicas", tags=["musicas"])


def _slide_para_api(slide: dict) -> dict:
    out = dict(slide)
    out.pop("imagem_arquivo", None)
    imagem_id = out.get("imagem_id")
    # Servir por id mantém nomes com acento e apóstrofo fora da URL.
    out["imagem_fundo"] = f"/api/imagem/{imagem_id}" if imagem_id else None
    return out


@router.get("/busca")
def busca(q: str = Query(default=""), conn: sqlite3.Connection = Depends(get_db)):
    return [dict(r) for r in buscar_musicas(conn, q)]


@router.get("/{id_music}/slides")
def slides(id_music: int, conn: sqlite3.Connection = Depends(get_db)):
    return [_slide_para_api(s) for s in get_slides(conn, id_music)]


@router.get("/{id_music}")
def detalhe(id_music: int, conn: sqlite3.Connection = Depends(get_db)):
    row = obter_musica(conn, id_music)
    if row is None:
        raise HTTPException(status_code=404, detail="Música não encontrada")
    return dict(row)
