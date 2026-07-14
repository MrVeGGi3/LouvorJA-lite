import sqlite3

from fastapi import APIRouter, Depends, Query

from app.db.connection import get_db
from app.db.hinario import buscar_hinario

router = APIRouter(prefix="/api/hinario", tags=["hinario"])


@router.get("")
def buscar(
    q: str = Query(default=""),
    edicao: str = Query(default="atual"),
    conn: sqlite3.Connection = Depends(get_db),
):
    return [dict(r) for r in buscar_hinario(conn, q, edicao)]
