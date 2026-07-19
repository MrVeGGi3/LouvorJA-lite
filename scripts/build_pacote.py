#!/usr/bin/env python3
"""Monta o pacote offline: o AppImage e a pasta `data/` lado a lado, prontos para o pendrive.

    python scripts/build_pacote.py --verificar     # confere o que já existe, sem construir
    python scripts/build_pacote.py                 # AppImage + pacote (assume data/ pronta)
    python scripts/build_pacote.py --baixar        # também baixa o que faltar (~15 GB)

O resultado é `dist/LouvorJA-Lite-<versão>/`. Copie a pasta inteira para o pendrive: o app acha a
`data/` porque ela está ao lado dele.
"""

import argparse
import os
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import DATA_DIR, DB_PATH, PROJECT_ROOT  # noqa: E402
from app.db.arquivos import arquivo_completo, caminho_local  # noqa: E402

VERSAO = "0.1.2"
APPIMAGE = PROJECT_ROOT / "dist" / "LouvorJA-Lite-x86_64.AppImage"

SQL_ESPERADOS = """
    SELECT f.id_file, f.type, f.dir, f.file_name, f.size
    FROM files f
    WHERE f.id_file IN (
            SELECT id_file_music FROM musics WHERE id_file_music IS NOT NULL
            UNION SELECT id_file_instrumental_music FROM musics WHERE id_file_instrumental_music IS NOT NULL
            UNION SELECT id_file_image FROM musics WHERE id_file_image IS NOT NULL
            UNION SELECT id_file_image FROM lyrics WHERE id_file_image IS NOT NULL
            UNION SELECT id_file_image FROM albums WHERE id_file_image IS NOT NULL
        )
"""

LEIAME = """LouvorJA Lite {versao}
=========================

Este pendrive tem tudo — o programa e as músicas. Não precisa de internet.

COMO USAR
---------
1. Copie a pasta inteira para o computador (ou rode direto do pendrive).
2. Dê dois cliques em LouvorJA-Lite-x86_64.AppImage.
   Se não abrir, marque como executável:
       chmod +x LouvorJA-Lite-x86_64.AppImage
3. O navegador abre na tela de controle. Clique em "Abrir Projeção", arraste a
   janela nova para o projetor e aperte F11.

IMPORTANTE
----------
A pasta "data" precisa ficar SEMPRE ao lado do AppImage — é onde estão o banco de
hinos e os arquivos de áudio. Se separar os dois, o programa não abre.

ATALHOS
-------
  seta direita / espaço ... próximo slide
  seta esquerda .......... slide anterior
  P ...................... tocar / pausar

CONTEÚDO
--------
  {arquivos} arquivos de mídia ({tamanho})
  Hinário Adventista, hinário de 1996 e as coletâneas — cantado e playback.

Formatação do pendrive: use exFAT. FAT32 funciona (nenhum arquivo passa de 4 GB),
mas copiar {tamanho} nele é bem mais lento.
"""


def formata_bytes(n: float) -> str:
    for unidade in ("B", "KB", "MB", "GB"):
        if abs(n) < 1024 or unidade == "GB":
            return f"{n:.1f} {unidade}"
        n /= 1024
    return f"{n:.1f} GB"


def esperados() -> list[sqlite3.Row]:
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        return conn.execute(SQL_ESPERADOS).fetchall()
    finally:
        conn.close()


def verificar(origem: Path) -> tuple[list[sqlite3.Row], list[sqlite3.Row]]:
    """Separa o que está íntegro do que falta — o pacote não pode sair pela metade."""
    completos, faltando = [], []
    for arq in esperados():
        caminho = caminho_local(origem, arq["type"], arq["dir"], arq["file_name"])
        if arquivo_completo(caminho, arq["size"]):
            completos.append(arq)
        else:
            faltando.append(arq)
    return completos, faltando


def rodar(comando: list[str]) -> None:
    print(f"\n==> {' '.join(str(c) for c in comando)}")
    subprocess.run(comando, check=True, cwd=PROJECT_ROOT)


def copiar_dados(origem: Path, destino: Path) -> None:
    """Hardlink quando dá (mesmo disco, custo zero); cópia de verdade quando não dá."""
    destino.mkdir(parents=True, exist_ok=True)
    try:
        shutil.copytree(
            origem, destino, dirs_exist_ok=True, copy_function=os.link,
            ignore=shutil.ignore_patterns("*.part", "_download_state.json", "projecao_estado.json"),
        )
        print("    (hardlink — não duplicou espaço em disco)")
    except OSError:
        shutil.copytree(
            origem, destino, dirs_exist_ok=True,
            ignore=shutil.ignore_patterns("*.part", "_download_state.json", "projecao_estado.json"),
        )
        print("    (cópia)")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--baixar", action="store_true", help="baixa a mídia que faltar antes de empacotar")
    parser.add_argument("--verificar", action="store_true", help="só confere o que já existe")
    parser.add_argument("--saida", type=Path, default=PROJECT_ROOT / "dist")
    args = parser.parse_args()

    if not DB_PATH.exists():
        raise SystemExit(f"database.db não encontrado em {DB_PATH}. Rode scripts/sync_data.py.")

    completos, faltando = verificar(DATA_DIR)
    total = len(completos) + len(faltando)
    bytes_ok = sum(a["size"] for a in completos)
    print(f"mídia: {len(completos)}/{total} arquivos completos ({formata_bytes(bytes_ok)})")

    if args.verificar:
        for arq in faltando[:10]:
            print(f"  falta: {arq['file_name']}")
        if len(faltando) > 10:
            print(f"  ... e mais {len(faltando) - 10}")
        return

    if faltando:
        if not args.baixar:
            raise SystemExit(
                f"\n{len(faltando)} arquivos ainda não foram baixados "
                f"({formata_bytes(sum(a['size'] for a in faltando))}).\n"
                "Rode com --baixar, ou rode scripts/download_media.py antes."
            )
        rodar([sys.executable, "scripts/download_media.py"])
        completos, faltando = verificar(DATA_DIR)
        if faltando:
            raise SystemExit(f"ainda faltam {len(faltando)} arquivos depois do download — veja _download_state.json")

    rodar(["bash", "scripts/build_appimage.sh"])
    if not APPIMAGE.exists():
        raise SystemExit(f"o AppImage não foi gerado em {APPIMAGE}")

    pacote = args.saida / f"LouvorJA-Lite-{VERSAO}"
    print(f"\n==> Montando {pacote}")
    if pacote.exists():
        shutil.rmtree(pacote)
    pacote.mkdir(parents=True)

    shutil.copy2(APPIMAGE, pacote / APPIMAGE.name)
    (pacote / APPIMAGE.name).chmod(0o755)
    print(f"    {APPIMAGE.name}")

    print("    data/ ...")
    copiar_dados(DATA_DIR, pacote / "data")

    (pacote / "LEIAME.txt").write_text(
        LEIAME.format(versao=VERSAO, arquivos=len(completos), tamanho=formata_bytes(bytes_ok)),
        encoding="utf-8",
    )

    finais, ausentes = verificar(pacote / "data")
    if ausentes:
        raise SystemExit(f"o pacote saiu incompleto: faltam {len(ausentes)} arquivos")

    print(f"\nOK — {pacote}")
    print(f"    {len(finais)} arquivos de mídia, {formata_bytes(bytes_ok)}")
    print("    Copie a pasta inteira para o pendrive (AppImage e data/ juntos).")


if __name__ == "__main__":
    main()
