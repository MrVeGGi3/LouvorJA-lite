"""Importa e atualiza o `database.db` — o catálogo de hinos, letras e arquivos.

O banco vem de uma instalação do LouvorJA Desktop (cópia local) ou do servidor oficial. Em ambos
os casos ele é validado numa cópia temporária antes de substituir o que já está em disco: uma
queda no meio do download nunca troca um banco bom por um truncado.
"""

import shutil
import sqlite3
from pathlib import Path

from app.sync import louvorja_api

# Nome do banco no servidor oficial (mesmo host das músicas). O catálogo em espanhol existe como
# es_database.db, mas o Lite só usa o português.
BANCO_REMOTO = "config/pt_database.db"

TABELAS_ESPERADAS = [
    "musics",
    "lyrics",
    "files",
    "albums",
    "albums_musics",
    "categories",
    "categories_albums",
]


class ErroDeCatalogo(RuntimeError):
    """O banco de origem não existe, está corrompido ou não tem as tabelas esperadas."""


def validar_e_copiar_banco(source_db: Path, dest_db: Path) -> dict:
    if not source_db.exists():
        raise ErroDeCatalogo(f"database.db não encontrado em {source_db}")

    dest_db.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest_db.with_suffix(".tmp")
    shutil.copy2(source_db, tmp)

    conn = sqlite3.connect(tmp)
    try:
        (resultado,) = conn.execute("PRAGMA integrity_check").fetchone()
        if resultado != "ok":
            tmp.unlink(missing_ok=True)
            raise ErroDeCatalogo(
                f"database.db copiado falhou na verificação de integridade: {resultado}"
            )
        tabelas = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    finally:
        conn.close()

    tmp.replace(dest_db)

    faltando = [t for t in TABELAS_ESPERADAS if t not in tabelas]
    return {"tables_found": sorted(tabelas), "tables_missing": faltando}


def baixar_banco_do_servidor(dest_db: Path, sessao: louvorja_api.Sessao | None = None) -> dict:
    """Baixa o banco do servidor oficial e o valida como o modo local faz.

    Baixa para um arquivo temporário e delega a validação/promoção a validar_e_copiar_banco, então
    uma queda no meio nunca substitui o banco bom por um truncado.
    """
    dest_db.parent.mkdir(parents=True, exist_ok=True)
    baixado = dest_db.with_suffix(".download")
    try:
        if sessao is not None:
            sessao.baixar(BANCO_REMOTO, baixado)
        else:
            with louvorja_api.Sessao() as propria:
                propria.baixar(BANCO_REMOTO, baixado)
        info = validar_e_copiar_banco(baixado, dest_db)
    finally:
        baixado.unlink(missing_ok=True)
    return info
