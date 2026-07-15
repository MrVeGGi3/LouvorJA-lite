#!/usr/bin/env python3
import argparse
import json
import shutil
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.config import DATA_DIR, DEFAULT_SOURCE_DIR  # noqa: E402

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


def parse_args():
    parser = argparse.ArgumentParser(
        description="Importa/atualiza os dados do LouvorJA Desktop para o LouvorJA Lite."
    )
    parser.add_argument(
        "--source", type=Path, default=DEFAULT_SOURCE_DIR,
        help="Pasta config/ de uma instalação existente do LouvorJA Desktop",
    )
    parser.add_argument(
        "--do-servidor", action="store_true",
        help="Baixa o banco do servidor oficial (não precisa do LouvorJA Desktop). As imagens "
             "vêm depois com scripts/download_media.py.",
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


def baixar_banco_do_servidor(dest_db: Path) -> dict:
    """Baixa o banco do servidor oficial e o valida como o modo local faz.

    Baixa para um arquivo temporário e delega a validação/promoção a validar_e_copiar_banco, então
    uma queda no meio nunca substitui o banco bom por um truncado.
    """
    import louvorja_api  # importado aqui para não exigir rede quando se usa uma origem local

    dest_db.parent.mkdir(parents=True, exist_ok=True)
    baixado = dest_db.with_suffix(".download")
    print(f"Baixando o banco do servidor ({BANCO_REMOTO}) ...")
    conexao = louvorja_api.obter_conexao()
    try:
        louvorja_api.baixar(conexao, BANCO_REMOTO, baixado)
        info = validar_e_copiar_banco(baixado, dest_db)
    finally:
        baixado.unlink(missing_ok=True)
    return info


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
    dest_db = args.dest / "database.db"
    print(f"Gravando em: {args.dest}")

    if args.do_servidor:
        info_banco = baixar_banco_do_servidor(dest_db)
        origem = "servidor"
        # As imagens (capas/imagens) chegam com scripts/download_media.py, junto das músicas.
        info_imagens = {"capas_copied": 0, "imagens_copied": 0, "skipped_unchanged": 0}
    else:
        source_db = args.source / "database.db"
        print(f"Lendo de: {args.source}")
        info_banco = validar_e_copiar_banco(source_db, dest_db)
        origem = str(args.source)
        info_imagens = sincronizar_imagens(
            args.source, dest_db, args.dest / "capas", args.dest / "imagens", args.images
        )

    if info_banco["tables_missing"]:
        print(f"AVISO: tabelas esperadas não encontradas no banco: {info_banco['tables_missing']}")

    manifest = {
        "last_sync_at": datetime.now(timezone.utc).isoformat(),
        "source": origem,
        "images_mode": "servidor" if args.do_servidor else args.images,
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
