import sqlite3

from fastapi import APIRouter, Depends

from app.db.albuns import listar_albuns, musicas_do_album
from app.db.connection import get_db

router = APIRouter(prefix="/api/albuns", tags=["albuns"])


@router.get("")
def listar(conn: sqlite3.Connection = Depends(get_db)):
    return [dict(r) for r in listar_albuns(conn)]


@router.get("/{album_id}/musicas")
def musicas(album_id: int, conn: sqlite3.Connection = Depends(get_db)):
    return [dict(r) for r in musicas_do_album(conn, album_id)]
