#!/usr/bin/env python3
"""Baixa as músicas e imagens do catálogo para `data/`.

    python scripts/download_media.py --dry-run          # o que seria baixado, e quanto pesa
    python scripts/download_media.py --album 712        # só o Hinário Adventista
    python scripts/download_media.py                    # o catálogo inteiro (~15 GB)

Idempotente: um arquivo já íntegro em disco não é rebaixado, então rodar de novo depois de uma
queda continua de onde parou (inclusive no meio de um arquivo).

A lógica de verdade mora em `app/sync/` — é de lá que a tela de download do app também a usa, e é
por isso que ela entra no bundle do AppImage. Este script é a porta de linha de comando para ela.
"""

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import DATA_DIR, DB_PATH  # noqa: E402
from app.db.arquivos import caminho_local, caminho_remoto  # noqa: E402
from app.sync import louvorja_api  # noqa: E402
from app.sync.midia import (  # noqa: E402
    formata_bytes,
    listar_arquivos,
    pendentes,
    salvar_estado,
)


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


def main() -> None:
    args = parse_args()
    dest = args.dest

    arquivos = listar_arquivos(DB_PATH, args.album, args.only)
    if not arquivos:
        raise SystemExit("nenhum arquivo a baixar — rode scripts/sync_data.py antes")

    faltando = pendentes(dest, arquivos)
    if args.limit:
        faltando = faltando[: args.limit]

    total_bytes = sum(a["size"] for a in faltando)
    print(f"catálogo: {len(arquivos)} arquivos ({formata_bytes(sum(a['size'] for a in arquivos))})")
    print(f"faltando: {len(faltando)} arquivos ({formata_bytes(total_bytes)})")

    if args.dry_run:
        for a in faltando[:10]:
            print(f"  {caminho_remoto(a['type'], a['dir'], a['file_name'])}")
        if len(faltando) > 10:
            print(f"  ... e mais {len(faltando) - 10}")
        return

    if not faltando:
        print("Nada a fazer — tudo já está em disco.")
        return

    baixados = 0
    bytes_baixados = 0
    falhas: list[dict] = []
    inicio = time.monotonic()

    with louvorja_api.Sessao() as sessao:
        print(f"conectado por {'FTP' if sessao.conexao.is_ftp else 'HTTPS'}\n")
        for i, a in enumerate(faltando, 1):
            remoto = caminho_remoto(a["type"], a["dir"], a["file_name"])
            destino = caminho_local(dest, a["type"], a["dir"], a["file_name"])
            rotulo = f"[{i}/{len(faltando)}]"
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
                salvar_estado(dest, len(arquivos), baixados, falhas)
            time.sleep(args.pausa)

    salvar_estado(dest, len(arquivos), baixados, falhas)
    print(f"\nOK — {baixados} arquivos, {formata_bytes(bytes_baixados)} em {(time.monotonic() - inicio) / 60:.1f} min")
    if falhas:
        print(f"{len(falhas)} falharam (registradas em _download_state.json) — rode de novo para retentar")


if __name__ == "__main__":
    main()
