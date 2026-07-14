import sqlite3
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from app import config
from app.db.arquivos import arquivo_completo, caminho_local
from app.db.connection import get_db
from app.db.midia import audio_da_musica, obter_arquivo

router = APIRouter(prefix="/api", tags=["midia"])

TIPOS_MIME = {
    ".mp3": "audio/mpeg",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".bmp": "image/bmp",
}


def _resolver(conn: sqlite3.Connection, id_file: int, tipos: tuple[str, ...]) -> Path:
    arquivo = obter_arquivo(conn, id_file)
    if arquivo is None or arquivo["type"] not in tipos:
        raise HTTPException(status_code=404, detail="Arquivo não encontrado no catálogo")

    caminho = caminho_local(config.DATA_DIR, arquivo["type"], arquivo["dir"], arquivo["file_name"])

    # O id vem da URL: garantir que o caminho resolvido não escapa de data/ é barato.
    if not caminho.resolve().is_relative_to(config.DATA_DIR.resolve()):
        raise HTTPException(status_code=404, detail="Arquivo fora do diretório de dados")

    if not caminho.exists():
        raise HTTPException(
            status_code=404,
            detail=f"'{arquivo['file_name']}' ainda não foi baixado. "
                   "Rode scripts/download_media.py.",
        )
    return caminho


def _servir(caminho: Path) -> FileResponse:
    # O FileResponse do Starlette (>=0.45) responde Range com 206 sozinho — é o que faz o seek
    # da barra de progresso funcionar sem baixar o mp3 inteiro.
    return FileResponse(
        caminho,
        media_type=TIPOS_MIME.get(caminho.suffix.lower(), "application/octet-stream"),
    )


@router.get("/audio/{id_file}")
def audio(id_file: int, conn: sqlite3.Connection = Depends(get_db)):
    return _servir(_resolver(conn, id_file, ("music",)))


@router.get("/imagem/{id_file}")
def imagem(id_file: int, conn: sqlite3.Connection = Depends(get_db)):
    return _servir(_resolver(conn, id_file, ("image_music", "image_album")))


@router.get("/musicas/{id_music}/audio")
def audio_da_musica_endpoint(id_music: int, conn: sqlite3.Connection = Depends(get_db)):
    """Faixas de uma música e se elas já estão em disco.

    O app tem que funcionar sem os mp3 — quando o áudio não foi baixado, o player fica
    desabilitado em vez de quebrar a projeção.
    """
    linha = audio_da_musica(conn, id_music)
    if linha is None:
        raise HTTPException(status_code=404, detail="Música não encontrada")

    def faixa(id_file: int | None, duracao: str | None) -> dict | None:
        if not id_file:
            return None
        arquivo = obter_arquivo(conn, id_file)
        if arquivo is None:
            return None
        caminho = caminho_local(
            config.DATA_DIR, arquivo["type"], arquivo["dir"], arquivo["file_name"]
        )
        return {
            "id_file": id_file,
            "duracao": duracao,
            "disponivel": arquivo_completo(caminho, arquivo["size"]),
            "url": f"/api/audio/{id_file}",
        }

    return {
        "cantado": faixa(linha["id_file_music"], linha["duracao_cantado"]),
        "playback": faixa(linha["id_file_instrumental_music"], linha["duracao_playback"]),
    }
