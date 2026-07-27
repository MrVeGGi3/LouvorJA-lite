"""Descobre o que o catálogo referencia, o que já está em disco e o que falta baixar.

Só entram aqui os arquivos que alguma música, letra ou álbum de fato referencia. A tabela `files`
tem mais do que isso (o catálogo em espanhol, por exemplo), e o manifesto legado ARQUIVOS_SISTEMA
tem linhas duplicadas e com tamanho zero — nada disso é baixado.
"""

import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path

from app.db.arquivos import arquivo_completo, caminho_local

ESTADO_ARQUIVO = "_download_state.json"

# Hinário Adventista: é o que a esmagadora maioria das igrejas usa, então ele vai fixado no topo
# da lista de álbuns em vez de perdido na ordem alfabética.
ALBUM_HINARIO = 712

SQL_ARQUIVOS = """
    SELECT f.id_file, f.type, f.dir, f.file_name, f.size
    FROM files f
    WHERE f.id_file IN (
            SELECT id_file_music FROM musics WHERE id_file_music IS NOT NULL
            UNION SELECT id_file_instrumental_music FROM musics WHERE id_file_instrumental_music IS NOT NULL
            UNION SELECT id_file_image FROM musics WHERE id_file_image IS NOT NULL
            UNION SELECT id_file_image FROM lyrics WHERE id_file_image IS NOT NULL
            UNION SELECT id_file_image FROM albums WHERE id_file_image IS NOT NULL
        )
    ORDER BY f.type, f.dir, f.file_name
"""

# Restringe a um álbum: as duas faixas (cantada e playback) das músicas dele, mais as imagens.
SQL_ARQUIVOS_DO_ALBUM = """
    SELECT f.id_file, f.type, f.dir, f.file_name, f.size
    FROM files f
    WHERE f.id_file IN (
            SELECT m.id_file_music FROM musics m
              JOIN albums_musics am ON am.id_music = m.id_music
             WHERE am.id_album = :album AND m.id_file_music IS NOT NULL
            UNION SELECT m.id_file_instrumental_music FROM musics m
              JOIN albums_musics am ON am.id_music = m.id_music
             WHERE am.id_album = :album AND m.id_file_instrumental_music IS NOT NULL
            UNION SELECT m.id_file_image FROM musics m
              JOIN albums_musics am ON am.id_music = m.id_music
             WHERE am.id_album = :album AND m.id_file_image IS NOT NULL
            UNION SELECT l.id_file_image FROM lyrics l
              JOIN albums_musics am ON am.id_music = l.id_music
             WHERE am.id_album = :album AND l.id_file_image IS NOT NULL
            UNION SELECT a.id_file_image FROM albums a
             WHERE a.id_album = :album AND a.id_file_image IS NOT NULL
        )
    ORDER BY f.type, f.dir, f.file_name
"""

# O mesmo vínculo arquivo↔álbum das duas consultas acima, mas de uma vez só para todos os álbuns.
# Fazer uma consulta por álbum custaria ~100 varreduras da tabela `files` toda vez que a tela de
# download abre.
SQL_ARQUIVOS_COM_ALBUM = """
    SELECT v.id_album, al.name AS titulo, f.id_file, f.type, f.dir, f.file_name, f.size
    FROM (
        SELECT am.id_album, m.id_file_music AS id_file
          FROM albums_musics am JOIN musics m ON m.id_music = am.id_music
        UNION SELECT am.id_album, m.id_file_instrumental_music
          FROM albums_musics am JOIN musics m ON m.id_music = am.id_music
        UNION SELECT am.id_album, m.id_file_image
          FROM albums_musics am JOIN musics m ON m.id_music = am.id_music
        UNION SELECT am.id_album, l.id_file_image
          FROM albums_musics am JOIN lyrics l ON l.id_music = am.id_music
        UNION SELECT a.id_album, a.id_file_image FROM albums a
    ) v
    JOIN albums al ON al.id_album = v.id_album
    JOIN files f ON f.id_file = v.id_file
    WHERE v.id_file IS NOT NULL
"""

SQL_ARQUIVO_UNICO = "SELECT id_file, type, dir, file_name, size FROM files WHERE id_file = ?"


def _conectar(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def listar_arquivos(db_path: Path, album: int | None = None, only: str = "all") -> list[sqlite3.Row]:
    conn = _conectar(db_path)
    try:
        if album:
            linhas = conn.execute(SQL_ARQUIVOS_DO_ALBUM, {"album": album}).fetchall()
        else:
            linhas = conn.execute(SQL_ARQUIVOS).fetchall()
    finally:
        conn.close()

    if only == "music":
        return [a for a in linhas if a["type"] == "music"]
    if only == "image":
        return [a for a in linhas if a["type"] != "music"]
    return linhas


def obter_arquivo(db_path: Path, id_file: int) -> sqlite3.Row | None:
    conn = _conectar(db_path)
    try:
        return conn.execute(SQL_ARQUIVO_UNICO, (id_file,)).fetchone()
    finally:
        conn.close()


def pendentes(dest: Path, arquivos: list[sqlite3.Row]) -> list[sqlite3.Row]:
    """Os que ainda não estão íntegros em disco — a lista que o download precisa percorrer."""
    return [
        a for a in arquivos
        if not arquivo_completo(caminho_local(dest, a["type"], a["dir"], a["file_name"]), a["size"])
    ]


def formata_bytes(n: int) -> str:
    for unidade in ("B", "KB", "MB", "GB"):
        if abs(n) < 1024 or unidade == "GB":
            return f"{n:.1f} {unidade}" if unidade != "B" else f"{n} B"
        n /= 1024
    return f"{n:.1f} GB"


def salvar_estado(dest: Path, total_no_catalogo: int, baixados: int, falhas: list) -> None:
    estado = {
        "atualizado_em": datetime.now(timezone.utc).isoformat(),
        "arquivos_no_catalogo": total_no_catalogo,
        "baixados_nesta_execucao": baixados,
        "falhas": falhas,
    }
    caminho = dest / ESTADO_ARQUIVO
    caminho.parent.mkdir(parents=True, exist_ok=True)
    tmp = caminho.with_suffix(".tmp")
    tmp.write_text(json.dumps(estado, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(caminho)


# ---------------------------------------------------------------------------
# Resumo para a tela de download
# ---------------------------------------------------------------------------

_cache_lock = threading.Lock()
_cache: dict | None = None


def invalidar_resumo() -> None:
    """Chamado quando um download termina — o que está em disco mudou."""
    global _cache
    with _cache_lock:
        _cache = None


def resumo(db_path: Path, dest: Path) -> dict:
    """Quanto do catálogo já está em disco, no total e por álbum.

    Um `stat()` por arquivo em ~4.756 arquivos é rápido num SSD e lento num pendrive, e a tela
    consulta isso a cada abertura — daí o cache, invalidado quando um download termina ou quando
    o próprio banco muda.
    """
    global _cache

    if not db_path.exists():
        return {
            "catalogo": {"total": 0, "prontos": 0, "bytes_total": 0, "bytes_prontos": 0},
            "albuns": [],
        }

    assinatura = (str(db_path), str(dest), db_path.stat().st_mtime_ns)
    with _cache_lock:
        if _cache is not None and _cache["assinatura"] == assinatura:
            return _cache["dados"]

    dados = _calcular_resumo(db_path, dest)
    with _cache_lock:
        _cache = {"assinatura": assinatura, "dados": dados}
    return dados


def _calcular_resumo(db_path: Path, dest: Path) -> dict:
    conn = _conectar(db_path)
    try:
        linhas = conn.execute(SQL_ARQUIVOS_COM_ALBUM).fetchall()
        catalogo = conn.execute(SQL_ARQUIVOS).fetchall()
    finally:
        conn.close()

    # Um mesmo arquivo pode aparecer em mais de um álbum (uma capa reaproveitada, por exemplo).
    # O stat() vai uma vez só por arquivo; a contagem por álbum consulta o resultado.
    estado_por_arquivo: dict[int, bool] = {}

    def completo(linha) -> bool:
        id_file = linha["id_file"]
        if id_file not in estado_por_arquivo:
            caminho = caminho_local(dest, linha["type"], linha["dir"], linha["file_name"])
            estado_por_arquivo[id_file] = arquivo_completo(caminho, linha["size"])
        return estado_por_arquivo[id_file]

    albuns: dict[int, dict] = {}
    for linha in linhas:
        alvo = albuns.setdefault(
            linha["id_album"],
            {
                "id_album": linha["id_album"],
                "titulo": linha["titulo"] or f"Álbum {linha['id_album']}",
                "total": 0, "prontos": 0, "bytes_total": 0, "bytes_prontos": 0,
            },
        )
        alvo["total"] += 1
        alvo["bytes_total"] += linha["size"]
        if completo(linha):
            alvo["prontos"] += 1
            alvo["bytes_prontos"] += linha["size"]

    total = prontos = bytes_total = bytes_prontos = 0
    for linha in catalogo:
        total += 1
        bytes_total += linha["size"]
        if completo(linha):
            prontos += 1
            bytes_prontos += linha["size"]

    ordenados = sorted(
        albuns.values(),
        key=lambda a: (a["id_album"] != ALBUM_HINARIO, a["titulo"].lower()),
    )
    return {
        "catalogo": {
            "total": total, "prontos": prontos,
            "bytes_total": bytes_total, "bytes_prontos": bytes_prontos,
        },
        "albuns": ordenados,
    }
