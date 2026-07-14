#!/usr/bin/env python3
import argparse
import json
import shutil
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import DATA_DIR, DEFAULT_SOURCE_DIR  # noqa: E402

TABELAS_ESPERADAS = [
    "musics",
    "lyrics",
    "files",
    "albums",
    "albums_musics",
    "categories",
    "categories_albums",
]


def parse_args():
    parser = argparse.ArgumentParser(
        description="Importa/atualiza os dados do LouvorJA Desktop para o LouvorJA Lite."
    )
    parser.add_argument(
        "--source", type=Path, default=DEFAULT_SOURCE_DIR,
        help="Pasta config/ de uma instalação existente do LouvorJA Desktop",
    )
    parser.add_argument("--dest", type=Path, default=DATA_DIR, help="Pasta data/ do LouvorJA Lite")
    parser.add_argument(
        "--images", choices=["referenced", "full", "symlink", "none"], default="referenced",
        help="referenced=só o que o banco referencia (padrão), full=pastas inteiras, "
             "symlink=sem copiar (mesma máquina), none=pula imagens",
    )
    return parser.parse_args()


def validar_e_copiar_banco(source_db: Path, dest_db: Path) -> dict:
    if not source_db.exists():
        raise SystemExit(f"database.db não encontrado em {source_db}")

    dest_db.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest_db.with_suffix(".tmp")
    shutil.copy2(source_db, tmp)

    conn = sqlite3.connect(tmp)
    try:
        (resultado,) = conn.execute("PRAGMA integrity_check").fetchone()
        if resultado != "ok":
            tmp.unlink(missing_ok=True)
            raise SystemExit(f"database.db copiado falhou na verificação de integridade: {resultado}")
        tabelas = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    finally:
        conn.close()

    tmp.replace(dest_db)

    faltando = [t for t in TABELAS_ESPERADAS if t not in tabelas]
    return {"tables_found": sorted(tabelas), "tables_missing": faltando}


SQL_IMAGENS_REFERENCIADAS = """
    SELECT f.type, f.file_name
    FROM files f
    WHERE f.type IN ('image_album', 'image_music')
      AND f.id_file IN (
          SELECT id_file_image FROM musics WHERE id_file_image IS NOT NULL
          UNION SELECT id_file_image FROM lyrics WHERE id_file_image IS NOT NULL
          UNION SELECT id_file_image FROM albums WHERE id_file_image IS NOT NULL
      )
"""


def _arquivos_referenciados(dest_db: Path) -> tuple[set[str], set[str]]:
    conn = sqlite3.connect(f"file:{dest_db}?mode=ro", uri=True)
    capas: set[str] = set()
    imagens: set[str] = set()
    try:
        for tipo, file_name in conn.execute(SQL_IMAGENS_REFERENCIADAS):
            if not file_name:
                continue
            destino = capas if tipo == "image_album" else imagens
            destino.add(file_name)
    finally:
        conn.close()
    return capas, imagens


def _copiar_arquivo(origem: Path, destino: Path, modo: str) -> bool:
    if not origem.exists():
        return False
    if (
        destino.exists()
        and destino.stat().st_mtime == origem.stat().st_mtime
        and destino.stat().st_size == origem.stat().st_size
    ):
        return False

    destino.parent.mkdir(parents=True, exist_ok=True)
    if modo == "symlink":
        if destino.exists() or destino.is_symlink():
            destino.unlink()
        destino.symlink_to(origem)
    else:
        shutil.copy2(origem, destino)
    return True


def sincronizar_imagens(source_dir: Path, dest_db: Path, dest_capas: Path, dest_imagens: Path, modo: str) -> dict:
    if modo == "none":
        return {"capas_copied": 0, "imagens_copied": 0, "skipped_unchanged": 0}

    if modo == "full":
        nomes_capas = [p.name for p in (source_dir / "capas").glob("*") if p.is_file()]
        nomes_imagens = [p.name for p in (source_dir / "imagens").glob("*") if p.is_file()]
    else:
        nomes_capas, nomes_imagens = _arquivos_referenciados(dest_db)

    copiados = pulados = 0
    for nome in nomes_capas:
        if _copiar_arquivo(source_dir / "capas" / nome, dest_capas / nome, modo):
            copiados += 1
        else:
            pulados += 1
    capas_copiadas = copiados

    for nome in nomes_imagens:
        if _copiar_arquivo(source_dir / "imagens" / nome, dest_imagens / nome, modo):
            copiados += 1
        else:
            pulados += 1

    return {
        "capas_copied": capas_copiadas,
        "imagens_copied": copiados - capas_copiadas,
        "skipped_unchanged": pulados,
    }


def main():
    args = parse_args()
    source_db = args.source / "database.db"
    dest_db = args.dest / "database.db"

    print(f"Lendo de: {args.source}")
    print(f"Gravando em: {args.dest}")

    info_banco = validar_e_copiar_banco(source_db, dest_db)
    if info_banco["tables_missing"]:
        print(f"AVISO: tabelas esperadas não encontradas no banco: {info_banco['tables_missing']}")

    info_imagens = sincronizar_imagens(
        args.source, dest_db, args.dest / "capas", args.dest / "imagens", args.images
    )

    manifest = {
        "last_sync_at": datetime.now(timezone.utc).isoformat(),
        "source": str(args.source),
        "images_mode": args.images,
        "database": info_banco,
        **info_imagens,
    }
    (args.dest / "_manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print(
        f"OK — capas copiadas: {info_imagens['capas_copied']}, "
        f"imagens copiadas: {info_imagens['imagens_copied']}, "
        f"sem alteração: {info_imagens['skipped_unchanged']}"
    )


if __name__ == "__main__":
    main()
