#!/usr/bin/env python3
"""Baixa as músicas e imagens do catálogo para `data/`.

    python scripts/download_media.py --dry-run          # o que seria baixado, e quanto pesa
    python scripts/download_media.py --album 712        # só o Hinário Adventista
    python scripts/download_media.py                    # o catálogo inteiro (~15 GB)

Idempotente: um arquivo já íntegro em disco não é rebaixado, então rodar de novo depois de uma
queda continua de onde parou (inclusive no meio de um arquivo).
"""

import argparse
import json
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.config import DATA_DIR, DB_PATH  # noqa: E402
from app.db.arquivos import arquivo_completo, caminho_local, caminho_remoto  # noqa: E402

import louvorja_api  # noqa: E402  isort:skip

# Só os arquivos que alguma música, letra ou álbum de fato referencia. A tabela `files` tem mais
# do que isso (o catálogo em espanhol, por exemplo), e o manifesto legado ARQUIVOS_SISTEMA tem
# linhas duplicadas e com tamanho zero — nada disso entra por aqui.
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


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dest", type=Path, default=DATA_DIR, help="pasta data/ de destino")
    parser.add_argument(
        "--only", choices=["music", "image", "all"], default="all",
        help="music=só os mp3, image=só as imagens, all=tudo (padrão)",
    )
    parser.add_argument("--album", type=int, help="baixa apenas os arquivos de um álbum (ex: 712)")
    parser.add_argument("--limit", type=int, help="para depois de N arquivos (útil para testar)")
    parser.add_argument("--dry-run", action="store_true", help="lista o que falta, sem baixar")
    parser.add_argument(
        "--pausa", type=float, default=0.1,
        help="segundos entre arquivos, para não martelar o servidor (padrão: 0.1)",
    )
    return parser.parse_args()


def listar_arquivos(album: int | None, only: str) -> list[sqlite3.Row]:
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
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


def formata_bytes(n: int) -> str:
    for unidade in ("B", "KB", "MB", "GB"):
        if abs(n) < 1024 or unidade == "GB":
            return f"{n:.1f} {unidade}" if unidade != "B" else f"{n} B"
        n /= 1024
    return f"{n:.1f} GB"


def salvar_estado(dest: Path, arquivos: list, baixados: int, falhas: list) -> None:
    estado = {
        "atualizado_em": datetime.now(timezone.utc).isoformat(),
        "arquivos_no_catalogo": len(arquivos),
        "baixados_nesta_execucao": baixados,
        "falhas": falhas,
    }
    (dest / "_download_state.json").write_text(
        json.dumps(estado, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def main() -> None:
    args = parse_args()
    dest = args.dest

    arquivos = listar_arquivos(args.album, args.only)
    if not arquivos:
        raise SystemExit("nenhum arquivo a baixar — rode scripts/sync_data.py antes")

    pendentes = [
        a for a in arquivos
        if not arquivo_completo(
            caminho_local(dest, a["type"], a["dir"], a["file_name"]), a["size"]
        )
    ]
    if args.limit:
        pendentes = pendentes[: args.limit]

    total_bytes = sum(a["size"] for a in pendentes)
    print(f"catálogo: {len(arquivos)} arquivos ({formata_bytes(sum(a['size'] for a in arquivos))})")
    print(f"faltando: {len(pendentes)} arquivos ({formata_bytes(total_bytes)})")

    if args.dry_run:
        for a in pendentes[:10]:
            print(f"  {caminho_remoto(a['type'], a['dir'], a['file_name'])}")
        if len(pendentes) > 10:
            print(f"  ... e mais {len(pendentes) - 10}")
        return

    if not pendentes:
        print("Nada a fazer — tudo já está em disco.")
        return

    baixados = 0
    bytes_baixados = 0
    falhas: list[dict] = []
    inicio = time.monotonic()

    with louvorja_api.Sessao() as sessao:
        print(f"conectado por {'FTP' if sessao.conexao.is_ftp else 'HTTPS'}\n")
        for i, a in enumerate(pendentes, 1):
            remoto = caminho_remoto(a["type"], a["dir"], a["file_name"])
            destino = caminho_local(dest, a["type"], a["dir"], a["file_name"])
            rotulo = f"[{i}/{len(pendentes)}]"
            try:
                bytes_baixados += sessao.baixar(remoto, destino, a["size"])
                baixados += 1
                decorrido = time.monotonic() - inicio
                taxa = bytes_baixados / decorrido if decorrido else 0
                restante = (total_bytes - bytes_baixados) / taxa if taxa else 0
                print(
                    f"{rotulo} {a['file_name'][:52]:<52} "
                    f"{formata_bytes(a['size']):>9} | {formata_bytes(int(taxa))}/s | "
                    f"faltam ~{restante / 60:.0f} min"
                )
            except louvorja_api.ErroDeConexao as erro:
                falhas.append({"id_file": a["id_file"], "caminho": remoto, "erro": str(erro)})
                print(f"{rotulo} FALHOU {remoto}: {erro}")

            if i % 25 == 0:
                salvar_estado(dest, arquivos, baixados, falhas)
            time.sleep(args.pausa)

    salvar_estado(dest, arquivos, baixados, falhas)
    print(f"\nOK — {baixados} arquivos, {formata_bytes(bytes_baixados)} em {(time.monotonic() - inicio) / 60:.1f} min")
    if falhas:
        print(f"{len(falhas)} falharam (registradas em _download_state.json) — rode de novo para retentar")


if __name__ == "__main__":
    main()
