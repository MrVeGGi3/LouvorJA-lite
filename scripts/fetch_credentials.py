#!/usr/bin/env python3
"""Valida o acesso ao servidor de mídia: autoriza a conexão e baixa alguns arquivos de teste.

    python scripts/fetch_credentials.py            # só mostra a conexão
    python scripts/fetch_credentials.py --baixar   # baixa 3 arquivos e confere os tamanhos
"""

import argparse
import sqlite3
import sys
import tempfile
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import DB_PATH  # noqa: E402
from app.db.arquivos import caminho_remoto  # noqa: E402
from app.sync import louvorja_api  # noqa: E402

# Um mp3 comum, uma imagem e um nome com apóstrofo — o caractere que mais quebra URL.
SQL_AMOSTRA = """
    SELECT id_file, type, dir, file_name, size
    FROM files
    WHERE (type = 'image_music' AND id_file IN (SELECT id_file_image FROM musics WHERE id_file_image IS NOT NULL))
       OR (type = 'music' AND file_name LIKE '%Stavas%')
       OR (type = 'music' AND id_file IN (
              SELECT id_file_music FROM musics WHERE id_file_music IS NOT NULL
           ) AND size < 3000000)
    ORDER BY type, size
    LIMIT 3
"""


def _amostra() -> list[sqlite3.Row]:
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        return conn.execute(SQL_AMOSTRA).fetchall()
    finally:
        conn.close()


def _testar_resume(conexao, caminho: str) -> str:
    """Descobre se o servidor aceita retomar um download interrompido."""
    if conexao.is_ftp:
        return "FTP: REST testado no download real"
    req = urllib.request.Request(
        louvorja_api._url_http(conexao, caminho),
        headers={"User-Agent": louvorja_api.USER_AGENT, "Range": "bytes=100-199"},
    )
    with urllib.request.urlopen(req, timeout=louvorja_api.TIMEOUT) as resp:
        if resp.status == 206:
            return f"sim (206, Content-Range: {resp.headers.get('Content-Range')})"
        return f"NÃO — respondeu {resp.status}, o downloader terá que refazer arquivos parciais"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baixar", action="store_true", help="baixa 3 arquivos de teste")
    args = parser.parse_args()

    params = louvorja_api.obter_params()
    print(f"versão no servidor: {params.get('pt_version')} | banco: v{params.get('db_version')}")

    conexao = louvorja_api.obter_conexao(params)
    print(f"protocolo: {'FTP' if conexao.is_ftp else 'HTTPS'}")
    print(f"host: {conexao.host}  porta: {conexao.port or '(padrão)'}  root: {conexao.root!r}")
    print(f"usuário: {conexao.username or '(anônimo)'}  senha: {'*' * len(conexao.password)}")
    print(f"base: {conexao.base_url}")

    if not args.baixar:
        return

    arquivos = _amostra()
    if not arquivos:
        raise SystemExit("nenhum arquivo de amostra no banco — rode scripts/sync_data.py antes")

    print(f"\nresume: {_testar_resume(conexao, caminho_remoto(arquivos[0]['type'], arquivos[0]['dir'], arquivos[0]['file_name']))}")

    print("\nbaixando amostra:")
    with tempfile.TemporaryDirectory() as tmp:
        for arq in arquivos:
            remoto = caminho_remoto(arq["type"], arq["dir"], arq["file_name"])
            destino = Path(tmp) / arq["file_name"]
            tamanho = louvorja_api.baixar(conexao, remoto, destino, arq["size"])
            print(f"  OK {tamanho:>9,} bytes  {remoto}")

    print("\nTodos os tamanhos conferem com a tabela files.")


if __name__ == "__main__":
    main()
